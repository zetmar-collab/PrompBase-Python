"""Dziennik błędów — bez niego awarie w buildzie okienkowym były niewidoczne.

PrompBase.spec ustawia `console=False`, więc `stderr` nie trafia nigdzie.
Tk łapie wyjątek z callbacku, wypisuje go na `stderr` i działa dalej, przez
co użytkownik widział tylko „kliknąłem i nic się nie stało".
"""

from __future__ import annotations

import tkinter
from contextlib import contextmanager
from tkinter import Tk

import pytest

from pbcore import app as app_module
from pbcore import core


@pytest.fixture(autouse=True)
def _isolated_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(core, "app_data_dir", lambda: tmp_path / "PrompBase")
    return tmp_path / "PrompBase"


def _boom():
    raise ValueError("celowy blad testowy")


def test_log_exception_writes_file(_isolated_appdata):
    try:
        _boom()
    except ValueError as exc:
        path = core.log_exception(type(exc), exc, exc.__traceback__)

    assert path is not None and path.is_file()
    content = path.read_text(encoding="utf-8")
    assert "celowy blad testowy" in content
    assert "ValueError" in content
    assert core.APP_VERSION in content


def test_log_exception_appends(_isolated_appdata):
    for _ in range(2):
        try:
            _boom()
        except ValueError as exc:
            path = core.log_exception(type(exc), exc, exc.__traceback__)
    # Liczymy nagłówki wpisów — sama fraza występuje dwa razy na wpis
    # (w wierszu źródła i w komunikacie wyjątku).
    assert path.read_text(encoding="utf-8").count("--- 20") == 2


def test_log_rotates_when_too_big(_isolated_appdata, monkeypatch):
    monkeypatch.setattr(core, "ERROR_LOG_MAX_BYTES", 100)
    for _ in range(6):
        try:
            _boom()
        except ValueError as exc:
            core.log_exception(type(exc), exc, exc.__traceback__)
    assert core.error_log_path().with_suffix(".log.1").is_file()


def test_log_exception_never_raises(monkeypatch):
    """Dziennik działa już w trakcie obsługi innego błędu — nie może dołożyć swojego."""
    monkeypatch.setattr(core, "app_data_dir", lambda: (_ for _ in ()).throw(OSError("brak dostępu")))
    try:
        _boom()
    except ValueError as exc:
        assert core.log_exception(type(exc), exc, exc.__traceback__) is None


@contextmanager
def tk_root():
    try:
        root = Tk()
    except tkinter.TclError as exc:  # pragma: no cover - zależne od środowiska
        pytest.skip(f"Tk niedostępny w tym procesie: {exc}")
    root.withdraw()
    try:
        yield root
    finally:
        try:
            root.destroy()
        finally:
            tkinter._default_root = None


def test_tk_callback_error_is_logged_and_reported(_isolated_appdata, monkeypatch):
    """Błąd w callbacku Tk ma trafić do dziennika i pokazać się użytkownikowi."""
    shown: list[str] = []
    monkeypatch.setattr(
        app_module.messagebox, "showerror", lambda *a, **k: shown.append(a[-1])
    )

    with tk_root() as root:
        app_module.install_error_handler(root)
        root.report_callback_exception(ValueError, ValueError("awaria callbacku"), None)

    assert shown, "użytkownik nie zobaczył żadnego komunikatu"
    assert "awaria callbacku" in shown[0]
    log = core.error_log_path()
    assert log.is_file()
    assert "awaria callbacku" in log.read_text(encoding="utf-8")
    # Ścieżka do dziennika musi być w komunikacie, żeby dało się go odesłać.
    assert str(log) in shown[0]
