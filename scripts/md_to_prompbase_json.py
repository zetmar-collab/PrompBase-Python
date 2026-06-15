#!/usr/bin/env python3
"""Konwertuje pakiet-promptow-cursor.md → JSON import PrompBase v2.6."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path

SRC = Path(r"C:\Users\Marek\Desktop\pakiet-promptow-cursor.md")
OUT_PROJECT = Path(__file__).resolve().parent.parent / "Prompty" / "pakiet-promptow-cursor.json"
OUT_DESKTOP = Path(r"C:\Users\Marek\Desktop\pakiet-promptow-cursor.json")

META = [
    {
        "zastosowanie": "Marketing i sprzedaż",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,sprzedaż,SaaS,CRO",
        "format": "tekst",
        "kontekst": "Opis, link lub screeny aplikacji: [OPIS_APLIKACJI]",
    },
    {
        "zastosowanie": "Marketing i sprzedaż",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,landing page,CRO",
        "format": "tekst",
        "kontekst": "URL lub treść landing page: [LANDING_PAGE]",
    },
    {
        "zastosowanie": "Product / UX",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,onboarding,UX",
        "format": "tekst",
        "kontekst": "Opis lub screeny onboardingu: [OPIS_ONBOARDINGU]",
    },
    {
        "zastosowanie": "Marketing i sprzedaż",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,pricing,monetyzacja",
        "format": "tekst",
        "kontekst": "Opis cennika lub plany: [OPIS_CENNIKA]",
    },
    {
        "zastosowanie": "Programowanie i DevOps",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,API,backend",
        "format": "kod",
        "kontekst": "Kod, endpointy lub opis API: [KOD_LUB_OPIS_API]",
    },
    {
        "zastosowanie": "Programowanie i DevOps",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,code review,architektura",
        "format": "kod",
        "kontekst": "Fragment kodu do review: [KOD]",
    },
    {
        "zastosowanie": "Product / UX",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,feature,product",
        "format": "tekst",
        "kontekst": "Opis proponowanego feature: [OPIS_FEATURE]",
    },
    {
        "zastosowanie": "Product / UX",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,startup,pomysl",
        "format": "tekst",
        "kontekst": "Opis pomysłu na aplikację: [OPIS_POMYSLU]",
    },
    {
        "zastosowanie": "Marketing i sprzedaż",
        "model": "GPT-5.5",
        "tags": "cursor,audyt,copywriting,positioning",
        "format": "tekst",
        "kontekst": "Teksty marketingowe do oceny: [TEKST_KOMUNIKACJI]",
    },
    {
        "zastosowanie": "Marketing i sprzedaż",
        "model": "Claude Sonnet 4.6",
        "tags": "cursor,audyt,GTM,sprzedaz",
        "format": "tekst",
        "kontekst": "Opis produktu i oferty: [OPIS_PRODUKTU]",
    },
]


def parse_prompts(md: str) -> list[tuple[str, str]]:
    pattern = re.compile(r"## \d+\. (.+?)\n\n```md\n(.*?)```", re.DOTALL)
    return [(m.group(1).strip(), m.group(2).strip()) for m in pattern.finditer(md)]


def build_content(body: str, kontekst: str) -> str:
    return f"## Kontekst\n{kontekst}\n\n## Zadanie\n{body}"


def main() -> None:
    md = SRC.read_text(encoding="utf-8")
    parsed = parse_prompts(md)
    if len(parsed) != 10:
        raise SystemExit(f"Oczekiwano 10 promptów, znaleziono {len(parsed)}")

    now_ms = int(datetime.now().timestamp() * 1000)
    prompts = []
    for i, ((title, body), meta) in enumerate(zip(parsed, META)):
        prompts.append(
            {
                "id": f"p_cursor_{i + 1:02d}_{uuid.uuid4().hex[:8]}",
                "name": title,
                "content": build_content(body, meta["kontekst"]),
                "status": "praca",
                "format": meta["format"],
                "model": meta["model"],
                "zastosowanie": meta["zastosowanie"],
                "tags": meta["tags"],
                "comment": "Pakiet promptów Cursor — import z pakiet-promptow-cursor.md",
                "pinned": False,
                "created": now_ms + i,
            }
        )

    payload = {
        "version": "2.6",
        "package": "Pakiet 10 promptów Cursor — audyt",
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "import_hint": "PrompBase → Plik → Szybki import JSON",
        "prompt_count": len(prompts),
        "prompts": prompts,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    OUT_PROJECT.parent.mkdir(parents=True, exist_ok=True)
    OUT_PROJECT.write_text(text, encoding="utf-8")
    OUT_DESKTOP.write_text(text, encoding="utf-8")
    print(f"Zapisano {len(prompts)} promptów:")
    print(f"  {OUT_PROJECT}")
    print(f"  {OUT_DESKTOP}")


if __name__ == "__main__":
    main()
