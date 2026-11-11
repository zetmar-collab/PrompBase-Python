"""Testy dymne podpięcia pisowni pod widget Text (prawdziwe okno Tk).

Sam checker jest przetestowany w test_spell.py; tutaj sprawdzamy warstwę,
która potrafi się zepsuć tylko w prawdziwym Tk: tagi podkreśleń, indeksy
znakowe (Text liczy je inaczej niż str przy wielu liniach) i to, że okno
edycji w ogóle się buduje z włączonym sprawdzaniem.
"""

from __future__ import annotations

import tkinter
from contextlib import contextmanager
from tkinter import Text, Tk

import pytest

from pbcore import spell, spell_ui


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


@pytest.fixture
def tiny_dict(tmp_path):
    dic = tmp_path / "xx_TEST.dic"
    aff = tmp_path / "xx_TEST.aff"
    dic.write_text("3\nkot\npies\nlas\n", encoding="utf-8")
    aff.write_text("SET UTF-8\nTRY kotpiesla\n", encoding="utf-8")
    return spell.load_dictionary(dic)


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    """Odcinamy się od słowników zainstalowanych w systemie.

    Bez tego konstruktor skanuje prawdziwe katalogi i wczytuje w tle
    kilkusettysięczny słownik — test zależałby wtedy od tego, co akurat
    stoi na maszynie, i potrafił wywrócić Tk w trakcie sprzątania.
    """
    spell_ui._CACHE.clear()
    monkeypatch.setattr(spell, "app_data_dir", lambda: tmp_path / "appdata")
    monkeypatch.setattr(spell, "available_dictionaries", lambda **_kw: {})
    yield
    spell_ui._CACHE.clear()


def _highlighter(root, dictionary, text=""):
    widget = Text(root)
    widget.pack()
    if text:
        widget.insert("1.0", text)
    highlighter = spell_ui.SpellHighlighter(widget, store=None)
    highlighter.checker = spell.SpellChecker(dictionary)
    highlighter.enabled = True
    highlighter.recheck()
    return widget, highlighter


def test_misspelled_words_get_tagged(tiny_dict):
    with tk_root() as root:
        widget, _h = _highlighter(root, tiny_dict, "kot pies bzdura")
        ranges = widget.tag_ranges(spell_ui.MISSPELLED_TAG)
        assert len(ranges) == 2  # jedno słowo = para indeksów
        assert widget.get(ranges[0], ranges[1]) == "bzdura"


def test_offsets_are_correct_across_lines(tiny_dict):
    """Text indeksuje wiersz/kolumnę — offsety z checkera są liczone od 1.0."""
    with tk_root() as root:
        widget, _h = _highlighter(root, tiny_dict, "kot\npies\nbzdura las")
        ranges = widget.tag_ranges(spell_ui.MISSPELLED_TAG)
        assert widget.get(ranges[0], ranges[1]) == "bzdura"


def test_correct_text_has_no_tags(tiny_dict):
    with tk_root() as root:
        widget, _h = _highlighter(root, tiny_dict, "kot pies las")
        assert widget.tag_ranges(spell_ui.MISSPELLED_TAG) == ()


def test_disabling_clears_underlines(tiny_dict):
    with tk_root() as root:
        widget, highlighter = _highlighter(root, tiny_dict, "bzdura")
        assert widget.tag_ranges(spell_ui.MISSPELLED_TAG)
        highlighter.set_enabled(False)
        assert widget.tag_ranges(spell_ui.MISSPELLED_TAG) == ()


def test_word_at_finds_the_misspelling(tiny_dict):
    with tk_root() as root:
        widget, highlighter = _highlighter(root, tiny_dict, "kot bzdura")
        hit = highlighter._word_at("1.6")
        assert hit is not None and hit[0] == "bzdura"
        assert highlighter._word_at("1.1") is None


def test_replacing_a_word_updates_text_and_tags(tiny_dict):
    with tk_root() as root:
        widget, highlighter = _highlighter(root, tiny_dict, "kot bzdura")
        _word, start, end = highlighter._word_at("1.6")
        highlighter._replace(start, end, "pies")
        assert widget.get("1.0", "end-1c") == "kot pies"
        assert widget.tag_ranges(spell_ui.MISSPELLED_TAG) == ()


def test_added_word_stops_being_underlined(tiny_dict):
    with tk_root() as root:
        widget, highlighter = _highlighter(root, tiny_dict, "PrompBase")
        assert widget.tag_ranges(spell_ui.MISSPELLED_TAG)
        highlighter._add_word("PrompBase")
        assert widget.tag_ranges(spell_ui.MISSPELLED_TAG) == ()


def test_no_dictionary_means_no_underlines():
    """Brak zainstalowanego słownika nie może pomalować całego tekstu."""
    with tk_root() as root:
        widget = Text(root)
        highlighter = spell_ui.SpellHighlighter(widget, store=None)
        highlighter.checker = spell.SpellChecker(None)
        widget.insert("1.0", "cokolwiek zupelnie bzdurnego")
        highlighter.recheck()
        assert widget.tag_ranges(spell_ui.MISSPELLED_TAG) == ()


def test_prompt_dialog_builds_with_spell_checking():
    """Okno edycji promptu musi się otworzyć z podpiętym sprawdzaniem."""
    from pbcore.dialogs import PromptDialog
    from pbcore.models import Prompt

    with tk_root() as root:
        dialog = PromptDialog(root, Prompt(name="Test", content="kot bzdura"))
        root.update()
        assert dialog.spell is not None
        assert dialog.content_text.get("1.0", "end-1c") == "kot bzdura"
        dialog.destroy()


def test_destroyed_widget_does_not_raise(tiny_dict):
    """Po zamknięciu okna zaplanowane sprawdzenie nie może wywalić aplikacji."""
    with tk_root() as root:
        widget, highlighter = _highlighter(root, tiny_dict, "bzdura")
        widget.destroy()
        root.update()
        highlighter.recheck()  # nie może rzucić wyjątku


def test_dictionary_cache_is_bounded(monkeypatch, tmp_path):
    """Cache słowników nie może rosnąć bez końca.

    Jeden słownik to dziesiątki megabajtów (pl_PL ok. 39 MB), a w systemie
    bywa ich kilkadziesiąt — bez limitu przełączanie języków urosłoby do
    setek megabajtów trzymanych do końca działania programu.
    """
    made: dict[str, object] = {}
    for code in ("aa_AA", "bb_BB", "cc_CC"):
        dic = tmp_path / f"{code}.dic"
        dic.write_text("1\nsalam\n", encoding="utf-8")
        (tmp_path / f"{code}.aff").write_text("SET UTF-8\n", encoding="utf-8")
        made[code] = dic

    monkeypatch.setattr(spell, "available_dictionaries", lambda **_kw: dict(made))
    for code in made:
        assert spell_ui.get_dictionary(code) is not None

    assert len(spell_ui._CACHE) <= spell_ui.CACHE_MAX_ENTRIES
    # Zostaje ostatnio używany, wypada najstarszy.
    assert "cc_CC" in spell_ui._CACHE
    assert "aa_AA" not in spell_ui._CACHE


def test_cache_hit_refreshes_recency(monkeypatch, tmp_path):
    made = {}
    for code in ("aa_AA", "bb_BB", "cc_CC"):
        dic = tmp_path / f"{code}.dic"
        dic.write_text("1\nsalam\n", encoding="utf-8")
        made[code] = dic
    monkeypatch.setattr(spell, "available_dictionaries", lambda **_kw: dict(made))

    spell_ui.get_dictionary("aa_AA")
    spell_ui.get_dictionary("bb_BB")
    spell_ui.get_dictionary("aa_AA")   # odświeża aa_AA
    spell_ui.get_dictionary("cc_CC")   # powinno wypchnąć bb_BB, nie aa_AA
    assert "aa_AA" in spell_ui._CACHE
    assert "bb_BB" not in spell_ui._CACHE
