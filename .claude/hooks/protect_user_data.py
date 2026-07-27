#!/usr/bin/env python3
"""PreToolUse hook — chroni dane użytkownika PrompBase przed edycją.

Blokuje zapis/edycję plików biblioteki (`promptbase.json`), kopii `*.json.bak*`
oraz plików tymczasowych `*.json.tmp`, niezależnie od lokalizacji (repo lub
%APPDATA%\\PrompBase\\). Chroni przed przypadkowym nadpisaniem danych podczas
pracy asystenta.

Kontrakt hooka: czyta payload z stdin (JSON), zwraca kod 2 aby zablokować.
"""

from __future__ import annotations

import json
import sys
from pathlib import PurePath

BLOCKED_NAMES = {"promptbase.json"}


def _target_path(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    return tool_input.get("file_path") or tool_input.get("path") or ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0  # brak payloadu — nie blokujemy

    path = _target_path(payload)
    if not path:
        return 0

    name = PurePath(path).name
    lowered = name.lower()
    is_backup = ".json.bak" in lowered or lowered.endswith(".json.tmp")

    if name in BLOCKED_NAMES or is_backup:
        sys.stderr.write(
            "Zablokowano: plik danych użytkownika PrompBase "
            f"({name}) nie powinien być edytowany przez asystenta.\n"
            "To biblioteka promptów / kopia zapasowa — zmieniaj ją w aplikacji.\n"
        )
        return 2  # kod 2 => blokada operacji

    return 0


if __name__ == "__main__":
    sys.exit(main())
