"""Główne okno aplikacji PrompBaseApp i wejście main()."""
from __future__ import annotations

import csv
import os
import platform
import subprocess
import threading
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
    TclError,
    Tk,
    W,
    X,
    messagebox,
    ttk,
)

from pbcore import ai, i18n
from pbcore.ai_dialogs import AiConfigDialog
from pbcore.app_ai import AiAssistantMixin
from pbcore.app_io import ImportExportMixin
from pbcore.app_n8n import N8nMixin
from pbcore.core import *  # noqa: F401,F403
from pbcore.dialogs import *  # noqa: F401,F403
from pbcore.i18n import t
from pbcore.models import *  # noqa: F401,F403


class PrompBaseApp(AiAssistantMixin, ImportExportMixin, N8nMixin):
    def __init__(self, root: Tk):
        self.root = root
        # PromptStore.load() wywołuje i18n.set_language() — musi zajść
        # PRZED jakimkolwiek t()/title(), inaczej pierwszy render (w tym
        # pasek tytułu okna) dostaje domyślny język, nie zapisany wybór.
        self.store = PromptStore(app_data_dir() / "promptbase.json")

        self.root.title(f"{APP_NAME}{t(' - Biblioteka Promptów AI')}")
        # Szersze okno startowe: przy 1180 px lista i podgląd dzieliły się tak,
        # że ostatnie kolumny („Zastosowanie", „Data") były ucinane.
        self.root.geometry("1400x820")
        self.root.minsize(1040, 640)
        self._set_window_icon()

        self.filtered: list[Prompt] = []
        self.selected_id: str | None = None

        self.search_var = StringVar()
        # Etykiety, nie literały: PromptStore (wyżej) ustawił już język,
        # więc wartości startowe muszą być w tym samym języku co listy.
        wszystkie = all_filter_label()
        self.status_filter = StringVar(value=wszystkie)
        self.model_filter = StringVar(value=wszystkie)
        self.zastosowanie_filter = StringVar(value=wszystkie)
        self.tag_filter = StringVar(value=wszystkie)
        self.sort_var = StringVar(value=sort_display_values()[0])
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

    # Kolejność preferencji krojów interfejsu. „Segoe UI Variable" to krój
    # systemowy Windows 11 — wygląda nowocześniej niż zwykłe Segoe UI, ale nie
    # ma go na starszych systemach, więc schodzimy po liście do tego, co jest.
    UI_FONT_CANDIDATES = ("Segoe UI Variable Text", "Segoe UI", "Tahoma")
    MONO_FONT_CANDIDATES = ("Cascadia Code", "Cascadia Mono", "Consolas", "Courier New")

    def _pick_font(self, candidates: tuple[str, ...], fallback: str) -> str:
        try:
            from tkinter import font as tkfont

            available = {name.lower() for name in tkfont.families(self.root)}
        except Exception:
            return fallback
        for name in candidates:
            if name.lower() in available:
                return name
        return fallback

    def ui_font(self, size: int, weight: str = "normal"):
        return (self._ui_family, size, weight)

    def _configure_style(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.style = style
        self._ui_family = self._pick_font(self.UI_FONT_CANDIDATES, "Segoe UI")
        self._mono_family = self._pick_font(self.MONO_FONT_CANDIDATES, "Consolas")
        self.apply_theme(save=False)

    def _set_initial_sash(self) -> None:
        """Ustawia belkę podziału na ~62% szerokości (lista / podgląd)."""
        split = getattr(self, "_split", None)
        if split is None:
            return
        try:
            width = split.winfo_width()
            if width > 400:
                split.sashpos(0, int(width * 0.62))
        except (TclError, AttributeError):
            pass

    def run_in_background(self, work, on_done, *, on_error=None, busy_status: str = "") -> None:
        """Liczy `work()` w wątku, a wynik oddaje w wątku Tk.

        Tk nie jest bezpieczne wątkowo, więc wątek roboczy NIE dotyka okna —
        odkłada wynik, a odbiera go pętla `after` należąca do wątku głównego.
        Dzięki temu wczytanie dużego arkusza nie zamraża interfejsu.
        """
        if busy_status:
            self.set_status(busy_status)
        box: dict = {}

        def worker() -> None:
            try:
                box["value"] = work()
            except Exception as exc:  # noqa: BLE001 - przekazujemy do on_error
                box["error"] = exc

        def poll() -> None:
            if not box:
                self.root.after(80, poll)
                return
            if "error" in box:
                error = box["error"]
                if on_error is not None:
                    on_error(error)
                else:
                    log_exception(type(error), error, error.__traceback__)
                    messagebox.showerror(APP_NAME, str(error), parent=self.root)
                    self.set_status(t('Operacja nie powiodła się.'))
                return
            on_done(box["value"])

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, poll)

    def save_store(self) -> bool:
        """Zapisuje bibliotekę i mówi o niepowodzeniu zamiast milczeć.

        Zapis sam w sobie jest atomowy (plik tymczasowy + os.replace), ale
        przy pełnym dysku albo pliku zablokowanym przez inny program rzuca
        wyjątkiem. Wcześniej leciał on przez wszystkie 18 miejsc wywołania
        prosto do Tk, więc użytkownik tracił zmianę, nie wiedząc o tym.
        """
        try:
            self.store.save()
            return True
        except (OSError, ValueError, TypeError) as exc:
            log_exception(type(exc), exc, exc.__traceback__)
            messagebox.showerror(
                APP_NAME,
                t('Nie udało się zapisać biblioteki:\n\n')
                + str(exc)
                + t('\n\nZmiana działa tylko do zamknięcia programu. '
                    'Zwolnij miejsce na dysku lub zamknij program blokujący plik '
                    'i zapisz ponownie.'),
                parent=self.root,
            )
            self.set_status(t('BŁĄD: nie udało się zapisać biblioteki.'))
            return False

    def get_theme_colors(self) -> dict:
        return theme_colors(self.theme_var.get())

    def register_text_widget(self, widget) -> None:
        if widget not in self._themed_text_widgets:
            self._themed_text_widgets.append(widget)
        apply_widget_theme(widget, self.get_theme_colors())

    def apply_theme(self, save: bool = True) -> None:
        theme_name = self.theme_var.get()
        colors = self.get_theme_colors()
        c = colors
        self.root.configure(bg=c["bg"])
        s = self.style
        ui = self.ui_font

        # Motyw clam rysuje przyciski i pola z trójwymiarową fazką. Ustawienie
        # lightcolor/darkcolor na kolor tła gasi ją całkowicie — to jest ta jedna
        # zmiana, po której interfejs przestaje wyglądać jak sprzed dwóch dekad,
        # a rolę krawędzi przejmuje włosowa ramka w kolorze `border`.
        flat = {"borderwidth": 0, "relief": "flat"}

        s.configure(
            ".",
            background=c["bg"],
            foreground=c["text"],
            fieldbackground=c["field"],
            bordercolor=c["border"],
            lightcolor=c["bg"],
            darkcolor=c["bg"],
            focuscolor=c["accent"],
            font=ui(10),
        )
        s.configure("TFrame", background=c["bg"])
        s.configure("TLabel", background=c["bg"], foreground=c["text"], font=ui(10))
        s.configure("TSeparator", background=c["border"])

        # Karty: panele boczne i podgląd stoją na jaśniejszej powierzchni odciętej
        # włosową ramką, zamiast zlewać się z tłem okna.
        s.configure(
            "TLabelframe",
            background=c["surface"],
            bordercolor=c["border"],
            lightcolor=c["surface"],
            darkcolor=c["surface"],
            borderwidth=1,
            relief="solid",
        )
        s.configure(
            "TLabelframe.Label",
            background=c["surface"],
            foreground=c["muted"],
            font=ui(9, "bold"),
        )

        # Skala typograficzna — jeden zestaw rozmiarów zamiast wartości
        # dobieranych osobno w każdym miejscu.
        s.configure("Header.TLabel", background=c["bg"], foreground=c["text"], font=ui(20, "bold"))
        s.configure("Title.TLabel", background=c["surface"], foreground=c["text"], font=ui(14, "bold"))
        s.configure("Stat.TLabel", background=c["bg"], foreground=c["text"], font=ui(10, "bold"))
        s.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"], font=ui(9))
        s.configure("CardMuted.TLabel", background=c["surface"], foreground=c["muted"], font=ui(9))
        s.configure("Card.TLabel", background=c["surface"], foreground=c["text"], font=ui(10))
        s.configure("Card.TFrame", background=c["surface"])
        s.configure("CardStat.TLabel", background=c["surface"], foreground=c["text"], font=ui(10, "bold"))

        # Przyciski: płaskie, z wyraźnym oddechem i stanem po najechaniu.
        s.configure(
            "TButton",
            background=c["surface"],
            foreground=c["text"],
            bordercolor=c["border"],
            lightcolor=c["surface"],
            darkcolor=c["surface"],
            borderwidth=1,
            relief="flat",
            padding=(12, 7),
            font=ui(10),
        )
        s.map(
            "TButton",
            background=[("pressed", c["select"]), ("active", c["select"])],
            bordercolor=[("focus", c["accent"]), ("active", c["accent"])],
            foreground=[("disabled", c["muted"])],
        )
        # Ciasne rzędy akcji: mniejszy padding, żeby etykiety mieściły się w całości.
        s.configure("Compact.TButton", padding=(6, 6), font=ui(9))
        s.map(
            "Compact.TButton",
            background=[("pressed", c["select"]), ("active", c["select"])],
            bordercolor=[("focus", c["accent"]), ("active", c["accent"])],
        )

        for name, size, pad in (("Primary.TButton", 11, (14, 8)), ("Accent.TButton", 10, (12, 7))):
            s.configure(
                name,
                background=c["accent"],
                foreground=c["accent_text"],
                bordercolor=c["accent"],
                lightcolor=c["accent"],
                darkcolor=c["accent"],
                borderwidth=1,
                relief="flat",
                padding=pad,
                font=ui(size, "bold"),
            )
            s.map(
                name,
                background=[("pressed", c["accent_hover"]), ("active", c["accent_hover"])],
                bordercolor=[("active", c["accent_hover"])],
                foreground=[("disabled", c["muted"])],
            )

        # Pola tekstowe i listy rozwijane: płaskie, ramka barwi się na akcent
        # dopiero gdy pole ma fokus. Krawędź jest wyraźniejsza niż przy kartach,
        # bo to ona pozwala rozpoznać kontrolkę — biała ramka na białym polu
        # czyniła pole wyszukiwania praktycznie niewidocznym (WCAG 1.4.11).
        for name in ("TEntry", "TCombobox", "TSpinbox"):
            s.configure(
                name,
                fieldbackground=c["field"],
                background=c["field"],
                foreground=c["text"],
                bordercolor=c["control_border"],
                lightcolor=c["control_border"],
                darkcolor=c["control_border"],
                insertcolor=c["text"],
                arrowcolor=c["muted"],
                borderwidth=1,
                relief="flat",
                padding=(8, 6),
            )
            s.map(
                name,
                bordercolor=[("focus", c["accent"]), ("hover", c["muted"])],
                lightcolor=[("focus", c["accent"])],
                darkcolor=[("focus", c["accent"])],
                arrowcolor=[("active", c["accent"])],
            )
        s.map(
            "TCombobox",
            fieldbackground=[("readonly", c["field"])],
            foreground=[("readonly", c["text"])],
            selectbackground=[("readonly", c["field"])],
            selectforeground=[("readonly", c["text"])],
        )
        # Rozwijana lista comboboxa to widget Tk, nie ttk — stylujemy ją osobno.
        self.root.option_add("*TCombobox*Listbox.background", c["surface"])
        self.root.option_add("*TCombobox*Listbox.foreground", c["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", c["select"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", c["text"])

        # Pola wyboru i przełączniki miały 23 px wysokości — za mało jak na
        # kontrolki używane przy każdym filtrowaniu. Padding podnosi cel kliknięcia
        # do poziomu pozostałych kontrolek (~33 px).
        s.configure(
            "TCheckbutton",
            background=c["surface"],
            foreground=c["text"],
            indicatorcolor=c["field"],
            bordercolor=c["control_border"],
            focuscolor=c["accent"],
            padding=(4, 7),
            font=ui(10),
        )
        s.map("TCheckbutton", indicatorcolor=[("selected", c["accent"])])
        s.configure(
            "TRadiobutton",
            background=c["bg"],
            foreground=c["text"],
            indicatorcolor=c["field"],
            bordercolor=c["control_border"],
            focuscolor=c["accent"],
            padding=(4, 7),
            font=ui(10),
        )
        s.map("TRadiobutton", indicatorcolor=[("selected", c["accent"])])

        # Lista promptów: wyższe wiersze (łatwiej trafić i czytać), bez kratownicy,
        # nagłówki jako ciche etykiety zamiast wypukłych klawiszy.
        s.configure(
            "Treeview",
            background=c["surface"],
            foreground=c["text"],
            fieldbackground=c["surface"],
            bordercolor=c["border"],
            lightcolor=c["surface"],
            darkcolor=c["surface"],
            rowheight=30,
            borderwidth=0,
            relief="flat",
            font=ui(10),
        )
        s.configure(
            "Treeview.Heading",
            background=c["surface"],
            foreground=c["muted"],
            bordercolor=c["border"],
            lightcolor=c["surface"],
            darkcolor=c["surface"],
            # Poziomy padding 10 px nie mieścił się w kolumnach ikon —
            # nagłówek „Pin" był ucinany do „Pir".
            padding=(6, 8),
            font=ui(9, "bold"),
            **flat,
        )
        s.map(
            "Treeview.Heading",
            background=[("active", c["row_alt"])],
            foreground=[("active", c["text"])],
        )
        s.map(
            "Treeview",
            background=[("selected", c["select"])],
            foreground=[("selected", c["text"])],
        )
        # Pasy co drugi wiersz — na długiej liście oko trzyma się wiersza.
        tree = getattr(self, "tree", None)
        if tree is not None:
            tree.tag_configure("odd", background=c["row_alt"])
            tree.tag_configure("even", background=c["surface"])

        # Smukłe paski przewijania bez strzałek.
        for orient in ("Vertical", "Horizontal"):
            s.configure(
                f"{orient}.TScrollbar",
                background=c["border"],
                troughcolor=c["bg"],
                bordercolor=c["bg"],
                lightcolor=c["border"],
                darkcolor=c["border"],
                arrowcolor=c["bg"],
                arrowsize=1,
                borderwidth=0,
                relief="flat",
            )
            s.map(f"{orient}.TScrollbar", background=[("active", c["muted"])])

        s.configure("TPanedwindow", background=c["bg"])
        s.configure("Sash", sashthickness=8, gripcount=0, background=c["bg"])
        s.configure("TProgressbar", background=c["accent"], troughcolor=c["border"], **flat)

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
            self.save_store()
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
        self.save_store()
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
        file_menu.add_command(label=t('Import XLSX (Excel)...'), command=self.import_xlsx)
        file_menu.add_command(label=t('Import z PWA (przeglądarka)...'), command=self.import_from_pwa)
        file_menu.add_command(label=t('Instrukcja importu PWA'), command=self.open_pwa_import_guide)
        file_menu.add_command(label=t('Eksport CSV...'), command=self.export_csv)
        file_menu.add_command(label=t('Eksport XLSX (Excel)...'), command=self.export_xlsx)
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
        if not is_msix_package():
            # Zasada Microsoft Store 10.1.5 (Software Distribution) zabrania
            # promowania planów/zakupów poza systemem płatności Store —
            # w wersji sklepowej (MSIX) ta pozycja jest ukryta.
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
        if not is_msix_package():
            # Jak wyżej — link do pobrania spoza Store i cennik planu Pro
            # nie mogą pojawiać się w wersji sklepowej (MSIX).
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
        # Wybór motywu w jednym rzędzie — wcześniej „Grafit" łamał się do
        # drugiej linii i wchodził pod przycisk nowego promptu.
        themes_row = ttk.Frame(header)
        themes_row.grid(row=0, column=1, rowspan=4, sticky="e", padx=(8, 12))
        for col, (value, label) in enumerate(
            (("jasny", t('Jasny')), ("ciemny", t('Ciemny')), ("grafit", t('Grafit')))
        ):
            ttk.Radiobutton(
                themes_row,
                text=label,
                variable=self.theme_var,
                value=value,
                command=self.apply_theme,
            ).grid(row=0, column=col, padx=(0, 10))
        ttk.Button(header, text=t('+ Nowy Prompt'), style="Primary.TButton", command=self.new_prompt).grid(
            row=0, column=2, rowspan=4, sticky="e"
        )

        sidebar = ttk.LabelFrame(main, text=t('Filtry'), padding=10)
        sidebar.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text=t('Status'), style="Card.TLabel").grid(row=0, column=0, sticky=W)
        self.status_combo = ttk.Combobox(sidebar, textvariable=self.status_filter, state="readonly", width=24)
        self.status_combo.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text=t('Model AI'), style="Card.TLabel").grid(row=2, column=0, sticky=W)
        self.model_combo = ttk.Combobox(sidebar, textvariable=self.model_filter, state="readonly", width=24)
        self.model_combo.grid(row=3, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text=t('Zastosowanie'), style="Card.TLabel").grid(row=4, column=0, sticky=W)
        self.zastosowanie_combo = ttk.Combobox(
            sidebar, textvariable=self.zastosowanie_filter, state="readonly", width=24
        )
        self.zastosowanie_combo.grid(row=5, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text=t('Tag'), style="Card.TLabel").grid(row=6, column=0, sticky=W)
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
            row_label = ttk.Label(
                self.checklist_frame,
                text=f"{t('○ ')}{t(label)}",
                style="CardMuted.TLabel",
                wraplength=200,
            )
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
        ttk.Label(sidebar, text=t('Przypięte'), style="CardStat.TLabel").grid(row=12, column=0, sticky=W)
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
        ttk.Combobox(toolbar, textvariable=self.sort_var, values=sort_display_values(), state="readonly", width=14).grid(
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
            "pinned": 44,
            "favorite": 36,
            "name": 210,
            "status": 84,
            "model": 96,
            "zastosowanie": 110,
            "format": 74,
            "created": 96,
        }
        # Suma szerokości kolumn przekracza zwykłą szerokość panelu, więc bez
        # rozciągania Tk ucinał ostatnie z nich („Zastosowanie", „Data").
        # Kolumny tekstowe dzielą się dostępnym miejscem, wąskie zostają stałe.
        flexible = {"name", "zastosowanie", "model", "status"}
        anchors = {"pinned": CENTER, "favorite": CENTER}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(
                col,
                width=widths[col],
                minwidth=28 if col in ("pinned", "favorite") else 60,
                stretch=(col in flexible),
                anchor=anchors.get(col, W),
            )
        self.tree.grid(row=0, column=0, sticky="nsew")
        # Kolory pasów ustawiamy tutaj, bo apply_theme() biegnie raz jeszcze
        # przed zbudowaniem listy — wtedy self.tree jeszcze nie istnieje.
        tree_colors = self.get_theme_colors()
        self.tree.tag_configure("odd", background=tree_colors["row_alt"])
        self.tree.tag_configure("even", background=tree_colors["surface"])
        tree_scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        split.add(list_frame, weight=3)

        detail = ttk.LabelFrame(split, text=t('Podgląd'), padding=10)
        detail.rowconfigure(5, weight=1)
        detail.columnconfigure(0, weight=1)
        self.detail_title = ttk.Label(detail, text=t('Wybierz prompt'), style="Title.TLabel")
        self.detail_title.grid(row=0, column=0, sticky=W, pady=(0, 6))
        self.detail_meta = ttk.Label(detail, text="", style="CardMuted.TLabel", wraplength=330)
        self.detail_meta.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.detail_comment = ttk.Label(detail, text="", style="Card.TLabel", wraplength=330)
        self.detail_comment.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.detail_text = self._text_widget(detail)
        self.detail_text.grid(row=5, column=0, sticky="nsew")
        self.detail_text.configure(state="disabled")
        self.register_text_widget(self.detail_text)

        self.empty_state = ttk.Frame(detail, style="Card.TFrame")
        self.empty_state.grid(row=5, column=0, sticky="nsew")
        self.empty_state.grid_remove()
        ttk.Label(
            self.empty_state,
            text=t('Biblioteka jest pusta.\nDodaj pierwszy prompt lub załaduj gotowe przykłady.'),
            style="Card.TLabel",
            justify=CENTER,
            wraplength=320,
        ).pack(pady=(24, 12))
        empty_actions = ttk.Frame(self.empty_state, style="Card.TFrame")
        empty_actions.pack()
        ttk.Button(empty_actions, text=t('+ Nowy Prompt'), style="Accent.TButton", command=self.new_prompt).pack(
            side=LEFT, padx=4
        )
        ttk.Button(empty_actions, text=t('Załaduj przykłady'), command=self.restore_sample_prompts).pack(side=LEFT, padx=4)

        self.primary_row = ttk.Frame(detail, style="Card.TFrame")
        self.primary_row.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        self.primary_row.columnconfigure(0, weight=1)
        ttk.Button(
            self.primary_row,
            text=t('Kopiuj i użyj w AI'),
            style="Primary.TButton",
            command=self.copy_and_use_ai,
        ).grid(row=0, column=0, sticky="ew")

        self.detail_actions = ttk.Frame(detail, style="Card.TFrame")
        self.detail_actions.grid(row=7, column=0, sticky="ew", pady=(6, 0))
        buttons = self.detail_actions
        # Osiem przycisków w jednym rzędzie nie mieściło się w wąskim panelu —
        # Tk przycinał napisy („Duplik", „Histori"). Układ 4×2 mieści pełne
        # etykiety przy każdej szerokości panelu.
        for idx in range(4):
            buttons.columnconfigure(idx, weight=1, uniform="act")
        for idx, (label, command) in enumerate(
            (
                (t('Kopiuj'), self.copy_selected),
                (t('Edytuj'), self.edit_selected),
                (t('Duplikuj'), self.duplicate_selected),
                (t('Historia'), self.show_history),
                (t('Przypnij'), self.toggle_selected_pin),
                (t('★ Ulubiony'), self.toggle_selected_favorite),
                (t('n8n'), self.send_selected_to_n8n),
                (t('Usuń'), self.delete_selected),
            )
        ):
            ttk.Button(buttons, text=label, style="Compact.TButton", command=command).grid(
                row=idx // 4, column=idx % 4, sticky="ew", padx=2, pady=2
            )

        # Rząd akcji asystenta AI (przepisywanie promptu przez model).
        self.assistant_buttons = ttk.Frame(detail, style="Card.TFrame")
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

        self.ai_buttons = ttk.Frame(detail, style="Card.TFrame")
        self.ai_buttons.grid(row=8, column=0, sticky="ew", pady=(6, 0))
        ai_buttons = self.ai_buttons
        for idx in range(4):
            ai_buttons.columnconfigure(idx, weight=1, uniform="ai")
        ttk.Button(
            ai_buttons,
            text=t('AI z modelu ↗'),
            style="Compact.TButton",
            command=self.open_ai_for_model,
        ).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        for idx, (platform_name, _url) in enumerate(AI_PLATFORMS, start=1):
            ttk.Button(
                ai_buttons,
                text=f"{platform_name}{t(' ↗')}",
                style="Compact.TButton",
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=True),
            ).grid(row=idx // 4, column=idx % 4, sticky="ew", padx=2, pady=2)
        split.add(detail, weight=2)
        # Waga PanedWindow steruje tylko podziałem przy zmianie rozmiaru —
        # startowa pozycja belki wynika z żądanych szerokości, a panel podglądu
        # (siatka przycisków) żąda dużo i spychał listę do ~połowy, przez co
        # ostatnie kolumny były ucinane. Ustawiamy belkę po rozłożeniu okna.
        self._split = split
        self.root.after_idle(self._set_initial_sash)
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
        wszystkie = all_filter_label()
        status_values = [wszystkie, *status_display_values()]
        model_values = [wszystkie, *models]
        zastosowanie_values = [wszystkie, *zastosowania]
        tag_values = [wszystkie, *tags]
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
                var.set(wszystkie)

    def refresh_list(self) -> None:
        query = self.search_var.get().strip().lower()
        status_filter = self.status_filter.get()
        model_filter = self.model_filter.get()
        zastosowanie_filter = self.zastosowanie_filter.get()
        tag_filter = self.tag_filter.get()

        wszystkie = all_filter_label()
        only_favorites = bool(self.favorites_only.get())
        terms = search_terms(query)

        result = []
        for prompt in self.store.prompts:
            if only_favorites and not prompt.favorite:
                continue
            if status_filter != wszystkie and status_display(prompt.status) != status_filter:
                continue
            if model_filter != wszystkie and prompt.model != model_filter:
                continue
            if zastosowanie_filter != wszystkie and prompt.zastosowanie != zastosowanie_filter:
                continue
            if tag_filter != wszystkie and tag_filter not in tag_list_from_string(prompt.tags):
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

        sort = sort_key_from_display(self.sort_var.get())
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
        row_index = 0
        for prompt in result:
            self.tree.insert(
                "",
                END,
                iid=prompt.id,
                values=(
                    # Pełne kółko zamiast gwiazdki ASCII — przy sąsiedniej
                    # gwiazdce ulubionych „*" czytało się jak artefakt.
                    "●" if prompt.pinned else "",
                    "★" if prompt.favorite else "",
                    prompt.name,
                    status_display(prompt.status),
                    prompt.model,
                    prompt.zastosowanie,
                    format_display(prompt.format),
                    format_date(prompt.created),
                ),
                tags=("even" if row_index % 2 == 0 else "odd",),
            )
            row_index += 1
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
                    f"{status_display(prompt.status)}{t(' | ')}{format_display(prompt.format)}{t(' | ')}"
                    f"{prompt.model or 'bez modelu'}{t(' | ')}{prompt.zastosowanie or 'bez kategorii'}{t(' | tagi: ')}{tags_text}{t(' | ')}{format_date(prompt.created)}"
                )
            )
            self.detail_comment.configure(
                text=(t('Wskazówka: ') + prompt.comment) if prompt.comment else ""
            )
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
            store=self.store,
        )
        self.root.wait_window(dialog)
        if dialog.result:
            self.store.prompts.insert(0, dialog.result)
            self.save_store()
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
            store=self.store,
        )
        self.root.wait_window(dialog)
        if dialog.result:
            self.save_store()
            self.refresh_all()
            self.set_status(t('Prompt zaktualizowany.'))







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
            self.save_store()
            self.refresh_all()
            self.set_status(f"{t('Przywrócono wersję promptu „')}{prompt.name}{t('”.')}")


    def delete_selected(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        if not messagebox.askyesno(APP_NAME, f"{t('Usunąć prompt „')}{prompt.name}{t('”?')}", parent=self.root):
            return
        self.store.prompts = [item for item in self.store.prompts if item.id != prompt.id]
        self.save_store()
        self.selected_id = None
        self.refresh_all()
        self.set_status(t('Prompt usunięty.'))

    def toggle_selected_pin(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        prompt.pinned = not prompt.pinned
        self.save_store()
        self.refresh_all()
        self.set_status("Przypięto prompt." if prompt.pinned else "Odpięto prompt.")

    # --- Asystent AI -------------------------------------------------------

    def configure_ai(self) -> None:
        dialog = AiConfigDialog(self.root, self.store.ai_settings, theme_getter=self.get_theme_colors)
        self.root.wait_window(dialog)
        if dialog.result:
            self.store.ai_settings.update(dialog.result)
            self.save_store()
            engine_label = ai.ENGINES.get(self.store.ai_settings["engine"], "")
            self.set_status(f"{t('Zapisano konfigurację AI (')}{engine_label}{t(').')}")







    def toggle_selected_favorite(self, _event=None) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        prompt.favorite = not prompt.favorite
        self.save_store()
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
        # Blok trafia do schowka i dalej do czatu AI — etykiety i wartości
        # w języku interfejsu, bo czyta go człowiek, nie integracja.
        lines = [
            f"# {prompt.name}",
            t('Status: ') + status_display(prompt.status)
            + t(' | Format: ') + format_display(prompt.format)
            + t(' | Model: ') + (prompt.model or "—"),
            t('Zastosowanie: ') + (prompt.zastosowanie or "—"),
        ]
        if prompt.comment:
            lines.append(t('Wskazówka: ') + prompt.comment)
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
        self.save_store()
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









    def show_help(self) -> None:
        landing_hint = (
            f"\nStrona produktu: {LANDING_PAGE_PATH}\n" if LANDING_PAGE_PATH.is_file() else ""
        )
        # Link do pobrania spoza Store nie może pojawić się w wersji
        # sklepowej (MSIX) — zasada 10.1.5 Software Distribution.
        download_hint = "" if is_msix_package() else t('\nPobierz: ') + APP_RELEASE_URL
        messagebox.showinfo(
            t("PrompBase - pomoc"),
            (str(t('PrompBase v')) + str(APP_VERSION) + str(t('\nAutor: ')) + str(APP_AUTHOR) + str(t('\nDokumentacja: ')) + str(APP_HELP_URL) + download_hint + str(landing_hint))
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


def install_error_handler(root: Tk) -> None:
    """Zapisuje nieobsłużone błędy do dziennika i mówi o tym użytkownikowi.

    Tk domyślnie wypisuje wyjątek z callbacku na `stderr` i działa dalej.
    W buildzie okienkowym `stderr` donikąd nie prowadzi, więc użytkownik
    widział „kliknąłem i nic się nie stało", a my nie mieliśmy z czego
    odtworzyć problemu.
    """

    def handler(exc_type, exc, tb) -> None:
        path = log_exception(exc_type, exc, tb)
        detail = f"{exc_type.__name__}: {exc}"
        message = t('Wystąpił nieoczekiwany błąd:\n\n') + detail
        if path is not None:
            message += t('\n\nSzczegóły zapisano w pliku:\n') + str(path)
        try:
            messagebox.showerror(APP_NAME, message)
        except Exception:  # noqa: BLE001 - okno błędu nie może wywołać kolejnego
            pass

    root.report_callback_exception = handler


def main() -> None:
    root = Tk()
    install_error_handler(root)
    # Przypięcie do root utrzymuje referencję do aplikacji przez cały mainloop.
    root.prompbase_app = PrompBaseApp(root)
    root.mainloop()
