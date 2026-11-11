"""Odpowiedzi HTTP muszą mieć limit rozmiaru.

Adres Ollamy (`ai_settings.ollama_host`) i webhooka n8n ustawia użytkownik,
więc endpoint nie musi być zaufany ani sprawny. `response.read()` bez
argumentu wciągało całe ciało do pamięci — wystarczył serwer odpowiadający
strumieniem bez końca, żeby wyczerpać RAM.
"""

from __future__ import annotations

import io

import pytest

from pbcore import ai


class _EndlessResponse(io.RawIOBase):
    """Udaje odpowiedź, która nigdy się nie kończy; liczy żądane bajty."""

    def __init__(self):
        self.requested: list[int | None] = []

    def read(self, amount=None):
        self.requested.append(amount)
        if amount is None or amount < 0:
            raise AssertionError("odczyt bez limitu — to jest właśnie ten błąd")
        return b"x" * amount

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def test_post_json_limits_response(monkeypatch):
    fake = _EndlessResponse()
    monkeypatch.setattr(ai.request, "urlopen", lambda *a, **k: fake)

    with pytest.raises(ai.AiError) as err:
        ai._post_json("http://localhost:11434/api/chat", {"a": 1}, {}, 5)

    # Odczyt był ograniczony, a nadmiarowa odpowiedź odrzucona zrozumiałym błędem.
    assert fake.requested and all(n is not None for n in fake.requested)
    assert fake.requested[0] <= ai.MAX_RESPONSE_BYTES + 1
    assert "MB" in str(err.value)


def test_response_within_limit_is_parsed(monkeypatch):
    payload = b'{"message": {"content": "gotowe"}}'

    class _Ok(io.RawIOBase):
        def read(self, amount=None):
            assert amount is not None, "odczyt bez limitu"
            return payload

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr(ai.request, "urlopen", lambda *a, **k: _Ok())
    data = ai._post_json("http://localhost:11434/api/chat", {"a": 1}, {}, 5)
    assert data["message"]["content"] == "gotowe"


def test_limits_are_sane():
    assert 0 < ai.MAX_ERROR_BYTES < ai.MAX_RESPONSE_BYTES
    assert ai.MAX_RESPONSE_BYTES >= 1024 * 1024  # zwykłe odpowiedzi muszą przechodzić
