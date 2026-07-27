#!/usr/bin/env python3
"""PrompBase — punkt wejścia i re-eksport publicznego API.

Logika i UI mieszkają w pakiecie pbcore/. Ten moduł zachowuje
kompatybilność: `import promptbase` udostępnia dotychczasowe nazwy,
a `python promptbase.py` uruchamia aplikację.
"""
from __future__ import annotations

from pbcore.app import *  # noqa: F401,F403
from pbcore.app import main
from pbcore.core import *  # noqa: F401,F403
from pbcore.dialogs import *  # noqa: F401,F403
from pbcore.models import *  # noqa: F401,F403

if __name__ == "__main__":
    main()
