"""Import cudzej kopii nie może po cichu przestawiać adresu webhooka n8n.

`validate_n8n_url` wymaga tylko http(s) i tekstu „/webhook", więc adres
atakującego przechodzi walidację. Wcześniej tryb „zastąp bibliotekę" brał
`n8n_url` z pliku bez pokazania go użytkownikowi — udostępniona kopia
zapasowa przekierowywała późniejszą wysyłkę promptów na cudzy serwer.
"""

from __future__ import annotations

import pytest

import promptbase as pb


class _FakeStore:
    def __init__(self, url=""):
        self.n8n_url = url


class _FakeApp:
    """Minimalny obiekt z samą testowaną metodą — bez budowania okna Tk."""

    def __init__(self, current_url="", answer=True):
        self.store = _FakeStore(current_url)
        self.root = None
        self.answer = answer
        self.asked: list[str] = []

    _confirm_imported_n8n_url = pb.PrompBaseApp._confirm_imported_n8n_url


@pytest.fixture
def ask(monkeypatch):
    def _setup(answer):
        calls: list[str] = []

        def fake_askyesno(_title, message, **_kw):
            calls.append(message)
            return answer

        monkeypatch.setattr(pb.messagebox, "askyesno", fake_askyesno)
        return calls

    return _setup


EVIL = "https://atakujacy.example.com/webhook/zbieraj"
OWN = "https://moja-instancja.app.n8n.cloud/webhook/prompbase"


def test_new_url_requires_confirmation_and_is_shown(ask):
    calls = ask(True)
    app = _FakeApp(current_url=OWN)
    assert app._confirm_imported_n8n_url(EVIL) == EVIL
    assert len(calls) == 1
    # Użytkownik musi zobaczyć konkretny adres, nie samo „ustawienia z pliku".
    assert EVIL in calls[0]


def test_declining_keeps_the_existing_url(ask):
    calls = ask(False)
    app = _FakeApp(current_url=OWN)
    assert app._confirm_imported_n8n_url(EVIL) == OWN
    assert len(calls) == 1


def test_no_question_when_url_unchanged(ask):
    calls = ask(True)
    app = _FakeApp(current_url=OWN)
    assert app._confirm_imported_n8n_url(OWN) == OWN
    assert calls == []


@pytest.mark.parametrize("empty", ["", None, "   "])
def test_empty_url_in_file_keeps_current(ask, empty):
    calls = ask(True)
    app = _FakeApp(current_url=OWN)
    assert app._confirm_imported_n8n_url(empty) == OWN
    assert calls == []


def test_evil_url_passes_validation_so_the_prompt_is_the_only_guard():
    """Dowód, że sama walidacja nie wystarcza — stąd potwierdzenie."""
    assert pb.validate_n8n_url(EVIL) is True
