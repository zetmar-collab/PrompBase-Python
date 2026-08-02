"""Testy warstwy AI (bez sieci).

Sprawdzamy budowanie żądań, parsowanie odpowiedzi i obsługę błędów —
wszystko na danych w pamięci, więc testy działają w CI bez Ollamy i bez
klucza OpenRouter.
"""

from __future__ import annotations

import pytest

from pbcore import ai

# --- prompty systemowe -----------------------------------------------------


def test_system_prompt_improve_mentions_rules():
    text = ai.build_system_prompt(ai.ACTION_IMPROVE)
    assert "WYŁĄCZNIE" in text
    assert "[TEMAT]" in text  # instrukcja zachowania zmiennych


def test_system_prompt_translate_uses_language():
    text = ai.build_system_prompt(ai.ACTION_TRANSLATE, language="niemiecki")
    assert "niemiecki" in text


def test_system_prompt_translate_defaults_to_english():
    assert "angielski" in ai.build_system_prompt(ai.ACTION_TRANSLATE)


@pytest.mark.parametrize("target", list(ai.ADAPT_TARGETS))
def test_system_prompt_adapt_known_targets(target):
    text = ai.build_system_prompt(ai.ACTION_ADAPT, target=target)
    assert ai.ADAPT_TARGETS[target][:25] in text


def test_system_prompt_adapt_unknown_target_is_generic():
    text = ai.build_system_prompt(ai.ACTION_ADAPT, target="NowaPlatforma")
    assert "NowaPlatforma" in text


def test_midjourney_prompt_mentions_parameters():
    text = ai.build_system_prompt(ai.ACTION_ADAPT, target="Midjourney")
    assert "--ar" in text


# --- czyszczenie odpowiedzi ------------------------------------------------


def test_clean_ai_output_strips_code_fence():
    raw = "```\nTreść promptu\n```"
    assert ai.clean_ai_output(raw) == "Treść promptu"


def test_clean_ai_output_strips_language_fence():
    raw = "```markdown\nTekst\nDruga linia\n```"
    assert ai.clean_ai_output(raw) == "Tekst\nDruga linia"


def test_clean_ai_output_plain_text_untouched():
    assert ai.clean_ai_output("  zwykły tekst  ") == "zwykły tekst"


# --- budowanie żądań -------------------------------------------------------


def test_openrouter_payload_shape():
    payload = ai.openrouter_payload("model-x", "SYS", "USER")
    assert payload["model"] == "model-x"
    assert payload["messages"][0] == {"role": "system", "content": "SYS"}
    assert payload["messages"][1] == {"role": "user", "content": "USER"}


def test_openrouter_payload_default_model():
    assert ai.openrouter_payload("", "s", "u")["model"] == ai.OPENROUTER_DEFAULT_MODEL


def test_ollama_payload_disables_streaming():
    payload = ai.ollama_payload("m", "s", "u")
    assert payload["stream"] is False


# --- parsowanie odpowiedzi -------------------------------------------------


def test_parse_openrouter_response():
    data = {"choices": [{"message": {"content": "wynik"}}]}
    assert ai.parse_openrouter_response(data) == "wynik"


def test_parse_openrouter_empty_choices_raises():
    with pytest.raises(ai.AiError):
        ai.parse_openrouter_response({"choices": []})


def test_parse_ollama_chat_response():
    assert ai.parse_ollama_response({"message": {"content": "abc"}}) == "abc"


def test_parse_ollama_generate_fallback():
    assert ai.parse_ollama_response({"response": "xyz"}) == "xyz"


def test_parse_ollama_missing_content_raises():
    with pytest.raises(ai.AiError):
        ai.parse_ollama_response({})


# --- host / modele ---------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", ai.OLLAMA_DEFAULT_HOST),
        ("localhost:11434", "http://localhost:11434"),
        ("http://localhost:11434/", "http://localhost:11434"),
        ("https://zdalny:1234", "https://zdalny:1234"),
    ],
)
def test_normalize_ollama_host(raw, expected):
    assert ai.normalize_ollama_host(raw) == expected


def test_parse_ollama_models_skips_embedding_only():
    data = {
        "models": [
            {"name": "gen:latest", "capabilities": ["completion"]},
            {"name": "emb:latest", "capabilities": ["embedding"]},
            {"name": "bez-capabilities:latest"},
        ]
    }
    names = ai.parse_ollama_models(data)
    assert "gen:latest" in names
    assert "emb:latest" not in names
    assert "bez-capabilities:latest" in names  # brak info => dopuszczamy


def test_parse_ollama_models_deduplicates():
    data = {"models": [{"name": "a"}, {"name": "a"}]}
    assert ai.parse_ollama_models(data) == ["a"]


def test_parse_ollama_models_empty():
    assert ai.parse_ollama_models({}) == []


def test_resolve_ollama_model_prefers_installed(monkeypatch):
    monkeypatch.setattr(ai, "list_ollama_models", lambda host=None: ["llama3.2:3b", "qwen:latest"])
    # Model spoza listy => pierwszy zainstalowany.
    assert ai.resolve_ollama_model("nieistnieje", "h") == "llama3.2:3b"
    # Dokładne trafienie zostaje.
    assert ai.resolve_ollama_model("qwen:latest", "h") == "qwen:latest"
    # Dopasowanie po prefiksie (llama3.2 -> llama3.2:3b).
    assert ai.resolve_ollama_model("llama3.2", "h") == "llama3.2:3b"


def test_resolve_ollama_model_without_server_keeps_value(monkeypatch):
    monkeypatch.setattr(ai, "list_ollama_models", lambda host=None: [])
    assert ai.resolve_ollama_model("cokolwiek", "h") == "cokolwiek"


# --- walidacja wejścia / błędy --------------------------------------------


def test_run_ai_action_empty_content_raises():
    with pytest.raises(ai.AiError):
        ai.run_ai_action(engine=ai.ENGINE_OLLAMA, action=ai.ACTION_IMPROVE, content="   ")


def test_run_ai_action_unknown_engine_raises():
    with pytest.raises(ai.AiError, match="Nieznany silnik"):
        ai.run_ai_action(engine="cokolwiek", action=ai.ACTION_IMPROVE, content="tekst")


def test_openrouter_without_key_raises(monkeypatch):
    monkeypatch.delenv(ai.OPENROUTER_API_KEY_ENV, raising=False)
    with pytest.raises(ai.AiError, match=ai.OPENROUTER_API_KEY_ENV):
        ai.run_openrouter("m", "s", "u")


def test_openrouter_api_key_read_from_env(monkeypatch):
    monkeypatch.setenv(ai.OPENROUTER_API_KEY_ENV, "  sk-test  ")
    assert ai.openrouter_api_key() == "sk-test"


def test_run_ai_action_uses_engine(monkeypatch):
    """Akcja trafia do właściwego silnika z poprawnym promptem systemowym."""
    captured = {}

    def fake_ollama(model, system_prompt, content, *, host="", timeout=0):
        captured["model"] = model
        captured["system"] = system_prompt
        captured["content"] = content
        return "WYNIK"

    monkeypatch.setattr(ai, "run_ollama", fake_ollama)
    monkeypatch.setattr(ai, "resolve_ollama_model", lambda m, h: m or "auto")

    out = ai.run_ai_action(
        engine=ai.ENGINE_OLLAMA,
        action=ai.ACTION_TRANSLATE,
        content="Tekst źródłowy",
        model="m1",
        language="hiszpański",
    )
    assert out == "WYNIK"
    assert captured["content"] == "Tekst źródłowy"
    assert "hiszpański" in captured["system"]


def test_run_ai_action_empty_model_answer_raises(monkeypatch):
    monkeypatch.setattr(ai, "resolve_ollama_model", lambda m, h: m)
    monkeypatch.setattr(ai, "run_ollama", lambda *a, **k: "   ")
    with pytest.raises(ai.AiError, match="pustą odpowiedź"):
        ai.run_ai_action(engine=ai.ENGINE_OLLAMA, action=ai.ACTION_IMPROVE, content="x")
