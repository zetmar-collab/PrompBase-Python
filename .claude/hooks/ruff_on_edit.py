#!/usr/bin/env python3
"""PostToolUse hook — uruchamia ruff na właśnie edytowanym pliku .py.

Lint tylko dla zmienionego pliku Pythona; wynik trafia do asystenta jako
informacja (nie blokuje). Jeśli ruff nie jest zainstalowany, hook milczy.
"""

from __future__ import annotations

import json
import subprocess
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not path.endswith(".py"):
        return 0

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", path],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return 0

    if result.returncode != 0:
        sys.stderr.write("ruff zgłosił uwagi:\n" + (result.stdout or result.stderr))
        # Nie blokujemy edycji (kod 0), tylko informujemy.
    return 0


if __name__ == "__main__":
    sys.exit(main())
