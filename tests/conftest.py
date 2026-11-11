"""Wspólne zabezpieczenie: testy nigdy nie dotykają prawdziwych danych.

`app_data_dir()` wskazuje na %APPDATA%\\PrompBase, gdzie leży biblioteka
promptów użytkownika, klucz API, słownik własnych słów i dziennik błędów.
Bez tej izolacji wystarczył jeden test bez własnego monkeypatcha, żeby
dopisać coś do prawdziwego katalogu — zdarzyło się to przy dzienniku błędów.

Fixture jest `autouse`, więc obejmuje też testy pisane w przyszłości.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_user_data(monkeypatch, tmp_path):
    appdata = tmp_path / "AppData"
    (appdata / "PrompBase").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setenv("XDG_DATA_HOME", str(appdata))
    monkeypatch.setenv("HOME", str(tmp_path))

    # Moduły trzymają własne odwołania do app_data_dir — podmieniamy każde.
    from pbcore import ai, core, models, spell

    target = appdata / "PrompBase"
    for module in (core, ai, models, spell):
        if hasattr(module, "app_data_dir"):
            monkeypatch.setattr(module, "app_data_dir", lambda _t=target: _t)

    return target
