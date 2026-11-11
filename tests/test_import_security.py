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


# --- ścieżka PWA ------------------------------------------------------------
#
# Poprawka dla importu kopii zapasowej nie objęła sąsiedniej ścieżki: import
# z PWA ustawiał `n8n_url` z okna importu bez pytania, w obu trybach
# (zastąp i dopisz). Wykryte przez automatyczny przegląd bezpieczeństwa.

class _PwaDialog:
    """Atrapa okna importu PWA z gotowym wynikiem."""

    def __init__(self, *_a, url=EVIL, **_k):
        self.imported = [pb.Prompt(name="Z PWA", content="treść")]
        self.n8n_url = url
        self.theme = ""


class _PwaApp:
    def __init__(self, current_url=""):
        self.store = type(
            "S", (), {"n8n_url": current_url, "prompts": [], "theme": "jasny"}
        )()
        self.root = None
        self.saved = 0
        self.theme_var = type("V", (), {"set": lambda _s, _v: None})()

    def wait_window(self, _w):
        pass

    def apply_theme(self, save=True):
        pass

    # import_from_pwa woła self.root.wait_window(...) — atrapa root to sam obiekt.
    def get_theme_colors(self):
        return {}

    def save_store(self):
        self.saved += 1

    def refresh_all(self):
        pass

    def set_status(self, _t):
        pass

    _confirm_imported_n8n_url = pb.PrompBaseApp._confirm_imported_n8n_url
    import_from_pwa = pb.PrompBaseApp.import_from_pwa


def _run_pwa_import(monkeypatch, *, mode, answer, current=""):
    from pbcore import app_io

    asked: list[str] = []
    monkeypatch.setattr(app_io, "PwaImportDialog", _PwaDialog)
    monkeypatch.setattr(app_io.messagebox, "askyesnocancel", lambda *a, **k: mode)

    def fake_yesno(_title, message, **_kw):
        asked.append(message)
        return answer

    monkeypatch.setattr(app_io.messagebox, "askyesno", fake_yesno)
    app = _PwaApp(current_url=current)
    app.root = app  # wait_window(dialog) jest wołane na root
    app.import_from_pwa()
    return app, asked


@pytest.mark.parametrize("mode, label", [(False, "zastąp"), (True, "dopisz")])
def test_pwa_import_asks_before_setting_webhook(monkeypatch, mode, label):
    app, asked = _run_pwa_import(monkeypatch, mode=mode, answer=True)
    assert len(asked) == 1, f"tryb {label}: brak pytania o adres webhooka"
    assert EVIL in asked[0]
    assert app.store.n8n_url == EVIL


@pytest.mark.parametrize("mode", [False, True])
def test_pwa_import_declined_url_is_not_applied(monkeypatch, mode):
    app, _asked = _run_pwa_import(monkeypatch, mode=mode, answer=False, current=OWN)
    assert app.store.n8n_url == OWN
    # Sam import promptów ma przejść mimo odmowy zmiany adresu.
    assert [p.name for p in app.store.prompts] == ["Z PWA"]


def test_pwa_import_declined_with_no_current_url_stays_empty(monkeypatch):
    app, _asked = _run_pwa_import(monkeypatch, mode=True, answer=False, current="")
    assert app.store.n8n_url == ""


def test_no_direct_webhook_assignment_from_imports():
    """Straż na przyszłość: żaden import nie ustawia n8n_url z pominięciem pytania."""
    import ast
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "pbcore" / "app_io.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Attribute) and t.attr == "n8n_url" for t in node.targets)
        ):
            assert "_confirm_imported_n8n_url" in ast.unparse(node.value), (
                f"app_io.py:{node.lineno}: n8n_url ustawiany bez potwierdzenia"
            )
