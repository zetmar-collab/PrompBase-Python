"""Praca w tle nie może zamrażać okna ani dotykać Tk z obcego wątku.

Import dużego arkusza działał wcześniej w wątku interfejsu — okno zamarzało
bez możliwości anulowania. `run_in_background` liczy w wątku roboczym,
a wynik oddaje pętlą `after` należącą do wątku głównego.
"""

from __future__ import annotations

import threading
import time
import tkinter
from contextlib import contextmanager
from tkinter import Tk

import pytest

from pbcore import app as app_module


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


class _App:
    """Sam mechanizm tła, bez budowania całego okna aplikacji."""

    def __init__(self, root):
        self.root = root
        self.statuses: list[str] = []

    def set_status(self, text):
        self.statuses.append(text)

    run_in_background = app_module.PrompBaseApp.run_in_background


def _pump(root, ready, timeout=5.0):
    """Kręci pętlą Tk, aż `ready()` zwróci prawdę (albo minie czas).

    Warunek musi być funkcją — przekazana wartość byłaby policzona raz
    i pętla kręciłaby się do końca limitu, niczego nie sprawdzając.
    """
    deadline = time.time() + timeout
    while not ready() and time.time() < deadline:
        root.update()
        time.sleep(0.02)
    return ready()


def test_result_arrives_on_the_tk_thread():
    with tk_root() as root:
        app = _App(root)
        got: dict = {}
        main_thread = threading.get_ident()

        def work():
            # Wątek roboczy to NIE wątek Tk — tu nie wolno dotykać okna.
            got["worker_thread"] = threading.get_ident()
            return 21 * 2

        def done(value):
            got["value"] = value
            got["callback_thread"] = threading.get_ident()

        app.run_in_background(work, done, busy_status="pracuję…")
        assert _pump(root, lambda: "value" in got), "wynik nie wrócił w wątku Tk"

        assert got.get("value") == 42
        assert got["worker_thread"] != main_thread, "praca nie trafiła do osobnego wątku"
        assert got["callback_thread"] == main_thread, "wynik odebrany poza wątkiem Tk"
        assert app.statuses[0] == "pracuję…"


def test_window_stays_responsive_while_working():
    """Dowód właściwy: w trakcie pracy okno nadal przetwarza zdarzenia."""
    with tk_root() as root:
        app = _App(root)
        release = threading.Event()
        finished: dict = {}
        ticks = {"n": 0}

        def tick():
            ticks["n"] += 1
            if not finished:
                root.after(10, tick)

        root.after(10, tick)
        app.run_in_background(
            lambda: (release.wait(2.0), "gotowe")[1],
            lambda value: finished.setdefault("value", value),
        )

        # Zanim zwolnimy pracę, interfejs musi zdążyć wykonać kilka zdarzeń.
        deadline = time.time() + 1.5
        while ticks["n"] < 5 and time.time() < deadline:
            root.update()
            time.sleep(0.02)
        assert ticks["n"] >= 5, "okno było zablokowane w trakcie pracy w tle"

        release.set()
        assert _pump(root, lambda: "value" in finished)
        assert finished.get("value") == "gotowe"


def test_error_goes_to_the_handler_not_the_worker():
    with tk_root() as root:
        app = _App(root)
        caught: dict = {}

        def boom():
            raise ValueError("awaria w tle")

        app.run_in_background(
            boom,
            lambda _v: caught.setdefault("done", True),
            on_error=lambda exc: caught.setdefault("error", exc),
        )
        assert _pump(root, lambda: "error" in caught)

        assert isinstance(caught.get("error"), ValueError)
        assert "done" not in caught
        assert str(caught["error"]) == "awaria w tle"
