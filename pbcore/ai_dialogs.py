"""Okna dialogowe warstwy AI: konfiguracja silnika i podgląd wyniku.

Wywołania sieciowe biegną w wątku roboczym, żeby okno nie zamarzało; wynik
wraca do wątku Tk przez `after`, bo widżetów nie wolno dotykać z innego wątku.
"""

from __future__ import annotations

import threading
import webbrowser
from tkinter import (
    END,
    BooleanVar,
    StringVar,
    Toplevel,
    W,
    messagebox,
    ttk,
)

from pbcore import ai
from pbcore.core import APP_NAME, REPORT_ISSUE_URL, apply_widget_theme, theme_colors
from pbcore.i18n import t


class AiConfigDialog(Toplevel):
    """Wybór silnika (OpenRouter / Ollama), modelu i języka tłumaczeń."""

    def __init__(self, parent, settings: dict, *, theme_getter=None):
        super().__init__(parent)
        self.theme_getter = theme_getter
        self.title(t('Konfiguracja AI'))
        self.geometry("660x510")
        self.minsize(600, 470)
        self.result: dict | None = None

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text=t('Silnik AI'), font=("Segoe UI", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=W, pady=(0, 8)
        )

        self.engine_var = StringVar(value=ai.ENGINES.get(settings.get("engine", ai.ENGINE_OLLAMA), ""))
        ttk.Label(body, text=t('Silnik')).grid(row=1, column=0, sticky=W, pady=4)
        engine_box = ttk.Combobox(
            body,
            textvariable=self.engine_var,
            values=list(ai.ENGINES.values()),
            state="readonly",
        )
        engine_box.grid(row=1, column=1, sticky="ew", pady=4)
        engine_box.bind("<<ComboboxSelected>>", lambda _e: self._update_hint())

        ttk.Label(body, text=t('Model OpenRouter')).grid(row=2, column=0, sticky=W, pady=4)
        self.or_model_var = StringVar(value=settings.get("openrouter_model", ai.OPENROUTER_DEFAULT_MODEL))
        ttk.Combobox(
            body,
            textvariable=self.or_model_var,
            values=[
                "anthropic/claude-sonnet-4.5",
                "anthropic/claude-opus-4.1",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "google/gemini-2.5-pro",
                "meta-llama/llama-3.3-70b-instruct",
                "deepseek/deepseek-chat",
            ],
        ).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(body, text=t('Klucz OpenRouter')).grid(row=3, column=0, sticky=W, pady=4)
        key_row = ttk.Frame(body)
        key_row.grid(row=3, column=1, sticky="ew", pady=4)
        key_row.columnconfigure(0, weight=1)
        self.api_key_var = StringVar(value=ai.load_stored_api_key())
        self.key_entry = ttk.Entry(key_row, textvariable=self.api_key_var, show="*")
        self.key_entry.grid(row=0, column=0, sticky="ew")
        self.show_key = BooleanVar(value=False)
        ttk.Checkbutton(key_row, text=t('Pokaż'), variable=self.show_key, command=self._toggle_key).grid(
            row=0, column=1, padx=(6, 0)
        )
        ttk.Button(key_row, text=t('Wyczyść'), command=self._clear_key).grid(row=0, column=2, padx=(6, 0))

        ttk.Label(body, text=t('Host Ollama')).grid(row=4, column=0, sticky=W, pady=4)
        self.host_var = StringVar(value=settings.get("ollama_host", ai.OLLAMA_DEFAULT_HOST))
        ttk.Entry(body, textvariable=self.host_var).grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(body, text=t('Model Ollama')).grid(row=5, column=0, sticky=W, pady=4)
        self.ollama_model_var = StringVar(value=settings.get("ollama_model", ai.OLLAMA_DEFAULT_MODEL))
        self.ollama_box = ttk.Combobox(body, textvariable=self.ollama_model_var, values=[])
        self.ollama_box.grid(row=5, column=1, sticky="ew", pady=4)

        ttk.Button(body, text=t('Wykryj modele Ollama'), command=self.detect_models).grid(
            row=6, column=1, sticky=W, pady=(0, 8)
        )

        ttk.Label(body, text=t('Język tłumaczeń')).grid(row=7, column=0, sticky=W, pady=4)
        self.lang_var = StringVar(value=settings.get("translate_language", "angielski"))
        ttk.Combobox(
            body,
            textvariable=self.lang_var,
            values=ai.TRANSLATE_LANGUAGES,
            state="readonly",
        ).grid(row=7, column=1, sticky="ew", pady=4)

        self.hint = ttk.Label(body, text="", wraplength=560, justify="left")
        self.hint.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        buttons = ttk.Frame(body)
        buttons.grid(row=9, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text=t('Anuluj'), command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text=t('Zapisz'), command=self.save).pack(side="right")

        self._update_hint()
        self.transient(parent)
        self.grab_set()

    def _engine_key(self) -> str:
        label = self.engine_var.get()
        for key, value in ai.ENGINES.items():
            if value == label:
                return key
        return ai.ENGINE_OLLAMA

    def _toggle_key(self) -> None:
        self.key_entry.configure(show="" if self.show_key.get() else "*")

    def _clear_key(self) -> None:
        self.api_key_var.set("")

    def _update_hint(self) -> None:
        if self._engine_key() == ai.ENGINE_OPENROUTER:
            source = ai.api_key_source()
            if source == "env":
                state = f"{t('wykryty ze zmiennej ')}{ai.OPENROUTER_API_KEY_ENV}{t(' (ma pierwszeństwo)')}"
            elif source == "plik":
                state = t("zapisany w ustawieniach")
            else:
                state = t("BRAK")
            self.hint.configure(
                text=(
                    (str(t('OpenRouter — klucz API: ')) + str(state) + str(t('.\nKlucz możesz wpisać powyżej (zapisujemy go w osobnym pliku ')) + str(ai.api_key_file().name) + str(t(' w folderze danych, poza promptbase.json — dzięki temu nie trafia do kopii zapasowych ani eksportu do chmury).\nAlternatywnie ustaw zmienną środowiskową ')) + str(ai.OPENROUTER_API_KEY_ENV))
                    + t(". Klucz zdobędziesz na https://openrouter.ai/keys")
                )
            )
        else:
            self.hint.configure(
                text=(
                    t('Ollama — działa lokalnie, bez klucza i bez wysyłania danych do sieci. Upewnij się, że aplikacja Ollama jest uruchomiona, i wybierz zainstalowany model (przycisk „Wykryj modele Ollama”).')
                )
            )

    def detect_models(self) -> None:
        models = ai.list_ollama_models(self.host_var.get())
        if not models:
            messagebox.showwarning(
                APP_NAME,
                t('Nie znaleziono modeli. Sprawdź, czy Ollama jest uruchomiona, a następnie pobierz model, np. w terminalu:\n\n    ollama pull llama3.1'),
                parent=self,
            )
            return
        self.ollama_box.configure(values=models)
        if self.ollama_model_var.get() not in models:
            self.ollama_model_var.set(models[0])
        messagebox.showinfo(APP_NAME, f"{t('Znaleziono modeli: ')}{len(models)}", parent=self)

    def save(self) -> None:
        # Klucz zapisujemy osobno — nigdy w promptbase.json.
        ai.save_stored_api_key(self.api_key_var.get())
        self.result = {
            "engine": self._engine_key(),
            "openrouter_model": self.or_model_var.get().strip() or ai.OPENROUTER_DEFAULT_MODEL,
            "ollama_model": self.ollama_model_var.get().strip() or ai.OLLAMA_DEFAULT_MODEL,
            "ollama_host": self.host_var.get().strip() or ai.OLLAMA_DEFAULT_HOST,
            "translate_language": self.lang_var.get().strip() or "angielski",
        }
        self.destroy()


class AiResultDialog(Toplevel):
    """Uruchamia akcję AI i pokazuje wynik obok oryginału.

    Zwraca decyzję użytkownika: "replace" (zastąp treść), "new" (zapisz jako
    nowy prompt) albo None (anulowano).
    """

    def __init__(self, parent, *, title: str, original: str, runner, theme_getter=None):
        super().__init__(parent)
        self.theme_getter = theme_getter
        self.runner = runner
        self.title(title)
        self.geometry("900x600")
        self.minsize(720, 480)
        self.decision: str | None = None
        self.result_text: str = ""
        self._closed = False

        body = ttk.Frame(self, padding=14)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        ttk.Label(body, text=t('Oryginał'), font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky=W)
        ttk.Label(body, text=t('Wynik AI'), font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=W, padx=(10, 0))

        self.left = self._text(body)
        self.left.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self.left.insert("1.0", original)
        self.left.configure(state="disabled")

        self.right = self._text(body)
        self.right.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(4, 0))
        self.right.insert("1.0", t('Pracuję… to może potrwać kilkanaście sekund.'))
        self.right.configure(state="disabled")

        self.status = ttk.Label(body, text=t('Wysyłam zapytanie do modelu…'))
        self.status.grid(row=2, column=0, columnspan=2, sticky=W, pady=(10, 0))

        self.buttons = ttk.Frame(body)
        self.buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        # Wymóg Microsoft Store 11.16 (Live Generative AI Content): użytkownik
        # musi mieć możliwość zgłoszenia nieodpowiedniej treści wygenerowanej
        # przez AI. Przycisk po lewej, aktywny dopiero gdy jest wynik.
        self.report_btn = ttk.Button(
            self.buttons,
            text=t('⚠ Zgłoś problem'),
            command=self._report_content,
            state="disabled",
        )
        self.report_btn.pack(side="left")
        self.cancel_btn = ttk.Button(self.buttons, text=t('Anuluj'), command=self.destroy)
        self.cancel_btn.pack(side="right", padx=(8, 0))
        self.new_btn = ttk.Button(self.buttons, text=t('Zapisz jako nowy'), command=self._save_new, state="disabled")
        self.new_btn.pack(side="right", padx=(8, 0))
        self.replace_btn = ttk.Button(self.buttons, text=t('Zastąp treść'), command=self._replace, state="disabled")
        self.replace_btn.pack(side="right")

        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start()

    def _text(self, parent):
        from tkinter import Text

        widget = Text(parent, wrap="word", height=20, width=40, relief="flat", borderwidth=1)
        if self.theme_getter:
            apply_widget_theme(widget, self.theme_getter())
        else:
            apply_widget_theme(widget, theme_colors("jasny"))
        return widget

    def _on_close(self) -> None:
        self._closed = True
        self.destroy()

    def _start(self) -> None:
        def worker():
            try:
                text = self.runner()
                self.after(0, lambda: self._done(text, None))
            except ai.AiError as exc:
                self.after(0, lambda exc=exc: self._done("", str(exc)))
            except Exception as exc:  # nieoczekiwany błąd — też pokaż użytkownikowi
                self.after(0, lambda exc=exc: self._done("", f"Nieoczekiwany błąd: {exc}"))

        threading.Thread(target=worker, daemon=True).start()

    def _done(self, text: str, error: str | None) -> None:
        if self._closed or not self.winfo_exists():
            return
        if error:
            self.status.configure(text=t('Nie udało się wykonać akcji.'))
            self._set_right(error)
            messagebox.showerror(APP_NAME, error, parent=self)
            return
        self.result_text = text
        self._set_right(text)
        self.status.configure(text=t('Gotowe. Wybierz, co zrobić z wynikiem.'))
        self.replace_btn.configure(state="normal")
        self.new_btn.configure(state="normal")
        self.report_btn.configure(state="normal")

    def _report_content(self) -> None:
        """Zgłoszenie nieodpowiedniej treści wygenerowanej przez AI."""
        ReportContentDialog(self, generated_text=self.result_text, theme_getter=self.theme_getter)

    def _set_right(self, value: str) -> None:
        self.right.configure(state="normal")
        self.right.delete("1.0", END)
        self.right.insert("1.0", value)
        self.right.configure(state="disabled")

    def _replace(self) -> None:
        self.decision = "replace"
        self.destroy()

    def _save_new(self) -> None:
        self.decision = "new"
        self.destroy()


class ReportContentDialog(Toplevel):
    """Zgłoszenie nieodpowiedniej treści wygenerowanej przez AI.

    Wymagane przez zasadę Microsoft Store 11.16 (Live Generative AI Content):
    produkty z generatywną AI muszą dać użytkownikowi sposób zgłoszenia
    nieodpowiedniego wyniku.

    Zgłoszenie zapisujemy do lokalnego pliku JSONL w folderze danych
    (aplikacja jest offline-first i nie wysyła danych na serwery autora),
    a użytkownik może je jednym kliknięciem wysłać do autora przez GitHub.
    """

    CATEGORIES = (
        "Treść obraźliwa lub nienawistna",
        "Treść seksualna lub nieodpowiednia dla nieletnich",
        "Przemoc lub niebezpieczne instrukcje",
        "Nieprawdziwe lub wprowadzające w błąd informacje",
        "Naruszenie prywatności lub praw autorskich",
        "Inny problem",
    )

    def __init__(self, parent, *, generated_text: str, theme_getter=None):
        super().__init__(parent)
        self.theme_getter = theme_getter
        self.generated_text = generated_text
        self.title(t('Zgłoś nieodpowiednią treść'))
        self.geometry("640x560")
        self.minsize(560, 480)

        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(4, weight=1)

        ttk.Label(
            body,
            text=t(
                "Zgłoś treść wygenerowaną przez AI, która jest nieodpowiednia, "
                "szkodliwa lub błędna. Zgłoszenie zapisujemy lokalnie na Twoim "
                "komputerze — możesz je potem wysłać do autora aplikacji."
            ),
            wraplength=580,
            justify="left",
        ).grid(row=0, column=0, sticky=W, pady=(0, 12))

        ttk.Label(body, text=t('Rodzaj problemu'), font=("Segoe UI", 10, "bold")).grid(
            row=1, column=0, sticky=W
        )
        self.category_var = StringVar(value=self.CATEGORIES[0])
        ttk.Combobox(
            body,
            textvariable=self.category_var,
            values=[t(c) for c in self.CATEGORIES],
            state="readonly",
        ).grid(row=2, column=0, sticky="ew", pady=(4, 12))

        ttk.Label(body, text=t('Opis (opcjonalnie)'), font=("Segoe UI", 10, "bold")).grid(
            row=3, column=0, sticky=W
        )

        from tkinter import Text

        self.details = Text(body, wrap="word", height=6, relief="flat", borderwidth=1)
        self.details.grid(row=4, column=0, sticky="nsew", pady=(4, 12))
        if theme_getter:
            apply_widget_theme(self.details, theme_getter())
        else:
            apply_widget_theme(self.details, theme_colors("jasny"))

        buttons = ttk.Frame(body)
        buttons.grid(row=5, column=0, sticky="e")
        ttk.Button(buttons, text=t('Anuluj'), command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text=t('Zapisz zgłoszenie'), command=self._submit).pack(side="right")

        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(parent)
        self.grab_set()

    def _submit(self) -> None:
        details = self.details.get("1.0", END).strip()
        try:
            path = ai.save_content_report(
                category=self.category_var.get(),
                details=details,
                generated_text=self.generated_text,
            )
        except OSError as exc:
            messagebox.showerror(
                APP_NAME,
                t('Nie udało się zapisać zgłoszenia:\n') + str(exc),
                parent=self,
            )
            return

        send = messagebox.askyesno(
            APP_NAME,
            t(
                "Zgłoszenie zapisane lokalnie:\n"
            )
            + str(path)
            + t(
                "\n\nCzy chcesz teraz otworzyć stronę zgłoszeń GitHub, "
                "aby przesłać je autorowi aplikacji?"
            ),
            parent=self,
        )
        if send:
            webbrowser.open(REPORT_ISSUE_URL)
        self.destroy()
