"""Testy lokalizacji PrompBase (PL/EN).

Sprawdzamy: fallback nieznanych kluczy, przełączanie języka, tłumaczenie
promptów systemowych AI, oraz persystencję wyboru języka w PromptStore.
"""

from __future__ import annotations

import json

import pytest

import promptbase as pb
from pbcore import ai, i18n


@pytest.fixture(autouse=True)
def _reset_language():
    """Każdy test startuje i kończy na domyślnym (polskim) języku."""
    i18n.set_language(i18n.LANG_PL)
    yield
    i18n.set_language(i18n.LANG_PL)


def test_default_language_is_polish():
    assert i18n.get_language() == i18n.LANG_PL
    assert i18n.is_english() is False


def test_t_identity_when_polish():
    assert i18n.t("Nowy prompt") == "Nowy prompt"


def test_t_translates_when_english():
    i18n.set_language(i18n.LANG_EN)
    assert i18n.t("Nowy prompt") == "New prompt"


def test_t_fallback_for_unknown_key():
    """Brak wpisu w katalogu = bezpieczny fallback do oryginału, nie wyjątek."""
    i18n.set_language(i18n.LANG_EN)
    assert i18n.t("Tekst spoza katalogu, którego nie ma") == "Tekst spoza katalogu, którego nie ma"


def test_set_language_unknown_falls_back_to_default():
    result = i18n.set_language("fr")
    assert result == i18n.LANG_PL
    assert i18n.get_language() == i18n.LANG_PL


def test_language_label():
    assert i18n.language_label(i18n.LANG_EN) == "English"
    assert i18n.language_label(i18n.LANG_PL) == "Polski"
    assert i18n.language_label("nieznany") == "Polski"


def test_tv_behaves_like_t():
    i18n.set_language(i18n.LANG_EN)
    assert i18n.tv("Status") == i18n.t("Status")


# --- prompty systemowe AI zależne od języka ---------------------------------


def test_build_system_prompt_polish_by_default():
    text = ai.build_system_prompt(ai.ACTION_IMPROVE)
    assert "Jesteś ekspertem" in text


def test_build_system_prompt_english_when_ui_language_en():
    text = ai.build_system_prompt(ai.ACTION_IMPROVE, ui_language=i18n.LANG_EN)
    assert "expert prompt engineer" in text
    assert "Jesteś" not in text


def test_build_system_prompt_follows_current_i18n_state():
    i18n.set_language(i18n.LANG_EN)
    text = ai.build_system_prompt(ai.ACTION_TRANSLATE, language="niemiecki")
    assert "Translate the prompt below into: German" in text


def test_build_system_prompt_adapt_english_midjourney():
    text = ai.build_system_prompt(ai.ACTION_ADAPT, target="Midjourney", ui_language=i18n.LANG_EN)
    assert "--ar" in text
    assert "Midjourney image prompt" in text


def test_translate_languages_switches_with_ui():
    assert ai.translate_languages() == ai.TRANSLATE_LANGUAGES
    i18n.set_language(i18n.LANG_EN)
    assert ai.translate_languages() == ai.TRANSLATE_LANGUAGES_EN


def test_action_labels_translated():
    i18n.set_language(i18n.LANG_EN)
    labels = ai.action_labels()
    assert labels[ai.ACTION_IMPROVE] == "Improve prompt"


def test_engine_labels_translated():
    i18n.set_language(i18n.LANG_EN)
    labels = ai.engine_labels()
    assert "Ollama" in labels[ai.ENGINE_OLLAMA]


# --- PromptStore: persystencja języka ---------------------------------------


def test_store_defaults_to_polish(tmp_path):
    store = pb.PromptStore(tmp_path / "promptbase.json")
    assert store.language == i18n.LANG_PL


def test_store_saves_and_reloads_language(tmp_path):
    path = tmp_path / "promptbase.json"
    store = pb.PromptStore(path)
    store.language = i18n.LANG_EN
    store.save()

    reloaded = pb.PromptStore(path)
    assert reloaded.language == i18n.LANG_EN
    assert i18n.get_language() == i18n.LANG_EN


def test_store_load_sets_global_i18n_state(tmp_path):
    path = tmp_path / "promptbase.json"
    path.write_text(json.dumps({"prompts": [], "language": "en"}), encoding="utf-8")
    pb.PromptStore(path)
    assert i18n.get_language() == i18n.LANG_EN


def test_store_invalid_language_falls_back(tmp_path):
    path = tmp_path / "promptbase.json"
    path.write_text(json.dumps({"prompts": [], "language": "klingon"}), encoding="utf-8")
    store = pb.PromptStore(path)
    assert store.language == i18n.LANG_PL


def test_store_legacy_list_format_defaults_language(tmp_path):
    path = tmp_path / "promptbase.json"
    path.write_text(json.dumps([{"name": "Stary", "content": "x"}]), encoding="utf-8")
    store = pb.PromptStore(path)
    assert store.language == i18n.LANG_PL


# --- przykładowe prompty zależne od języka ----------------------------------


def test_sample_data_polish_by_default(tmp_path):
    store = pb.PromptStore(tmp_path / "promptbase.json")
    store.sample_data(force=True)
    assert store.prompts[0].name == "Post LinkedIn — marketing"


def test_sample_data_english_when_language_en(tmp_path):
    i18n.set_language(i18n.LANG_EN)
    store = pb.PromptStore(tmp_path / "promptbase.json")
    store.sample_data(force=True)
    assert store.prompts[0].name == "LinkedIn post — marketing"
    assert "[TOPIC]" in store.prompts[0].content
