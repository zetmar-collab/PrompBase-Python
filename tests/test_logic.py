"""Testy logiki PrompBase (bez GUI).

Importujemy moduł aplikacji; nie tworzymy okna Tk, więc testy działają
w środowisku headless (CI). Skupiamy się na funkcjach czystych oraz na
PromptStore.load/save (w tym rotacji backupów).
"""

from __future__ import annotations

import json

import pytest

import promptbase as pb

# --- placeholdery / zmienne ------------------------------------------------

def test_extract_placeholders_unique_order():
    text = "Temat: [TEMAT], odbiorca: [ODBIORCA], znowu [TEMAT]"
    assert pb.extract_placeholders(text) == ["[TEMAT]", "[ODBIORCA]"]


def test_extract_placeholders_empty():
    assert pb.extract_placeholders("") == []
    assert pb.extract_placeholders(None) == []


def test_fill_placeholders_single_pass_no_cascade():
    # Wartość jednej zmiennej nie może być ponownie podmieniona jako inna.
    text = "[A] i [B]"
    values = {"[A]": "[B]", "[B]": "koniec"}
    assert pb.fill_placeholders(text, values) == "[B] i koniec"


def test_fill_placeholders_missing_left_intact():
    assert pb.fill_placeholders("[X] [Y]", {"[X]": "1"}) == "1 [Y]"


# --- tagi ------------------------------------------------------------------

def test_parse_tags_value_from_list():
    assert pb.parse_tags_value(["seo", " blog ", ""]) == "seo, blog"


def test_parse_tags_value_from_string():
    assert pb.parse_tags_value("  social, polski ") == "social, polski"


def test_tag_list_from_string():
    assert pb.tag_list_from_string("seo, blog ,, email") == ["seo", "blog", "email"]


# --- n8n URL ---------------------------------------------------------------

@pytest.mark.parametrize(
    "url,valid",
    [
        ("https://x.app.n8n.cloud/webhook/prompbase", True),
        ("http://localhost:5678/webhook-test/abc", True),
        ("ftp://x/webhook", False),
        ("https://example.com/api", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_n8n_url(url, valid):
    assert pb.validate_n8n_url(url) is valid


def test_normalize_n8n_url_strips():
    assert pb.normalize_n8n_url("  https://a/webhook/x  ") == "https://a/webhook/x"


# --- sugerowana platforma AI ----------------------------------------------

@pytest.mark.parametrize(
    "model,platform",
    [
        ("GPT-5.5", "ChatGPT"),
        ("o3-mini", "ChatGPT"),
        ("Claude Opus 4.7", "Claude"),
        ("Gemini 3.5 Pro", "Gemini"),
        ("Perplexity Sonar", "Perplexity"),
        ("Manus", "Manus"),
        ("Nieznany model", None),
    ],
)
def test_suggest_ai_platform(model, platform):
    assert pb.suggest_ai_platform(model) == platform


# --- łączenie list modeli --------------------------------------------------

def test_merge_model_options_dedup_and_strip():
    result = pb.merge_model_options(["A", " B "], ["b", "A", "C", ""])
    # Deduplikacja jest wrażliwa na wielkość liter ("B" != "b").
    assert result == ["A", "B", "b", "C"]


# --- daty ------------------------------------------------------------------

def test_parse_date_to_ms_roundtrip():
    ms = pb.parse_date_to_ms("2024-01-15")
    assert isinstance(ms, int) and ms > 0
    assert pb.format_date(ms).startswith("15.01.2024")


def test_parse_date_to_ms_empty_returns_now():
    ms = pb.parse_date_to_ms("")
    assert abs(ms - pb.now_ms()) < 5000


def test_format_date_invalid():
    assert pb.format_date(None) == ""
    assert pb.format_date(0) == ""


# --- Prompt (de)serializacja ----------------------------------------------

def test_prompt_from_dict_polish_and_english_keys():
    p = pb.Prompt.from_dict({"Nazwa": "  Test  ", "Treść Promptu": "  abc  ", "Tagi": ["x", "y"]})
    assert p.name == "Test"
    assert p.content == "abc"
    assert p.tags == "x, y"
    assert p.status == "nowy"  # domyślny


def test_prompt_roundtrip_to_dict():
    p = pb.Prompt(name="N", content="C", model="GPT-5.5", tags="a, b")
    data = p.to_dict()
    p2 = pb.Prompt.from_dict(data)
    assert (p2.name, p2.content, p2.model, p2.tags) == ("N", "C", "GPT-5.5", "a, b")


@pytest.mark.parametrize(
    "created",
    ["2026-01-01", {"rok": 2026}, [], "", "nie-liczba", None],
)
def test_prompt_from_dict_survives_broken_created(created):
    """Regresja: `created` zapisane inaczej niż liczbą wywracało cały import.

    int("2026-01-01") rzuca ValueError, a żadna ze ścieżek importu tego nie
    łapała — w wersji okienkowej import po prostu cicho nic nie robił.
    """
    p = pb.Prompt.from_dict({"name": "N", "content": "C", "created": created})
    assert isinstance(p.created, int)
    assert p.created > 0


def test_prompt_from_dict_keeps_valid_created():
    p = pb.Prompt.from_dict({"name": "N", "content": "C", "created": 1757000000000})
    assert p.created == 1757000000000
    # Liczba zapisana tekstem lub zmiennoprzecinkowo nadal ma być honorowana.
    assert pb.Prompt.from_dict({"name": "N", "content": "C", "created": "1757000000000"}).created == 1757000000000
    assert pb.Prompt.from_dict({"name": "N", "content": "C", "created": 1757000000000.0}).created == 1757000000000


def test_prompt_history_capped():
    hist = [{"content": str(i)} for i in range(20)]
    p = pb.Prompt.from_dict({"name": "N", "content": "C", "history": hist})
    assert len(p.history) == pb.PROMPT_HISTORY_MAX


# --- import PWA ------------------------------------------------------------

def test_parse_pwa_import_list():
    raw, url, theme = pb.parse_pwa_import_data([{"name": "A", "content": "x"}])
    assert len(raw) == 1 and url == "" and theme == ""


def test_parse_pwa_import_nested_string():
    payload = {
        "promptLibrary": json.dumps([{"name": "A", "content": "x"}]),
        "n8nUrl": "https://a/webhook/x",
        "theme": "ciemny",
    }
    raw, url, theme = pb.parse_pwa_import_data(payload)
    assert len(raw) == 1
    assert url == "https://a/webhook/x"
    assert theme == "ciemny"


def test_prompts_from_pwa_data_builds_prompts():
    prompts, _, _ = pb.prompts_from_pwa_data([{"name": "A", "content": "x"}])
    assert len(prompts) == 1 and isinstance(prompts[0], pb.Prompt)


# --- PromptStore: zapis / odczyt / rotacja backupów ------------------------

def _make_store(tmp_path):
    store = pb.PromptStore(tmp_path / "promptbase.json")
    return store


def test_store_save_and_reload(tmp_path):
    store = _make_store(tmp_path)
    store.prompts = [pb.Prompt(name="N1", content="C1")]
    store.theme = "grafit"
    store.save()

    reloaded = pb.PromptStore(tmp_path / "promptbase.json")
    assert len(reloaded.prompts) == 1
    assert reloaded.prompts[0].name == "N1"
    assert reloaded.theme == "grafit"


def test_store_load_legacy_list(tmp_path):
    path = tmp_path / "promptbase.json"
    path.write_text(json.dumps([{"name": "Stary", "content": "x"}]), encoding="utf-8")
    store = pb.PromptStore(path)
    assert len(store.prompts) == 1
    assert store.onboarding_done is True  # istniejące dane => onboarding zaliczony


def test_store_load_corrupt_json_is_safe(tmp_path):
    path = tmp_path / "promptbase.json"
    path.write_text("{ to nie jest json", encoding="utf-8")
    store = pb.PromptStore(path)
    assert store.prompts == []


def test_store_invalid_theme_falls_back(tmp_path):
    path = tmp_path / "promptbase.json"
    path.write_text(json.dumps({"prompts": [], "theme": "nieistnieje"}), encoding="utf-8")
    store = pb.PromptStore(path)
    assert store.theme == "jasny"


def test_backup_rotation_keeps_limited_copies(tmp_path):
    store = _make_store(tmp_path)
    # Pierwszy zapis tworzy plik, kolejne rotują .bak1..bakN.
    for i in range(pb.PROMPT_BACKUP_KEEP + 3):
        store.prompts = [pb.Prompt(name=f"N{i}", content="c")]
        store.save()

    base = tmp_path / "promptbase.json"
    bak1 = base.with_suffix(".json.bak1")
    assert bak1.exists()
    # Najstarszy poza limitem nie istnieje.
    overflow = base.with_suffix(f".json.bak{pb.PROMPT_BACKUP_KEEP + 1}")
    assert not overflow.exists()
    # Liczba kopii nie przekracza limitu.
    baks = list(tmp_path.glob("promptbase.json.bak*"))
    assert len(baks) <= pb.PROMPT_BACKUP_KEEP


def test_backup_contains_previous_content(tmp_path):
    store = _make_store(tmp_path)
    store.prompts = [pb.Prompt(name="pierwszy", content="c")]
    store.save()
    store.prompts = [pb.Prompt(name="drugi", content="c")]
    store.save()

    bak1 = (tmp_path / "promptbase.json").with_suffix(".json.bak1")
    data = json.loads(bak1.read_text(encoding="utf-8"))
    names = [p["name"] for p in data["prompts"]]
    assert names == ["pierwszy"]


# --- status / etykiety -----------------------------------------------------

def test_status_label_roundtrip():
    for key in pb.STATUSES:
        label = pb.status_label(key)
        assert pb.status_key_from_label(label) == key


# --- ulubione --------------------------------------------------------------

def test_prompt_favorite_defaults_false():
    assert pb.Prompt(name="N", content="C").favorite is False


def test_prompt_favorite_roundtrip():
    p = pb.Prompt(name="N", content="C", favorite=True)
    assert pb.Prompt.from_dict(p.to_dict()).favorite is True


def test_prompt_favorite_missing_key_is_false():
    # Prompty z wersji 2.7 nie mają pola favorite — nie mogą się wywalić.
    assert pb.Prompt.from_dict({"name": "N", "content": "C"}).favorite is False


def test_store_persists_favorite(tmp_path):
    store = pb.PromptStore(tmp_path / "promptbase.json")
    store.prompts = [pb.Prompt(name="N", content="C", favorite=True)]
    store.save()
    assert pb.PromptStore(tmp_path / "promptbase.json").prompts[0].favorite is True


# --- wyszukiwarka: wiele słów i frazy --------------------------------------

def test_search_terms_splits_words():
    assert pb.search_terms("post linkedin") == ["post", "linkedin"]


def test_search_terms_keeps_quoted_phrase():
    assert pb.search_terms('"post na blog" seo') == ["post na blog", "seo"]


def test_search_terms_empty():
    assert pb.search_terms("") == []
    assert pb.search_terms("   ") == []


def test_search_terms_lowercased():
    assert pb.search_terms("SEO Blog") == ["seo", "blog"]


# --- historia: limit 20 ----------------------------------------------------

def test_history_limit_is_20():
    assert pb.PROMPT_HISTORY_MAX == 20


def test_push_history_respects_limit():
    p = pb.Prompt(name="N", content="C0")
    for i in range(30):
        p.content = f"C{i}"
        pb.push_prompt_history(p)
    assert len(p.history) == pb.PROMPT_HISTORY_MAX
    # Najnowsza wersja na początku.
    assert p.history[0]["content"] == "C29"


def test_push_history_skips_duplicate():
    p = pb.Prompt(name="N", content="C")
    pb.push_prompt_history(p)
    pb.push_prompt_history(p)
    assert len(p.history) == 1


# --- ustawienia AI w store -------------------------------------------------

def test_store_default_ai_settings(tmp_path):
    store = pb.PromptStore(tmp_path / "promptbase.json")
    assert store.ai_settings["engine"] in ("ollama", "openrouter")


def test_store_persists_ai_settings(tmp_path):
    path = tmp_path / "promptbase.json"
    store = pb.PromptStore(path)
    store.ai_settings["ollama_model"] = "llama3.2:3b"
    store.save()
    assert pb.PromptStore(path).ai_settings["ollama_model"] == "llama3.2:3b"


def test_store_ai_settings_no_api_key_saved(tmp_path):
    """Klucz OpenRouter nigdy nie może trafić do pliku danych."""
    path = tmp_path / "promptbase.json"
    store = pb.PromptStore(path)
    store.save()
    assert "api_key" not in path.read_text(encoding="utf-8").lower()
