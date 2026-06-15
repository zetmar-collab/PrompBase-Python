#!/usr/bin/env python3
"""
Migruje kopię zapasową PrompBase (JSON) do formatu v2.6.

Wymaga sklonowanego repozytorium PrompBase-Python (import promptbase.py).
https://github.com/zetmar-collab/PrompBase-Python
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from promptbase import (  # noqa: E402
    APP_VERSION,
    DEFAULT_CHECKLIST,
    FORMATS,
    STATUSES,
    Prompt,
    suggest_ai_platform,
)

PLACEHOLDER_MAP = {
    "[temat]": "[TEMAT]",
    "[ilość]": "[ILOSC]",
    "{input}": "[INPUT]",
    "[TWÓJ TEKST TUTAJ]": "[TWOJ_TEKST_TUTAJ]",
}

MODEL_ALIASES = {
    "chatgpt": "GPT-5.5",
    "chat gpt": "GPT-5.5",
    "chatgpy": "GPT-5.5",
    "claude": "Claude Sonnet 4.6",
    "claude code": "Claude Sonnet 4.6",
}


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


def normalize_model(model: str) -> str:
    raw = (model or "").strip()
    if not raw:
        return ""
    key = raw.lower()
    if key in MODEL_ALIASES:
        return MODEL_ALIASES[key]
    suggested = suggest_ai_platform(raw)
    if suggested == "ChatGPT" and "gpt" not in raw.lower():
        return "GPT-5.5"
    if suggested == "Claude" and raw.lower() == "claude":
        return "Claude Sonnet 4.6"
    return raw


def clean_content(name: str, content: str) -> str:
    content = fix_placeholders(content)

    if name == "sprawdzanie kodu któtki":
        content = re.sub(r"\ngrafit\s*\n\+1\s*$", "", content, flags=re.IGNORECASE)

    if name == "kogucik":
        cut = content.find("## 1. Nazwa ciasteczka")
        if cut > 0:
            content = content[:cut].strip()
        dup = content.find(
            "Jesteś kreatywnym cukiernikiem",
            content.find("Jesteś kreatywnym cukiernikiem") + 1,
        )
        if dup > 0:
            content = content[:dup].strip()
        if content.startswith("Prompt "):
            content = content[7:].lstrip()

    return content.strip()


def clean_zastosowanie(name: str, zastosowanie: str, content: str) -> str:
    z = (zastosowanie or "").strip()
    if len(z) > 120 or z.startswith("Jesteś ") or "plan obiadowy" in z.lower():
        if "obiad" in name.lower() or "kucharz" in content.lower():
            return "kuchnia"
    return z[:200] if len(z) > 200 else z


def migrate_prompt(raw: dict) -> dict:
    name = str(raw.get("name") or "").strip()
    raw = dict(raw)
    raw["name"] = name
    raw["content"] = clean_content(name, str(raw.get("content") or ""))
    raw["status"] = str(raw.get("status") or "nowy").strip()
    if raw["status"] not in STATUSES:
        raw["status"] = "nowy"
    fmt = str(raw.get("format") or "tekst").strip()
    raw["format"] = fmt if fmt in FORMATS else "tekst"
    raw["model"] = normalize_model(str(raw.get("model") or ""))
    raw["zastosowanie"] = clean_zastosowanie(
        name, str(raw.get("zastosowanie") or ""), raw["content"]
    )
    prompt = Prompt.from_dict(raw)
    return prompt.to_dict()


def find_default_backup(prompty_dir: Path) -> Path | None:
    candidates = sorted(prompty_dir.glob("prompbase-backup-*.json"), reverse=True)
    return candidates[0] if candidates else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migruj kopię zapasową PrompBase do formatu v2.6 (nowe.json)."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        help="Plik kopii zapasowej JSON (domyślnie: najnowszy Prompty/prompbase-backup-*.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "Prompty" / "nowe.json",
        help="Plik wynikowy (domyślnie: Prompty/nowe.json)",
    )
    parser.add_argument(
        "--keep-source",
        action="store_true",
        help="Nie usuwaj pliku wejściowego po migracji",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    src = args.input
    if src is None:
        src = find_default_backup(ROOT / "Prompty")
    if src is None or not src.is_file():
        print("Brak pliku kopii. Podaj --input lub umieść prompbase-backup-*.json w Prompty/")
        sys.exit(1)

    dst: Path = args.output
    dst.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(src.read_text(encoding="utf-8-sig"))
    theme = str(data.get("theme") or "jasny")
    if theme not in ("jasny", "ciemny", "grafit"):
        theme = "jasny"

    checklist = dict(DEFAULT_CHECKLIST)
    if isinstance(data.get("checklist"), dict):
        checklist.update(
            {k: bool(v) for k, v in data["checklist"].items() if k in checklist}
        )

    cloud = data.get("cloud_folders") or {}
    prompts_out = [
        migrate_prompt(item)
        for item in data.get("prompts", [])
        if isinstance(item, dict)
    ]

    payload = {
        "version": APP_VERSION,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "n8n_url": str(data.get("n8n_url") or "").strip(),
        "theme": theme,
        "cloud_folders": {
            "google_drive": str(cloud.get("google_drive", "")).strip(),
            "onedrive": str(cloud.get("onedrive", "")).strip(),
        },
        "onboarding_done": bool(data.get("onboarding_done", True)),
        "checklist": checklist,
        "prompts": prompts_out,
    }

    dst.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not args.keep_source:
        src.unlink()
        print(f"Usunięto: {src.name}")

    print(f"Zapisano {len(prompts_out)} promptów -> {dst}")


if __name__ == "__main__":
    main()
