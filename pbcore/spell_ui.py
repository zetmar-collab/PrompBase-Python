"""Podpięcie sprawdzania pisowni pod widget Text (podkreślenia + menu)."""

from __future__ import annotations

import threading
import tkinter as tk
from collections import OrderedDict
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from pbcore import spell
from pbcore.i18n import LANG_EN, get_language, t

MISSPELLED_TAG = "spell_error"
UNDERLINE_COLOR = "#d13438"

# Opóźnienie po ostatnim naciśnięciu klawisza — żeby nie sprawdzać przy
# każdej literze (polski słownik to ponad 300 tys. rdzeni).
RECHECK_DELAY_MS = 350

# Wczytane słowniki trzymamy globalnie: otwieranie kolejnych okien edycji
# nie może oznaczać ponownego parsowania kilkumegabajtowego pliku.
#
# Cache jest ograniczony, bo jeden słownik potrafi zająć sporo pamięci
# (zmierzone: pl_PL ok. 39 MB, en_US ok. 7 MB), a w systemie bywa ich
# kilkadziesiąt — przełączanie języków urosłoby do setek megabajtów.
# Dwa miejsca wystarczą na typowy układ „polski + angielski".
CACHE_MAX_ENTRIES = 2
_CACHE: OrderedDict[str, spell.Dictionary] = OrderedDict()
_CACHE_LOCK = threading.Lock()


def default_language_code() -> str:
    """Słownik pasujący do języka interfejsu, jeśli jest zainstalowany."""
    available = spell.available_dictionaries()
    preferred = ("en_US", "en_GB") if get_language() == LANG_EN else ("pl_PL", "pl")
    for code in preferred:
        if code in available:
            return code
    return next(iter(sorted(available)), "")


def get_dictionary(code: str) -> spell.Dictionary | None:
    """Zwraca słownik z pamięci podręcznej (wczytuje przy pierwszym użyciu)."""
    if not code:
        return None
    with _CACHE_LOCK:
        if code in _CACHE:
            _CACHE.move_to_end(code)  # ostatnio użyty zostaje najdłużej
            return _CACHE[code]
    path = spell.available_dictionaries().get(code)
    if not path:
        return None
    try:
        loaded = spell.load_dictionary(path)
    except (OSError, ValueError):
        return None
    with _CACHE_LOCK:
        _CACHE[code] = loaded
        _CACHE.move_to_end(code)
        while len(_CACHE) > CACHE_MAX_ENTRIES:
            _CACHE.popitem(last=False)
    return loaded


def forget_dictionary(code: str) -> None:
    with _CACHE_LOCK:
        _CACHE.pop(code, None)


class SpellHighlighter:
    """Podkreśla błędy w widgecie Text i obsługuje menu podręczne.

    Słownik wczytujemy w wątku, żeby otwarcie okna edycji nie zamarzało;
    pierwsze sprawdzenie odpala się dopiero, gdy dane są gotowe.
    """

    def __init__(self, widget: tk.Text, store=None):
        self.widget = widget
        self.store = store
        self.checker = spell.SpellChecker()
        self.language = ""
        self._job = None
        self._menu: tk.Menu | None = None
        self._destroyed = False
        self._result_lock = threading.Lock()
        self._pending: tuple[int, object] | None = None
        self._token = 0

        settings = getattr(store, "spell_settings", None) or {}
        self.enabled = bool(settings.get("enabled", True))

        try:
            widget.tag_configure(
                MISSPELLED_TAG, underline=True, underlinefg=UNDERLINE_COLOR
            )
        except tk.TclError:
            # Starsze Tk nie zna `underlinefg` — samo podkreślenie wystarczy.
            widget.tag_configure(MISSPELLED_TAG, underline=True)

        widget.bind("<KeyRelease>", self._schedule, add="+")
        widget.bind("<Button-3>", self._popup, add="+")
        widget.bind("<Destroy>", self._on_destroy, add="+")

        if self.enabled:
            stored = (settings.get("language") or "").strip()
            if stored:
                self.set_language(stored)
            else:
                # Wykrycie języka przegląda katalogi ze słownikami — robimy to
                # w tle, żeby otwarcie okna edycji nie czekało na dysk.
                self._detect_language_async()

    # --- cykl życia -------------------------------------------------------

    def _on_destroy(self, _event=None) -> None:
        self._destroyed = True
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _alive(self) -> bool:
        if self._destroyed:
            return False
        try:
            return bool(self.widget.winfo_exists())
        except tk.TclError:
            return False

    # --- konfiguracja -----------------------------------------------------

    def _start_background(self, produce) -> None:
        """Uruchamia `produce()` w wątku i odbiera wynik w wątku Tk.

        Tk nie jest bezpieczne wątkowo — wątek roboczy NIE dotyka widgetu
        (nawet `after()` czy `winfo_exists()` to wywołania Tcl). Wątek tylko
        odkłada wynik, a odbiera go pętla `after` należąca do wątku głównego.
        """
        with self._result_lock:
            self._pending = None
            self._token += 1
            token = self._token

        def worker() -> None:
            try:
                value = produce()
            except Exception:  # nie zabijamy wątku cichym wyjątkiem
                value = None
            with self._result_lock:
                self._pending = (token, value)

        threading.Thread(target=worker, daemon=True).start()
        self._poll_background()

    def _poll_background(self) -> None:
        """Sprawdza (już w wątku Tk), czy wątek roboczy coś odłożył."""
        if not self._alive():
            return
        with self._result_lock:
            pending = self._pending
            current = self._token
        if pending is None:
            try:
                self.widget.after(80, self._poll_background)
            except tk.TclError:
                pass
            return
        token, value = pending
        with self._result_lock:
            self._pending = None
        if token != current:
            return  # wynik z nieaktualnego żądania
        self._apply_background(value)

    def _apply_background(self, value) -> None:
        """Wynik zadania w tle: kod języka do ustawienia albo gotowy słownik."""
        if isinstance(value, spell.Dictionary) or value is None:
            self.checker = spell.SpellChecker(value)
            self.recheck()
        else:
            self.set_language(str(value))

    def _detect_language_async(self) -> None:
        self._start_background(default_language_code)

    def set_language(self, code: str) -> None:
        self.language = code or ""
        self._persist()
        if not self.language:
            self.checker = spell.SpellChecker()
            self._clear_tags()
            return

        with _CACHE_LOCK:
            cached = _CACHE.get(self.language)
        if cached is not None:
            self.checker = spell.SpellChecker(cached)
            self.recheck()
            return

        wanted = self.language
        self._start_background(lambda: get_dictionary(wanted))

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        self._persist()
        if self.enabled:
            if not self.language:
                self.set_language(default_language_code())
            else:
                self.recheck()
        else:
            self._clear_tags()

    def _persist(self) -> None:
        if self.store is None:
            return
        settings = getattr(self.store, "spell_settings", None)
        if not isinstance(settings, dict):
            return
        settings["enabled"] = self.enabled
        settings["language"] = self.language
        try:
            self.store.save()
        except (OSError, AttributeError):
            pass

    # --- sprawdzanie ------------------------------------------------------

    def _schedule(self, _event=None) -> None:
        if not self.enabled or not self._alive():
            return
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
        self._job = self.widget.after(RECHECK_DELAY_MS, self.recheck)

    def _clear_tags(self) -> None:
        if not self._alive():
            return
        try:
            self.widget.tag_remove(MISSPELLED_TAG, "1.0", "end")
        except tk.TclError:
            pass

    def recheck(self) -> None:
        self._job = None
        if not self._alive():
            return
        self._clear_tags()
        if not self.enabled or not self.checker.ready:
            return
        try:
            text = self.widget.get("1.0", "end-1c")
        except tk.TclError:
            return
        for _word, start, end in self.checker.check_text(text):
            try:
                self.widget.tag_add(
                    MISSPELLED_TAG, f"1.0+{start}c", f"1.0+{end}c"
                )
            except tk.TclError:
                break

    # --- menu podręczne ---------------------------------------------------

    def _word_at(self, index: str) -> tuple[str, str, str] | None:
        """Błędne słowo pod kursorem jako (słowo, indeks_od, indeks_do)."""
        ranges = self.widget.tag_ranges(MISSPELLED_TAG)
        for i in range(0, len(ranges), 2):
            start, end = ranges[i], ranges[i + 1]
            if self.widget.compare(index, ">=", start) and self.widget.compare(
                index, "<", end
            ):
                return self.widget.get(start, end), str(start), str(end)
        return None

    def _popup(self, event) -> str | None:
        if not self._alive():
            return None
        index = self.widget.index(f"@{event.x},{event.y}")
        menu = tk.Menu(self.widget, tearoff=0)
        self._menu = menu

        hit = self._word_at(index) if self.enabled else None
        if hit:
            word, start, end = hit
            for suggestion in self.checker.suggest(word):
                menu.add_command(
                    label=suggestion,
                    command=lambda s=suggestion, a=start, b=end: self._replace(a, b, s),
                )
            if menu.index("end") is None:
                menu.add_command(label=t('(brak propozycji)'), state="disabled")
            menu.add_separator()
            menu.add_command(
                label=t('Dodaj do słownika'), command=lambda w=word: self._add_word(w)
            )
            menu.add_command(
                label=t('Ignoruj wszędzie'), command=lambda w=word: self._ignore_word(w)
            )
            menu.add_separator()

        menu.add_command(
            label=t('Sprawdzanie pisowni: wyłącz') if self.enabled
            else t('Sprawdzanie pisowni: włącz'),
            command=lambda: self.set_enabled(not self.enabled),
        )
        menu.add_command(label=t('Język pisowni…'), command=self.choose_language)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _replace(self, start: str, end: str, replacement: str) -> None:
        self.widget.delete(start, end)
        self.widget.insert(start, replacement)
        self.recheck()

    def _add_word(self, word: str) -> None:
        self.checker.add_word(word)
        self.recheck()

    def _ignore_word(self, word: str) -> None:
        self.checker.ignore_word(word)
        self.recheck()

    def choose_language(self) -> None:
        dialog = SpellLanguageDialog(self.widget.winfo_toplevel(), self.language)
        self.widget.wait_window(dialog)
        if dialog.result is not None:
            self.set_language(dialog.result)


class SpellLanguageDialog(tk.Toplevel):
    """Wybór języka pisowni i instalacja słowników Hunspell."""

    def __init__(self, parent, current: str = ""):
        super().__init__(parent)
        self.title(t('Język pisowni'))
        self.result: str | None = None
        self.resizable(False, False)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text=t('Wybierz język sprawdzania pisowni:')).pack(anchor="w")

        self.listbox = tk.Listbox(body, height=12, width=34, exportselection=False)
        self.listbox.pack(fill="both", expand=True, pady=(8, 4))
        self.codes: list[str] = []
        self._fill(current)

        ttk.Label(
            body,
            text=t('Słowniki w formacie Hunspell (.dic + .aff), takie jak w LibreOffice.'),
            wraplength=320,
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(
            buttons, text=t('Zainstaluj słownik…'), command=self._install
        ).pack(side="left")
        ttk.Button(buttons, text=t('Anuluj'), command=self.destroy).pack(
            side="right", padx=(4, 0)
        )
        ttk.Button(buttons, text=t('Wybierz'), command=self._accept).pack(side="right")

        self.listbox.bind("<Double-Button-1>", lambda _e: self._accept())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.transient(parent)
        self.grab_set()

    def _fill(self, current: str) -> None:
        self.listbox.delete(0, "end")
        self.codes = sorted(spell.available_dictionaries())
        self.listbox.insert("end", t('(bez sprawdzania)'))
        for code in self.codes:
            self.listbox.insert("end", code)
        if current in self.codes:
            index = self.codes.index(current) + 1
        else:
            index = 0
        self.listbox.selection_set(index)
        self.listbox.see(index)

    def _accept(self) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        self.result = "" if index == 0 else self.codes[index - 1]
        self.destroy()

    def _install(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title=t('Wybierz plik słownika (.dic)'),
            filetypes=[(t('Słownik Hunspell'), "*.dic"), (t('Wszystkie pliki'), "*.*")],
        )
        if not path:
            return
        try:
            installed = spell.install_dictionary(Path(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror(t('Język pisowni'), str(exc), parent=self)
            return
        forget_dictionary(installed.stem)
        self._fill(installed.stem)
        messagebox.showinfo(
            t('Język pisowni'),
            t('Zainstalowano słownik: ') + installed.stem,
            parent=self,
        )
