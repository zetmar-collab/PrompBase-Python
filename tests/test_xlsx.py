"""Testy czytnika/zapisywacza XLSX (bez openpyxl — projekt jest stdlib-only)."""

from __future__ import annotations

import zipfile

import pytest

from pbcore import xlsx


def _make_xlsx(tmp_path, header, rows, name="wej.xlsx"):
    path = tmp_path / name
    xlsx.write_sheet(path, header, rows)
    return path


def test_round_trip_preserves_special_characters(tmp_path):
    """Emoji, znaki wymagające ucieczki w XML i wielolinijkowość muszą przeżyć."""
    header = ["Nazwa", "Prompt"]
    rows = [["Anime 🌸", "Treść z <tagiem> & \"cudzysłowem\"\ndruga linia"]]
    path = _make_xlsx(tmp_path, header, rows)

    back = xlsx.read_rows(path)
    assert back[0] == header
    assert back[1] == rows[0]


def test_written_file_is_a_valid_xlsx_zip(tmp_path):
    """Excel/LibreOffice wymagają kompletu części OOXML, nie samego arkusza."""
    path = _make_xlsx(tmp_path, ["A"], [["1"]])
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        assert "[Content_Types].xml" in names
        assert "_rels/.rels" in names
        assert "xl/workbook.xml" in names
        assert any(n.startswith("xl/worksheets/") for n in names)
        assert zf.testzip() is None


def test_map_headers_recognises_polish_and_english(tmp_path):
    mapping = xlsx.map_headers(["ID", "Styl", "Ikona", "Kategoria", "Numer", "Prompt"])
    assert mapping["id"] == 0
    assert mapping["tags"] == 1
    assert mapping["icon"] == 2
    assert mapping["zastosowanie"] == 3
    assert mapping["number"] == 4
    assert mapping["content"] == 5

    english = xlsx.map_headers(["Title", "Category", "Tags", "Content"])
    assert english["name"] == 0
    assert english["zastosowanie"] == 1
    assert english["content"] == 3


def test_missing_content_column_is_an_error(tmp_path):
    with pytest.raises(xlsx.XlsxError):
        xlsx.rows_to_prompt_dicts([["ID", "Kategoria"], ["a", "b"]])


def test_rows_to_prompt_dicts_builds_readable_names():
    rows = [
        ["ID", "Ikona", "Kategoria", "Numer", "Prompt"],
        ["anime-1", "🌸", "Anime – postacie", "1", "Wygeneruj postać"],
        ["", "", "", "", "Bez kategorii, sama treść"],
        ["x", "", "", "", ""],  # brak treści → pomijamy
    ]
    items, mapping = xlsx.rows_to_prompt_dicts(rows)
    assert mapping["content"] == 4
    assert len(items) == 2
    assert items[0]["name"] == "🌸 Anime – postacie #1"
    assert items[0]["comment"] == "ID: anime-1"
    assert items[1]["name"] == "Bez kategorii, sama treść"


def test_explicit_name_column_wins():
    rows = [
        ["Nazwa", "Kategoria", "Prompt"],
        ["Moja nazwa", "Anime", "treść"],
    ]
    items, _ = xlsx.rows_to_prompt_dicts(rows)
    assert items[0]["name"] == "Moja nazwa"


def test_categories_survive_import():
    rows = [
        ["Kategoria", "Prompt"],
        ["Anime", "a"],
        ["Krajobraz", "b"],
        ["Anime", "c"],
    ]
    items, _ = xlsx.rows_to_prompt_dicts(rows)
    assert {item["zastosowanie"] for item in items} == {"Anime", "Krajobraz"}


def test_dtd_declaration_is_rejected(tmp_path):
    """Ochrona przed 'billion laughs' — ElementTree sam tego nie blokuje.

    Sprawdzone empirycznie na Pythonie 3.12: XXE jest blokowane, ale bomba
    encyjna rozwija się bez ograniczeń, więc odrzucamy pliki z DTD.
    """
    bomb = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE lolz [<!ENTITY lol "lol">'
        b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;">]>'
        b"<worksheet><sheetData>&lol2;</sheetData></worksheet>"
    )
    path = tmp_path / "zly.xlsx"
    source = _make_xlsx(tmp_path, ["A"], [["1"]], name="zrodlo.xlsx")
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(path, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.startswith("xl/worksheets/"):
                data = bomb
            dst.writestr(info.filename, data)

    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(path)


def test_crafted_column_reference_is_rejected(tmp_path):
    """Regresja: adres komórki typu 'ZZZZZZZZ1' zawieszał import na stałe.

    `_column_index` liczyło z niego indeks 217 180 147 157, a `read_rows`
    próbowało dopisać tyle pustych komórek. Limity rozmiaru nie pomagały —
    plik ma 2 kB i jeden wiersz, a okno aplikacji zamarzało bez możliwości
    anulowania.
    """
    source = _make_xlsx(tmp_path, ["A"], [["1"]], name="zrodlo.xlsx")
    evil = tmp_path / "zly-adres.xlsx"
    sheet = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b'<sheetData><row r="1">'
        b'<c r="ZZZZZZZZ1" t="inlineStr"><is><t>x</t></is></c>'
        b"</row></sheetData></worksheet>"
    )
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(evil, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.startswith("xl/worksheets/"):
                data = sheet
            dst.writestr(info.filename, data)

    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(evil)


@pytest.mark.parametrize(
    "ref, expected",
    [("A1", 0), ("B7", 1), ("Z1", 25), ("AA1", 26), ("XFD1", 16383)],
)
def test_column_index_handles_real_references(ref, expected):
    assert xlsx._column_index(ref) == expected


@pytest.mark.parametrize("ref", ["XFE1", "ZZZZ1", "ZZZZZZZZ1"])
def test_column_index_rejects_out_of_range(ref):
    """Excel kończy się na kolumnie XFD — wszystko dalej to uszkodzony plik."""
    with pytest.raises(xlsx.XlsxError):
        xlsx._column_index(ref)


def test_oversized_archive_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(xlsx, "MAX_UNCOMPRESSED_BYTES", 100)
    path = _make_xlsx(tmp_path, ["A"], [["x" * 5000]])
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(path)


def test_not_a_zip_is_reported_clearly(tmp_path):
    path = tmp_path / "udaje.xlsx"
    path.write_text("to nie jest xlsx", encoding="utf-8")
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(path)


def test_export_header_matches_import_aliases():
    """Eksport musi dać się z powrotem zaimportować bez ręcznego mapowania."""
    mapping = xlsx.map_headers(xlsx.EXPORT_HEADER)
    assert "content" in mapping
    assert "name" in mapping
    assert "zastosowanie" in mapping


def test_export_round_trip_through_prompt_dicts(tmp_path):
    """Eksport prawdziwego Prompta i ponowny import muszą dać to samo.

    Używamy prawdziwej klasy Prompt, a nie atrapy — atrapa z własnym zestawem
    pól nie wyłapie zmiany nazwy pola w modelu (co się już zdarzyło).
    """
    from pbcore.models import Prompt

    prompt = Prompt(
        name="Test 🌸",
        content="Treść\nwieloliniowa",
        status="nowy",
        format="tekst",
        model="GPT",
        zastosowanie="Anime",
        tags="a, b",
        comment="uwaga",
    )
    rows = xlsx.prompts_to_rows([prompt], lambda s: s, str)
    path = tmp_path / "eksport.xlsx"
    xlsx.write_sheet(path, xlsx.EXPORT_HEADER, rows)

    items, _ = xlsx.rows_to_prompt_dicts(xlsx.read_rows(path))
    assert items[0]["name"] == "Test 🌸"
    assert items[0]["content"] == "Treść\nwieloliniowa"
    assert items[0]["zastosowanie"] == "Anime"
    assert items[0]["tags"] == "a, b"


def test_default_export_name_is_an_xlsx_file():
    assert xlsx.default_export_name().endswith(".xlsx")


def _multi_sheet_xlsx(path, first_target="worksheets/sheet3.xml"):
    """Skoroszyt, w którym pierwsza zakładka to NIE sheet1.xml."""
    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ct = "http://schemas.openxmlformats.org/package/2006/content-types"

    def sheet_xml(text):
        return (
            f'<?xml version="1.0"?><worksheet xmlns="{main}"><sheetData>'
            f'<row r="1"><c r="A1" t="inlineStr"><is><t>Prompt</t></is></c></row>'
            f'<row r="2"><c r="A2" t="inlineStr"><is><t>{text}</t></is></c></row>'
            f"</sheetData></worksheet>"
        ).encode()

    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", f'<?xml version="1.0"?><Types xmlns="{ct}">'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   "</Types>")
        z.writestr("_rels/.rels", f'<?xml version="1.0"?><Relationships xmlns="{ct.replace("content-types","relationships")}">'
                   '<Relationship Id="rId1" Type="x" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml",
                   f'<?xml version="1.0"?><workbook xmlns="{main}" xmlns:r="{rel}"><sheets>'
                   '<sheet name="Pierwsza" sheetId="1" r:id="rIdA"/>'
                   '<sheet name="Druga" sheetId="2" r:id="rIdB"/>'
                   "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   f'<Relationship Id="rIdA" Target="{first_target}"/>'
                   '<Relationship Id="rIdB" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml("NIEWLASCIWY"))
        z.writestr("xl/worksheets/sheet3.xml", sheet_xml("WLASCIWY"))
    return path


def test_reads_first_sheet_from_workbook_order(tmp_path):
    """Nazwa pliku nie określa kolejności — liczy się wpis w workbook.xml.

    Wcześniej brany był pierwszy plik alfabetycznie (sheet1.xml), więc
    skoroszyt z pierwszą zakładką w sheet3.xml importował się z innego arkusza.
    """
    path = _multi_sheet_xlsx(tmp_path / "wielo.xlsx")
    rows = xlsx.read_rows(path)
    assert rows[1][0] == "WLASCIWY"


def test_falls_back_when_relationships_are_broken(tmp_path):
    """Uszkodzone powiązania nie mogą wywrócić importu — wracamy do nazwy pliku."""
    path = _multi_sheet_xlsx(tmp_path / "zepsute.xlsx", first_target="worksheets/brak.xml")
    rows = xlsx.read_rows(path)
    assert rows[1][0] == "NIEWLASCIWY"  # sheet1.xml jako awaryjny wybór


# --- obejścia znalezione przez przegląd bezpieczeństwa ----------------------

_BOMB = (
    '<!DOCTYPE lolz [<!ENTITY lol "lol">'
    '<!ENTITY l2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
    '<!ENTITY l3 "&l2;&l2;&l2;&l2;&l2;&l2;&l2;&l2;&l2;&l2;">]>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<sheetData><row><c t="inlineStr"><is><t>&l3;</t></is></c></row></sheetData></worksheet>'
)


def _with_sheet(tmp_path, sheet_bytes, name):
    source = _make_xlsx(tmp_path, ["A"], [["1"]], name=f"src-{name}")
    out = tmp_path / name
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(out, "w") as dst:
        for info in src.infolist():
            data = src.read(info.filename)
            if info.filename.startswith("xl/worksheets/"):
                data = sheet_bytes
            dst.writestr(info.filename, data)
    return out


@pytest.mark.parametrize(
    "label, payload",
    [
        ("utf-8", _BOMB.encode("utf-8")),
        ("utf-8-bom", b"\xef\xbb\xbf" + _BOMB.encode("utf-8")),
        ("utf-16-le z BOM", b"\xff\xfe" + _BOMB.encode("utf-16-le")),
        ("utf-16-be z BOM", b"\xfe\xff" + _BOMB.encode("utf-16-be")),
        (
            "utf-16 z deklaracją",
            ('<?xml version="1.0" encoding="UTF-16"?>' + _BOMB).encode("utf-16"),
        ),
        (
            "latin-1",
            ('<?xml version="1.0" encoding="ISO-8859-1"?>' + _BOMB).encode("latin-1"),
        ),
    ],
)
def test_dtd_is_rejected_in_every_encoding(tmp_path, label, payload):
    """Regresja: filtr szukał bajtów „<!DOCTYPE", więc UTF-16 go omijał.

    W UTF-16 znaki są poprzeplatane zerami i wyrażenie regularne nic nie
    znajdowało, a parser nadal rozwijał encje. Odrzucenie musi działać na
    poziomie parsera, który widzi dokument tak samo jak ElementTree.
    """
    path = _with_sheet(tmp_path, payload, "enc.xlsx")
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(path)


def test_utf16_sheet_without_dtd_still_reads(tmp_path):
    """Poprawny arkusz w UTF-16 (Excel go nie zapisuje, ale to legalny XML)."""
    sheet = (
        '<?xml version="1.0" encoding="UTF-16"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Prompt</t></is></c></row>'
        '<row r="2"><c r="A2" t="inlineStr"><is><t>zażółć</t></is></c></row>'
        "</sheetData></worksheet>"
    ).encode("utf-16")
    rows = xlsx.read_rows(_with_sheet(tmp_path, sheet, "u16ok.xlsx"))
    assert rows[1][0] == "zażółć"


def test_comment_mentioning_doctype_is_not_a_false_positive(tmp_path):
    """Sam tekst „<!DOCTYPE" w komórce nie jest deklaracją DTD."""
    rows = [["Prompt"], ["napisz o <!DOCTYPE html> i <!ENTITY>"]]
    path = _make_xlsx(tmp_path, rows[0], rows[1:], name="tekst.xlsx")
    assert xlsx.read_rows(path)[1][0] == "napisz o <!DOCTYPE html> i <!ENTITY>"


def test_padding_cannot_amplify_memory(tmp_path, monkeypatch):
    """Regresja: kolumna XFD w każdym wierszu dopełniała 16 383 pustych komórek.

    Plik 1,4 MB z 20 tys. wierszy zajmował ok. 440 MB, a przy limicie
    100 tys. wierszy ok. 2,2 GB. Limit komórek liczy też dopełnienie.
    """
    monkeypatch.setattr(xlsx, "MAX_CELLS", 100_000)
    body = "".join(
        f'<row r="{i}"><c r="XFD{i}" t="inlineStr"><is><t>x</t></is></c></row>'
        for i in range(1, 50)
    )
    sheet = (
        '<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
        f'spreadsheetml/2006/main"><sheetData>{body}</sheetData></worksheet>'
    ).encode()
    with pytest.raises(xlsx.XlsxError):
        xlsx.read_rows(_with_sheet(tmp_path, sheet, "amp.xlsx"))


def test_normal_sheet_is_far_below_the_cell_limit():
    """Limit nie może ograniczać zwykłych arkuszy — typowa baza to kilka kolumn."""
    assert xlsx.MAX_CELLS >= xlsx.MAX_ROWS * 20
