"""Wartości słownikowe: interfejs tłumaczony, dane i n8n bez zmian.

Statusy, formaty, sortowanie i filtr „Wszystkie" były pokazywane po polsku
także w wersji angielskiej — tłumaczenia leżały w `_EN_VALUES`, ale nigdy nie
trafiły na ekran. Tłumaczymy wyłącznie WARSTWĘ WIDOKU: w pliku i w ładunku
wysyłanym do n8n zostają wartości kanoniczne, bo zmiana języka interfejsu nie
może cicho zmienić kontraktu danych ani zepsuć istniejących bibliotek.
"""

from __future__ import annotations

import pytest

import promptbase as pb
from pbcore import i18n


@pytest.fixture
def pl():
    i18n.set_language(i18n.LANG_PL)
    yield
    i18n.set_language(i18n.LANG_PL)


@pytest.fixture
def en():
    i18n.set_language(i18n.LANG_EN)
    yield
    i18n.set_language(i18n.LANG_PL)


# --- widok ----------------------------------------------------------------

def test_status_shown_translated(en):
    assert pb.status_display("praca") == "Work"
    assert pb.status_display("nowy") == "New"
    assert "Work" in pb.status_display_values()


def test_status_shown_in_polish(pl):
    assert pb.status_display("praca") == "Praca"
    assert pb.status_display_values() == ["Nowy", "Osobiste", "Praca", "Uniwersalne"]


def test_format_and_sort_shown_translated(en):
    assert pb.format_display("tekst") == "text"
    assert pb.format_display_values()[:2] == ["text", "code"]
    assert pb.sort_display_values()[0] == "Newest"


def test_all_filter_label_follows_language(pl):
    assert pb.all_filter_label() == "Wszystkie"
    i18n.set_language(i18n.LANG_EN)
    assert pb.all_filter_label() == "All"


# --- powrót z widoku do danych --------------------------------------------

@pytest.mark.parametrize("lang", [i18n.LANG_PL, i18n.LANG_EN])
def test_display_label_maps_back_to_key(lang):
    i18n.set_language(lang)
    try:
        for key in pb.STATUSES:
            assert pb.status_key_from_display(pb.status_display(key)) == key
        for value in pb.FORMATS:
            assert pb.format_from_display(pb.format_display(value)) == value
        for polish, expected in pb.SORT_OPTIONS.items():
            assert pb.sort_key_from_display(i18n.t(polish)) == expected
    finally:
        i18n.set_language(i18n.LANG_PL)


def test_polish_labels_still_accepted_in_english_ui(en):
    """Stare dane i pliki niosą polskie etykiety — muszą dalej działać."""
    assert pb.status_key_from_display("Praca") == "praca"
    assert pb.format_from_display("tekst") == "tekst"
    assert pb.sort_key_from_display("Najnowsze") == "newest"


# --- kontrakt danych ------------------------------------------------------

def test_n8n_payload_is_language_independent():
    prompt = pb.Prompt(name="N", content="C", status="praca", format="tekst")

    i18n.set_language(i18n.LANG_PL)
    polish = pb.prompt_to_n8n_dict(prompt)
    i18n.set_language(i18n.LANG_EN)
    english = pb.prompt_to_n8n_dict(prompt)
    i18n.set_language(i18n.LANG_PL)

    assert polish == english, "język interfejsu zmienił ładunek wysyłany do n8n"
    assert polish["status"] == "praca"
    assert polish["status_label"] == "Praca"
    assert polish["format"] == "tekst"


def test_saved_prompt_keeps_canonical_values(en):
    prompt = pb.Prompt(name="N", content="C", status="praca", format="tekst")
    data = prompt.to_dict()
    assert data["status"] == "praca"
    assert data["format"] == "tekst"
    assert pb.Prompt.from_dict(data).status == "praca"


# --- okno edycji ----------------------------------------------------------

@pytest.fixture
def tk_root():
    import tkinter
    from tkinter import Tk

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


@pytest.mark.parametrize("lang", [i18n.LANG_PL, i18n.LANG_EN])
def test_edit_dialog_keeps_canonical_values(tk_root, lang):
    """Edycja w dowolnym języku zapisuje te same wartości w danych.

    Okno pokazuje „Work"/„text", ale w `promptbase.json` ma wylądować
    „praca"/„tekst" — inaczej zmiana języka psułaby istniejącą bibliotekę
    i ładunek wysyłany do n8n.
    """
    i18n.set_language(lang)
    try:
        from pbcore.dialogs import PromptDialog

        prompt = pb.Prompt(name="N", content="C", status="praca", format="tekst")
        dialog = PromptDialog(tk_root, prompt)
        tk_root.update()

        # To, co widzi użytkownik, zależy od języka...
        assert dialog.status_var.get() == pb.status_display("praca")
        assert dialog.format_var.get() == pb.format_display("tekst")

        dialog.save()
        # ...ale zapisane dane już nie.
        assert dialog.result is not None
        assert dialog.result.status == "praca"
        assert dialog.result.format == "tekst"
    finally:
        i18n.set_language(i18n.LANG_PL)


# --- normalizacja przy imporcie -------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("praca", "praca"),        # klucz z własnego pliku JSON
        ("Praca", "praca"),        # etykieta z eksportu CSV/XLSX
        ("Work", "praca"),         # etykieta z eksportu w wersji angielskiej
        ("nowy", "nowy"),
        ("Uniwersalne", "uniwersalne"),
        ("Universal", "uniwersalne"),
    ],
)
def test_imported_status_becomes_canonical_key(raw, expected):
    """Regresja: import zapisywał etykietę („Praca") zamiast klucza („praca").

    Prompt z takim statusem wysyłał do n8n złą wartość, a w angielskim
    interfejsie znikał z filtra, bo lista pokazywała „Work", a prompt „Praca".
    """
    p = pb.Prompt.from_dict({"name": "N", "content": "C", "status": raw})
    assert p.status == expected
    assert p.status in pb.STATUSES
    assert pb.prompt_to_n8n_dict(p)["status"] == expected


@pytest.mark.parametrize(
    "raw, expected",
    [("tekst", "tekst"), ("text", "tekst"), ("kod", "kod"), ("code", "kod")],
)
def test_imported_format_becomes_canonical(raw, expected):
    p = pb.Prompt.from_dict({"name": "N", "content": "C", "format": raw})
    assert p.format == expected


def test_unknown_status_is_left_alone():
    """Obca wartość ma przetrwać — nie zgadujemy za użytkownika."""
    p = pb.Prompt.from_dict({"name": "N", "content": "C", "status": "mój-własny"})
    assert p.status == "mój-własny"
