"""Regresja: każde wywołanie t('literał') w kodzie musi mieć wpis w katalogu.

Bez tego testu brakujący wpis w i18n._EN po cichu pokazuje polski tekst nawet
w trybie English — t() ma bezpieczny fallback (nie wywala aplikacji), ale to
oznacza, że dziura w tłumaczeniu jest niewidoczna, dopóki ktoś nie zobaczy jej
na ekranie. Wykryto to ręcznie po zainstalowaniu pakietu MSIX z prawdziwą
biblioteką promptów — ten test ma to wyłapywać automatycznie.

Sprawdzamy tylko wywołania t("literał") z pojedynczym stałym argumentem
(pomijamy t(zmienna) i t(f"...") — te nie są kluczami katalogu z definicji).
"""

from __future__ import annotations

import ast
from pathlib import Path

from pbcore import i18n

ROOT = Path(__file__).resolve().parent.parent
# Lista wykrywana automatycznie — przy sztywnym spisie nowy moduł UI
# (np. spell_ui.py) wchodził do programu z nieprzetłumaczonymi napisami,
# a test i tak świecił na zielono.
FILES = sorted(
    str(path.relative_to(ROOT)).replace("\\", "/")
    for path in (ROOT / "pbcore").glob("*.py")
)


def _literal_t_calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "t"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value
        ):
            keys.add(node.args[0].value)
    return keys


def test_every_t_call_has_a_catalog_entry():
    known = set(i18n._EN.keys()) | set(i18n._EN_VALUES.keys())
    missing: dict[str, list[str]] = {}
    for rel in FILES:
        for key in _literal_t_calls(ROOT / rel):
            if key not in known:
                missing.setdefault(key, []).append(rel)

    assert not missing, (
        f"{len(missing)} wywołań t('...') bez wpisu w katalogu i18n "
        f"(w trybie English pokażą się po polsku): {missing}"
    )
