"""Testy sprawdzania pisowni na syntetycznych słownikach Hunspell.

Świadomie NIE korzystamy ze słowników zainstalowanych w systemie — na CI ich
nie ma, a na maszynie autora są, więc test oparty o nie dawałby różne wyniki
w zależności od komputera. Budujemy więc miniaturowe .dic/.aff w tmp_path,
w tym jeden w ISO-8859-2, bo prawdziwe polskie słowniki nie są w UTF-8
i to właśnie na tym najłatwiej się przewrócić.
"""

from __future__ import annotations

import pytest

from pbcore import spell


def _write_dict(tmp_path, name, stems, aff_lines, encoding="utf-8"):
    dic = tmp_path / f"{name}.dic"
    aff = tmp_path / f"{name}.aff"
    dic.write_text(f"{len(stems)}\n" + "\n".join(stems) + "\n", encoding=encoding)
    aff.write_text("\n".join(aff_lines) + "\n", encoding=encoding)
    return dic


@pytest.fixture
def en_dict(tmp_path):
    return _write_dict(
        tmp_path,
        "en_TEST",
        ["cat/S", "dog/S", "image/S", "detail/SD", "quality"],
        [
            "SET ISO8859-1",
            "TRY esianrtolcd",
            "SFX S Y 1",
            "SFX S 0 s .",
            "SFX D Y 1",
            "SFX D 0 ed .",
        ],
        encoding="iso-8859-1",
    )


@pytest.fixture
def pl_dict(tmp_path):
    # Zapisany w ISO-8859-2 — tak jak prawdziwy pl_PL.
    return _write_dict(
        tmp_path,
        "pl_TEST",
        ["kot/A", "żółw", "zdjęcie", "źdźbło", "Warszawa"],
        [
            "SET ISO8859-2",
            "TRY aioeznrwcysptkmdąułjźgbhćęó",
            "SFX A Y 2",
            "SFX A 0 y t",
            "SFX A 0 em t",
        ],
        encoding="iso-8859-2",
    )


def test_reads_non_utf8_dictionary(pl_dict):
    """Kodowanie bierzemy z linii SET, inaczej diakrytyki się rozjeżdżają."""
    dictionary = spell.load_dictionary(pl_dict)
    assert "żółw" in dictionary.stems
    assert dictionary.check("żółw")
    assert dictionary.check("źdźbło")


def test_suffix_rules_expand_forms(pl_dict):
    dictionary = spell.load_dictionary(pl_dict)
    assert dictionary.check("kot")
    assert dictionary.check("koty")
    assert dictionary.check("kotem")
    assert not dictionary.check("kotów")  # brak takiej reguły w testowym .aff


def test_english_affixes(en_dict):
    dictionary = spell.load_dictionary(en_dict)
    for word in ("cat", "cats", "image", "images", "detail", "details", "detailed"):
        assert dictionary.check(word), word
    assert not dictionary.check("catz")


@pytest.mark.parametrize(
    "word, expected",
    [
        ("kot", True),      # jak w słowniku
        ("Kot", True),      # początek zdania
        ("KOT", True),      # wersaliki
        ("kOt", False),     # przypadkowy Shift to nie jest poprawna forma
        ("Koty", True),     # odmiana na początku zdania
    ],
)
def test_casing_rules(pl_dict, word, expected):
    assert spell.load_dictionary(pl_dict).check(word) is expected


def test_suggestions_restore_diacritics(pl_dict):
    dictionary = spell.load_dictionary(pl_dict)
    assert "żółw" in dictionary.suggest("żółw".replace("ó", "o"))


def test_suggestions_are_lowercase_only(pl_dict):
    """TRY zawiera też wielkie litery — nie mogą trafiać w środek propozycji."""
    dictionary = spell.load_dictionary(pl_dict)
    for suggestion in dictionary.suggest("kt"):
        assert suggestion == suggestion.lower() or suggestion.istitle()


def test_iter_words_skips_placeholders_and_urls():
    text = "Wygeneruj [TEMAT] w stylu, https://example.com oraz `kod` tutaj."
    words = [w for w, _s, _e in spell.iter_words(text)]
    assert "TEMAT" not in words
    assert "example" not in words
    assert "kod" not in words
    assert "Wygeneruj" in words


def test_iter_words_offsets_match_source():
    text = "kot zdjecei pies"
    for word, start, end in spell.iter_words(text):
        assert text[start:end] == word


def test_checker_without_dictionary_reports_nothing():
    """Brak słownika nie może oznaczać, że całość jest podkreślona na czerwono."""
    checker = spell.SpellChecker(None)
    assert not checker.ready
    assert checker.check_text("cokolwiek zupelnie bzdurnego") == []


def test_personal_words_are_accepted(pl_dict, monkeypatch, tmp_path):
    monkeypatch.setattr(spell, "app_data_dir", lambda: tmp_path / "data")
    checker = spell.SpellChecker(spell.load_dictionary(pl_dict))
    assert checker.check_text("PrompBase")
    checker.add_word("PrompBase")
    assert checker.check_text("PrompBase") == []
    # Zapisane trwale — kolejna sesja też ma je znać.
    assert "PrompBase" in spell.load_personal_words()


def test_ignore_word_is_session_only(pl_dict, monkeypatch, tmp_path):
    monkeypatch.setattr(spell, "app_data_dir", lambda: tmp_path / "data")
    checker = spell.SpellChecker(spell.load_dictionary(pl_dict))
    checker.ignore_word("Xyzzy")
    assert checker.check_text("Xyzzy") == []
    assert spell.load_personal_words() == set()


def test_install_dictionary_copies_pair(pl_dict, monkeypatch, tmp_path):
    monkeypatch.setattr(spell, "app_data_dir", lambda: tmp_path / "data")
    installed = spell.install_dictionary(pl_dict)
    assert installed.is_file()
    assert installed.with_suffix(".aff").is_file()
    assert spell.available_dictionaries()["pl_TEST"] == installed


def test_install_rejects_non_dic(tmp_path, monkeypatch):
    monkeypatch.setattr(spell, "app_data_dir", lambda: tmp_path / "data")
    bogus = tmp_path / "cos.txt"
    bogus.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        spell.install_dictionary(bogus)


def test_missing_aff_still_loads_stems(tmp_path):
    """Same .dic bez .aff to poprawny (choć uboższy) słownik."""
    dic = tmp_path / "xx_XX.dic"
    dic.write_text("2\nalfa\nbeta\n", encoding="utf-8")
    dictionary = spell.load_dictionary(dic)
    assert dictionary.check("alfa")
    assert not dictionary.check("gamma")
