"""Główne okno aplikacji PrompBaseApp i wejście main()."""
from __future__ import annotations

import csv
import json
import os
import platform
import subprocess
import webbrowser
from datetime import datetime
from io import StringIO
from pathlib import Path
from tkinter import (
    BOTH,
    BOTTOM,
    CENTER,
    END,
    LEFT,
    VERTICAL,
    BooleanVar,
    Listbox,
    Menu,
    StringVar,
    Tk,
    W,
    X,
    filedialog,
    messagebox,
    ttk,
)
from urllib import request
from urllib.error import HTTPError, URLError

from pbcore import ai, i18n
from pbcore.ai_dialogs import AiConfigDialog, AiResultDialog
from pbcore.core import *  # noqa: F401,F403
from pbcore.dialogs import *  # noqa: F401,F403
from pbcore.i18n import t
from pbcore.models import *  # noqa: F401,F403


class PrompBaseApp:
    def __init__(self, root: Tk):
        self.root = root
        # PromptStore.load() wywołuje i18n.set_language() — musi zajść
        # PRZED jakimkolwiek t()/title(), inaczej pierwszy render (w tym
        # pasek tytułu okna) dostaje domyślny język, nie zapisany wybór.
        self.store = PromptStore(app_data_dir() / "promptbase.json")

        self.root.title(f"{APP_NAME}{t(' - Biblioteka Promptów AI')}")
        self.root.geometry("1180x760")
        self.root.minsize(980, 620)
        self._set_window_icon()

        self.filtered: list[Prompt] = []
        self.selected_id: str | None = None

        self.search_var = StringVar()
        self.status_filter = StringVar(value="Wszystkie")
        self.model_filter = StringVar(value="Wszystkie")
        self.zastosowanie_filter = StringVar(value="Wszystkie")
        self.tag_filter = StringVar(value="Wszystkie")
        self.sort_var = StringVar(value="Najnowsze")
        self.favorites_only = BooleanVar(value=False)
        self.theme_var = StringVar(value=self.store.theme)
        self.language_var = StringVar(value=self.store.language)
        self._themed_text_widgets: list = []

        self._configure_style()
        self._build_menu()
        self._build_ui()
        self._bind_shortcuts()

        if not self.store.prompts:
            self.store.sample_data()
        self.refresh_all()
        if self.store.prompts and not self.store.checklist.get("selected"):
            first_id = self.store.prompts[0].id
            self.tree.selection_set(first_id)
            self.selected_id = first_id
            self.update_detail()
            self.store.mark_checklist("selected")

        if not self.store.onboarding_done:
            self.root.after(200, self.show_onboarding)

    def _set_window_icon(self) -> None:
        ico_path = ASSETS_DIR / "promptbase.ico"
        png_path = ASSETS_DIR / "promptbase-256.png"
        try:
            if platform.system().lower() == "windows" and ico_path.exists():
                self.root.iconbitmap(default=str(ico_path))
            elif png_path.exists():
                from tkinter import PhotoImage

                self.window_icon = PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self.window_icon)
        except Exception:
            pass

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.style = style
        self.apply_theme(save=False)

    def get_theme_colors(self) -> dict:
        return theme_colors(self.theme_var.get())

    def register_text_widget(self, widget) -> None:
        if widget not in self._themed_text_widgets:
            self._themed_text_widgets.append(widget)
        apply_widget_theme(widget, self.get_theme_colors())

    def apply_theme(self, save: bool = True) -> None:
        theme_name = self.theme_var.get()
        colors = self.get_theme_colors()
        self.root.configure(bg=colors["bg"])
        self.style.configure(".", background=colors["bg"], foreground=colors["text"], fieldbackground=colors["field"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("TLabelframe", background=colors["bg"], foreground=colors["text"])
        self.style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["text"])
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        self.style.configure("Header.TLabel", background=colors["bg"], foreground=colors["text"], font=("Segoe UI", 18, "bold"))
        self.style.configure("Stat.TLabel", background=colors["bg"], foreground=colors["text"], font=("Segoe UI", 10, "bold"))
        self.style.configure("Muted.TLabel", background=colors["bg"], foreground=colors["muted"])
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        self.style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=(10, 6))
        try:
            self.style.map(
                "Primary.TButton",
                background=[("active", colors["accent"]), ("!disabled", colors["accent"])],
                foreground=[("!disabled", "#ffffff")],
            )
            self.style.configure("Primary.TButton", background=colors["accent"], foreground="#ffffff")
        except Exception:
            pass
        self.style.configure("Treeview", background=colors["surface"], foreground=colors["text"], fieldbackground=colors["surface"])
        self.style.configure("Treeview.Heading", background=colors["surface"], foreground=colors["text"])
        self.style.map("Treeview", background=[("selected", colors["select"])], foreground=[("selected", colors["text"])])

        for widget_name in ("pinned_list", "detail_text"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                apply_widget_theme(widget, colors)

        for widget in self._themed_text_widgets:
            try:
                apply_widget_theme(widget, colors)
            except Exception:
                pass

        status_bar = getattr(self, "status_bar", None)
        if status_bar is not None:
            status_bar.configure(background=colors["surface"], foreground=colors["muted"])

        if save:
            self.store.theme = theme_name
            self.store.save()
            self.set_status(f"{t('Motyw zmieniony: ')}{theme_name}{t('.')}")

    def apply_language(self) -> None:
        """Przełącza język UI natychmiast dla menu i przyszłych okien.

        Statyczne widżety zbudowane raz przy starcie (etykiety, przyciski,
        nagłówki listy) NIE są przebudowywane na żywo — restart w pełni
        stosuje zmianę. Menu jest budowane od nowa (tanie, więc robimy to
        zawsze), a każde NOWO otwierane okno dialogowe już użyje nowego
        języka, bo woła t() dopiero przy konstrukcji.
        """
        lang = self.language_var.get()
        i18n.set_language(lang)
        self.store.language = i18n.get_language()
        self.store.save()
        self._build_menu()
        messagebox.showinfo(
            APP_NAME,
            t(
                "Język zmieniony. Uruchom ponownie PrompBase, aby zastosować "
                "zmianę we wszystkich oknach."
            ),
            parent=self.root,
        )

    def _build_menu(self) -> None:
        menu = Menu(self.root)
        file_menu = Menu(menu, tearoff=False)
        file_menu.add_command(label=t('Nowy prompt'), accelerator="Ctrl+N", command=self.new_prompt)
        file_menu.add_command(label=t('Import CSV...'), command=self.import_csv)
        file_menu.add_command(label=t('Import z PWA (przeglądarka)...'), command=self.import_from_pwa)
        file_menu.add_command(label=t('Instrukcja importu PWA'), command=self.open_pwa_import_guide)
        file_menu.add_command(label=t('Eksport CSV...'), command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label=t('Kopia zapasowa JSON...'), command=self.export_backup_json)
        file_menu.add_command(label=t('Przywróć z JSON...'), command=self.import_backup_json)
        file_menu.add_command(label=t('Eksport dla PWA (przeglądarka)...'), command=self.export_for_pwa)
        file_menu.add_command(label=t('Eksport do chmury (Drive / OneDrive)...'), command=self.export_to_cloud)
        file_menu.add_separator()
        file_menu.add_command(label=t('Szybki import pliku CSV/JSON...'), command=self.quick_import_file)
        file_menu.add_separator()
        file_menu.add_command(label=t('Pokaż plik danych'), command=self.show_data_path)
        file_menu.add_command(label=t('Otwórz folder danych'), command=self.open_data_folder)
        file_menu.add_separator()
        file_menu.add_command(label=t('Zamknij'), command=self.root.destroy)
        menu.add_cascade(label=t('Plik'), menu=file_menu)

        ai_menu = Menu(menu, tearoff=False)
        for platform_name, _url in AI_PLATFORMS:
            ai_menu.add_command(
                label=f"{t('Otwórz ')}{platform_name}",
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=False),
            )
            ai_menu.add_command(
                label=f"{t('Kopiuj prompt i otwórz ')}{platform_name}",
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=True),
            )
        menu.add_cascade(label=t('AI'), menu=ai_menu)

        assistant_menu = Menu(menu, tearoff=False)
        assistant_menu.add_command(
            label=t('Ulepsz prompt'), accelerator="Ctrl+Shift+I", command=self.ai_improve_selected
        )
        assistant_menu.add_command(
            label=t('Przetłumacz prompt'), accelerator="Ctrl+Shift+T", command=self.ai_translate_selected
        )
        adapt_menu = Menu(assistant_menu, tearoff=False)
        for target in ai.ADAPT_TARGETS:
            adapt_menu.add_command(
                label=f"{t('Dostosuj do ')}{target}",
                command=lambda name=target: self.ai_adapt_selected(name),
            )
        assistant_menu.add_cascade(label=t('Dostosuj do platformy'), menu=adapt_menu)
        assistant_menu.add_separator()
        assistant_menu.add_command(label=t('Konfiguracja AI...'), command=self.configure_ai)
        assistant_menu.add_command(label=t('Status silników AI'), command=self.show_ai_status)
        menu.add_cascade(label=t('Asystent AI'), menu=assistant_menu)

        tools_menu = Menu(menu, tearoff=False)
        tools_menu.add_command(label=t('Konfiguracja n8n...'), command=self.configure_n8n)
        tools_menu.add_command(label=t('Testuj webhook n8n'), command=self.test_n8n_webhook)
        tools_menu.add_separator()
        tools_menu.add_command(label=t('Wyślij zaznaczony do n8n'), command=self.send_selected_to_n8n)
        tools_menu.add_command(label=t('Synchronizuj bibliotekę do n8n'), command=self.sync_all_to_n8n)
        tools_menu.add_command(label=t('Eksportuj JSON dla n8n...'), command=self.export_n8n_json)
        tools_menu.add_separator()
        tools_menu.add_command(label=t('Paczki promptów Pro (wkrótce)...'), command=self.show_pro_coming_soon)
        menu.add_cascade(label=t('Narzędzia'), menu=tools_menu)

        view_menu = Menu(menu, tearoff=False)
        view_menu.add_radiobutton(label=t('Tryb jasny'), variable=self.theme_var, value="jasny", command=self.apply_theme)
        view_menu.add_radiobutton(label=t('Tryb ciemny'), variable=self.theme_var, value="ciemny", command=self.apply_theme)
        view_menu.add_radiobutton(label=t('Motyw grafit'), variable=self.theme_var, value="grafit", command=self.apply_theme)
        view_menu.add_separator()
        language_menu = Menu(view_menu, tearoff=False)
        for lang_code, lang_label in i18n.LANGUAGES.items():
            language_menu.add_radiobutton(
                label=lang_label,
                variable=self.language_var,
                value=lang_code,
                command=self.apply_language,
            )
        view_menu.add_cascade(label=t("Język"), menu=language_menu)
        menu.add_cascade(label=t('Widok'), menu=view_menu)

        help_menu = Menu(menu, tearoff=False)
        help_menu.add_command(label=t('Przewodnik startowy'), command=self.show_onboarding)
        help_menu.add_command(label=t('Szybki start (PDF/MD)'), command=self.open_quickstart_doc)
        help_menu.add_command(label=t('Instrukcja importu PWA'), command=self.open_pwa_import_guide)
        help_menu.add_command(label=t('Pomoc i skróty'), accelerator="?", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label=t('Strona produktu'), command=self.open_product_page)
        help_menu.add_command(label=t('Pobierz najnowszą wersję'), command=self.open_download_page)
        help_menu.add_command(label=t('Cennik (Free / Pro)'), command=self.open_pricing_doc)
        menu.add_cascade(label=t('Pomoc'), menu=help_menu)
        self.root.config(menu=menu)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=BOTH, expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=f"{t('PrompBase v')}{APP_VERSION}", style="Header.TLabel").grid(row=0, column=0, sticky=W)
        ttk.Label(
            header,
            text=t('Znajdź prompt · skopiuj · wklej do AI'),
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky=W)
        self.stats_label = ttk.Label(header, text="", style="Muted.TLabel")
        self.stats_label.grid(row=2, column=0, sticky=W)
        ttk.Label(header, text=f"{t('Autor: ')}{APP_AUTHOR}", style="Muted.TLabel").grid(row=3, column=0, sticky=W)
        ttk.Radiobutton(header, text=t('Jasny'), variable=self.theme_var, value="jasny", command=self.apply_theme).grid(
            row=0, column=1, rowspan=2, padx=(4, 0)
        )
        ttk.Radiobutton(header, text=t('Ciemny'), variable=self.theme_var, value="ciemny", command=self.apply_theme).grid(
            row=0, column=2, rowspan=2, padx=(4, 0)
        )
        ttk.Radiobutton(header, text=t('Grafit'), variable=self.theme_var, value="grafit", command=self.apply_theme).grid(
            row=2, column=1, columnspan=2, sticky=W, padx=(4, 8)
        )
        ttk.Button(header, text=t('+ Nowy Prompt'), style="Accent.TButton", command=self.new_prompt).grid(
            row=0, column=3, rowspan=4, padx=4
        )

        sidebar = ttk.LabelFrame(main, text=t('Filtry'), padding=10)
        sidebar.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text=t('Status')).grid(row=0, column=0, sticky=W)
        self.status_combo = ttk.Combobox(sidebar, textvariable=self.status_filter, state="readonly", width=24)
        self.status_combo.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text=t('Model AI')).grid(row=2, column=0, sticky=W)
        self.model_combo = ttk.Combobox(sidebar, textvariable=self.model_filter, state="readonly", width=24)
        self.model_combo.grid(row=3, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text=t('Zastosowanie')).grid(row=4, column=0, sticky=W)
        self.zastosowanie_combo = ttk.Combobox(
            sidebar, textvariable=self.zastosowanie_filter, state="readonly", width=24
        )
        self.zastosowanie_combo.grid(row=5, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text=t('Tag')).grid(row=6, column=0, sticky=W)
        self.tag_combo = ttk.Combobox(sidebar, textvariable=self.tag_filter, state="readonly", width=24)
        self.tag_combo.grid(row=7, column=0, sticky="ew", pady=(2, 10))

        ttk.Button(sidebar, text=t('Wyczyść filtry'), command=self.clear_filters).grid(row=8, column=0, sticky="ew")

        self.checklist_frame = ttk.LabelFrame(sidebar, text=t('Pierwsze kroki'), padding=8)
        self.checklist_frame.grid(row=9, column=0, sticky="ew", pady=(10, 0))
        self.checklist_labels: dict[str, ttk.Label] = {}
        checklist_steps = (
            ("selected", "1. Wybierz prompt z listy"),
            ("copied", "2. Skopiuj treść do schowka"),
            ("opened_ai", "3. Otwórz ChatGPT / Claude"),
            ("added_prompt", "4. Dodaj własny prompt"),
        )
        for idx, (key, label) in enumerate(checklist_steps):
            row_label = ttk.Label(self.checklist_frame, text=f"{t('○ ')}{t(label)}", style="Muted.TLabel", wraplength=200)
            row_label.grid(row=idx, column=0, sticky=W, pady=1)
            self.checklist_labels[key] = row_label

        import_frame = ttk.LabelFrame(sidebar, text=t('Import pliku'), padding=8)
        import_frame.grid(row=10, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(
            import_frame,
            text=t('Kliknij, aby wczytać\nCSV lub JSON'),
            style="Muted.TLabel",
            justify=CENTER,
            cursor="hand2",
        ).pack(fill=X)
        import_frame.bind("<Button-1>", lambda _e: self.quick_import_file())
        for child in import_frame.winfo_children():
            child.bind("<Button-1>", lambda _e: self.quick_import_file())

        ttk.Separator(sidebar).grid(row=11, column=0, sticky="ew", pady=12)
        ttk.Label(sidebar, text=t('Przypięte'), style="Stat.TLabel").grid(row=12, column=0, sticky=W)
        self.pinned_list = Listbox(sidebar, height=8, activestyle="dotbox")
        self.pinned_list.grid(row=13, column=0, sticky="nsew", pady=(4, 8))
        self.pinned_list.bind("<Double-Button-1>", self.open_pinned)
        ttk.Button(sidebar, text=t('Otwórz przypięty'), command=self.open_pinned).grid(row=14, column=0, sticky="ew")
        sidebar.rowconfigure(13, weight=1)

        content = ttk.Frame(main)
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(content)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text=t('Szukaj')).grid(row=0, column=0, padx=(0, 6))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Checkbutton(
            toolbar,
            text=t('★ Tylko ulubione'),
            variable=self.favorites_only,
            command=self.refresh_list,
        ).grid(row=0, column=2, padx=(0, 10))
        ttk.Label(toolbar, text=t('Sortuj')).grid(row=0, column=3, padx=(0, 6))
        ttk.Combobox(toolbar, textvariable=self.sort_var, values=list(SORT_OPTIONS), state="readonly", width=14).grid(
            row=0, column=4
        )

        split = ttk.PanedWindow(content, orient="horizontal")
        split.grid(row=1, column=0, sticky="nsew")

        list_frame = ttk.Frame(split)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        columns = ("pinned", "favorite", "name", "status", "model", "zastosowanie", "format", "created")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "pinned": "Pin",
            "favorite": "★",
            "name": t("Nazwa"),
            "status": t("Status"),
            "model": "Model",
            "zastosowanie": t("Zastosowanie"),
            "format": "Format",
            "created": t("Data"),
        }
        widths = {
            "pinned": 42,
            "favorite": 32,
            "name": 230,
            "status": 90,
            "model": 100,
            "zastosowanie": 130,
            "format": 90,
            "created": 125,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], minwidth=40, stretch=(col == "name"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        split.add(list_frame, weight=3)

        detail = ttk.LabelFrame(split, text=t('Podgląd'), padding=10)
        detail.rowconfigure(5, weight=1)
        detail.columnconfigure(0, weight=1)
        self.detail_title = ttk.Label(detail, text=t('Wybierz prompt'), font=("Segoe UI", 14, "bold"))
        self.detail_title.grid(row=0, column=0, sticky=W, pady=(0, 6))
        self.detail_meta = ttk.Label(detail, text="", style="Muted.TLabel", wraplength=330)
        self.detail_meta.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.detail_comment = ttk.Label(detail, text="", wraplength=330)
        self.detail_comment.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.detail_text = self._text_widget(detail)
        self.detail_text.grid(row=5, column=0, sticky="nsew")
        self.detail_text.configure(state="disabled")
        self.register_text_widget(self.detail_text)

        self.empty_state = ttk.Frame(detail)
        self.empty_state.grid(row=5, column=0, sticky="nsew")
        self.empty_state.grid_remove()
        ttk.Label(
            self.empty_state,
            text=t('Biblioteka jest pusta.\nDodaj pierwszy prompt lub załaduj gotowe przykłady.'),
            justify=CENTER,
            wraplength=320,
        ).pack(pady=(24, 12))
        empty_actions = ttk.Frame(self.empty_state)
        empty_actions.pack()
        ttk.Button(empty_actions, text=t('+ Nowy Prompt'), style="Accent.TButton", command=self.new_prompt).pack(
            side=LEFT, padx=4
        )
        ttk.Button(empty_actions, text=t('Załaduj przykłady'), command=self.restore_sample_prompts).pack(side=LEFT, padx=4)

        self.primary_row = ttk.Frame(detail)
        self.primary_row.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.primary_row.columnconfigure(0, weight=1)
        ttk.Button(
            self.primary_row,
            text=t('Kopiuj i użyj w AI'),
            style="Primary.TButton",
            command=self.copy_and_use_ai,
        ).grid(row=0, column=0, sticky="ew")

        self.detail_actions = ttk.Frame(detail)
        self.detail_actions.grid(row=7, column=0, sticky="ew", pady=(6, 0))
        buttons = self.detail_actions
        for idx in range(8):
            buttons.columnconfigure(idx, weight=1)
        ttk.Button(buttons, text=t('Kopiuj'), command=self.copy_selected).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(buttons, text=t('Edytuj'), command=self.edit_selected).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(buttons, text=t('Duplikuj'), command=self.duplicate_selected).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(buttons, text=t('Historia'), command=self.show_history).grid(row=0, column=3, sticky="ew", padx=2)
        ttk.Button(buttons, text=t('Przypnij'), command=self.toggle_selected_pin).grid(row=0, column=4, sticky="ew", padx=2)
        ttk.Button(buttons, text=t('★ Ulubiony'), command=self.toggle_selected_favorite).grid(
            row=0, column=5, sticky="ew", padx=2
        )
        ttk.Button(buttons, text=t('n8n'), command=self.send_selected_to_n8n).grid(row=0, column=6, sticky="ew", padx=2)
        ttk.Button(buttons, text=t('Usuń'), command=self.delete_selected).grid(row=0, column=7, sticky="ew", padx=2)

        # Rząd akcji asystenta AI (przepisywanie promptu przez model).
        self.assistant_buttons = ttk.Frame(detail)
        self.assistant_buttons.grid(row=9, column=0, sticky="ew", pady=(6, 0))
        for idx in range(3):
            self.assistant_buttons.columnconfigure(idx, weight=1)
        ttk.Button(
            self.assistant_buttons, text=t('✨ Ulepsz'), command=self.ai_improve_selected
        ).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(
            self.assistant_buttons, text=t('🌐 Przetłumacz'), command=self.ai_translate_selected
        ).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(
            self.assistant_buttons, text=t('🎯 Dostosuj…'), command=self._ask_adapt_target
        ).grid(row=0, column=2, sticky="ew", padx=2)

        self.ai_buttons = ttk.Frame(detail)
        self.ai_buttons.grid(row=8, column=0, sticky="ew", pady=(6, 0))
        ai_buttons = self.ai_buttons
        for idx in range(len(AI_PLATFORMS) + 1):
            ai_buttons.columnconfigure(idx, weight=1)
        ttk.Button(
            ai_buttons,
            text=t('AI z modelu ↗'),
            command=self.open_ai_for_model,
        ).grid(row=0, column=0, sticky="ew", padx=2)
        for idx, (platform_name, _url) in enumerate(AI_PLATFORMS, start=1):
            ttk.Button(
                ai_buttons,
                text=f"{platform_name}{t(' ↗')}",
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=True),
            ).grid(row=0, column=idx, sticky="ew", padx=2)
        split.add(detail, weight=2)
        self.register_text_widget(self.pinned_list)

        self.status_bar = ttk.Label(self.root, text="", relief="sunken", anchor=W, padding=(8, 3))
        self.status_bar.pack(side=BOTTOM, fill=X)

        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        self.sort_var.trace_add("write", lambda *_: self.refresh_list())
        self.status_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.model_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.zastosowanie_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.tag_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-Button-1>", lambda _event: self.edit_selected())

        self._update_checklist_ui()

    def _on_tree_select(self, _event=None) -> None:
        if self.tree.selection():
            self.store.mark_checklist("selected")
        self.update_detail()
        self._update_checklist_ui()

    def _text_widget(self, parent):
        from tkinter import Text

        return Text(parent, wrap="word", height=10, font=("Consolas", 10))

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-Shift-N>", lambda _event: self.configure_n8n())
        self.root.bind("<Control-f>", lambda _event: self.focus_search())
        self.root.bind("/", lambda _event: self.focus_search())
        self.root.bind("?", lambda _event: self.show_help())
        self.root.bind("<Delete>", self._on_delete_key)
        self.root.bind("<Control-e>", lambda _event: self.export_csv())
        self.root.bind("<Control-i>", lambda _event: self.import_csv())
        self.root.bind("<Control-n>", lambda _event: self.new_prompt())
        self.root.bind("<Control-d>", lambda _event: self.duplicate_selected())
        self.root.bind("<Control-Return>", lambda _event: self.edit_selected())
        self.root.bind("<Control-Shift-C>", lambda _event: self.copy_selected_with_meta())
        self.root.bind("<Control-Shift-A>", lambda _event: self.copy_and_use_ai())
        self.root.bind("<Control-b>", self.toggle_selected_favorite)
        self.root.bind("<Control-Shift-I>", lambda _event: self.ai_improve_selected())
        self.root.bind("<Control-Shift-T>", lambda _event: self.ai_translate_selected())

    def _on_delete_key(self, _event=None):
        """Delete usuwa prompt tylko gdy fokus jest na liście — nie podczas
        edycji w polu wyszukiwania czy comboboxach."""
        focus = self.root.focus_get()
        if focus is not None and focus.winfo_class() in ("Entry", "TEntry", "Text", "TCombobox"):
            return None
        self.delete_selected()
        return "break"

    def available_models(self) -> list[str]:
        custom = [prompt.model for prompt in self.store.prompts if prompt.model]
        return merge_model_options(load_model_options(), custom)

    def available_zastosowania(self) -> list[str]:
        custom = [prompt.zastosowanie for prompt in self.store.prompts if prompt.zastosowanie]
        return merge_model_options(ZASTOSOWANIA_PRESET, custom)

    def available_tags(self) -> list[str]:
        custom: list[str] = []
        for prompt in self.store.prompts:
            custom.extend(tag_list_from_string(prompt.tags))
        return merge_model_options(TAGS_PRESET, custom)

    def copy_content_with_variables(self, content: str) -> bool:
        placeholders = extract_placeholders(content)
        if placeholders:
            dialog = FillVariablesDialog(self.root, content, title=t('Uzupełnij zmienne przed kopiowaniem'))
            self.root.wait_window(dialog)
            if not dialog.filled_content:
                return False
            content = dialog.filled_content
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()
        return True

    def _clipboard_from_prompt(self, prompt: Prompt) -> bool:
        return self.copy_content_with_variables(prompt.content)

    def copy_and_use_ai(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            messagebox.showinfo(
                APP_NAME,
                t('Wybierz prompt z listy po lewej, potem użyj „Kopiuj i użyj w AI”.'),
                parent=self.root,
            )
            return
        if not self._clipboard_from_prompt(prompt):
            return
        self.store.mark_checklist("copied")
        self._update_checklist_ui()
        platform = suggest_ai_platform(prompt.model) or "ChatGPT"
        self.open_ai_platform(platform, copy_prompt=False)
        self.store.mark_checklist("opened_ai")
        self._update_checklist_ui()
        self.set_status(f"{t('Skopiowano „')}{prompt.name}{t('” i otwarto ')}{platform}{t('.')}")

    def _update_checklist_ui(self) -> None:
        if not hasattr(self, "checklist_labels"):
            return
        labels = {
            "selected": "1. Wybierz prompt z listy",
            "copied": "2. Skopiuj treść do schowka",
            "opened_ai": "3. Otwórz ChatGPT / Claude",
            "added_prompt": "4. Dodaj własny prompt",
        }
        done = self.store.checklist
        all_done = all(done.get(key) for key in labels)
        if hasattr(self, "checklist_frame"):
            if all_done and self.store.onboarding_done:
                self.checklist_frame.grid_remove()
            else:
                self.checklist_frame.grid()
        for key, base in labels.items():
            mark = "✓" if done.get(key) else "○"
            self.checklist_labels[key].configure(text=f"{mark} {t(base)}")

    def show_onboarding(self) -> None:
        def _done() -> None:
            self.store.complete_onboarding()
            self._update_checklist_ui()

        OnboardingDialog(self.root, on_finish=_done)

    def open_product_page(self) -> None:
        if LANDING_PAGE_PATH.is_file():
            webbrowser.open(LANDING_PAGE_PATH.resolve().as_uri())
            self.set_status(t('Otwarto stronę produktu (landing).'))
        else:
            webbrowser.open(APP_HELP_URL)
            self.set_status(t('Otwarto dokumentację na GitHub.'))

    def open_download_page(self) -> None:
        webbrowser.open(APP_RELEASE_URL)
        self.set_status(t('Otwarto stronę pobrań.'))

    def _open_doc(self, path: Path, fallback_url: str, status: str) -> None:
        if path.is_file():
            webbrowser.open(path.resolve().as_uri())
            self.set_status(status)
        else:
            webbrowser.open(fallback_url)
            self.set_status(t('Otwarto dokumentację online.'))

    def open_pwa_import_guide(self) -> None:
        self._open_doc(DOC_PWA_IMPORT, APP_HELP_URL, "Otwarto instrukcję importu PWA.")

    def open_quickstart_doc(self) -> None:
        self._open_doc(DOC_QUICKSTART, APP_HELP_URL, "Otwarto szybki start.")

    def open_pricing_doc(self) -> None:
        pricing = APP_DIR / "PRICING.md"
        self._open_doc(pricing, APP_HELP_URL, "Otwarto cennik.")

    def show_pro_coming_soon(self) -> None:
        messagebox.showinfo(
            APP_NAME,
            t(
                "Paczki promptów Pro — w przygotowaniu\n\n"
                "Plan obejmuje gotowe zestawy (marketing, kod, automatyzacja) "
                "bez wymuszania konta w chmurze.\n\n"
                "Wersja Free zawiera pełną bibliotekę i wszystkie funkcje aplikacji.\n"
                "Szczegóły: "
            )
            + str(APP_DIR / "PRICING.md"),
            parent=self.root,
        )

    def restore_sample_prompts(self) -> None:
        if self.store.prompts:
            if not messagebox.askyesno(
                APP_NAME,
                t('Zastąpić obecną bibliotekę przykładowymi promptami?\nObecne wpisy zostaną usunięte.'),
                parent=self.root,
            ):
                return
        self.store.sample_data(force=True)
        self.selected_id = self.store.prompts[0].id if self.store.prompts else None
        self.refresh_all()
        if self.selected_id:
            self.tree.selection_set(self.selected_id)
            self.update_detail()
        self.set_status(t('Załadowano przykładowe prompty.'))

    def _highlight_search_in_text(self, widget, query: str) -> None:
        widget.tag_delete("search_hit")
        if not query:
            return
        colors = self.get_theme_colors()
        widget.tag_configure("search_hit", background=colors["search_hit"], foreground=colors["text"])
        start = "1.0"
        while True:
            pos = widget.search(query, start, stopindex=END, nocase=True)
            if not pos:
                break
            end_index = f"{pos}+{len(query)}c"
            widget.tag_add("search_hit", pos, end_index)
            start = end_index

    def open_ai_for_model(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            messagebox.showinfo(APP_NAME, t('Zaznacz prompt, aby otworzyć sugerowaną platformę AI.'), parent=self.root)
            return
        platform = suggest_ai_platform(prompt.model)
        if not platform:
            messagebox.showinfo(
                APP_NAME,
                f"{t('Nie rozpoznano platformy dla modelu „')}{prompt.model or 'brak'}"
                + t("”.\nUżyj przycisków ChatGPT, Claude lub Gemini."),
                parent=self.root,
            )
            return
        if not self._clipboard_from_prompt(prompt):
            return
        self.store.mark_checklist("copied")
        self._update_checklist_ui()
        self.open_ai_platform(platform, copy_prompt=False)
        self.store.mark_checklist("opened_ai")
        self._update_checklist_ui()
        self.set_status(f"{t('Skopiowano „')}{prompt.name}{t('” i otwarto ')}{platform}{t('.')}")

    def open_ai_platform(self, platform_name: str, *, copy_prompt: bool) -> None:
        url = next((item_url for name, item_url in AI_PLATFORMS if name == platform_name), "")
        if not url:
            return
        prompt = self.selected_prompt()
        if copy_prompt:
            if not prompt:
                messagebox.showinfo(
                    APP_NAME,
                    f"{t('Brak zaznaczonego promptu. Otwieram ')}{platform_name}{t(' bez kopiowania treści.')}",
                    parent=self.root,
                )
            elif not self._clipboard_from_prompt(prompt):
                return
            else:
                self.store.mark_checklist("copied")
                self._update_checklist_ui()
        webbrowser.open(url)
        if copy_prompt and prompt:
            self.store.mark_checklist("opened_ai")
            self._update_checklist_ui()
            self.set_status(f"{t('Skopiowano „')}{prompt.name}{t('” i otwarto ')}{platform_name}{t('.')}")
        else:
            self.set_status(f"{t('Otwarto ')}{platform_name}{t(' w przeglądarce.')}")

    def focus_search(self) -> str:
        self.search_entry.focus_set()
        self.search_entry.select_range(0, END)
        return "break"

    def refresh_all(self) -> None:
        self.refresh_filters()
        self.refresh_list()
        self.refresh_pinned()
        self.update_stats()

    def refresh_filters(self) -> None:
        models = self.available_models()
        zastosowania = self.available_zastosowania()
        tags = self.available_tags()
        status_values = ["Wszystkie", *STATUSES.values()]
        model_values = ["Wszystkie", *models]
        zastosowanie_values = ["Wszystkie", *zastosowania]
        tag_values = ["Wszystkie", *tags]
        self.status_combo.configure(values=status_values)
        self.model_combo.configure(values=model_values)
        self.zastosowanie_combo.configure(values=zastosowanie_values)
        self.tag_combo.configure(values=tag_values)
        for var, values in (
            (self.status_filter, status_values),
            (self.model_filter, model_values),
            (self.zastosowanie_filter, zastosowanie_values),
            (self.tag_filter, tag_values),
        ):
            if var.get() not in values:
                var.set("Wszystkie")

    def refresh_list(self) -> None:
        query = self.search_var.get().strip().lower()
        status_filter = self.status_filter.get()
        model_filter = self.model_filter.get()
        zastosowanie_filter = self.zastosowanie_filter.get()
        tag_filter = self.tag_filter.get()

        only_favorites = bool(self.favorites_only.get())
        terms = search_terms(query)

        result = []
        for prompt in self.store.prompts:
            if only_favorites and not prompt.favorite:
                continue
            if status_filter != "Wszystkie" and status_label(prompt.status) != status_filter:
                continue
            if model_filter != "Wszystkie" and prompt.model != model_filter:
                continue
            if zastosowanie_filter != "Wszystkie" and prompt.zastosowanie != zastosowanie_filter:
                continue
            if tag_filter != "Wszystkie" and tag_filter not in tag_list_from_string(prompt.tags):
                continue
            haystack = " ".join(
                [
                    prompt.name,
                    prompt.content,
                    prompt.comment,
                    prompt.model,
                    prompt.zastosowanie,
                    prompt.tags,
                    prompt.status,
                ]
            ).lower()
            # Wiele słów = warunek AND (kolejność bez znaczenia).
            if terms and not all(term in haystack for term in terms):
                continue
            result.append(prompt)

        sort = SORT_OPTIONS.get(self.sort_var.get(), "newest")
        if sort == "newest":
            result.sort(key=lambda p: p.created, reverse=True)
        elif sort == "oldest":
            result.sort(key=lambda p: p.created)
        elif sort == "az":
            result.sort(key=lambda p: p.name.lower())
        elif sort == "za":
            result.sort(key=lambda p: p.name.lower(), reverse=True)
        # Ulubione zawsze na górze — sort stabilny, więc kolejność wyżej zostaje.
        result.sort(key=lambda p: not p.favorite)

        self.filtered = result
        selected = self.selected_id
        self.tree.delete(*self.tree.get_children())
        for prompt in result:
            self.tree.insert(
                "",
                END,
                iid=prompt.id,
                values=(
                    "*" if prompt.pinned else "",
                    "★" if prompt.favorite else "",
                    prompt.name,
                    status_label(prompt.status),
                    prompt.model,
                    prompt.zastosowanie,
                    prompt.format,
                    format_date(prompt.created),
                ),
            )
        if selected and selected in {p.id for p in result}:
            self.tree.selection_set(selected)
        elif result:
            self.tree.selection_set(result[0].id)
        else:
            self.selected_id = None
            self.update_detail()

        self.status_bar.configure(text=f"{t('Wyświetlono ')}{len(result)}{t(' z ')}{len(self.store.prompts)}{t(' promptów')}")

    def refresh_pinned(self) -> None:
        self.pinned_list.delete(0, END)
        for prompt in self.store.prompts:
            if prompt.pinned:
                label = prompt.name if not prompt.model else f"{prompt.name} [{prompt.model}]"
                self.pinned_list.insert(END, label)

    def update_stats(self) -> None:
        total = len(self.store.prompts)
        models = len({p.model for p in self.store.prompts if p.model})
        pinned = len([p for p in self.store.prompts if p.pinned])
        today = datetime.now().date()
        added_today = len(
            [p for p in self.store.prompts if datetime.fromtimestamp(p.created / 1000).date() == today]
        )
        self.stats_label.configure(
            text=f"{total}{t(' promptów | ')}{models}{t(' modeli | ')}{pinned}{t(' przypiętych | dziś dodano: ')}{added_today}"
        )

    def update_detail(self) -> None:
        selection = self.tree.selection()
        self.selected_id = selection[0] if selection else None
        prompt = self.selected_prompt()
        library_empty = not self.store.prompts
        if library_empty:
            self.empty_state.grid()
            self.detail_text.grid_remove()
            self.primary_row.grid_remove()
            self.detail_actions.grid_remove()
            self.ai_buttons.grid_remove()
            self.detail_title.configure(text=t('Brak promptów'))
            self.detail_meta.configure(text="")
            self.detail_comment.configure(text="")
            return

        self.empty_state.grid_remove()
        self.detail_text.grid()
        self.primary_row.grid()
        self.detail_actions.grid()
        self.ai_buttons.grid()
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", END)
        if not prompt:
            self.detail_title.configure(text=t('Wybierz prompt z listy'))
            self.detail_meta.configure(text=t('Kliknij wiersz po lewej lub użyj „Kopiuj i użyj w AI”.'))
            self.detail_comment.configure(text="")
        else:
            self.detail_title.configure(text=prompt.name)
            tags_text = prompt.tags or "bez tagów"
            self.detail_meta.configure(
                text=(
                    f"{status_label(prompt.status)}{t(' | ')}{prompt.format}{t(' | ')}"
                    f"{prompt.model or 'bez modelu'}{t(' | ')}{prompt.zastosowanie or 'bez kategorii'}{t(' | tagi: ')}{tags_text}{t(' | ')}{format_date(prompt.created)}"
                )
            )
            self.detail_comment.configure(text=f"Wskazówka: {prompt.comment}" if prompt.comment else "")
            self.detail_text.insert("1.0", prompt.content)
            self._highlight_search_in_text(self.detail_text, self.search_var.get().strip())
        self.detail_text.configure(state="disabled")

    def selected_prompt(self) -> Prompt | None:
        if not self.selected_id:
            return None
        return next((prompt for prompt in self.store.prompts if prompt.id == self.selected_id), None)

    def new_prompt(self) -> None:
        dialog = PromptDialog(
            self.root,
            model_options=self.available_models(),
            zastosowanie_options=self.available_zastosowania(),
            tag_options=self.available_tags(),
            theme_getter=self.get_theme_colors,
        )
        self.root.wait_window(dialog)
        if dialog.result:
            self.store.prompts.insert(0, dialog.result)
            self.store.save()
            self.store.mark_checklist("added_prompt")
            self._update_checklist_ui()
            self.selected_id = dialog.result.id
            self.refresh_all()
            self.set_status(t('Prompt zapisany.'))

    def edit_selected(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        dialog = PromptDialog(
            self.root,
            prompt,
            model_options=self.available_models(),
            zastosowanie_options=self.available_zastosowania(),
            tag_options=self.available_tags(),
            theme_getter=self.get_theme_colors,
        )
        self.root.wait_window(dialog)
        if dialog.result:
            self.store.save()
            self.refresh_all()
            self.set_status(t('Prompt zaktualizowany.'))

    def export_for_pwa(self) -> None:
        data = self.store.to_pwa_library_json()
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=t('Eksport dla PWA'),
            defaultextension=".json",
            initialfile="promptLibrary-pwa.json",
            filetypes=[("JSON", "*.json")],
        )
        if path:
            Path(path).write_text(data, encoding="utf-8")
        self.root.clipboard_clear()
        self.root.clipboard_append(data)
        self.root.update()
        messagebox.showinfo(
            APP_NAME,
            "Skopiowano JSON do schowka.\n\n"
            "W przeglądarce (F12 → Application → Local Storage):\n"
            "wklej jako wartość klucza „promptLibrary”\n\n"
            + (f"Zapisano też plik:\n{path}" if path else ""),
            parent=self.root,
        )
        self.set_status(t('Eksport dla PWA — skopiowano do schowka.'))

    def export_to_cloud(self) -> None:
        dialog = CloudExportDialog(self.root, self.store)
        self.root.wait_window(dialog)
        if dialog.exported_path:
            self.set_status(f"{t('Eksport chmury: ')}{dialog.exported_path}")

    def quick_import_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title=t('Import CSV lub JSON'),
            filetypes=[
                ("CSV i JSON", "*.csv;*.json"),
                ("CSV", "*.csv"),
                ("JSON", "*.json"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not path:
            return
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            self._import_csv_path(file_path)
        elif suffix == ".json":
            self._import_json_path(file_path)
        else:
            messagebox.showwarning(APP_NAME, t('Obsługiwane rozszerzenia: .csv, .json'), parent=self.root)

    def _import_csv_path(self, path: Path) -> None:
        imported = self._read_csv(path)
        self._finish_file_import(imported, source_label=str(path.name))

    def _import_json_path(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, (str(t('Błąd JSON:\n')) + str(exc)), parent=self.root)
            return
        if isinstance(data, dict) and "prompts" in data:
            raw = data["prompts"]
        else:
            raw, _, _ = parse_pwa_import_data(data)
        imported = [Prompt.from_dict(item) for item in raw if isinstance(item, dict)]
        self._finish_file_import(imported, source_label=path.name)

    def _finish_file_import(self, imported: list[Prompt], *, source_label: str) -> None:
        valid = [p for p in imported if p.name and p.content]
        if not valid:
            messagebox.showwarning(APP_NAME, t('Brak poprawnych promptów w pliku.'), parent=self.root)
            return
        mode = messagebox.askyesnocancel(
            APP_NAME,
            (str(t('Plik: ')) + str(source_label) + str(t('\nZnaleziono ')) + str(len(valid)))
            + t(" promptów.\n\nTak = dopisz\nNie = zastąp bibliotekę\nAnuluj"),
            parent=self.root,
        )
        if mode is None:
            return
        if mode is False:
            self.store.prompts = valid
        else:
            existing = {p.name + "|" + p.content[:80] for p in self.store.prompts}
            fresh = [p for p in valid if p.name + "|" + p.content[:80] not in existing]
            self.store.prompts = fresh + self.store.prompts
        self.store.save()
        self.refresh_all()
        self.set_status(f"{t('Zaimportowano z pliku: ')}{source_label}")

    def show_history(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            messagebox.showinfo(APP_NAME, t('Zaznacz prompt, aby zobaczyć historię wersji.'), parent=self.root)
            return
        if not prompt.history:
            messagebox.showinfo(
                APP_NAME,
                t('Brak zapisanych wersji.\nHistoria powstaje przy każdej edycji promptu (do 5 wersji).'),
                parent=self.root,
            )
            return
        dialog = HistoryDialog(self.root, prompt, theme_getter=self.get_theme_colors)
        self.root.wait_window(dialog)
        if dialog.restored:
            self.store.save()
            self.refresh_all()
            self.set_status(f"{t('Przywrócono wersję promptu „')}{prompt.name}{t('”.')}")

    def import_from_pwa(self) -> None:
        dialog = PwaImportDialog(self.root, theme_getter=self.get_theme_colors)
        self.root.wait_window(dialog)
        if not dialog.imported:
            return
        valid = dialog.imported
        mode = messagebox.askyesnocancel(
            APP_NAME,
            f"{t('Znaleziono ')}{len(valid)}"
            + t(
                " promptów z PWA.\n\nTak = dopisz do biblioteki\nNie = zastąp całą bibliotekę\nAnuluj"
            ),
            parent=self.root,
        )
        if mode is None:
            return
        if mode is False:
            self.store.prompts = valid
            if dialog.n8n_url:
                self.store.n8n_url = dialog.n8n_url
            pwa_theme = dialog.theme.lower()
            if pwa_theme in ("dark", "ciemny"):
                self.store.theme = "ciemny"
            elif pwa_theme in ("grafit", "graphite"):
                self.store.theme = "grafit"
            elif pwa_theme in ("light", "jasny"):
                self.store.theme = "jasny"
            if self.store.theme in THEMES:
                self.theme_var.set(self.store.theme)
                self.apply_theme(save=False)
        else:
            existing_ids = {p.id for p in self.store.prompts}
            existing_keys = {p.name + "|" + p.content[:80] for p in self.store.prompts}
            fresh = [
                p
                for p in valid
                if p.id not in existing_ids and p.name + "|" + p.content[:80] not in existing_keys
            ]
            self.store.prompts = fresh + self.store.prompts
            if dialog.n8n_url and not self.store.n8n_url:
                self.store.n8n_url = dialog.n8n_url
        self.store.save()
        self.refresh_all()
        self.set_status(f"{t('Zaimportowano ')}{len(valid)}{t(' promptów z PWA.')}")

    def delete_selected(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        if not messagebox.askyesno(APP_NAME, f"{t('Usunąć prompt „')}{prompt.name}{t('”?')}", parent=self.root):
            return
        self.store.prompts = [item for item in self.store.prompts if item.id != prompt.id]
        self.store.save()
        self.selected_id = None
        self.refresh_all()
        self.set_status(t('Prompt usunięty.'))

    def toggle_selected_pin(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        prompt.pinned = not prompt.pinned
        self.store.save()
        self.refresh_all()
        self.set_status("Przypięto prompt." if prompt.pinned else "Odpięto prompt.")

    # --- Asystent AI -------------------------------------------------------

    def configure_ai(self) -> None:
        dialog = AiConfigDialog(self.root, self.store.ai_settings, theme_getter=self.get_theme_colors)
        self.root.wait_window(dialog)
        if dialog.result:
            self.store.ai_settings.update(dialog.result)
            self.store.save()
            engine_label = ai.ENGINES.get(self.store.ai_settings["engine"], "")
            self.set_status(f"{t('Zapisano konfigurację AI (')}{engine_label}{t(').')}")

    def show_ai_status(self) -> None:
        settings = self.store.ai_settings
        engine = settings.get("engine", ai.ENGINE_OLLAMA)
        source = ai.api_key_source()
        key_state = {
            "env": f"wykryty (zmienna {ai.OPENROUTER_API_KEY_ENV})",
            "plik": f"wykryty (ustawienia: {ai.api_key_file().name})",
        }.get(source, "BRAK — wpisz go w Konfiguracja AI")
        models = ai.list_ollama_models(settings.get("ollama_host", ai.OLLAMA_DEFAULT_HOST))
        lines = [
            f"Aktywny silnik: {ai.ENGINES.get(engine, engine)}",
            "",
            "OpenRouter (chmura)",
            f"  Klucz API: {key_state}",
            f"  Model: {settings.get('openrouter_model', '')}",
            "",
            "Ollama (lokalnie)",
            f"  Host: {settings.get('ollama_host', '')}",
            f"  Status: {'działa — modeli: ' + str(len(models)) if models else 'brak odpowiedzi'}",
            f"  Model: {settings.get('ollama_model', '')}",
        ]
        if models:
            lines.append("  Dostępne: " + ", ".join(models[:8]))
        messagebox.showinfo(APP_NAME, "\n".join(lines), parent=self.root)

    def _run_ai_action(self, action: str, *, title: str, target: str = "") -> None:
        prompt = self.selected_prompt()
        if not prompt:
            messagebox.showinfo(APP_NAME, t('Najpierw wybierz prompt z listy.'), parent=self.root)
            return
        if not prompt.content.strip():
            messagebox.showinfo(APP_NAME, t('Ten prompt nie ma treści.'), parent=self.root)
            return

        settings = self.store.ai_settings
        engine = settings.get("engine", ai.ENGINE_OLLAMA)
        model = (
            settings.get("openrouter_model", "")
            if engine == ai.ENGINE_OPENROUTER
            else settings.get("ollama_model", "")
        )

        def runner():
            return ai.run_ai_action(
                engine=engine,
                action=action,
                content=prompt.content,
                model=model,
                target=target,
                language=settings.get("translate_language", "angielski"),
                host=settings.get("ollama_host", ai.OLLAMA_DEFAULT_HOST),
            )

        dialog = AiResultDialog(
            self.root,
            title=f"{title}{t(' — ')}{ai.ENGINES.get(engine, engine)}",
            original=prompt.content,
            runner=runner,
            theme_getter=self.get_theme_colors,
        )
        self.root.wait_window(dialog)

        if not dialog.decision or not dialog.result_text.strip():
            return

        if dialog.decision == "replace":
            # Poprzednia treść trafia do historii — zmianę można cofnąć.
            push_prompt_history(prompt)
            prompt.content = dialog.result_text
            self.store.save()
            self.refresh_all()
            self.set_status(f"{title}{t(': treść zaktualizowana (poprzednia wersja w historii).')}")
        else:
            clone = Prompt(
                name=f"{prompt.name} ({title})",
                content=dialog.result_text,
                status=prompt.status,
                format=prompt.format,
                model=prompt.model,
                zastosowanie=prompt.zastosowanie,
                tags=prompt.tags,
                comment=prompt.comment,
            )
            self.store.prompts.insert(0, clone)
            self.store.save()
            self.selected_id = clone.id
            self.refresh_all()
            self.set_status(f"{title}{t(': zapisano jako nowy prompt.')}")

    def ai_improve_selected(self) -> None:
        self._run_ai_action(ai.ACTION_IMPROVE, title=t('Ulepszony'))

    def ai_translate_selected(self) -> None:
        language = self.store.ai_settings.get("translate_language", "angielski")
        self._run_ai_action(ai.ACTION_TRANSLATE, title=f"{t('Tłumaczenie ')}{language}")

    def ai_adapt_selected(self, target: str) -> None:
        self._run_ai_action(ai.ACTION_ADAPT, title=f"{t('Wersja ')}{target}", target=target)

    def _ask_adapt_target(self) -> None:
        """Menu podręczne z listą platform — wywoływane przyciskiem „Dostosuj…”."""
        menu = Menu(self.root, tearoff=False)
        for target in ai.ADAPT_TARGETS:
            menu.add_command(label=target, command=lambda name=target: self.ai_adapt_selected(name))
        try:
            widget = self.assistant_buttons
            menu.tk_popup(widget.winfo_rootx(), widget.winfo_rooty() + widget.winfo_height())
        finally:
            menu.grab_release()

    def toggle_selected_favorite(self, _event=None) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        prompt.favorite = not prompt.favorite
        self.store.save()
        self.refresh_all()
        self.set_status("Dodano do ulubionych." if prompt.favorite else "Usunięto z ulubionych.")

    def copy_selected(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        if self.copy_content_with_variables(prompt.content):
            self.store.mark_checklist("copied")
            self._update_checklist_ui()
            self.set_status(t('Prompt skopiowany do schowka.'))

    def copy_selected_with_meta(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        lines = [
            f"# {prompt.name}",
            f"Status: {status_label(prompt.status)} | Format: {prompt.format} | Model: {prompt.model or '—'}",
            f"Zastosowanie: {prompt.zastosowanie or '—'}",
        ]
        if prompt.comment:
            lines.append(f"Wskazówka: {prompt.comment}")
        lines.extend(["", prompt.content])
        body = "\n".join(lines)
        placeholders = extract_placeholders(prompt.content)
        if placeholders:
            dialog = FillVariablesDialog(self.root, prompt.content, title=t('Uzupełnij zmienne w treści'))
            self.root.wait_window(dialog)
            if dialog.filled_content:
                lines[-1] = dialog.filled_content
                body = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(body)
        self.root.update()
        self.set_status(t('Skopiowano prompt z metadanymi.'))

    def duplicate_selected(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        clone = Prompt(
            name=f"{prompt.name} (kopia)",
            content=prompt.content,
            status=prompt.status,
            format=prompt.format,
            model=prompt.model,
            zastosowanie=prompt.zastosowanie,
            tags=prompt.tags,
            comment=prompt.comment,
            pinned=False,
        )
        self.store.prompts.insert(0, clone)
        self.store.save()
        self.selected_id = clone.id
        self.refresh_all()
        self.set_status(f"{t('Utworzono kopię: „')}{clone.name}{t('”.')}")

    def open_pinned(self, _event=None) -> None:
        index = self.pinned_list.curselection()
        if not index:
            return
        pinned = [p for p in self.store.prompts if p.pinned]
        if index[0] >= len(pinned):
            return
        prompt = pinned[index[0]]
        self.selected_id = prompt.id
        self.clear_filters()
        self.tree.selection_set(prompt.id)
        self.tree.see(prompt.id)
        self.update_detail()

    def clear_filters(self) -> None:
        self.status_filter.set("Wszystkie")
        self.model_filter.set("Wszystkie")
        self.zastosowanie_filter.set("Wszystkie")
        self.tag_filter.set("Wszystkie")
        self.favorites_only.set(False)
        self.search_var.set("")
        self.refresh_list()

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=t('Eksport CSV'),
            defaultextension=".csv",
            initialfile="biblioteka-promptow.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Nazwa", "Status", "Format", "Model AI", "Zastosowanie", "Tagi", "Data Utworzenia", "Komentarz", "Treść Promptu"]
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
        self.set_status(f"{t('Eksport gotowy: ')}{path}")

    def export_backup_json(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=t('Kopia zapasowa JSON'),
            defaultextension=".json",
            initialfile=f"prompbase-backup-{datetime.now().strftime('%Y%m%d')}.json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(
            json.dumps(self.store.to_payload(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.set_status(f"{t('Kopia zapasowa zapisana: ')}{path}")

    def import_backup_json(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title=t('Przywróć z JSON'),
            filetypes=[("JSON", "*.json"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, (str(t('Nie można wczytać pliku JSON:\n')) + str(exc)), parent=self.root)
            return

        if isinstance(data, list):
            raw_prompts = data
            n8n_url = self.store.n8n_url
            theme = self.store.theme
        elif isinstance(data, dict):
            raw_prompts = data.get("prompts", [])
            n8n_url = data.get("n8n_url", self.store.n8n_url)
            theme = data.get("theme", self.store.theme)
        else:
            messagebox.showerror(APP_NAME, t('Nieprawidłowy format kopii zapasowej.'), parent=self.root)
            return

        imported = [Prompt.from_dict(item) for item in raw_prompts if isinstance(item, dict)]
        valid = [p for p in imported if p.name and p.content]
        if not valid:
            messagebox.showwarning(APP_NAME, t('W kopii nie ma poprawnych promptów.'), parent=self.root)
            return

        mode = messagebox.askyesnocancel(
            APP_NAME,
            f"{t('Znaleziono ')}{len(valid)}"
            + t(
                " promptów.\n\nTak = dopisz do biblioteki\n"
                "Nie = zastąp całą bibliotekę (i ustawienia z pliku)\nAnuluj"
            ),
            parent=self.root,
        )
        if mode is None:
            return

        if mode is False:
            self.store.prompts = valid
            self.store.n8n_url = str(n8n_url or "")
            if theme in THEMES:
                self.store.theme = theme
                self.theme_var.set(theme)
                self.apply_theme(save=False)
        else:
            existing = {p.name + "|" + p.content[:80] for p in self.store.prompts}
            fresh = [p for p in valid if p.name + "|" + p.content[:80] not in existing]
            self.store.prompts = fresh + self.store.prompts

        self.store.save()
        self.refresh_all()
        self.set_status(f"{t('Przywrócono ')}{len(valid)}{t(' promptów z kopii zapasowej.')}")

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title=t('Import CSV'),
            filetypes=[("CSV", "*.csv"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        mode = messagebox.askyesnocancel(
            APP_NAME,
            t('Tak = dopisz nowe prompty\nNie = zastąp całą bibliotekę\nAnuluj = przerwij import'),
            parent=self.root,
        )
        if mode is None:
            return
        replace = mode is False

        imported = self._read_csv(Path(path))
        valid = [prompt for prompt in imported if prompt.name and prompt.content]
        if not valid:
            messagebox.showwarning(APP_NAME, t('Nie znaleziono poprawnych promptów w CSV.'), parent=self.root)
            return

        if replace:
            self.store.prompts = valid
            skipped = 0
        else:
            existing = {p.name + "|" + p.content[:50] for p in self.store.prompts}
            fresh = [p for p in valid if p.name + "|" + p.content[:50] not in existing]
            skipped = len(valid) - len(fresh)
            self.store.prompts = fresh + self.store.prompts

        self.store.save()
        self.refresh_all()
        self.set_status(f"{t('Zaimportowano ')}{len(valid) - skipped}{t(' promptów. Pominięto duplikatów: ')}{skipped}{t('.')}")

    def _read_csv(self, path: Path) -> list[Prompt]:
        text = path.read_text(encoding="utf-8-sig")
        first_line = text.splitlines()[0] if text.splitlines() else ""
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        prompts = []
        mapping = {
            "nazwa": "name",
            "name": "name",
            "status": "status",
            "format": "format",
            "model ai": "model",
            "model": "model",
            "zastosowanie": "zastosowanie",
            "tagi": "tags",
            "tags": "tags",
            "komentarz": "comment",
            "komentarz / wskazówka": "comment",
            "komentarz / wskazowka": "comment",
            "comment": "comment",
            "treść promptu": "content",
            "tresc promptu": "content",
            "treść": "content",
            "tresc": "content",
            "content": "content",
            "data utworzenia": "created_str",
        }
        for row in reader:
            normalized = {}
            for key, value in row.items():
                mapped = mapping.get((key or "").lower().strip())
                if mapped:
                    normalized[mapped] = (value or "").strip()
            if normalized.get("content"):
                normalized["content"] = normalized["content"].replace(" ↵ ", "\n")
            status_raw = normalized.get("status", "nowy") or "nowy"
            if status_raw in STATUS_FROM_LABEL:
                status_value = STATUS_FROM_LABEL[status_raw]
            elif status_raw in STATUSES:
                status_value = status_raw
            else:
                status_value = status_raw
            prompt = Prompt(
                name=normalized.get("name", ""),
                content=normalized.get("content", ""),
                status=status_value,
                format=normalized.get("format", "tekst") or "tekst",
                model=normalized.get("model", ""),
                zastosowanie=normalized.get("zastosowanie", ""),
                tags=parse_tags_value(normalized.get("tags", "")),
                comment=normalized.get("comment", ""),
                created=parse_date_to_ms(normalized.get("created_str", "")),
            )
            prompts.append(prompt)
        return prompts

    def ensure_n8n_url(self) -> str:
        if self.store.n8n_url and validate_n8n_url(self.store.n8n_url):
            return self.store.n8n_url
        self.configure_n8n()
        url = normalize_n8n_url(self.store.n8n_url)
        if url and validate_n8n_url(url):
            return url
        return ""

    def configure_n8n(self) -> None:
        dialog = N8nConfigDialog(self.root, self.store.n8n_url, post_json=self._post_json)
        self.root.wait_window(dialog)
        if dialog.saved_url is None:
            return
        self.store.n8n_url = dialog.saved_url
        self.store.save()
        self.set_status(t('Konfiguracja n8n zapisana.'))

    def test_n8n_webhook(self) -> None:
        url = self.ensure_n8n_url()
        if not url:
            return
        payload = n8n_envelope(
            "test",
            message=t('Test połączenia z Biblioteki Promptów AI (PrompBase Python)'),
        )
        self._post_json(url, payload, "Test webhooka n8n zakończony pomyślnie.")

    def send_selected_to_n8n(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            messagebox.showinfo(APP_NAME, t('Zaznacz prompt na liście, który chcesz wysłać do n8n.'), parent=self.root)
            return
        url = self.ensure_n8n_url()
        if not url:
            return
        payload = n8n_envelope("single_prompt", **prompt_to_n8n_dict(prompt))
        self._post_json(url, payload, f'Wysłano „{prompt.name}” do n8n.')

    def sync_all_to_n8n(self) -> None:
        url = self.ensure_n8n_url()
        if not url:
            return
        choice = messagebox.askyesnocancel(
            APP_NAME,
            t('Co wysłać do n8n?\n\nTak — cała biblioteka\nNie — tylko przypięte prompty\nAnuluj — przerwij'),
            parent=self.root,
        )
        if choice is None:
            return
        pinned_only = choice is False
        prompts = [p for p in self.store.prompts if p.pinned] if pinned_only else list(self.store.prompts)
        if not prompts:
            messagebox.showwarning(
                APP_NAME,
                "Brak przypiętych promptów do synchronizacji." if pinned_only else "Biblioteka jest pusta.",
                parent=self.root,
            )
            return
        payload = n8n_envelope(
            "sync",
            count=len(prompts),
            pinned_only=pinned_only,
            prompts=[prompt_to_n8n_dict(p) for p in prompts],
        )
        size_kb = len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) // 1024
        if size_kb > 5120:
            if not messagebox.askyesno(
                APP_NAME,
                f"{t('Payload ma ok. ')}{size_kb}{t(' KB (')}{len(prompts)}{t(' promptów). Kontynuować wysyłkę?')}",
                parent=self.root,
            ):
                return
        self._post_json(url, payload, f"Synchronizacja OK: {len(prompts)} promptów.")

    def export_n8n_json(self) -> None:
        """Zapis lokalny tego samego JSON co webhook sync — do testów workflow n8n."""
        choice = messagebox.askyesnocancel(
            APP_NAME,
            t('Zapis JSON dla n8n:\n\nTak — cała biblioteka\nNie — tylko przypięte\nAnuluj'),
            parent=self.root,
        )
        if choice is None:
            return
        pinned_only = choice is False
        prompts = [p for p in self.store.prompts if p.pinned] if pinned_only else list(self.store.prompts)
        if not prompts:
            messagebox.showwarning(APP_NAME, t('Brak promptów do eksportu.'), parent=self.root)
            return
        payload = n8n_envelope(
            "sync",
            count=len(prompts),
            pinned_only=pinned_only,
            prompts=[prompt_to_n8n_dict(p) for p in prompts],
        )
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=t('Eksport JSON dla n8n'),
            defaultextension=".json",
            initialfile="prompbase-n8n-sync.json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.set_status(f"{t('Zapisano JSON dla n8n: ')}{path}")

    def _post_json(self, url: str, payload: dict, ok_message: str) -> bool:
        normalized_url = normalize_n8n_url(url)
        if not validate_n8n_url(normalized_url):
            messagebox.showerror(
                APP_NAME,
                t('Nieprawidłowy URL webhooka.\n\nAdres musi zaczynać się od http:// lub https:// i zawierać ścieżkę /webhook/ (np. https://twoja-instancja.app.n8n.cloud/webhook/prompbase).'),
                parent=self.root,
            )
            return False

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            normalized_url,
            data=data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": f"{APP_NAME}/{APP_VERSION}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=N8N_HTTP_TIMEOUT) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace").strip()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip() if exc.fp else ""
            messagebox.showwarning(
                APP_NAME,
                (str(t('n8n zwrócił błąd HTTP ')) + str(exc.code) + str(t('.\n\n')) + str(detail or exc.reason)),
                parent=self.root,
            )
            self.set_status(f"{t('Błąd n8n: HTTP ')}{exc.code}")
            return False
        except URLError as exc:
            messagebox.showwarning(
                APP_NAME,
                (str(t('Nie udało się połączyć z n8n:\n')) + str(exc.reason or exc)),
                parent=self.root,
            )
            self.set_status(t('Błąd połączenia z n8n.'))
            return False
        except TimeoutError:
            messagebox.showwarning(
                APP_NAME,
                f"{t('Przekroczono limit czasu (')}{N8N_HTTP_TIMEOUT}{t('s). Sprawdź URL i czy workflow n8n jest aktywny.')}",
                parent=self.root,
            )
            self.set_status(t('Timeout połączenia z n8n.'))
            return False

        if status < 200 or status >= 300:
            messagebox.showwarning(
                APP_NAME,
                (str(t('n8n zwrócił nieoczekiwany status HTTP ')) + str(status) + str(t('.\n\n')) + str(body[:500])),
                parent=self.root,
            )
            self.set_status(f"{t('Błąd n8n: HTTP ')}{status}")
            return False

        suffix = f" — odpowiedź: {body[:120]}" if body else ""
        self.set_status(f"{ok_message}{t(' (HTTP ')}{status}{t(')')}{suffix}")
        return True

    def show_help(self) -> None:
        landing_hint = (
            f"\nStrona produktu: {LANDING_PAGE_PATH}\n" if LANDING_PAGE_PATH.is_file() else ""
        )
        messagebox.showinfo(
            t("PrompBase - pomoc"),
            (str(t('PrompBase v')) + str(APP_VERSION) + str(t('\nAutor: ')) + str(APP_AUTHOR) + str(t('\nDokumentacja: ')) + str(APP_HELP_URL) + str(t('\nPobierz: ')) + str(APP_RELEASE_URL) + str(landing_hint))
            + t(
                "\n\nGłówna akcja: „Kopiuj i użyj w AI” — kopiuje prompt i otwiera platformę.\n"
                "Przewodnik startowy: menu Pomoc.\n\n"
                "Skróty:\n"
                "Ctrl+N - nowy prompt\n"
                "Ctrl+D - duplikuj prompt\n"
                "Ctrl+Enter - edytuj zaznaczony\n"
                "Ctrl+Shift+A - kopiuj i użyj w AI (główna akcja)\n"
                "Ctrl+Shift+C - kopiuj z metadanymi\n"
                "/ lub Ctrl+F - wyszukiwanie\n"
                "Delete - usuń zaznaczony\n"
                "Ctrl+I - import CSV\n"
                "Ctrl+E - eksport CSV\n"
                "Ctrl+Shift+N - konfiguracja n8n\n\n"
                "Plik -> Kopia zapasowa JSON / Przywróć z JSON\n"
                "Plik -> Import z PWA / Eksport dla PWA\n"
                "Plik -> Eksport do chmury (folder Google Drive lub OneDrive)\n"
                "Tagi — filtrowanie i pole w edycji (po przecinku)\n"
                "Kopiowanie — uzupełnia [TEMAT], [TEKST] jeśli są w prompcie\n"
                "Szukaj — podświetla frazę w podglądzie treści\n"
                "Historia — do 5 wersji przy edycji\n"
                "Przy zapisie tworzona jest kopia promptbase.json.bak\n\n"
                "Menu AI oraz przyciski ChatGPT / Claude / Gemini:\n"
                "kopiują zaznaczony prompt do schowka i otwierają stronę modelu.\n\n"
                "n8n (Narzędzia):\n"
                "- skonfiguruj URL webhooka (/webhook/ w adresie)\n"
                "- Testuj webhook — wysyła type: test\n"
                "- Wyślij zaznaczony — type: single_prompt\n"
                "- Synchronizuj — type: sync (cała biblioteka lub przypięte)\n"
                "- Eksportuj JSON — ten sam format bez wysyłki HTTP\n\n"
                "Widok -> Tryb jasny/ciemny zmienia wygląd aplikacji.\n"
                "Dane są zapisywane lokalnie w pliku JSON. Import/eksport CSV jest zgodny z wersją PWA."
            ),
            parent=self.root,
        )

    def show_data_path(self) -> None:
        backup = self.store.path.with_suffix(".json.bak")
        extra = f"\n\nOstatnia kopia automatyczna:\n{backup}" if backup.exists() else ""
        messagebox.showinfo(APP_NAME, (str(t('Plik danych:\n')) + str(self.store.path) + str(extra)), parent=self.root)

    def open_data_folder(self) -> None:
        folder = self.store.path.parent
        try:
            if platform.system().lower() == "windows":
                os.startfile(folder)  # noqa: S606
            elif platform.system().lower() == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
            self.set_status(f"{t('Otwarto folder: ')}{folder}")
        except OSError as exc:
            messagebox.showwarning(APP_NAME, (str(t('Nie udało się otworzyć folderu:\n')) + str(exc)), parent=self.root)

    def set_status(self, message: str) -> None:
        self.status_bar.configure(text=message)


def main() -> None:
    root = Tk()
    # Przypięcie do root utrzymuje referencję do aplikacji przez cały mainloop.
    root.prompbase_app = PrompBaseApp(root)
    root.mainloop()
