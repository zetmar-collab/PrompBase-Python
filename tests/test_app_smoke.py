"""Testy dymne PrompBaseApp — budują prawdziwe okno Tk (headless: root.withdraw()).

Cięższe niż reszta zestawu (tworzą Tk), więc trzymane osobno od test_logic.py.
Chronią przed regresjami w kolejności inicjalizacji, które nie są widoczne
bez faktycznego zbudowania okna (np. i18n ustawiane po tym, jak coś już go
użyło).
"""

from __future__ import annotations

import json
import tkinter
from contextlib import contextmanager
from tkinter import Tk, messagebox

import pytest

import promptbase as pb
from pbcore import i18n


@pytest.fixture(autouse=True)
def _isolated_appdata(monkeypatch, tmp_path):
    """Izolowany %APPDATA% — nie dotykamy prawdziwej biblioteki użytkownika."""
    appdata = tmp_path / "AppData"
    appdata.mkdir(exist_ok=True)  # conftest tworzy ten katalog wcześniej
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


@contextmanager
def tk_root():
    """Okno Tk sprzątane tak, by kolejny test mógł je utworzyć na nowo.

    Samo root.destroy() nie czyści globalnego `tkinter._default_root`;
    przy kilku kolejnych oknach w jednym procesie kolejne Tk() potrafi
    wywalić się przy szukaniu bibliotek Tcl/Tk. Zerujemy domyślnego roota,
    a gdy interpreter Tcl i tak odmówi startu (środowiskowe, nie błąd
    aplikacji) — pomijamy test zamiast zgłaszać fałszywą regresję.
    """
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


def test_window_title_reflects_saved_language_on_first_render(_isolated_appdata):
    """Regresja: root.title() był ustawiany PRZED wczytaniem PromptStore,
    więc pierwszy render zawsze dostawał domyślny (polski) tytuł, nawet gdy
    użytkownik miał zapisane language=en. Wykryto po instalacji pakietu MSIX
    z prawdziwą biblioteką w trybie English."""
    _write_store(_isolated_appdata, language="en")

    with tk_root() as root:
        pb.PrompBaseApp(root)
        root.update()
        assert i18n.get_language() == "en"
        assert root.title() == "PrompBase - AI Prompt Library"


def test_window_title_polish_default(_isolated_appdata):
    with tk_root() as root:
        pb.PrompBaseApp(root)
        root.update()
        assert root.title() == "PrompBase - Biblioteka Promptów AI"


def test_app_builds_without_error_in_both_languages(_isolated_appdata):
    """Smoke: całe okno (menu, sidebar, detail, checklista) buduje się bez
    wyjątku w obu językach — łapie literały poza pokryciem testu i18n
    coverage (np. te budowane dynamicznie, nie przez proste t('...'))."""
    for lang in ("pl", "en"):
        _write_store(_isolated_appdata, language=lang)
        with tk_root() as root:
            app = pb.PrompBaseApp(root)
            root.update()
            assert app.store.language == lang


# --- zgodność z polityką Microsoft Store -----------------------------------


def _menu_labels(root, menu):
    """Wszystkie etykiety pozycji menu (rekurencyjnie przez podmenu)."""
    out = []
    end = menu.index("end")
    if end is None:
        return out
    for i in range(end + 1):
        try:
            typ = menu.type(i)
        except Exception:
            continue
        if typ in ("command", "radiobutton", "checkbutton"):
            out.append(str(menu.entrycget(i, "label")))
        elif typ == "cascade":
            out.append(str(menu.entrycget(i, "label")))
            sub = menu.entrycget(i, "menu")
            if sub:
                try:
                    out.extend(_menu_labels(root, root.nametowidget(sub)))
                except Exception:
                    pass
    return out


def _all_menu_labels(monkeypatch, *, msix: bool):
    import pbcore.app as appmod

    monkeypatch.setattr(appmod, "is_msix_package", lambda: msix)
    with tk_root() as root:
        appmod.PrompBaseApp(root)
        root.update()
        return _menu_labels(root, root.nametowidget(root.cget("menu")))


# Pozycje zakazane w wersji sklepowej przez zasadę 10.1.5 (Software
# Distribution): promują pobranie/zakup poza Microsoft Store.
STORE_BANNED_LABELS = (
    "Pobierz najnowszą wersję",
    "Cennik (Free / Pro)",
    "Paczki promptów Pro (wkrótce)...",
)


def test_msix_build_hides_out_of_store_distribution(_isolated_appdata, monkeypatch):
    """Regresja: certyfikacja Store odrzuciła build 2.9.1 za promowanie
    pobierania oprogramowania poza Store (zasada 10.1.5)."""
    labels = _all_menu_labels(monkeypatch, msix=True)
    present = [x for x in STORE_BANNED_LABELS if x in labels]
    assert not present, f"W wersji MSIX nie może być pozycji: {present}"


def test_non_msix_build_keeps_download_and_pricing(_isolated_appdata, monkeypatch):
    """Poza Store (zwykły EXE z GitHub) te pozycje mają nadal działać."""
    labels = _all_menu_labels(monkeypatch, msix=False)
    for banned in STORE_BANNED_LABELS:
        assert banned in labels, f"Wersja EXE powinna zawierać: {banned}"
