"""Nieudany zapis biblioteki musi być widoczny, a nie cichy.

`PromptStore.save()` jest atomowy, ale przy pełnym dysku albo pliku
zablokowanym przez inny program rzuca wyjątkiem. Wcześniej leciał on
z 18 miejsc prosto do Tk — użytkownik tracił zmianę, nie wiedząc o tym.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import promptbase as pb
from pbcore import app as app_module

ROOT = Path(__file__).resolve().parent.parent


class _Store:
    def __init__(self, exc=None):
        self.exc = exc
        self.calls = 0

    def save(self):
        self.calls += 1
        if self.exc:
            raise self.exc


class _App:
    """Sam testowany punkt zapisu, bez budowania okna Tk."""

    def __init__(self, exc=None):
        self.store = _Store(exc)
        self.root = None
        self.statuses: list[str] = []

    def set_status(self, text):
        self.statuses.append(text)

    save_store = pb.PrompBaseApp.save_store


@pytest.fixture
def errors(monkeypatch):
    shown: list[str] = []
    monkeypatch.setattr(app_module.messagebox, "showerror", lambda *a, **k: shown.append(a[-1]))
    return shown


def test_successful_save_reports_nothing(errors):
    app = _App()
    assert app.save_store() is True
    assert app.store.calls == 1
    assert errors == []


@pytest.mark.parametrize(
    "exc",
    [OSError("na dysku nie ma miejsca"), PermissionError("plik zablokowany"), TypeError("zły typ")],
)
def test_failed_save_tells_the_user(errors, exc, monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "log_exception", lambda *a: tmp_path / "error.log")
    app = _App(exc=exc)

    assert app.save_store() is False
    assert len(errors) == 1
    assert str(exc) in errors[0]
    # Użytkownik musi wiedzieć, że zmiana nie przetrwa zamknięcia programu.
    assert "do zamknięcia programu" in errors[0]
    assert app.statuses and "BŁĄD" in app.statuses[-1]


def test_failed_save_is_logged(errors, monkeypatch):
    logged: list[str] = []
    monkeypatch.setattr(app_module, "log_exception", lambda t, e, tb: logged.append(str(e)))
    _App(exc=OSError("brak miejsca")).save_store()
    assert logged == ["brak miejsca"]


def test_every_save_goes_through_the_guard():
    """Regresja: nowe wywołanie `store.save()` w app.py znów byłoby ciche."""
    tree = ast.parse((ROOT / "pbcore" / "app.py").read_text(encoding="utf-8"))
    direct = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "save"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "store"
        ):
            direct.append(node.lineno)
    # Dokładnie jedno — to wewnątrz save_store().
    assert len(direct) == 1, f"bezpośrednie store.save() poza save_store(): linie {direct}"
