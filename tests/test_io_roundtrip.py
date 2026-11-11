"""Eksport i import przez prawdziwe metody okna (po wydzieleniu do app_io).

Testy jednostkowe nie dotykały tych metod, a refaktor przeniósł je do
domieszki `ImportExportMixin`. Tu budujemy prawdziwe okno i przechodzimy
pełną pętlę: eksport do pliku → import z powrotem.
"""

from __future__ import annotations

import tkinter
from contextlib import contextmanager
from tkinter import Tk

import pytest

import promptbase as pb
from pbcore import app as app_module
from pbcore import xlsx


@contextmanager
def app_window():
    try:
        root = Tk()
    except tkinter.TclError as exc:  # pragma: no cover - zależne od środowiska
        pytest.skip(f"Tk niedostępny w tym procesie: {exc}")
    root.withdraw()
    try:
        yield app_module.PrompBaseApp(root), root
    finally:
        try:
            root.destroy()
        finally:
            tkinter._default_root = None


def _seed(app):
    app.store.prompts = [
        pb.Prompt(name="Anime 🌸", content="Treść z <tagiem> & \"cudzysłowem\"",
                  status="praca", format="tekst", model="GPT-5.5",
                  zastosowanie="marketing", tags="a, b", comment="uwaga"),
        pb.Prompt(name="Drugi", content="Wieloliniowa\ntreść", status="osobiste",
                  format="kod", zastosowanie="kodowanie"),
    ]


def test_mixins_are_actually_wired():
    """Metody muszą nadal być dostępne na klasie po wydzieleniu."""
    for name in ("export_xlsx", "import_xlsx", "export_csv", "import_csv",
                 "export_backup_json", "import_backup_json"):
        assert hasattr(app_module.PrompBaseApp, name), name
    for name in ("send_selected_to_n8n", "ensure_n8n_url", "configure_n8n"):
        assert hasattr(app_module.PrompBaseApp, name), name
    assert app_module.ImportExportMixin in app_module.PrompBaseApp.__mro__
    assert app_module.N8nMixin in app_module.PrompBaseApp.__mro__


def test_xlsx_export_then_import(tmp_path, monkeypatch):
    target = tmp_path / "eksport.xlsx"
    with app_window() as (app, root):
        _seed(app)
        monkeypatch.setattr(app_module.filedialog, "asksaveasfilename",
                            lambda **k: str(target))
        monkeypatch.setattr(app_module.messagebox, "showinfo", lambda *a, **k: None)
        app.export_xlsx()
        root.update()

    assert target.is_file() and target.stat().st_size > 0

    rows = xlsx.read_rows(target)
    items, mapping = xlsx.rows_to_prompt_dicts(rows)
    assert len(items) == 2
    assert items[0]["name"] == "Anime 🌸"
    assert "<tagiem>" in items[0]["content"]
    assert items[1]["content"] == "Wieloliniowa\ntreść"
    # Status zapisany kanonicznie, więc import go rozpozna.
    assert "zastosowanie" in mapping


def test_csv_export_then_import(tmp_path, monkeypatch):
    target = tmp_path / "eksport.csv"
    with app_window() as (app, root):
        _seed(app)
        monkeypatch.setattr(app_module.filedialog, "asksaveasfilename",
                            lambda **k: str(target))
        monkeypatch.setattr(app_module.messagebox, "showinfo", lambda *a, **k: None)
        app.export_csv()
        root.update()

    assert target.is_file()
    text = target.read_text(encoding="utf-8-sig")
    assert "Anime 🌸" in text
    assert "Wieloliniowa" in text


def test_json_backup_roundtrip(tmp_path, monkeypatch):
    target = tmp_path / "kopia.json"
    with app_window() as (app, root):
        _seed(app)
        monkeypatch.setattr(app_module.filedialog, "asksaveasfilename",
                            lambda **k: str(target))
        monkeypatch.setattr(app_module.messagebox, "showinfo", lambda *a, **k: None)
        app.export_backup_json()
        root.update()
        assert target.is_file()

        # Import tej samej kopii w trybie „zastąp bibliotekę".
        app.store.prompts = []
        monkeypatch.setattr(app_module.filedialog, "askopenfilename",
                            lambda **k: str(target))
        monkeypatch.setattr(app_module.messagebox, "askyesnocancel", lambda *a, **k: False)
        monkeypatch.setattr(app_module.messagebox, "askyesno", lambda *a, **k: False)
        app.import_backup_json()
        root.update()

        assert len(app.store.prompts) == 2
        assert {p.name for p in app.store.prompts} == {"Anime 🌸", "Drugi"}
        assert app.store.prompts[0].status in ("praca", "osobiste")


# --- eksport w jednym jezyku, import w drugim -----------------------------

@pytest.mark.parametrize("export_lang, import_lang", [("pl", "en"), ("en", "pl"), ("en", "en")])
def test_xlsx_roundtrip_across_languages(tmp_path, monkeypatch, export_lang, import_lang):
    """Plik wyeksportowany w jednym języku musi wejść w drugim.

    Nagłówki i etykiety są tłumaczone (angielski użytkownik nie powinien
    dostawać arkusza po polsku), ale import rozpoznaje oba zapisy, a status
    i format lądują w danych jako wartości kanoniczne.
    """
    from pbcore import i18n

    target = tmp_path / f"{export_lang}.xlsx"
    i18n.set_language(export_lang)
    try:
        with app_window() as (app, root):
            _seed(app)
            monkeypatch.setattr(app_module.filedialog, "asksaveasfilename",
                                lambda **k: str(target))
            monkeypatch.setattr(app_module.messagebox, "showinfo", lambda *a, **k: None)
            app.export_xlsx()
            root.update()
    finally:
        i18n.set_language(i18n.LANG_PL)

    assert target.is_file()
    header = xlsx.read_rows(target)[0]
    if export_lang == "en":
        assert header[0] == "Name" and header[-1] == "Content"
    else:
        assert header[0] == "Nazwa" and header[-1] == "Treść Promptu"

    i18n.set_language(import_lang)
    try:
        items, mapping = xlsx.rows_to_prompt_dicts(xlsx.read_rows(target))
        prompts = [pb.Prompt.from_dict(item) for item in items]
    finally:
        i18n.set_language(i18n.LANG_PL)

    assert len(prompts) == 2
    assert {"name", "content", "status", "format"} <= set(mapping)
    # Niezależnie od języka pliku w danych siedzą wartości kanoniczne.
    assert prompts[0].status == "praca"
    assert prompts[0].format == "tekst"
    assert prompts[1].status == "osobiste"
    assert prompts[1].format == "kod"
    assert prompts[0].name == "Anime 🌸"
