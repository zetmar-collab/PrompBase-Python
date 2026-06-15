#!/usr/bin/env python3
"""Buduje paczkę premium promptów zgodną z importem PrompBase v2.6."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTY_DIR = ROOT / "Prompty"
OUT_MASTER = PROMPTY_DIR / "premium-prompbase-v2.6.json"
OUT_PWA = PROMPTY_DIR / "premium-promptLibrary-pwa.json"

SOURCE_FILES = [
    "marketing.json",
    "marketing2.json",
    "marketing3.json",
    "programowanie.json",
    "programowanie2.json",
    "media.json",
]

PLACEHOLDER_MAP = {
    "[OPIS BIZNESU]": "[OPIS_BIZNESU]",
    "[JĘZYK]": "[JEZYK]",
    "[OPIS ZADANIA]": "[OPIS_ZADANIA]",
    "[OPIS MODUŁU]": "[OPIS_MODULU]",
    "[OPIS FUNKCJI]": "[OPIS_FUNKCJI]",
    "[FRAMEWORK TESTOWY]": "[FRAMEWORK_TESTOWY]",
    "[STARA WERSJA/FRAMEWORK]": "[STARA_WERSJA]",
    "[NOWA WERSJA/FRAMEWORK]": "[NOWA_WERSJA]",
    "[TECH STACK]": "[TECH_STACK]",
    "[NAZWA WZORCA]": "[NAZWA_WZORCA]",
    "[NARZĘDZIE CI]": "[NARZEDZIE_CI]",
    "[SERWIS A]": "[SERWIS_A]",
    "[SERWIS B]": "[SERWIS_B]",
    "[CALL TO ACTION]": "[CALL_TO_ACTION]",
    "[PRZYKŁAD]": "[PRZYKLAD]",
    "[DZIAŁANIE]": "[DZIALANIE]",
}

CATEGORY_META = {
    "marketing": {
        "zastosowanie": "Marketing i sprzedaż",
        "status": "praca",
        "model": "Claude Sonnet 4.6",
        "prefix": "premium,marketing",
        "context": (
            "- Opis biznesu / produktu: [OPIS_BIZNESU]\n"
            "- Grupa docelowa: [GRUPA_DOCLOWA]\n"
            "- Cel / kontekst (opcjonalnie): [CEL]"
        ),
        "format": (
            "Użyj nagłówków markdown (##). Listy punktowane tam, gdzie to czytelniejsze.\n"
            "Na końcu dodaj sekcję **Następne kroki** (3 konkretne działania)."
        ),
    },
    "programowanie": {
        "zastosowanie": "Programowanie i DevOps",
        "status": "praca",
        "model": "Claude Sonnet 4.6",
        "prefix": "premium,programowanie",
        "context": (
            "- Język / stack: [JEZYK] / [TECH_STACK]\n"
            "- Kod, błąd lub opis zadania: [KOD_LUB_OPIS]\n"
            "- Ograniczenia (opcjonalnie): [OGRANICZENIA]"
        ),
        "format": (
            "Struktura: podsumowanie → analiza → rekomendacje → przykładowy kod (jeśli dotyczy).\n"
            "Kod w blokach ``` z oznaczeniem języka. Krótkie komentarze przy nietypowych fragmentach."
        ),
    },
    "content": {
        "zastosowanie": "Content i social media",
        "status": "praca",
        "model": "GPT-5.5",
        "prefix": "premium,content,social media",
        "context": (
            "- Temat / nisza: [TEMAT]\n"
            "- Grupa docelowa: [GRUPA_DOCLOWA]\n"
            "- Platforma (opcjonalnie): [PLATFORMA]"
        ),
        "format": (
            "Hook → rozwinięcie → CTA. Przy scenariuszach video: kolumny Hook | Treść | Ujęcie | CTA.\n"
            "Teksty gotowe do wklejenia — bez meta-komentarzy o procesie tworzenia."
        ),
    },
}

COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
STRUCTURED_RE = re.compile(r"^## (Rola|Kontekst|Zadanie)", re.MULTILINE)
ROLE_RE = re.compile(r"^(Jesteś|Działasz jako|Jestem)[^.]+\.\s*", re.IGNORECASE)


def split_role(content: str) -> tuple[str, str]:
    match = ROLE_RE.match(content)
    if not match:
        return "", content
    return match.group(0).strip(), content[match.end() :].strip()


def enhance_content(content: str, category: str) -> str:
    content = fix_placeholders(content.strip())
    if STRUCTURED_RE.search(content):
        return content

    meta = CATEGORY_META.get(category, CATEGORY_META["marketing"])
    role, task_body = split_role(content)
    if not role:
        role = content.split(".")[0].strip() + "."
        task_body = content

    parts = [f"## Rola\n{role}\n"]

    if needs_context_block(content, category):
        parts.append(f"## Kontekst\n{meta['context']}\n")

    parts.append(f"## Zadanie\n{task_body}\n")
    parts.append(f"## Format odpowiedzi\n{meta['format']}\n")
    parts.append(
        "## Zasady\n"
        "- Odpowiadaj po polsku, konkretnie i bez lania wody.\n"
        "- Jeśli brakuje danych wejściowych, wypisz założenia przed wynikiem.\n"
        "- Unikaj ogólników — każda rekomendacja z krótkim uzasadnieniem."
    )
    return "\n".join(parts)


def fix_placeholders(text: str) -> str:
    for old, new in PLACEHOLDER_MAP.items():
        text = text.replace(old, new)

    def _norm(match: re.Match) -> str:
        inner = match.group(1)
        if re.fullmatch(r"[A-Za-z0-9_]+", inner):
            return match.group(0)
        fixed = re.sub(r"[^A-Za-z0-9_]+", "_", inner.strip()).strip("_").upper()
        return f"[{fixed}]" if fixed else match.group(0)

    return re.sub(r"\[([^\]]+)\]", _norm, text)


def needs_context_block(content: str, category: str) -> bool:
    known = {"OPIS_BIZNESU", "GRUPA_DOCLOWA", "TEMAT", "JEZYK", "KOD_LUB_OPIS", "TECH_STACK"}
    found = set(re.findall(r"\[([A-Za-z0-9_]+)\]", content))
    if category == "marketing":
        return not (found & {"OPIS_BIZNESU", "GRUPA_DOCLOWA"})
    if category == "programowanie":
        return not (found & {"JEZYK", "KOD_LUB_OPIS", "TECH_STACK"})
    if category == "content":
        return not (found & {"TEMAT"})
    return not found


def load_source(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig")
    raw = COMMENT_RE.sub("", raw)
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"{path.name}: oczekiwano tablicy promptów")
    return data


def merge_tags(item: dict, category: str) -> str:
    meta = CATEGORY_META.get(category, CATEGORY_META["marketing"])
    parts = [meta["prefix"]]
    if item.get("tags"):
        parts.append(str(item["tags"]).strip())
    if item.get("category") and item["category"] not in parts[0]:
        pass  # już w prefix
    return ",".join(dict.fromkeys(",".join(parts).split(",")))


def convert_item(item: dict, seq: int) -> dict:
    category = str(item.get("category") or "marketing").strip()
    meta = CATEGORY_META.get(category, CATEGORY_META["marketing"])
    title = str(item.get("title") or item.get("name") or f"Prompt {seq}").strip()
    content = str(item.get("content") or "").strip()

    return {
        "id": f"p_premium_{seq:03d}_{uuid.uuid4().hex[:6]}",
        "name": title,
        "content": enhance_content(content, category),
        "status": meta["status"],
        "format": "tekst",
        "model": meta["model"],
        "zastosowanie": meta["zastosowanie"],
        "tags": merge_tags(item, category),
        "comment": f"Paczka premium PrompBase | {category} | PL",
        "pinned": False,
    }


def main() -> None:
    all_items: list[dict] = []
    seq = 1
    for filename in SOURCE_FILES:
        path = PROMPTY_DIR / filename
        if not path.is_file():
            print(f"Pominięto (brak pliku): {filename}")
            continue
        for item in load_source(path):
            all_items.append(convert_item(item, seq))
            seq += 1

    # Sort: marketing → programowanie → content, potem alfabetycznie
    order = {"Marketing i sprzedaż": 0, "Programowanie i DevOps": 1, "Content i social media": 2}
    all_items.sort(key=lambda p: (order.get(p["zastosowanie"], 9), p["name"].lower()))

    master = {
        "version": "2.6",
        "package": "PrompBase Premium PL",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "prompt_count": len(all_items),
        "import_hint": "PrompBase → Plik → Szybki import pliku CSV/JSON → wybierz ten plik",
        "prompts": all_items,
    }

    OUT_MASTER.write_text(json.dumps(master, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_PWA.write_text(json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8")

    by_cat: dict[str, int] = {}
    for p in all_items:
        by_cat[p["zastosowanie"]] = by_cat.get(p["zastosowanie"], 0) + 1

    print(f"Zapisano {len(all_items)} promptów:")
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat}: {n}")
    print(f"  -> {OUT_MASTER.name}")
    print(f"  -> {OUT_PWA.name}")


if __name__ == "__main__":
    main()
