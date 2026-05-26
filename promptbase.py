#!/usr/bin/env python3
"""PrompBase desktop app.

Cross-platform Python rewrite of the original single-file PWA.
Uses only the Python standard library: tkinter, json, csv and urllib.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import re
import shutil
import subprocess
import time
import uuid
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from tkinter import (
    BOTH,
    BOTTOM,
    CENTER,
    END,
    LEFT,
    RIGHT,
    TOP,
    VERTICAL,
    W,
    X,
    Y,
    Listbox,
    Menu,
    StringVar,
    Tk,
    Toplevel,
    filedialog,
    messagebox,
)
from tkinter import ttk
from urllib import request
from urllib.error import HTTPError, URLError


APP_NAME = "PrompBase"
APP_VERSION = "2.4"
PLACEHOLDER_RE = re.compile(r"\[([A-Za-z0-9_]+)\]")
CLOUD_SUBDIR = "PrompBase"
PROMPT_HISTORY_MAX = 5
PWA_STORAGE_KEY = "promptLibrary"
N8N_SOURCE = "biblioteka-promptow"
N8N_HTTP_TIMEOUT = 30
APP_AUTHOR = "Marek Zettel"
APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"

THEMES = {
    "jasny": {
        "bg": "#f5f6fb",
        "surface": "#ffffff",
        "text": "#1f2430",
        "muted": "#667085",
        "accent": "#6557d2",
        "select": "#e7e5ff",
        "field": "#ffffff",
        "search_hit": "#fff59d",
    },
    "ciemny": {
        "bg": "#11131a",
        "surface": "#1b1f2a",
        "text": "#f2f4f8",
        "muted": "#a8b0c0",
        "accent": "#8d7cff",
        "select": "#2d3350",
        "field": "#151923",
        "search_hit": "#4a4520",
    },
}

CLOUD_PROVIDERS = {
    "google_drive": "Google Drive",
    "onedrive": "OneDrive",
}

STATUSES = {
    "nowy": "Nowy",
    "osobiste": "Osobiste",
    "praca": "Praca",
    "uniwersalne": "Uniwersalne",
}
STATUS_FROM_LABEL = {label: key for key, label in STATUSES.items()}

# Najpopularniejsze modele (aktualizacja: maj 2026, źródła: openai.com, anthropic.com, blog.google).
AI_MODELS = [
    # OpenAI / ChatGPT
    "GPT-5.5 Pro",
    "GPT-5.5",
    "GPT-5.5 Instant",
    "GPT-5.4",
    "GPT-5.4 Nano",
    "GPT-5 Mini",
    "o4-mini",
    "o3",
    "o3-mini",
    # Anthropic / Claude
    "Claude Opus 4.7",
    "Claude Sonnet 4.6",
    "Claude Haiku 4.5",
    "Claude Opus 4.6",
    "Claude Sonnet 4.5",
    # Google / Gemini
    "Gemini 3.5 Flash",
    "Gemini 3.5 Pro",
    "Gemini 3.1 Pro",
    "Gemini 3 Flash",
    # Inne dostawcy
    "DeepSeek V3",
    "Grok 3",
    "Mistral Large",
    "Llama 4",
    "Perplexity Sonar",
    # Poprzednie generacje (stare prompty / kompatybilność)
    "GPT-4.1",
    "GPT-4o",
    "Claude Opus 4",
    "Claude Sonnet 4",
    "Gemini 2.5 Pro",
    "Gemini 2.5 Flash",
]

AI_PLATFORMS = (
    ("ChatGPT", "https://chatgpt.com/"),
    ("Claude", "https://claude.ai/"),
    ("Gemini", "https://gemini.google.com/app"),
    ("Perplexity", "https://www.perplexity.ai/"),
    ("Copilot", "https://copilot.microsoft.com/"),
)

ZASTOSOWANIA_PRESET = [
    "pisanie",
    "kodowanie",
    "analiza",
    "obraz",
    "badania",
    "marketing",
    "tlumaczenie",
    "automatyzacja",
]

TAGS_PRESET = [
    "seo",
    "blog",
    "email",
    "social",
    "kod",
    "n8n",
    "szablon",
    "polski",
]

FORMATS = ["tekst", "kod", "zdjecie/screen"]
SORT_OPTIONS = {
    "Najnowsze": "newest",
    "Najstarsze": "oldest",
    "A -> Z": "az",
    "Z -> A": "za",
}


def default_onedrive_path() -> Path | None:
    for key in ("OneDriveCommercial", "OneDriveConsumer", "OneDrive"):
        value = os.environ.get(key)
        if value:
            path = Path(value)
            if path.is_dir():
                return path
    home = Path.home()
    for name in ("OneDrive", "OneDrive - Osobisty", "OneDrive - Personal"):
        path = home / name
        if path.is_dir():
            return path
    return None


def default_google_drive_path() -> Path | None:
    home = Path.home()
    for name in ("Google Drive", "Mój dysk", "My Drive"):
        path = home / name
        if path.is_dir():
            return path
    for letter in "GHIJKLM":
        path = Path(f"{letter}:/Mój dysk")
        if path.is_dir():
            return path
        path = Path(f"{letter}:/My Drive")
        if path.is_dir():
            return path
    return None


def detect_cloud_folder(provider: str) -> str:
    if provider == "onedrive":
        path = default_onedrive_path()
    elif provider == "google_drive":
        path = default_google_drive_path()
    else:
        path = None
    return str(path) if path else ""


def extract_placeholders(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for match in PLACEHOLDER_RE.finditer(text or ""):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            result.append(token)
    return result


def fill_placeholders(text: str, values: dict[str, str]) -> str:
    result = text
    for key, value in values.items():
        result = result.replace(key, value)
    return result


def parse_tags_value(raw) -> str:
    if isinstance(raw, list):
        return ", ".join(str(item).strip() for item in raw if str(item).strip())
    return str(raw or "").strip()


def tag_list_from_string(tags: str) -> list[str]:
    return [part.strip() for part in (tags or "").split(",") if part.strip()]


def app_data_dir() -> Path:
    system = platform.system().lower()
    if system == "windows":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    if system == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME


def now_ms() -> int:
    return int(time.time() * 1000)


def format_date(ms: int | float | str | None) -> str:
    """Data w formacie zgodnym z PWA i eksportem n8n (pl-PL)."""
    try:
        value = float(ms or 0) / 1000
        if value <= 0:
            return ""
        return datetime.fromtimestamp(value).strftime("%d.%m.%Y, %H:%M")
    except (TypeError, ValueError, OSError):
        return ""


def validate_n8n_url(url: str) -> bool:
    normalized = (url or "").strip()
    if not normalized.startswith(("http://", "https://")):
        return False
    lowered = normalized.lower()
    return "/webhook" in lowered


def normalize_n8n_url(url: str) -> str:
    return (url or "").strip()


def prompt_to_n8n_dict(prompt: Prompt) -> dict:
    """Płaski obiekt promptu — ten sam kształt co synchronizacja w PWA."""
    return {
        "id": prompt.id,
        "name": prompt.name,
        "status": prompt.status,
        "status_label": status_label(prompt.status),
        "format": prompt.format,
        "model": prompt.model,
        "zastosowanie": prompt.zastosowanie,
        "tags": prompt.tags,
        "content": prompt.content,
        "comment": prompt.comment,
        "pinned": bool(prompt.pinned),
        "created": prompt.created,
        "created_human": format_date(prompt.created),
    }


def theme_colors(theme_name: str) -> dict:
    return THEMES.get(theme_name, THEMES["jasny"])


def apply_widget_theme(widget, colors: dict) -> None:
    """Motyw dla Text/Entry/Listbox — tylko opcje wspierane przez dany widget."""
    options = {
        "background": colors["field"],
        "foreground": colors["text"],
        "selectbackground": colors["select"],
        "selectforeground": colors["text"],
    }
    if widget.winfo_class() in ("Text", "Entry"):
        options.update(
            {
                "insertbackground": colors["text"],
                "relief": "flat",
                "borderwidth": 1,
                "highlightthickness": 1,
                "highlightbackground": colors["muted"],
                "highlightcolor": colors["accent"],
            }
        )
    widget.configure(**options)


def apply_text_theme(widget, colors: dict) -> None:
    """Zgodność wsteczna — alias dla Text."""
    apply_widget_theme(widget, colors)


def prompt_snapshot(prompt: Prompt) -> dict:
    return {
        "saved_at": now_ms(),
        "name": prompt.name,
        "content": prompt.content,
        "status": prompt.status,
        "format": prompt.format,
        "model": prompt.model,
        "zastosowanie": prompt.zastosowanie,
        "comment": prompt.comment,
        "tags": prompt.tags,
    }


def snapshots_equal(left: dict, right: dict) -> bool:
    keys = ("name", "content", "status", "format", "model", "zastosowanie", "tags", "comment")
    return all(left.get(key) == right.get(key) for key in keys)


def push_prompt_history(prompt: Prompt) -> None:
    snap = prompt_snapshot(prompt)
    if prompt.history and snapshots_equal(prompt.history[0], snap):
        return
    prompt.history.insert(0, snap)
    del prompt.history[PROMPT_HISTORY_MAX:]


def parse_pwa_import_data(data) -> tuple[list[dict], str, str]:
    """Zwraca surowe dicty promptów oraz opcjonalnie n8n_url i theme z eksportu PWA."""
    n8n_url = ""
    theme = ""
    raw_prompts: list = []

    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, list):
        raw_prompts = data
    elif isinstance(data, dict):
        n8n_url = str(data.get("n8nUrl") or data.get("n8n_url") or "").strip()
        theme = str(data.get("theme") or "").strip()
        if PWA_STORAGE_KEY in data:
            nested = data[PWA_STORAGE_KEY]
            if isinstance(nested, str):
                nested = json.loads(nested)
            if isinstance(nested, list):
                raw_prompts = nested
        elif "prompts" in data:
            raw_prompts = data.get("prompts") or []
    return raw_prompts, n8n_url, theme


def prompts_from_pwa_data(data) -> tuple[list[Prompt], str, str]:
    raw_prompts, n8n_url, theme = parse_pwa_import_data(data)
    prompts = [Prompt.from_dict(item) for item in raw_prompts if isinstance(item, dict)]
    return prompts, n8n_url, theme


def suggest_ai_platform(model: str) -> str | None:
    lowered = (model or "").lower()
    if any(token in lowered for token in ("gpt", "o3", "o4", "openai", "chatgpt")):
        return "ChatGPT"
    if "claude" in lowered:
        return "Claude"
    if "gemini" in lowered:
        return "Gemini"
    if "perplexity" in lowered or "sonar" in lowered:
        return "Perplexity"
    if "copilot" in lowered:
        return "Copilot"
    return None


def n8n_envelope(event_type: str, **fields) -> dict:
    payload = {
        "source": N8N_SOURCE,
        "client": "python",
        "type": event_type,
        "timestamp": datetime.now().isoformat(),
    }
    payload.update(fields)
    return payload


def status_label(status_key: str) -> str:
    return STATUSES.get(status_key, status_key)


def status_key_from_label(label: str) -> str:
    return STATUS_FROM_LABEL.get(label, label)


def merge_model_options(*sources: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for source in sources:
        for item in source:
            value = (item or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged


def parse_date_to_ms(value: str) -> int:
    value = (value or "").strip()
    if not value:
        return now_ms()
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y, %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(value, fmt).timestamp() * 1000)
        except ValueError:
            pass
    return now_ms()


@dataclass
class Prompt:
    name: str
    content: str
    status: str = "nowy"
    format: str = "tekst"
    model: str = ""
    zastosowanie: str = ""
    tags: str = ""
    comment: str = ""
    pinned: bool = False
    created: int = field(default_factory=now_ms)
    id: str = field(default_factory=lambda: f"p_{uuid.uuid4().hex[:12]}")
    history: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Prompt":
        history_raw = data.get("history", [])
        history: list[dict] = []
        if isinstance(history_raw, list):
            history = [item for item in history_raw if isinstance(item, dict)][:PROMPT_HISTORY_MAX]
        return cls(
            id=str(data.get("id") or f"p_{uuid.uuid4().hex[:12]}"),
            name=str(data.get("name") or data.get("Nazwa") or "").strip(),
            content=str(data.get("content") or data.get("Treść Promptu") or data.get("Tresc Promptu") or "").strip(),
            status=str(data.get("status") or "nowy").strip() or "nowy",
            format=str(data.get("format") or "tekst").strip() or "tekst",
            model=str(data.get("model") or data.get("Model AI") or "").strip(),
            zastosowanie=str(data.get("zastosowanie") or data.get("Zastosowanie") or "").strip(),
            tags=parse_tags_value(data.get("tags") or data.get("Tagi") or data.get("tagi") or ""),
            comment=str(data.get("comment") or data.get("Komentarz") or "").strip(),
            pinned=bool(data.get("pinned", False)),
            created=int(data.get("created") or now_ms()),
            history=history,
        )

    def to_dict(self) -> dict:
        payload = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "format": self.format,
            "model": self.model,
            "zastosowanie": self.zastosowanie,
            "tags": self.tags,
            "content": self.content,
            "comment": self.comment,
            "pinned": self.pinned,
            "created": self.created,
        }
        if self.history:
            payload["history"] = self.history[:PROMPT_HISTORY_MAX]
        return payload


class PromptStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prompts: list[Prompt] = []
        self.n8n_url = ""
        self.theme = "jasny"
        self.cloud_folders: dict[str, str] = {"google_drive": "", "onedrive": ""}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.prompts = []
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.prompts = []
            return

        if isinstance(data, list):
            raw_prompts = data
            self.n8n_url = ""
            stored_cloud: dict = {}
        else:
            raw_prompts = data.get("prompts", [])
            self.n8n_url = data.get("n8n_url", "")
            self.theme = data.get("theme", "jasny")
            stored_cloud = data.get("cloud_folders", {}) or {}
        if self.theme not in THEMES:
            self.theme = "jasny"

        self.cloud_folders = {
            "google_drive": str(stored_cloud.get("google_drive", "")).strip(),
            "onedrive": str(stored_cloud.get("onedrive", "")).strip(),
        }
        for provider in CLOUD_PROVIDERS:
            if not self.cloud_folders.get(provider):
                detected = detect_cloud_folder(provider)
                if detected:
                    self.cloud_folders[provider] = detected

        self.prompts = [Prompt.from_dict(item) for item in raw_prompts if isinstance(item, dict)]

    def to_payload(self) -> dict:
        return {
            "version": APP_VERSION,
            "exported_at": datetime.now().isoformat(),
            "n8n_url": self.n8n_url,
            "theme": self.theme,
            "cloud_folders": self.cloud_folders,
            "prompts": [prompt.to_dict() for prompt in self.prompts],
        }

    def to_pwa_library_json(self) -> str:
        """JSON tablicy promptów — format localStorage promptLibrary w PWA."""
        items = []
        for prompt in self.prompts:
            row = prompt.to_dict()
            row.pop("history", None)
            items.append(row)
        return json.dumps(items, ensure_ascii=False, indent=2)

    def cloud_export_path(self, provider: str) -> Path | None:
        base = (self.cloud_folders.get(provider) or "").strip()
        if not base:
            return None
        root = Path(base)
        if not root.is_dir():
            return None
        target_dir = root / CLOUD_SUBDIR
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        return target_dir / f"prompbase-backup-{stamp}.json"

    def save(self) -> None:
        payload = self.to_payload()
        if self.path.exists():
            backup_path = self.path.with_suffix(".json.bak")
            try:
                shutil.copy2(self.path, backup_path)
            except OSError:
                pass
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def sample_data(self) -> None:
        if self.prompts:
            return
        samples = [
            Prompt(
                name="Redaktor Bloga Technicznego",
                status="praca",
                format="tekst",
                model="GPT-5.5",
                zastosowanie="pisanie",
                content=(
                    "Jesteś doświadczonym redaktorem bloga technologicznego. "
                    "Pisz przystępnym językiem dla niespecjalistów.\n\n"
                    "Temat artykułu: [TEMAT]\nDługość: [LICZBA] słów\nTon: [TON]"
                ),
                comment='Dobry do serii "Podstawy AI"',
            ),
            Prompt(
                name="Korektor Ortografii PL",
                status="uniwersalne",
                format="tekst",
                model="Claude Sonnet 4.6",
                zastosowanie="pisanie",
                content=(
                    "Popraw błędy ortograficzne, interpunkcyjne i stylistyczne w tekście. "
                    "Zachowaj oryginalny styl i sens.\n\nTekst do korekty:\n[TEKST]"
                ),
                comment="Claude Sonnet 4.6 radzi sobie z tym bardzo dobrze",
            ),
            Prompt(
                name="Analiza kodu Python",
                status="praca",
                format="kod",
                model="Claude Opus 4.7",
                zastosowanie="kodowanie",
                content=(
                    "Jesteś senior developerem Python. Przeanalizuj poniższy kod pod kątem "
                    "błędów, wydajności, refaktoryzacji, PEP8 i bezpieczeństwa.\n\n```python\n[KOD]\n```"
                ),
                comment="Używać przy review skryptów",
            ),
        ]
        for index, prompt in enumerate(samples):
            prompt.created = now_ms() - index * 3600 * 1000
        self.prompts = samples
        self.save()


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
                "Eksport z przeglądarki (PrompBase PWA):\n"
                "1. Otwórz PrompBase w Chrome/Edge → F12 → Application → Local Storage\n"
                "2. Skopiuj wartość klucza „promptLibrary” LUB w konsoli wpisz:\n"
                "   copy(localStorage.getItem('promptLibrary'))\n"
                "3. Wklej poniżej albo wczytaj plik .json (tablica promptów lub pełny eksport)."
            ),
            wraplength=660,
            justify=LEFT,
        ).grid(row=0, column=0, sticky=W, pady=(0, 10))

        toolbar = ttk.Frame(body)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(toolbar, text="Wczytaj plik JSON...", command=self.load_file).pack(side=LEFT)

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
        for col, (name, _url) in enumerate(AI_PLATFORMS, start=1):
            ttk.Button(
                model_row,
                text=name,
                width=8,
                command=lambda platform=name: self._open_platform(platform),
            ).grid(row=0, column=col, padx=(4, 0))

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
        self.transient(parent)
        self.grab_set()
        self.name_var.set(self.name_var.get())
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


class PrompBaseApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"{APP_NAME} - Biblioteka Promptów AI")
        self.root.geometry("1180x760")
        self.root.minsize(980, 620)
        self._set_window_icon()

        self.store = PromptStore(app_data_dir() / "promptbase.json")
        self.filtered: list[Prompt] = []
        self.selected_id: str | None = None

        self.search_var = StringVar()
        self.status_filter = StringVar(value="Wszystkie")
        self.model_filter = StringVar(value="Wszystkie")
        self.zastosowanie_filter = StringVar(value="Wszystkie")
        self.tag_filter = StringVar(value="Wszystkie")
        self.sort_var = StringVar(value="Najnowsze")
        self.theme_var = StringVar(value=self.store.theme)
        self._themed_text_widgets: list = []

        self._configure_style()
        self._build_menu()
        self._build_ui()
        self._bind_shortcuts()

        if not self.store.prompts:
            self.store.sample_data()
        self.refresh_all()

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
            self.set_status(f"Motyw zmieniony: {theme_name}.")

    def _build_menu(self) -> None:
        menu = Menu(self.root)
        file_menu = Menu(menu, tearoff=False)
        file_menu.add_command(label="Nowy prompt", accelerator="N", command=self.new_prompt)
        file_menu.add_command(label="Import CSV...", command=self.import_csv)
        file_menu.add_command(label="Import z PWA (przeglądarka)...", command=self.import_from_pwa)
        file_menu.add_command(label="Eksport CSV...", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Kopia zapasowa JSON...", command=self.export_backup_json)
        file_menu.add_command(label="Przywróć z JSON...", command=self.import_backup_json)
        file_menu.add_command(label="Eksport dla PWA (przeglądarka)...", command=self.export_for_pwa)
        file_menu.add_command(label="Eksport do chmury (Drive / OneDrive)...", command=self.export_to_cloud)
        file_menu.add_separator()
        file_menu.add_command(label="Szybki import pliku CSV/JSON...", command=self.quick_import_file)
        file_menu.add_separator()
        file_menu.add_command(label="Pokaż plik danych", command=self.show_data_path)
        file_menu.add_command(label="Otwórz folder danych", command=self.open_data_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Zamknij", command=self.root.destroy)
        menu.add_cascade(label="Plik", menu=file_menu)

        ai_menu = Menu(menu, tearoff=False)
        for platform_name, _url in AI_PLATFORMS:
            ai_menu.add_command(
                label=f"Otwórz {platform_name}",
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=False),
            )
            ai_menu.add_command(
                label=f"Kopiuj prompt i otwórz {platform_name}",
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=True),
            )
        menu.add_cascade(label="AI", menu=ai_menu)

        tools_menu = Menu(menu, tearoff=False)
        tools_menu.add_command(label="Konfiguracja n8n...", command=self.configure_n8n)
        tools_menu.add_command(label="Testuj webhook n8n", command=self.test_n8n_webhook)
        tools_menu.add_separator()
        tools_menu.add_command(label="Wyślij zaznaczony do n8n", command=self.send_selected_to_n8n)
        tools_menu.add_command(label="Synchronizuj bibliotekę do n8n", command=self.sync_all_to_n8n)
        tools_menu.add_command(label="Eksportuj JSON dla n8n...", command=self.export_n8n_json)
        menu.add_cascade(label="Narzędzia", menu=tools_menu)

        view_menu = Menu(menu, tearoff=False)
        view_menu.add_radiobutton(label="Tryb jasny", variable=self.theme_var, value="jasny", command=self.apply_theme)
        view_menu.add_radiobutton(label="Tryb ciemny", variable=self.theme_var, value="ciemny", command=self.apply_theme)
        menu.add_cascade(label="Widok", menu=view_menu)

        help_menu = Menu(menu, tearoff=False)
        help_menu.add_command(label="Pomoc i skróty", accelerator="?", command=self.show_help)
        menu.add_cascade(label="Pomoc", menu=help_menu)
        self.root.config(menu=menu)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=BOTH, expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=f"PrompBase v{APP_VERSION}", style="Header.TLabel").grid(row=0, column=0, sticky=W)
        self.stats_label = ttk.Label(header, text="", style="Muted.TLabel")
        self.stats_label.grid(row=1, column=0, sticky=W)
        ttk.Label(header, text=f"Autor: {APP_AUTHOR}", style="Muted.TLabel").grid(row=2, column=0, sticky=W)
        ttk.Radiobutton(header, text="Jasny", variable=self.theme_var, value="jasny", command=self.apply_theme).grid(
            row=0, column=1, rowspan=2, padx=(4, 0)
        )
        ttk.Radiobutton(header, text="Ciemny", variable=self.theme_var, value="ciemny", command=self.apply_theme).grid(
            row=0, column=2, rowspan=2, padx=(4, 8)
        )
        ttk.Button(header, text="+ Nowy Prompt", style="Accent.TButton", command=self.new_prompt).grid(
            row=0, column=3, rowspan=2, padx=4
        )
        ttk.Button(header, text="Import CSV", command=self.import_csv).grid(row=0, column=4, rowspan=2, padx=4)
        ttk.Button(header, text="Eksport CSV", command=self.export_csv).grid(row=0, column=5, rowspan=2, padx=4)

        ai_bar = ttk.Frame(header)
        ai_bar.grid(row=3, column=0, columnspan=6, sticky=W, pady=(8, 0))
        ttk.Label(ai_bar, text="Otwórz AI:", style="Muted.TLabel").pack(side=LEFT, padx=(0, 6))
        for platform_name, _url in AI_PLATFORMS:
            ttk.Button(
                ai_bar,
                text=platform_name,
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=True),
            ).pack(side=LEFT, padx=3)

        sidebar = ttk.LabelFrame(main, text="Filtry", padding=10)
        sidebar.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text="Status").grid(row=0, column=0, sticky=W)
        self.status_combo = ttk.Combobox(sidebar, textvariable=self.status_filter, state="readonly", width=24)
        self.status_combo.grid(row=1, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text="Model AI").grid(row=2, column=0, sticky=W)
        self.model_combo = ttk.Combobox(sidebar, textvariable=self.model_filter, state="readonly", width=24)
        self.model_combo.grid(row=3, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text="Zastosowanie").grid(row=4, column=0, sticky=W)
        self.zastosowanie_combo = ttk.Combobox(
            sidebar, textvariable=self.zastosowanie_filter, state="readonly", width=24
        )
        self.zastosowanie_combo.grid(row=5, column=0, sticky="ew", pady=(2, 10))

        ttk.Label(sidebar, text="Tag").grid(row=6, column=0, sticky=W)
        self.tag_combo = ttk.Combobox(sidebar, textvariable=self.tag_filter, state="readonly", width=24)
        self.tag_combo.grid(row=7, column=0, sticky="ew", pady=(2, 10))

        ttk.Button(sidebar, text="Wyczyść filtry", command=self.clear_filters).grid(row=8, column=0, sticky="ew")

        import_frame = ttk.LabelFrame(sidebar, text="Import pliku", padding=8)
        import_frame.grid(row=9, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(
            import_frame,
            text="Kliknij, aby wczytać\nCSV lub JSON",
            style="Muted.TLabel",
            justify=CENTER,
            cursor="hand2",
        ).pack(fill=X)
        import_frame.bind("<Button-1>", lambda _e: self.quick_import_file())
        for child in import_frame.winfo_children():
            child.bind("<Button-1>", lambda _e: self.quick_import_file())

        ttk.Separator(sidebar).grid(row=10, column=0, sticky="ew", pady=12)
        ttk.Label(sidebar, text="Przypięte", style="Stat.TLabel").grid(row=11, column=0, sticky=W)
        self.pinned_list = Listbox(sidebar, height=8, activestyle="dotbox")
        self.pinned_list.grid(row=12, column=0, sticky="nsew", pady=(4, 8))
        self.pinned_list.bind("<Double-Button-1>", self.open_pinned)
        ttk.Button(sidebar, text="Otwórz przypięty", command=self.open_pinned).grid(row=13, column=0, sticky="ew")
        sidebar.rowconfigure(12, weight=1)

        content = ttk.Frame(main)
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(content)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Szukaj").grid(row=0, column=0, padx=(0, 6))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(toolbar, text="Sortuj").grid(row=0, column=2, padx=(0, 6))
        ttk.Combobox(toolbar, textvariable=self.sort_var, values=list(SORT_OPTIONS), state="readonly", width=14).grid(
            row=0, column=3
        )

        split = ttk.PanedWindow(content, orient="horizontal")
        split.grid(row=1, column=0, sticky="nsew")

        list_frame = ttk.Frame(split)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        columns = ("pinned", "name", "status", "model", "zastosowanie", "format", "created")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "pinned": "Pin",
            "name": "Nazwa",
            "status": "Status",
            "model": "Model",
            "zastosowanie": "Zastosowanie",
            "format": "Format",
            "created": "Data",
        }
        widths = {"pinned": 42, "name": 230, "status": 90, "model": 100, "zastosowanie": 130, "format": 90, "created": 125}
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], minwidth=40, stretch=(col == "name"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        split.add(list_frame, weight=3)

        detail = ttk.LabelFrame(split, text="Podgląd", padding=10)
        detail.rowconfigure(5, weight=1)
        detail.columnconfigure(0, weight=1)
        self.detail_title = ttk.Label(detail, text="Wybierz prompt", font=("Segoe UI", 14, "bold"))
        self.detail_title.grid(row=0, column=0, sticky=W, pady=(0, 6))
        self.detail_meta = ttk.Label(detail, text="", style="Muted.TLabel", wraplength=330)
        self.detail_meta.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.detail_comment = ttk.Label(detail, text="", wraplength=330)
        self.detail_comment.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.detail_text = self._text_widget(detail)
        self.detail_text.grid(row=5, column=0, sticky="nsew")
        self.detail_text.configure(state="disabled")
        self.register_text_widget(self.detail_text)
        self.register_text_widget(self.pinned_list)
        buttons = ttk.Frame(detail)
        buttons.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        for idx in range(7):
            buttons.columnconfigure(idx, weight=1)
        ttk.Button(buttons, text="Kopiuj", command=self.copy_selected).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(buttons, text="Edytuj", command=self.edit_selected).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(buttons, text="Duplikuj", command=self.duplicate_selected).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(buttons, text="Historia", command=self.show_history).grid(row=0, column=3, sticky="ew", padx=2)
        ttk.Button(buttons, text="Przypnij", command=self.toggle_selected_pin).grid(row=0, column=4, sticky="ew", padx=2)
        ttk.Button(buttons, text="n8n", command=self.send_selected_to_n8n).grid(row=0, column=5, sticky="ew", padx=2)
        ttk.Button(buttons, text="Usuń", command=self.delete_selected).grid(row=0, column=6, sticky="ew", padx=2)

        ai_buttons = ttk.Frame(detail)
        ai_buttons.grid(row=7, column=0, sticky="ew", pady=(6, 0))
        for idx in range(len(AI_PLATFORMS) + 1):
            ai_buttons.columnconfigure(idx, weight=1)
        ttk.Button(
            ai_buttons,
            text="AI z modelu ↗",
            command=self.open_ai_for_model,
        ).grid(row=0, column=0, sticky="ew", padx=2)
        for idx, (platform_name, _url) in enumerate(AI_PLATFORMS, start=1):
            ttk.Button(
                ai_buttons,
                text=f"{platform_name} ↗",
                command=lambda name=platform_name: self.open_ai_platform(name, copy_prompt=True),
            ).grid(row=0, column=idx, sticky="ew", padx=2)
        split.add(detail, weight=2)

        self.status_bar = ttk.Label(self.root, text="", relief="sunken", anchor=W, padding=(8, 3))
        self.status_bar.pack(side=BOTTOM, fill=X)

        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        self.sort_var.trace_add("write", lambda *_: self.refresh_list())
        self.status_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.model_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.zastosowanie_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.tag_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_list())
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self.update_detail())
        self.tree.bind("<Double-Button-1>", lambda _event: self.edit_selected())

    def _text_widget(self, parent):
        from tkinter import Text

        return Text(parent, wrap="word", height=10, font=("Consolas", 10))

    def _bind_shortcuts(self) -> None:
        self.root.bind("<KeyPress-n>", lambda _event: self.new_prompt())
        self.root.bind("<Control-Shift-N>", lambda _event: self.configure_n8n())
        self.root.bind("<Control-f>", lambda _event: self.focus_search())
        self.root.bind("/", lambda _event: self.focus_search())
        self.root.bind("?", lambda _event: self.show_help())
        self.root.bind("<Delete>", lambda _event: self.delete_selected())
        self.root.bind("<Control-e>", lambda _event: self.export_csv())
        self.root.bind("<Control-i>", lambda _event: self.import_csv())
        self.root.bind("<Control-n>", lambda _event: self.new_prompt())
        self.root.bind("<Control-d>", lambda _event: self.duplicate_selected())
        self.root.bind("<Control-Return>", lambda _event: self.edit_selected())
        self.root.bind("<Control-Shift-C>", lambda _event: self.copy_selected_with_meta())

    def available_models(self) -> list[str]:
        custom = [prompt.model for prompt in self.store.prompts if prompt.model]
        return merge_model_options(AI_MODELS, custom)

    def available_zastosowania(self) -> list[str]:
        custom = [prompt.zastosowanie for prompt in self.store.prompts if prompt.zastosowanie]
        return merge_model_options(ZASTOSOWANIA_PRESET, custom)

    def available_tags(self) -> list[str]:
        custom: list[str] = []
        for prompt in self.store.prompts:
            custom.extend(tag_list_from_string(prompt.tags))
        return merge_model_options(TAGS_PRESET, custom)

    def copy_content_with_variables(self, content: str) -> None:
        placeholders = extract_placeholders(content)
        if placeholders:
            dialog = FillVariablesDialog(self.root, content, title="Uzupełnij zmienne przed kopiowaniem")
            self.root.wait_window(dialog)
            if not dialog.filled_content:
                return
            content = dialog.filled_content
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()

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
            messagebox.showinfo(APP_NAME, "Zaznacz prompt, aby otworzyć sugerowaną platformę AI.", parent=self.root)
            return
        platform = suggest_ai_platform(prompt.model)
        if not platform:
            messagebox.showinfo(
                APP_NAME,
                f"Nie rozpoznano platformy dla modelu „{prompt.model or 'brak'}”.\n"
                "Użyj przycisków ChatGPT, Claude lub Gemini.",
                parent=self.root,
            )
            return
        self.open_ai_platform(platform, copy_prompt=True)

    def open_ai_platform(self, platform_name: str, *, copy_prompt: bool) -> None:
        url = next((item_url for name, item_url in AI_PLATFORMS if name == platform_name), "")
        if not url:
            return
        prompt = self.selected_prompt()
        if copy_prompt:
            if not prompt:
                messagebox.showinfo(
                    APP_NAME,
                    f"Brak zaznaczonego promptu. Otwieram {platform_name} bez kopiowania treści.",
                    parent=self.root,
                )
            else:
                self.root.clipboard_clear()
                self.root.clipboard_append(prompt.content)
                self.root.update()
        webbrowser.open(url)
        if copy_prompt and prompt:
            self.set_status(f"Skopiowano „{prompt.name}” i otwarto {platform_name}.")
        else:
            self.set_status(f"Otwarto {platform_name} w przeglądarce.")

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

        result = []
        for prompt in self.store.prompts:
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
            if query and query not in haystack:
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

        self.status_bar.configure(text=f"Wyświetlono {len(result)} z {len(self.store.prompts)} promptów")

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
            text=f"{total} promptów | {models} modeli | {pinned} przypiętych | dziś dodano: {added_today}"
        )

    def update_detail(self) -> None:
        selection = self.tree.selection()
        self.selected_id = selection[0] if selection else None
        prompt = self.selected_prompt()
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", END)
        if not prompt:
            self.detail_title.configure(text="Wybierz prompt")
            self.detail_meta.configure(text="")
            self.detail_comment.configure(text="")
        else:
            self.detail_title.configure(text=prompt.name)
            tags_text = prompt.tags or "bez tagów"
            self.detail_meta.configure(
                text=(
                    f"{status_label(prompt.status)} | {prompt.format} | "
                    f"{prompt.model or 'bez modelu'} | {prompt.zastosowanie or 'bez kategorii'} | "
                    f"tagi: {tags_text} | {format_date(prompt.created)}"
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
            self.selected_id = dialog.result.id
            self.refresh_all()
            self.set_status("Prompt zapisany.")

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
            self.set_status("Prompt zaktualizowany.")

    def export_for_pwa(self) -> None:
        data = self.store.to_pwa_library_json()
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Eksport dla PWA",
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
        self.set_status("Eksport dla PWA — skopiowano do schowka.")

    def export_to_cloud(self) -> None:
        dialog = CloudExportDialog(self.root, self.store)
        self.root.wait_window(dialog)
        if dialog.exported_path:
            self.set_status(f"Eksport chmury: {dialog.exported_path}")

    def quick_import_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Import CSV lub JSON",
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
            messagebox.showwarning(APP_NAME, "Obsługiwane rozszerzenia: .csv, .json", parent=self.root)

    def _import_csv_path(self, path: Path) -> None:
        imported = self._read_csv(path)
        self._finish_file_import(imported, source_label=str(path.name))

    def _import_json_path(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, f"Błąd JSON:\n{exc}", parent=self.root)
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
            messagebox.showwarning(APP_NAME, "Brak poprawnych promptów w pliku.", parent=self.root)
            return
        mode = messagebox.askyesnocancel(
            APP_NAME,
            f"Plik: {source_label}\nZnaleziono {len(valid)} promptów.\n\n"
            "Tak = dopisz\nNie = zastąp bibliotekę\nAnuluj",
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
        self.set_status(f"Zaimportowano z pliku: {source_label}")

    def show_history(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            messagebox.showinfo(APP_NAME, "Zaznacz prompt, aby zobaczyć historię wersji.", parent=self.root)
            return
        if not prompt.history:
            messagebox.showinfo(
                APP_NAME,
                "Brak zapisanych wersji.\nHistoria powstaje przy każdej edycji promptu (do 5 wersji).",
                parent=self.root,
            )
            return
        dialog = HistoryDialog(self.root, prompt, theme_getter=self.get_theme_colors)
        self.root.wait_window(dialog)
        if dialog.restored:
            self.store.save()
            self.refresh_all()
            self.set_status(f"Przywrócono wersję promptu „{prompt.name}”.")

    def import_from_pwa(self) -> None:
        dialog = PwaImportDialog(self.root, theme_getter=self.get_theme_colors)
        self.root.wait_window(dialog)
        if not dialog.imported:
            return
        valid = dialog.imported
        mode = messagebox.askyesnocancel(
            APP_NAME,
            f"Znaleziono {len(valid)} promptów z PWA.\n\n"
            "Tak = dopisz do biblioteki\n"
            "Nie = zastąp całą bibliotekę\n"
            "Anuluj",
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
        self.set_status(f"Zaimportowano {len(valid)} promptów z PWA.")

    def delete_selected(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        if not messagebox.askyesno(APP_NAME, f"Usunąć prompt „{prompt.name}”?", parent=self.root):
            return
        self.store.prompts = [item for item in self.store.prompts if item.id != prompt.id]
        self.store.save()
        self.selected_id = None
        self.refresh_all()
        self.set_status("Prompt usunięty.")

    def toggle_selected_pin(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        prompt.pinned = not prompt.pinned
        self.store.save()
        self.refresh_all()
        self.set_status("Przypięto prompt." if prompt.pinned else "Odpięto prompt.")

    def copy_selected(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            return
        self.copy_content_with_variables(prompt.content)
        self.set_status("Prompt skopiowany do schowka.")

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
            dialog = FillVariablesDialog(self.root, prompt.content, title="Uzupełnij zmienne w treści")
            self.root.wait_window(dialog)
            if dialog.filled_content:
                lines[-1] = dialog.filled_content
                body = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(body)
        self.root.update()
        self.set_status("Skopiowano prompt z metadanymi.")

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
        self.set_status(f"Utworzono kopię: „{clone.name}”.")

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
        self.search_var.set("")
        self.refresh_list()

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Eksport CSV",
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
        self.set_status(f"Eksport gotowy: {path}")

    def export_backup_json(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Kopia zapasowa JSON",
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
        self.set_status(f"Kopia zapasowa zapisana: {path}")

    def import_backup_json(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Przywróć z JSON",
            filetypes=[("JSON", "*.json"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, f"Nie można wczytać pliku JSON:\n{exc}", parent=self.root)
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
            messagebox.showerror(APP_NAME, "Nieprawidłowy format kopii zapasowej.", parent=self.root)
            return

        imported = [Prompt.from_dict(item) for item in raw_prompts if isinstance(item, dict)]
        valid = [p for p in imported if p.name and p.content]
        if not valid:
            messagebox.showwarning(APP_NAME, "W kopii nie ma poprawnych promptów.", parent=self.root)
            return

        mode = messagebox.askyesnocancel(
            APP_NAME,
            f"Znaleziono {len(valid)} promptów.\n\n"
            "Tak = dopisz do biblioteki\n"
            "Nie = zastąp całą bibliotekę (i ustawienia z pliku)\n"
            "Anuluj",
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
        self.set_status(f"Przywrócono {len(valid)} promptów z kopii zapasowej.")

    def import_csv(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Import CSV",
            filetypes=[("CSV", "*.csv"), ("Wszystkie pliki", "*.*")],
        )
        if not path:
            return
        mode = messagebox.askyesnocancel(
            APP_NAME,
            "Tak = dopisz nowe prompty\nNie = zastąp całą bibliotekę\nAnuluj = przerwij import",
            parent=self.root,
        )
        if mode is None:
            return
        replace = mode is False

        imported = self._read_csv(Path(path))
        valid = [prompt for prompt in imported if prompt.name and prompt.content]
        if not valid:
            messagebox.showwarning(APP_NAME, "Nie znaleziono poprawnych promptów w CSV.", parent=self.root)
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
        self.set_status(f"Zaimportowano {len(valid) - skipped} promptów. Pominięto duplikatów: {skipped}.")

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
        self.set_status("Konfiguracja n8n zapisana.")

    def test_n8n_webhook(self) -> None:
        url = self.ensure_n8n_url()
        if not url:
            return
        payload = n8n_envelope(
            "test",
            message="Test połączenia z Biblioteki Promptów AI (PrompBase Python)",
        )
        self._post_json(url, payload, "Test webhooka n8n zakończony pomyślnie.")

    def send_selected_to_n8n(self) -> None:
        prompt = self.selected_prompt()
        if not prompt:
            messagebox.showinfo(APP_NAME, "Zaznacz prompt na liście, który chcesz wysłać do n8n.", parent=self.root)
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
            "Co wysłać do n8n?\n\n"
            "Tak — cała biblioteka\n"
            "Nie — tylko przypięte prompty\n"
            "Anuluj — przerwij",
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
                f"Payload ma ok. {size_kb} KB ({len(prompts)} promptów). Kontynuować wysyłkę?",
                parent=self.root,
            ):
                return
        self._post_json(url, payload, f"Synchronizacja OK: {len(prompts)} promptów.")

    def export_n8n_json(self) -> None:
        """Zapis lokalny tego samego JSON co webhook sync — do testów workflow n8n."""
        choice = messagebox.askyesnocancel(
            APP_NAME,
            "Zapis JSON dla n8n:\n\n"
            "Tak — cała biblioteka\n"
            "Nie — tylko przypięte\n"
            "Anuluj",
            parent=self.root,
        )
        if choice is None:
            return
        pinned_only = choice is False
        prompts = [p for p in self.store.prompts if p.pinned] if pinned_only else list(self.store.prompts)
        if not prompts:
            messagebox.showwarning(APP_NAME, "Brak promptów do eksportu.", parent=self.root)
            return
        payload = n8n_envelope(
            "sync",
            count=len(prompts),
            pinned_only=pinned_only,
            prompts=[prompt_to_n8n_dict(p) for p in prompts],
        )
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Eksport JSON dla n8n",
            defaultextension=".json",
            initialfile="prompbase-n8n-sync.json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.set_status(f"Zapisano JSON dla n8n: {path}")

    def _post_json(self, url: str, payload: dict, ok_message: str) -> bool:
        normalized_url = normalize_n8n_url(url)
        if not validate_n8n_url(normalized_url):
            messagebox.showerror(
                APP_NAME,
                "Nieprawidłowy URL webhooka.\n\n"
                "Adres musi zaczynać się od http:// lub https:// i zawierać ścieżkę /webhook/ "
                "(np. https://twoja-instancja.app.n8n.cloud/webhook/prompbase).",
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
                f"n8n zwrócił błąd HTTP {exc.code}.\n\n{detail or exc.reason}",
                parent=self.root,
            )
            self.set_status(f"Błąd n8n: HTTP {exc.code}")
            return False
        except URLError as exc:
            messagebox.showwarning(
                APP_NAME,
                f"Nie udało się połączyć z n8n:\n{exc.reason or exc}",
                parent=self.root,
            )
            self.set_status("Błąd połączenia z n8n.")
            return False
        except TimeoutError:
            messagebox.showwarning(
                APP_NAME,
                f"Przekroczono limit czasu ({N8N_HTTP_TIMEOUT}s). Sprawdź URL i czy workflow n8n jest aktywny.",
                parent=self.root,
            )
            self.set_status("Timeout połączenia z n8n.")
            return False

        if status < 200 or status >= 300:
            messagebox.showwarning(
                APP_NAME,
                f"n8n zwrócił nieoczekiwany status HTTP {status}.\n\n{body[:500]}",
                parent=self.root,
            )
            self.set_status(f"Błąd n8n: HTTP {status}")
            return False

        suffix = f" — odpowiedź: {body[:120]}" if body else ""
        self.set_status(f"{ok_message} (HTTP {status}){suffix}")
        return True

    def show_help(self) -> None:
        messagebox.showinfo(
            "PrompBase - pomoc",
            f"PrompBase v{APP_VERSION}\n"
            f"Autor: {APP_AUTHOR}\n\n"
            "Skróty:\n"
            "N lub Ctrl+N - nowy prompt\n"
            "Ctrl+D - duplikuj prompt\n"
            "Ctrl+Enter - edytuj zaznaczony\n"
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
            "Dane są zapisywane lokalnie w pliku JSON. Import/eksport CSV jest zgodny z wersją PWA.",
            parent=self.root,
        )

    def show_data_path(self) -> None:
        backup = self.store.path.with_suffix(".json.bak")
        extra = f"\n\nOstatnia kopia automatyczna:\n{backup}" if backup.exists() else ""
        messagebox.showinfo(APP_NAME, f"Plik danych:\n{self.store.path}{extra}", parent=self.root)

    def open_data_folder(self) -> None:
        folder = self.store.path.parent
        try:
            if platform.system().lower() == "windows":
                os.startfile(folder)  # noqa: S606
            elif platform.system().lower() == "darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
            self.set_status(f"Otwarto folder: {folder}")
        except OSError as exc:
            messagebox.showwarning(APP_NAME, f"Nie udało się otworzyć folderu:\n{exc}", parent=self.root)

    def set_status(self, message: str) -> None:
        self.status_bar.configure(text=message)


def main() -> None:
    root = Tk()
    app = PrompBaseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
