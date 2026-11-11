"""Regresja: napisy widoczne dla użytkownika muszą przechodzić przez t().

test_i18n_coverage.py pilnuje, żeby każde t('literał') miało wpis w katalogu,
ale nie wykryje sytuacji odwrotnej — literału, który w ogóle nie został owinięty
w t(). Tak było z tytułem okna edycji promptu: `self.title("Edytuj prompt")`
pokazywał polski tekst w wersji angielskiej, mimo że tłumaczenie leżało gotowe
w katalogu. Ten test szuka polskich napisów przekazywanych do funkcji
ustawiających tekst w UI z pominięciem t().
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILES = sorted((ROOT / "pbcore").glob("*.py"))

# Wywołania, których argument trafia wprost na ekran.
UI_CALLS = {"title"}
# Argumenty nazwane, których wartość trafia wprost na ekran.
UI_KWARGS = {"text", "label", "title", "message"}

# Znaki występujące tylko po polsku — heurystyka „to jest tekst do tłumaczenia".
POLISH = set("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ")

# Napisy techniczne/markowe, które celowo zostają bez tłumaczenia.
ALLOWED = {
    "PrompBase",
}


def _is_translated(node: ast.AST) -> bool:
    """Czy węzeł to t(...) albo wyrażenie zbudowane z t(...)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "t":
            return True
    return False


def _looks_polish(value: str) -> bool:
    if value.strip() in ALLOWED or not value.strip():
        return False
    if set(value) & POLISH:
        return True
    # Polskie słowa bez diakrytyków, które i tak są tekstem UI.
    lowered = value.lower()
    return any(w in lowered for w in (" prompt", "prompt ", "nowy", "edytuj", "zapisz", "anuluj"))


def _offenders(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = ""
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id

        # 1) self.title("...") i podobne
        if name in UI_CALLS:
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if _looks_polish(arg.value):
                        found.append(f"{name}(): {arg.value!r}")
                elif not isinstance(arg, ast.Constant) and not _is_translated(arg):
                    for sub in ast.walk(arg):
                        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                            if _looks_polish(sub.value):
                                found.append(f"{name}(): {sub.value!r}")

        # 2) text=/label=/... z gołym polskim literałem
        for kw in node.keywords:
            if kw.arg not in UI_KWARGS:
                continue
            if _is_translated(kw.value):
                continue
            for sub in ast.walk(kw.value):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    if _looks_polish(sub.value):
                        found.append(f"{kw.arg}=: {sub.value!r}")
    return found


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_ui_strings_go_through_t(path: Path):
    offenders = _offenders(path)
    assert not offenders, (
        f"Napisy UI w {path.name} pominęły t() — w wersji angielskiej zobaczy je "
        f"użytkownik po polsku: {offenders}"
    )
