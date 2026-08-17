"""Testy dymne PrompBaseApp — budują prawdziwe okno Tk (headless: root.withdraw()).

Cięższe niż reszta zestawu (tworzą Tk), więc trzymane osobno od test_logic.py.
Chronią przed regresjami w kolejności inicjalizacji, które nie są widoczne
bez faktycznego zbudowania okna (np. i18n ustawiane po tym, jak coś już go
użyło).
"""

from __future__ import annotations

import json
from tkinter import Tk, messagebox

import pytest

import promptbase as pb
from pbcore import i18n


@pytest.fixture(autouse=True)
def _isolated_appdata(monkeypatch, tmp_path):
    """Izolowany %APPDATA% — nie dotykamy prawdziwej biblioteki użytkownika."""
    appdata = tmp_path / "AppData"
    appdata.mkdir()
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(messagebox, "showinfo", lambda *a, **k: None)
    yield appdata
    i18n.set_language(i18n.LANG_PL)


def _write_store(appdata, **overrides):
    prompbase_dir = appdata / "PrompBase"
    prompbase_dir.mkdir(parents=True, exist_ok=True)
    payload = {"prompts": [], "onboarding_done": True}
    payload.update(overrides)
    (prompbase_dir / "promptbase.json").write_text(json.dumps(payload), encoding="utf-8")


def test_window_title_reflects_saved_language_on_first_render(_isolated_appdata):
    """Regresja: root.title() był ustawiany PRZED wczytaniem PromptStore,
    więc pierwszy render zawsze dostawał domyślny (polski) tytuł, nawet gdy
    użytkownik miał zapisane language=en. Wykryto po instalacji pakietu MSIX
    z prawdziwą biblioteką w trybie English."""
    _write_store(_isolated_appdata, language="en")

    root = Tk()
    root.withdraw()
    try:
        pb.PrompBaseApp(root)
        root.update()
        assert i18n.get_language() == "en"
        assert root.title() == "PrompBase - AI Prompt Library"
    finally:
        root.destroy()


def test_window_title_polish_default(_isolated_appdata):
    root = Tk()
    root.withdraw()
    try:
        pb.PrompBaseApp(root)
        root.update()
        assert root.title() == "PrompBase - Biblioteka Promptów AI"
    finally:
        root.destroy()


def test_app_builds_without_error_in_both_languages(_isolated_appdata):
    """Smoke: całe okno (menu, sidebar, detail, checklista) buduje się bez
    wyjątku w obu językach — łapie literały poza pokryciem testu i18n
    coverage (np. te budowane dynamicznie, nie przez proste t('...'))."""
    for lang in ("pl", "en"):
        _write_store(_isolated_appdata, language=lang)
        root = Tk()
        root.withdraw()
        try:
            app = pb.PrompBaseApp(root)
            root.update()
            assert app.store.language == lang
        finally:
            root.destroy()
