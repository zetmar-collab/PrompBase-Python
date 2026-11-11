"""Import i eksport XLSX bez zależności zewnętrznych (stdlib: zipfile + XML).

XLSX to archiwum ZIP z plikami XML w środku, więc czytamy i zapisujemy je
samodzielnie — runtime aplikacji pozostaje stdlib-only (patrz .cursorrules).

Bezpieczeństwo (plik pochodzi od użytkownika, więc traktujemy go jak dane
niezaufane):

* **DTD odrzucane** — `xml.etree.ElementTree` w Pythonie 3.12 nie rozwija
  encji zewnętrznych (XXE jest zablokowane), ale ROZWIJA encje wewnętrzne,
  czyli jest podatny na „billion laughs" (wykładnicze rozwijanie encji =
  DoS pamięciowy). Sprawdzone empirycznie. Arkusze z Excela, LibreOffice
  czy Google Sheets nigdy nie zawierają DTD, więc odrzucenie deklaracji
  `<!DOCTYPE`/`<!ENTITY` zamyka ten wektor bez utraty zgodności.
* **Limit rozmiaru po dekompresji** — chroni przed zip-bombą (mały .xlsx
  rozpakowujący się do gigabajtów).
"""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.parsers import expat

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": NS_MAIN}

# Limity ochronne przy czytaniu niezaufanego pliku.
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024  # 200 MB łącznie po dekompresji
MAX_ROWS = 100_000
# Excel kończy się na kolumnie XFD (16384). Adres spoza tego zakresu oznacza
# uszkodzony lub spreparowany plik — bez tego limitu `read_rows` próbowało
# dopisać miliardy pustych komórek i aplikacja zawieszała się na stałe.
MAX_COLUMNS = 16_384
# Limit wszystkich komórek w arkuszu LICZONY RAZEM Z DOPEŁNIENIEM. Sam limit
# wierszy nie wystarcza: komórka w kolumnie XFD dopełnia 16 383 puste komórki,
# więc plik 1,4 MB z 20 tys. wierszy zajmował ok. 440 MB (przy 100 tys. wierszy
# ok. 2,2 GB). 5 mln komórek to ponad 50 razy więcej niż zwykła baza promptów.
MAX_CELLS = 5_000_000



class XlsxError(Exception):
    """Błąd odczytu/zapisu pliku XLSX (komunikat gotowy dla użytkownika)."""


# --- czytanie --------------------------------------------------------------


class _DtdFound(Exception):
    """Dokument zawiera deklarację DOCTYPE."""


class _RootReached(Exception):
    """Doszliśmy do elementu głównego bez DOCTYPE — dalej nie ma po co czytać."""


def _reject_dtd(data: bytes) -> None:
    """Odrzuca dokument z deklaracją DTD, patrząc na niego jak parser.

    Wcześniej filtr szukał w bajtach napisu `<!DOCTYPE`, ale w UTF-16 znaki są
    poprzeplatane zerami i takie dokumenty go omijały, a ElementTree nadal
    rozwijał encje (billion laughs). Tu używamy tego samego parsera expat, który
    stoi pod ElementTree, więc dekodowanie jest identyczne dla każdego kodowania.

    DOCTYPE musi stać przed elementem głównym, więc przerywamy odczyt na
    pierwszym elemencie — zwykły arkusz nie jest przez to parsowany dwa razy.
    """
    parser = expat.ParserCreate()

    def on_doctype(*_args):
        raise _DtdFound

    def on_root(*_args):
        raise _RootReached

    parser.StartDoctypeDeclHandler = on_doctype
    parser.StartElementHandler = on_root
    try:
        parser.Parse(data, True)
    except _DtdFound:
        raise XlsxError(
            "Plik zawiera deklarację DTD, której poprawne arkusze nie używają. "
            "Odrzucono ze względów bezpieczeństwa."
        ) from None
    except _RootReached:
        return
    except expat.ExpatError as exc:
        raise XlsxError(f"Uszkodzony XML w pliku XLSX: {exc}") from exc


def _safe_xml(data: bytes) -> ET.Element:
    """Parsuje XML po odrzuceniu deklaracji DTD (ochrona przed billion laughs)."""
    _reject_dtd(data)
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise XlsxError(f"Uszkodzony XML w pliku XLSX: {exc}") from exc


def _read_member(zf: zipfile.ZipFile, name: str) -> bytes:
    info = zf.getinfo(name)
    if info.file_size > MAX_UNCOMPRESSED_BYTES:
        raise XlsxError("Plik po rozpakowaniu jest zbyt duży (możliwa zip-bomba).")
    return zf.read(name)


def _column_index(ref: str) -> int:
    """'B7' -> 1 (indeks kolumny liczony od zera).

    Odrzuca adresy spoza zakresu Excela. Litery sprawdzamy jeszcze przed
    liczeniem, bo sama długość wystarczy, żeby wynik urósł do miliardów.
    """
    letters = "".join(ch for ch in ref if ch.isalpha())
    if not letters or len(letters) > 3:
        raise XlsxError(f"Nieprawidłowy adres komórki w arkuszu: {ref!r}")
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch.upper()) - ord("A") + 1)
    if index > MAX_COLUMNS:
        raise XlsxError(f"Adres komórki poza zakresem arkusza: {ref!r}")
    return index - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = _safe_xml(_read_member(zf, "xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall("m:si", NS):
        out.append("".join(node.text or "" for node in si.iter(f"{{{NS_MAIN}}}t")))
    return out


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.get("t")
    if kind == "inlineStr":
        is_el = cell.find("m:is", NS)
        if is_el is None:
            return ""
        return "".join(node.text or "" for node in is_el.iter(f"{{{NS_MAIN}}}t"))
    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return ""
    if kind == "s":
        try:
            return shared[int(value.text)]
        except (ValueError, IndexError):
            return ""
    return value.text


def _first_sheet_path(zf: zipfile.ZipFile) -> str:
    """Ścieżka pierwszego arkusza wg kolejności ze skoroszytu.

    Nazwa pliku nie mówi nic o kolejności — pierwszą zakładką może być
    `sheet3.xml`. Kolejność trzyma `xl/workbook.xml`, a powiązanie
    identyfikatora z plikiem `xl/_rels/workbook.xml.rels`. Gdy którejś
    części brakuje, wracamy do wyboru po nazwie pliku.
    """
    names = zf.namelist()
    try:
        workbook = _safe_xml(_read_member(zf, "xl/workbook.xml"))
        rels = _safe_xml(_read_member(zf, "xl/_rels/workbook.xml.rels"))
        targets = {
            rel.get("Id"): (rel.get("Target") or "").lstrip("/")
            for rel in rels
            if rel.get("Id")
        }
        for sheet in workbook.iter(f"{{{NS_MAIN}}}sheet"):
            rid = sheet.get(f"{{{NS_REL}}}id")
            target = targets.get(rid, "")
            if not target:
                continue
            candidate = target if target.startswith("xl/") else f"xl/{target}"
            if candidate in names:
                return candidate
    except (XlsxError, KeyError):
        pass  # uszkodzony lub niekompletny skoroszyt — próbujemy po nazwie

    sheets = sorted(n for n in names if n.startswith("xl/worksheets/sheet"))
    if not sheets:
        raise XlsxError("W pliku XLSX nie znaleziono żadnego arkusza.")
    return sheets[0]


def read_rows(path: Path | str) -> list[list[str]]:
    """Zwraca wiersze pierwszego arkusza jako listy tekstów (puste = '')."""
    try:
        with zipfile.ZipFile(path) as zf:
            total = sum(i.file_size for i in zf.infolist())
            if total > MAX_UNCOMPRESSED_BYTES:
                raise XlsxError("Plik po rozpakowaniu jest zbyt duży (możliwa zip-bomba).")

            shared = _shared_strings(zf)
            sheet = _safe_xml(_read_member(zf, _first_sheet_path(zf)))

            rows: list[list[str]] = []
            total_cells = 0
            for row in sheet.iter(f"{{{NS_MAIN}}}row"):
                if len(rows) >= MAX_ROWS:
                    break
                cells: list[str] = []
                for cell in row.findall("m:c", NS):
                    ref = cell.get("r") or ""
                    # Część generatorów pomija atrybut `r` albo zapisuje go bez
                    # części literowej — wtedy pozycja wynika z kolejności.
                    has_letters = any(ch.isalpha() for ch in ref)
                    idx = _column_index(ref) if has_letters else len(cells)
                    # Dopełnienie liczy się do limitu — inaczej jedna komórka
                    # w kolumnie XFD mnożyłaby pamięć w każdym wierszu.
                    total_cells += max(idx + 1 - len(cells), 1)
                    if total_cells > MAX_CELLS:
                        raise XlsxError(
                            "Arkusz jest zbyt duży (za dużo komórek) — import przerwano."
                        )
                    while len(cells) < idx:
                        cells.append("")
                    cells.append(_cell_value(cell, shared))
                rows.append(cells)
            return rows
    except zipfile.BadZipFile as exc:
        raise XlsxError("To nie jest poprawny plik XLSX (uszkodzone archiwum).") from exc
    except OSError as exc:
        raise XlsxError(f"Nie można odczytać pliku: {exc}") from exc


# --- mapowanie kolumn na prompty ------------------------------------------

# Nagłówki rozpoznawane dla każdego pola. Obsługujemy zarówno format własny
# PrompBase (eksport CSV/XLSX), jak i zewnętrzne bazy promptów z kategoriami
# (np. kolumny ID / Styl / Ikona / Kategoria / Numer / Prompt).
HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "content": ("treść promptu", "tresc promptu", "treść", "tresc", "prompt", "content", "text"),
    "name": ("nazwa", "name", "tytuł", "tytul", "title"),
    "zastosowanie": ("zastosowanie", "kategoria", "category", "use case", "grupa"),
    "tags": ("tagi", "tags", "styl", "style", "tag"),
    "model": ("model ai", "model", "ai model"),
    "status": ("status",),
    "format": ("format",),
    "comment": ("komentarz", "comment", "wskazówka", "wskazowka", "notes", "uwagi"),
    "icon": ("ikona", "icon", "emoji"),
    "number": ("numer", "number", "nr", "lp", "lp."),
    "id": ("id", "identyfikator"),
}


def map_headers(header_row: list[str]) -> dict[str, int]:
    """Dopasowuje nagłówki do pól promptu; zwraca {pole: indeks kolumny}."""
    mapping: dict[str, int] = {}
    for idx, raw in enumerate(header_row):
        key = (raw or "").strip().lower()
        if not key:
            continue
        for field, aliases in HEADER_ALIASES.items():
            if field in mapping:
                continue
            if key in aliases:
                mapping[field] = idx
                break
    return mapping


def _cell(row: list[str], idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ""
    return (row[idx] or "").strip()


def build_name(row: list[str], mapping: dict[str, int], content: str) -> str:
    """Nazwa promptu: kolumna nazwy → ikona+kategoria+numer → początek treści.

    Zewnętrzne bazy często nie mają kolumny „Nazwa", a samo ID (`anime-1`)
    nic nie mówi na liście — dlatego składamy czytelną etykietę z kategorii
    i numeru, a w ostateczności bierzemy początek treści.
    """
    explicit = _cell(row, mapping.get("name"))
    if explicit:
        return explicit

    icon = _cell(row, mapping.get("icon"))
    category = _cell(row, mapping.get("zastosowanie"))
    number = _cell(row, mapping.get("number"))
    if category:
        label = f"{category} #{number}" if number else category
        return f"{icon} {label}".strip()

    identifier = _cell(row, mapping.get("id"))
    if identifier:
        return identifier

    first_line = content.strip().splitlines()[0] if content.strip() else ""
    return (first_line[:60] + "…") if len(first_line) > 60 else (first_line or "Prompt")


def rows_to_prompt_dicts(rows: list[list[str]]) -> tuple[list[dict], dict[str, int]]:
    """Zamienia wiersze arkusza na słowniki zgodne z `Prompt.from_dict`.

    Zwraca (lista_słowników, mapowanie_nagłówków). Wiersze bez treści są
    pomijane — bez treści prompt jest bezużyteczny.
    """
    if not rows:
        return [], {}

    mapping = map_headers(rows[0])
    if "content" not in mapping:
        raise XlsxError(
            "Nie znaleziono kolumny z treścią promptu. "
            "Nagłówek powinien zawierać jedną z kolumn: Prompt, Treść Promptu, Content."
        )

    out: list[dict] = []
    for row in rows[1:]:
        content = _cell(row, mapping.get("content"))
        if not content:
            continue
        item: dict[str, str] = {
            "name": build_name(row, mapping, content),
            "content": content,
        }
        for field in ("zastosowanie", "tags", "model", "status", "format", "comment"):
            value = _cell(row, mapping.get(field))
            if value:
                item[field] = value
        # ID ze źródła zachowujemy w komentarzu — ułatwia późniejsze
        # dopasowanie do oryginalnego arkusza.
        source_id = _cell(row, mapping.get("id"))
        if source_id and not item.get("comment"):
            item["comment"] = f"ID: {source_id}"
        out.append(item)
    return out, mapping


# --- zapis -----------------------------------------------------------------


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _strip_illegal(text: str) -> str:
    """Usuwa znaki sterujące niedozwolone w XML 1.0 (poza \\t \\n \\r)."""
    return "".join(
        ch for ch in str(text) if ch in "\t\n\r" or ord(ch) >= 32 or ord(ch) == 9
    )


def _column_letter(index: int) -> str:
    """0 -> 'A', 26 -> 'AA'."""
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


def write_sheet(path: Path | str, header: list[str], rows: list[list[str]], sheet_name: str = "Prompty") -> None:
    """Zapisuje minimalny, ale poprawny plik XLSX (jeden arkusz, inline strings)."""
    all_rows = [header, *rows]

    body = []
    for r_idx, row in enumerate(all_rows, start=1):
        cells = []
        for c_idx, value in enumerate(row):
            ref = f"{_column_letter(c_idx)}{r_idx}"
            text = _escape(_strip_illegal(value if value is not None else ""))
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>')
        body.append(f'<row r="{r_idx}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{NS_MAIN}"><sheetData>{"".join(body)}</sheetData></worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{NS_MAIN}" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{_escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    try:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("xl/workbook.xml", workbook_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    except OSError as exc:
        raise XlsxError(f"Nie można zapisać pliku: {exc}") from exc


# Kolumny eksportu — zgodne z eksportem CSV, żeby oba formaty się pokrywały.
EXPORT_HEADER = [
    "Nazwa",
    "Status",
    "Format",
    "Model AI",
    "Zastosowanie",
    "Tagi",
    "Data Utworzenia",
    "Komentarz",
    "Treść Promptu",
]


def prompts_to_rows(prompts, status_label, format_date, format_label=None) -> list[list[str]]:
    """Buduje wiersze eksportu z listy promptów.

    `status_label` i `format_label` decydują, w jakim języku trafią do
    pliku etykiety statusu i formatu. Import rozpoznaje oba zapisy.
    """
    format_label = format_label or (lambda value: value)
    rows = []
    for prompt in prompts:
        rows.append(
            [
                prompt.name,
                status_label(prompt.status),
                format_label(prompt.format),
                prompt.model,
                prompt.zastosowanie,
                prompt.tags,
                format_date(prompt.created),
                prompt.comment,
                prompt.content,
            ]
        )
    return rows


def default_export_name() -> str:
    return f"prompbase-{datetime.now().strftime('%Y%m%d')}.xlsx"
