"""Okna dialogowe (Toplevel)."""
from __future__ import annotations

import csv
import json
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    VERTICAL,
    Listbox,
    StringVar,
    Tk,
    Toplevel,
    W,
    filedialog,
    messagebox,
    ttk,
)

from pbcore.core import *  # noqa: F401,F403
from pbcore.models import *  # noqa: F401,F403


class PwaImportDialog(Toplevel):
    def __init__(self, parent: Tk, *, theme_getter=None):
        super().__init__(parent)
        self.theme_getter = theme_getter
        self.title("Import z PrompBase PWA")
        self.geometry("720x520")
        self.minsize(600, 440)
        self.imported: list[Prompt] | None = None
        self.n8n_url = ""
        self.theme = ""

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        ttk.Label(
            body,
            text=(
                "Masz bibliotekę w starej wersji przeglądarkowej (PWA)?\n\n"
                "1. Otwórz PrompBase w Chrome lub Edge.\n"
                "2. Naciśnij F12 → zakładka Console (Konsola).\n"
                "3. Kliknij „Kopiuj polecenie” poniżej, wklej w konsoli Enter.\n"
                "4. Wklej skopiowany JSON tutaj (Ctrl+V) lub wczytaj plik .json."
            ),
            wraplength=660,
            justify=LEFT,
        ).grid(row=0, column=0, sticky=W, pady=(0, 10))

        toolbar = ttk.Frame(body)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(toolbar, text="Kopiuj polecenie do konsoli", command=self.copy_console_command).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Wczytaj plik JSON...", command=self.load_file).pack(side=LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Pełna instrukcja", command=self.open_full_guide).pack(side=LEFT)

        from tkinter import Text

        self.paste_text = Text(body, wrap="word", height=14, font=("Consolas", 10))
        self.paste_text.grid(row=2, column=0, sticky="nsew")
        if theme_getter:
            apply_text_theme(self.paste_text, theme_getter())

        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side=LEFT, padx=4)
        ttk.Button(buttons, text="Importuj", command=self.do_import).pack(side=LEFT, padx=4)

        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(parent)
        self.grab_set()

    def copy_console_command(self) -> None:
        cmd = f"copy(localStorage.getItem('{PWA_STORAGE_KEY}'))"
        self.clipboard_clear()
        self.clipboard_append(cmd)
        self.update()
        messagebox.showinfo(
            APP_NAME,
            "Skopiowano do schowka:\n\n"
            f"{cmd}\n\n"
            "Wklej w konsoli przeglądarki (F12) i naciśnij Enter.\n"
            "Potem wklej wynik w pole poniżej.",
            parent=self,
        )

    def open_full_guide(self) -> None:
        if DOC_PWA_IMPORT.is_file():
            webbrowser.open(DOC_PWA_IMPORT.resolve().as_uri())
        else:
            webbrowser.open(f"{APP_HELP_URL}#import-z-pwa-przeglądarka")

    def load_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Wybierz eksport PWA",
            filetypes=[("JSON", "*.json"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding="utf-8-sig")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Nie można odczytać pliku:\n{exc}", parent=self)
            return
        self.paste_text.delete("1.0", END)
        self.paste_text.insert("1.0", raw)

    def do_import(self) -> None:
        raw = self.paste_text.get("1.0", END).strip()
        if not raw:
            messagebox.showwarning(APP_NAME, "Wklej dane z localStorage lub wczytaj plik JSON.", parent=self)
            return
        try:
            data = json.loads(raw)
            prompts, n8n_url, theme = prompts_from_pwa_data(data)
        except json.JSONDecodeError as exc:
            messagebox.showerror(APP_NAME, f"Nieprawidłowy JSON:\n{exc}", parent=self)
            return
        valid = [p for p in prompts if p.name and p.content]
        if not valid:
            messagebox.showwarning(APP_NAME, "Nie znaleziono poprawnych promptów w danych PWA.", parent=self)
            return
        self.imported = valid
        self.n8n_url = n8n_url
        self.theme = theme
        self.destroy()


class HistoryDialog(Toplevel):
    def __init__(self, parent: Tk, prompt: Prompt, *, theme_getter=None):
        super().__init__(parent)
        self.prompt = prompt
        self.theme_getter = theme_getter
        self.restored = False
        self.title(f"Historia — {prompt.name}")
        self.geometry("760x520")
        self.minsize(620, 420)

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        ttk.Label(body, text="Wersje (najnowsza na górze):", style="Stat.TLabel").grid(row=0, column=0, columnspan=2, sticky=W)

        self.version_list = Listbox(body, height=8, activestyle="dotbox", exportselection=False)
        self.version_list.grid(row=1, column=0, sticky="nsw", padx=(0, 10))
        self.version_list.bind("<<ListboxSelect>>", lambda _event: self._show_preview())

        from tkinter import Text

        self.preview_text = Text(body, wrap="word", height=16, font=("Consolas", 10), state="disabled")
        self.preview_text.grid(row=1, column=1, sticky="nsew")

        if theme_getter:
            apply_text_theme(self.preview_text, theme_getter())
            apply_text_theme(self.version_list, theme_getter())

        for index, entry in enumerate(prompt.history):
            label = format_date(entry.get("saved_at"))
            self.version_list.insert(END, f"{index + 1}. {label}")

        if prompt.history:
            self.version_list.selection_set(0)
            self._show_preview()

        buttons = ttk.Frame(body)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Zamknij", command=self.destroy).pack(side=LEFT, padx=4)
        ttk.Button(buttons, text="Przywróć zaznaczoną", command=self.restore).pack(side=LEFT, padx=4)

        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(parent)
        self.grab_set()

    def _show_preview(self) -> None:
        selection = self.version_list.curselection()
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", END)
        if not selection:
            self.preview_text.configure(state="disabled")
            return
        entry = self.prompt.history[selection[0]]
        header = (
            f"{entry.get('name', '')}\n"
            f"Status: {status_label(entry.get('status', ''))} | "
            f"Model: {entry.get('model') or '—'} | "
            f"Zapis: {format_date(entry.get('saved_at'))}\n\n"
        )
        self.preview_text.insert("1.0", header + (entry.get("content") or ""))
        self.preview_text.configure(state="disabled")

    def restore(self) -> None:
        selection = self.version_list.curselection()
        if not selection:
            messagebox.showinfo(APP_NAME, "Wybierz wersję do przywrócenia.", parent=self)
            return
        entry = self.prompt.history[selection[0]]
        if not messagebox.askyesno(
            APP_NAME,
            f"Przywrócić wersję z {format_date(entry.get('saved_at'))}?\n"
            "Obecna treść zostanie zapisana w historii.",
            parent=self,
        ):
            return
        push_prompt_history(self.prompt)
        self.prompt.name = str(entry.get("name") or self.prompt.name)
        self.prompt.content = str(entry.get("content") or "")
        self.prompt.status = str(entry.get("status") or self.prompt.status)
        self.prompt.format = str(entry.get("format") or self.prompt.format)
        self.prompt.model = str(entry.get("model") or "")
        self.prompt.zastosowanie = str(entry.get("zastosowanie") or "")
        self.prompt.comment = str(entry.get("comment") or "")
        self.prompt.tags = str(entry.get("tags") or "")
        self.restored = True
        self.destroy()


class FillVariablesDialog(Toplevel):
    def __init__(self, parent: Tk, content: str, *, title: str = "Uzupełnij zmienne"):
        super().__init__(parent)
        self.title(title)
        self.geometry("520x420")
        self.filled_content: str | None = None
        self.placeholders = extract_placeholders(content)

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(
            body,
            text="Prompt zawiera pola w nawiasach [TEMAT], [TEKST] itd.\nUzupełnij je przed skopiowaniem:",
            wraplength=460,
        ).grid(row=0, column=0, columnspan=2, sticky=W, pady=(0, 12))

        self.vars: dict[str, StringVar] = {}
        for index, token in enumerate(self.placeholders):
            ttk.Label(body, text=token).grid(row=index + 1, column=0, sticky=W, pady=4)
            var = StringVar()
            self.vars[token] = var
            ttk.Entry(body, textvariable=var).grid(row=index + 1, column=1, sticky="ew", pady=4)

        buttons = ttk.Frame(body)
        buttons.grid(row=len(self.placeholders) + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side=LEFT, padx=4)
        ttk.Button(buttons, text="Kopiuj uzupełniony", command=self.apply).pack(side=LEFT, padx=4)

        self._source_content = content
        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(parent)
        self.grab_set()

    def apply(self) -> None:
        values = {token: var.get() for token, var in self.vars.items()}
        missing = [token for token, value in values.items() if not value.strip()]
        if missing:
            messagebox.showwarning(
                APP_NAME,
                f"Uzupełnij pola: {', '.join(missing)}",
                parent=self,
            )
            return
        self.filled_content = fill_placeholders(self._source_content, values)
        self.destroy()


ONBOARDING_STEPS = [
    (
        "Witaj w PrompBase",
        "Twoja biblioteka promptów AI — lokalnie na dysku, bez konta i bez chmury.\n\n"
        "Za chwilę skopiujesz gotowy przykład i wkleisz go do ChatGPT lub Claude. "
        "To zajmie około 30 sekund.",
    ),
    (
        "Krok 1: wybierz prompt",
        "Po lewej zobaczysz przykłady (marketing, kod, n8n).\n\n"
        "Kliknij wiersz na liście — treść pojawi się w podglądzie po prawej.",
    ),
    (
        "Krok 2: Kopiuj i użyj w AI",
        "Użyj dużego przycisku „Kopiuj i użyj w AI”.\n\n"
        "Aplikacja skopiuje treść (z uzupełnieniem pól [TEMAT] jeśli trzeba) "
        "i otworzy sugerowaną platformę w przeglądarce.",
    ),
    (
        "Gotowe — Twoja kolej",
        "Import CSV i eksport są w menu Plik.\n"
        "Pomoc: klawisz ? lub menu Pomoc.\n\n"
        "Dodaj własny prompt przyciskiem „+ Nowy Prompt”.",
    ),
]


class OnboardingDialog(Toplevel):
    def __init__(self, parent: Tk, *, on_finish=None):
        super().__init__(parent)
        self.on_finish = on_finish
        self.step_index = 0
        self.title("PrompBase — szybki start")
        self.geometry("560x340")
        self.minsize(480, 300)
        self.resizable(False, False)

        body = ttk.Frame(self, padding=20)
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(0, weight=1)

        self.step_title = ttk.Label(body, text="", font=("Segoe UI", 14, "bold"))
        self.step_title.grid(row=0, column=0, sticky=W, pady=(0, 10))

        self.step_body = ttk.Label(body, text="", wraplength=500, justify=LEFT)
        self.step_body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(1, weight=1)

        nav = ttk.Frame(body)
        nav.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self.back_btn = ttk.Button(nav, text="Wstecz", command=self.prev_step)
        self.back_btn.pack(side=LEFT)
        self.next_btn = ttk.Button(nav, text="Dalej", style="Accent.TButton", command=self.next_step)
        self.next_btn.pack(side=RIGHT)

        self._render_step()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._finish)

    def _render_step(self) -> None:
        title, text = ONBOARDING_STEPS[self.step_index]
        self.step_title.configure(text=title)
        self.step_body.configure(text=text)
        self.back_btn.configure(state="normal" if self.step_index > 0 else "disabled")
        last = self.step_index >= len(ONBOARDING_STEPS) - 1
        self.next_btn.configure(text="Zaczynam" if last else "Dalej")

    def prev_step(self) -> None:
        if self.step_index > 0:
            self.step_index -= 1
            self._render_step()

    def next_step(self) -> None:
        if self.step_index < len(ONBOARDING_STEPS) - 1:
            self.step_index += 1
            self._render_step()
        else:
            self._finish()

    def _finish(self) -> None:
        if self.on_finish:
            self.on_finish()
        self.destroy()


class CloudExportDialog(Toplevel):
    def __init__(self, parent: Tk, store: PromptStore):
        super().__init__(parent)
        self.store = store
        self.exported_path: Path | None = None
        self.title("Eksport do chmury")
        self.geometry("640x320")
        self.minsize(560, 280)

        self.provider_var = StringVar(value="onedrive")
        self.path_var = StringVar()

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(1, weight=1)

        ttk.Label(
            body,
            text=(
                "Kopia trafia do folderu synchronizowanego z chmurą\n"
                f"(podfolder {CLOUD_SUBDIR}/). Wymagany Google Drive Desktop lub OneDrive."
            ),
            wraplength=580,
        ).grid(row=0, column=0, columnspan=3, sticky=W, pady=(0, 12))

        row = 1
        for provider, label in CLOUD_PROVIDERS.items():
            ttk.Radiobutton(
                body,
                text=label,
                variable=self.provider_var,
                value=provider,
                command=self._sync_path_field,
            ).grid(row=row, column=0, sticky=W, pady=2)
            row += 1

        ttk.Label(body, text="Folder synchronizacji").grid(row=row, column=0, sticky=W, pady=(10, 4))
        ttk.Entry(body, textvariable=self.path_var).grid(row=row, column=1, sticky="ew", pady=(10, 4), padx=(0, 8))
        ttk.Button(body, text="Wybierz…", command=self.browse_folder).grid(row=row, column=2, pady=(10, 4))
        row += 1

        self.hint = ttk.Label(body, text="", style="Muted.TLabel", wraplength=580)
        self.hint.grid(row=row, column=0, columnspan=3, sticky=W, pady=(8, 0))
        row += 1

        buttons = ttk.Frame(body)
        buttons.grid(row=row, column=0, columnspan=3, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side=LEFT, padx=4)
        ttk.Button(buttons, text="Eksportuj teraz", command=self.export).pack(side=LEFT, padx=4)

        self._sync_path_field()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(parent)
        self.grab_set()

    def _sync_path_field(self) -> None:
        provider = self.provider_var.get()
        current = self.store.cloud_folders.get(provider) or detect_cloud_folder(provider)
        self.path_var.set(current)
        if current:
            self.hint.configure(text=f"Plik zostanie zapisany w: {Path(current) / CLOUD_SUBDIR}")
        else:
            self.hint.configure(text="Nie wykryto folderu — wybierz ręcznie katalog synchronizacji.")

    def browse_folder(self) -> None:
        path = filedialog.askdirectory(parent=self, title="Wybierz folder Google Drive / OneDrive")
        if path:
            self.path_var.set(path)

    def export(self) -> None:
        provider = self.provider_var.get()
        folder = self.path_var.get().strip()
        if not folder:
            messagebox.showerror(APP_NAME, "Wybierz folder synchronizacji chmury.", parent=self)
            return
        root = Path(folder)
        if not root.is_dir():
            messagebox.showerror(APP_NAME, "Podany folder nie istnieje.", parent=self)
            return

        self.store.cloud_folders[provider] = folder
        self.store.save()

        target_dir = root / CLOUD_SUBDIR
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        target = target_dir / f"prompbase-backup-{stamp}.json"
        payload = self.store.to_payload()
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        csv_target = target_dir / f"prompbase-biblioteka-{stamp}.csv"
        self._write_csv(csv_target)

        self.exported_path = target
        messagebox.showinfo(
            APP_NAME,
            f"Zapisano w chmurze (folder synchronizacji):\n\n{target}\n{csv_target}",
            parent=self,
        )
        self.destroy()

    def _write_csv(self, path: Path) -> None:
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "Nazwa",
                    "Status",
                    "Format",
                    "Model AI",
                    "Zastosowanie",
                    "Tagi",
                    "Data Utworzenia",
                    "Komentarz",
                    "Treść Promptu",
                ]
            )
            for prompt in self.store.prompts:
                writer.writerow(
                    [
                        prompt.name,
                        status_label(prompt.status),
                        prompt.format,
                        prompt.model,
                        prompt.zastosowanie,
                        prompt.tags,
                        format_date(prompt.created),
                        prompt.comment,
                        prompt.content.replace("\n", " ↵ "),
                    ]
                )


class PromptDialog(Toplevel):
    def __init__(
        self,
        parent: Tk,
        prompt: Prompt | None = None,
        *,
        model_options: list[str] | None = None,
        zastosowanie_options: list[str] | None = None,
        tag_options: list[str] | None = None,
        theme_getter=None,
    ):
        super().__init__(parent)
        self.title("Edytuj prompt" if prompt else "Nowy prompt")
        self.geometry("760x650")
        self.minsize(650, 540)
        self.result: Prompt | None = None
        self.original = prompt
        self.model_options = model_options or AI_MODELS
        self.zastosowanie_options = zastosowanie_options or ZASTOSOWANIA_PRESET
        self.tag_options = tag_options or TAGS_PRESET
        self.theme_getter = theme_getter

        self.name_var = StringVar(value=prompt.name if prompt else "")
        initial_status = status_label(prompt.status) if prompt else STATUSES["nowy"]
        self.status_var = StringVar(value=initial_status)
        self.format_var = StringVar(value=prompt.format if prompt else "tekst")
        self.model_var = StringVar(value=prompt.model if prompt else "")
        self.zastosowanie_var = StringVar(value=prompt.zastosowanie if prompt else "")
        self.tags_var = StringVar(value=prompt.tags if prompt else "")
        self.comment_var = StringVar(value=prompt.comment if prompt else "")

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(7, weight=1)

        ttk.Label(body, text="Nazwa").grid(row=0, column=0, sticky=W, pady=4)
        ttk.Entry(body, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(body, text="Status").grid(row=1, column=0, sticky=W, pady=4)
        ttk.Combobox(body, textvariable=self.status_var, values=list(STATUSES.values()), state="readonly").grid(
            row=1, column=1, sticky="ew", pady=4
        )

        ttk.Label(body, text="Format").grid(row=2, column=0, sticky=W, pady=4)
        ttk.Combobox(body, textvariable=self.format_var, values=FORMATS, state="readonly").grid(
            row=2, column=1, sticky="ew", pady=4
        )

        ttk.Label(body, text="Model AI").grid(row=3, column=0, sticky=W, pady=4)
        model_row = ttk.Frame(body)
        model_row.grid(row=3, column=1, sticky="ew", pady=4)
        model_row.columnconfigure(0, weight=1)
        self.model_combo = ttk.Combobox(
            model_row,
            textvariable=self.model_var,
            values=self.model_options,
            state="normal",
        )
        self.model_combo.grid(row=0, column=0, sticky="ew")
        platform_row = ttk.Frame(model_row)
        platform_row.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        for col, (name, _url) in enumerate(AI_PLATFORMS):
            ttk.Button(
                platform_row,
                text=name,
                width=8,
                command=lambda platform=name: self._open_platform(platform),
            ).grid(row=0, column=col, padx=(0, 4))

        ttk.Label(body, text="Zastosowanie").grid(row=4, column=0, sticky=W, pady=4)
        ttk.Combobox(
            body,
            textvariable=self.zastosowanie_var,
            values=self.zastosowanie_options,
            state="normal",
        ).grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(body, text="Tagi").grid(row=5, column=0, sticky=W, pady=4)
        ttk.Combobox(
            body,
            textvariable=self.tags_var,
            values=self.tag_options,
            state="normal",
        ).grid(row=5, column=1, sticky="ew", pady=4)
        ttk.Label(body, text="(po przecinku)", style="Muted.TLabel").grid(row=5, column=2, sticky=W, padx=(6, 0))

        ttk.Label(body, text="Komentarz").grid(row=6, column=0, sticky=W, pady=4)
        ttk.Entry(body, textvariable=self.comment_var).grid(row=6, column=1, sticky="ew", pady=4)

        ttk.Label(body, text="Treść").grid(row=7, column=0, sticky="nw", pady=4)
        text_frame = ttk.Frame(body)
        text_frame.grid(row=7, column=1, sticky="nsew", pady=4)
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self.content_text = self._text_widget(text_frame)
        self.content_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(text_frame, orient=VERTICAL, command=self.content_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.content_text.configure(yscrollcommand=scroll.set)
        if prompt:
            self.content_text.insert("1.0", prompt.content)
        if self.theme_getter:
            apply_text_theme(self.content_text, self.theme_getter())

        buttons = ttk.Frame(body)
        buttons.grid(row=8, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side=LEFT, padx=4)
        if prompt and prompt.history:
            ttk.Button(buttons, text="Historia…", command=self._open_history).pack(side=LEFT, padx=4)
        ttk.Button(buttons, text="Zapisz", command=self.save).pack(side=LEFT, padx=4)

        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Control-s>", lambda _event: self.save())
        self.bind("<Control-Return>", lambda _event: self.save())
        self.transient(parent)
        self.grab_set()
        self.after(100, lambda: self.focus_force())

    def _text_widget(self, parent: ttk.Frame):
        from tkinter import Text

        return Text(parent, wrap="word", undo=True, font=("Consolas", 11))

    def _open_history(self) -> None:
        if not self.original:
            return
        dialog = HistoryDialog(self, self.original, theme_getter=self.theme_getter)
        self.wait_window(dialog)

    def save(self) -> None:
        name = self.name_var.get().strip()
        content = self.content_text.get("1.0", END).strip()
        if not name:
            messagebox.showerror(APP_NAME, "Podaj nazwę promptu.", parent=self)
            return
        if not content:
            messagebox.showerror(APP_NAME, "Wklej treść promptu.", parent=self)
            return

        prompt = self.original or Prompt(name=name, content=content)
        if self.original:
            candidate = {
                "name": name,
                "content": content,
                "status": status_key_from_label(self.status_var.get().strip()),
                "format": self.format_var.get(),
                "model": self.model_var.get().strip(),
                "zastosowanie": self.zastosowanie_var.get().strip(),
                "tags": self.tags_var.get().strip(),
                "comment": self.comment_var.get().strip(),
            }
            if not snapshots_equal(prompt_snapshot(self.original), candidate):
                push_prompt_history(self.original)

        prompt.name = name
        prompt.content = content
        prompt.status = status_key_from_label(self.status_var.get().strip())
        prompt.format = self.format_var.get()
        prompt.model = self.model_var.get().strip()
        prompt.zastosowanie = self.zastosowanie_var.get().strip()
        prompt.tags = self.tags_var.get().strip()
        prompt.comment = self.comment_var.get().strip()
        self.result = prompt
        self.destroy()

    def _open_platform(self, platform_name: str) -> None:
        url = next((url for name, url in AI_PLATFORMS if name == platform_name), "")
        if url:
            webbrowser.open(url)


class N8nConfigDialog(Toplevel):
    def __init__(self, parent: Tk, current_url: str, *, post_json=None):
        super().__init__(parent)
        self._post_json = post_json
        self.title("Konfiguracja n8n")
        self.geometry("620x220")
        self.minsize(520, 200)
        self.saved_url: str | None = None
        self.url_var = StringVar(value=current_url or "")

        body = ttk.Frame(self, padding=16)
        body.pack(fill=BOTH, expand=True)
        body.columnconfigure(0, weight=1)

        ttk.Label(
            body,
            text="URL webhooka n8n (węzeł Webhook → Production URL):",
            wraplength=560,
        ).grid(row=0, column=0, sticky=W, pady=(0, 6))
        entry = ttk.Entry(body, textvariable=self.url_var)
        entry.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.hint_label = ttk.Label(body, text="", style="Muted.TLabel", wraplength=560)
        self.hint_label.grid(row=2, column=0, sticky=W, pady=(0, 12))

        buttons = ttk.Frame(body)
        buttons.grid(row=3, column=0, sticky="e")
        ttk.Button(buttons, text="Anuluj", command=self.destroy).pack(side=LEFT, padx=4)
        ttk.Button(buttons, text="Testuj", command=self.test).pack(side=LEFT, padx=4)
        ttk.Button(buttons, text="Zapisz", command=self.save).pack(side=LEFT, padx=4)

        self.url_var.trace_add("write", lambda *_: self._update_hint())
        self._update_hint()
        self.bind("<Escape>", lambda _event: self.destroy())
        self.transient(parent)
        self.grab_set()
        entry.focus_set()

    def _update_hint(self) -> None:
        url = normalize_n8n_url(self.url_var.get())
        if not url:
            self.hint_label.configure(text="Przykład: https://twoja-instancja.app.n8n.cloud/webhook/prompbase")
            return
        if validate_n8n_url(url):
            self.hint_label.configure(text="✓ Adres wygląda poprawnie (http/https + /webhook/).")
        else:
            self.hint_label.configure(text="✗ Wymagany pełny URL z fragmentem /webhook/ w ścieżce.")

    def test(self) -> None:
        url = normalize_n8n_url(self.url_var.get())
        if not validate_n8n_url(url):
            messagebox.showerror(APP_NAME, "Podaj poprawny URL webhooka przed testem.", parent=self)
            return
        payload = n8n_envelope(
            "test",
            message="Test połączenia z Biblioteki Promptów AI (PrompBase Python)",
        )
        if self._post_json:
            self._post_json(url, payload, "Test webhooka n8n zakończony pomyślnie.")
        else:
            messagebox.showinfo(APP_NAME, "Test wymaga uruchomionej aplikacji PrompBase.", parent=self)

    def save(self) -> None:
        url = normalize_n8n_url(self.url_var.get())
        if url and not validate_n8n_url(url):
            messagebox.showerror(
                APP_NAME,
                "Nieprawidłowy URL webhooka.\n\nUżyj adresu Production URL z węzła Webhook w n8n.",
                parent=self,
            )
            return
        self.saved_url = url
        self.destroy()


