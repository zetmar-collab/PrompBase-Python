"""Stałe i funkcje czyste PrompBase (bez GUI)."""
from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # tylko dla adnotacji — brak cyklu w czasie wykonania
    from pbcore.models import Prompt

APP_NAME = "PrompBase"
APP_VERSION = "2.10.1"
PLACEHOLDER_RE = re.compile(r"\[([A-Za-z0-9_]+)\]")
APP_AUTHOR_URL = "https://github.com/zetmar-collab"
APP_RELEASE_URL = "https://github.com/zetmar-collab/PrompBase-Python/releases"
APP_HELP_URL = "https://github.com/zetmar-collab/PrompBase-Python#readme"
# Zgłaszanie nieodpowiednich treści wygenerowanych przez AI (Store 11.16).
REPORT_ISSUE_URL = "https://github.com/zetmar-collab/PrompBase-Python/issues/new"
DEFAULT_CHECKLIST = {
    "selected": False,
    "copied": False,
    "opened_ai": False,
    "added_prompt": False,
}
CLOUD_SUBDIR = "PrompBase"
PROMPT_HISTORY_MAX = 20
# Ustawienia silników AI zapisywane w promptbase.json.
# Klucz OpenRouter celowo NIE jest tu trzymany — czytamy go ze zmiennej
# środowiskowej OPENROUTER_API_KEY, żeby nie leżał jawnie w pliku danych.
DEFAULT_AI_SETTINGS = {
    "engine": "ollama",
    "openrouter_model": "anthropic/claude-sonnet-4.5",
    "ollama_model": "llama3.1",
    "ollama_host": "http://localhost:11434",
    "translate_language": "angielski",
}
PROMPT_BACKUP_KEEP = 5
PWA_STORAGE_KEY = "promptLibrary"
N8N_SOURCE = "biblioteka-promptow"
N8N_HTTP_TIMEOUT = 30
APP_AUTHOR = "Marek Zettel"


def resolve_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # core.py mieszka w pbcore/, więc katalog aplikacji to poziom wyżej
    # (tam gdzie models.json, assets/, landing/, docs/).
    return Path(__file__).resolve().parent.parent


def is_msix_package() -> bool:
    """Czy aplikacja działa jako zainstalowany pakiet MSIX (Desktop Bridge).

    Wykorzystywane, żeby ukryć w wersji sklepowej elementy UI niezgodne
    z polityką Microsoft Store (np. link do pobrania spoza Store, cennik
    planu Pro sprzedawanego poza systemem płatności Store) — zob.
    certyfikacja Store, zasada 10.1.5 Software Distribution.

    Wywołuje Win32 GetCurrentPackageFullName z zerowym buforem: wewnątrz
    pakietu MSIX zwraca ERROR_INSUFFICIENT_BUFFER (122, bo bufor jest za
    mały) i ustawia wymagany rozmiar; poza pakietem zwraca
    APPMODEL_ERROR_NO_PACKAGE (15700). Kod błędu to bezpośredni wynik
    wywołania — nie GetLastError().
    """
    if platform.system().lower() != "windows":
        return False
    try:
        import ctypes

        length = ctypes.c_uint32(0)
        result = ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
        return result != 15700  # APPMODEL_ERROR_NO_PACKAGE
    except (AttributeError, OSError):
        return False


APP_DIR = resolve_app_dir()
ASSETS_DIR = APP_DIR / "assets"
LANDING_PAGE_PATH = APP_DIR / "landing" / "index.html"
DOCS_DIR = APP_DIR / "docs"
DOC_PWA_IMPORT = DOCS_DIR / "PWA-IMPORT.md"
DOC_QUICKSTART = DOCS_DIR / "QUICKSTART.md"

# Motywy. Poza kolorami marki (fiolet) trzymamy tu tokeny potrzebne do
# „płaskiego" wyglądu: `border` zastępuje trójwymiarowe krawędzie motywu clam,
# `control_border` to krawędź pola tekstowego — musi mieć kontrast 3:1, bo to
# ona pozwala rozpoznać kontrolkę (WCAG 1.4.11); `border` jest dekoracyjny.
# `row_alt` daje delikatne pasy na liście, a `accent_text` to kolor napisu na
# przycisku akcentowym (na jasnym fiolecie w ciemnych motywach czytelniejszy
# jest ciemny tekst niż biały).
THEMES = {
    "jasny": {
        "bg": "#f4f5f9",
        "surface": "#ffffff",
        "border": "#e2e4ee",
        "control_border": "#7f8699",
        "text": "#171a23",
        "muted": "#5f6673",
        "accent": "#5b4bd6",
        "accent_hover": "#4a3cc4",
        "accent_text": "#ffffff",
        "select": "#eae7ff",
        "row_alt": "#f2f3f9",
        "field": "#ffffff",
        "search_hit": "#fff3a3",
    },
    "ciemny": {
        "bg": "#0f1117",
        "surface": "#171a23",
        "border": "#262b38",
        "control_border": "#636f89",
        "text": "#eef1f7",
        "muted": "#98a1b3",
        "accent": "#8a7bff",
        "accent_hover": "#9c90ff",
        "accent_text": "#10121a",
        "select": "#2a2f4a",
        "row_alt": "#1b1f2a",
        "field": "#12151d",
        "search_hit": "#4a4520",
    },
    "grafit": {
        "bg": "#1a1d24",
        "surface": "#232730",
        "border": "#333846",
        "control_border": "#6e7890",
        "text": "#e9edf4",
        "muted": "#99a2b2",
        "accent": "#7c8cff",
        "accent_hover": "#8f9cff",
        "accent_text": "#12141a",
        "select": "#303649",
        "row_alt": "#262a34",
        "field": "#1e222a",
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
    "Manus",
    # Poprzednie generacje (stare prompty / kompatybilność)
    "GPT-4.1",
    "GPT-4o",
    "Claude Opus 4",
    "Claude Sonnet 4",
    "Gemini 2.5 Pro",
    "Gemini 2.5 Flash",
]

MODELS_FILE = APP_DIR / "models.json"


def load_model_options() -> list[str]:
    """Lista modeli z opcjonalnego models.json (obok aplikacji); gdy brak pliku
    lub jest niepoprawny — wbudowana lista AI_MODELS. Dzięki temu aktualizacja
    modeli nie wymaga przebudowy aplikacji."""
    if MODELS_FILE.is_file():
        try:
            data = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
            models = data.get("models") if isinstance(data, dict) else data
            if isinstance(models, list):
                cleaned = [str(m).strip() for m in models if str(m).strip()]
                if cleaned:
                    return cleaned
        except (OSError, json.JSONDecodeError):
            pass
    return list(AI_MODELS)


AI_PLATFORMS = (
    ("ChatGPT", "https://chatgpt.com/"),
    ("Claude", "https://claude.ai/"),
    ("Gemini", "https://gemini.google.com/app"),
    ("Perplexity", "https://www.perplexity.ai/"),
    ("Copilot", "https://copilot.microsoft.com/"),
    ("Manus", "https://manus.im/app"),
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
    """Podmienia [TOKEN] w jednym przejściu — wartość jednej zmiennej nie jest
    ponownie traktowana jako placeholder innej (brak kaskadowych podmian)."""
    def _replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return values[token] if token in values else token

    return PLACEHOLDER_RE.sub(_replace, text or "")


def parse_tags_value(raw) -> str:
    if isinstance(raw, list):
        return ", ".join(str(item).strip() for item in raw if str(item).strip())
    return str(raw or "").strip()


def search_terms(query: str) -> list[str]:
    """Dzieli zapytanie na słowa (warunek AND).

    Fraza w cudzysłowie traktowana jest jako całość: `"post na blog" seo`
    daje ["post na blog", "seo"].
    """
    value = (query or "").strip().lower()
    if not value:
        return []
    terms: list[str] = []
    for index, chunk in enumerate(value.split('"')):
        if index % 2:  # tekst pomiędzy cudzysłowami
            phrase = chunk.strip()
            if phrase:
                terms.append(phrase)
        else:
            terms.extend(part for part in chunk.split() if part)
    return terms


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


ERROR_LOG_MAX_BYTES = 512 * 1024


def error_log_path() -> Path:
    return app_data_dir() / "error.log"


def log_exception(exc_type, exc, tb) -> Path | None:
    """Dopisuje wyjątek do pliku dziennika. Zwraca ścieżkę albo None.

    Aplikacja jest budowana jako okienkowa (console=False), więc `stderr`
    donikąd nie prowadzi — bez tego dziennika każda awaria była niewidoczna
    i nie dało się zdiagnozować zgłoszenia użytkownika.

    Sama nigdy nie rzuca: zawodzi po cichu, bo wywołujemy ją już w trakcie
    obsługi innego błędu.
    """
    try:
        path = error_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        # Prosta rotacja — dziennik nie może rosnąć w nieskończoność.
        try:
            if path.stat().st_size > ERROR_LOG_MAX_BYTES:
                path.replace(path.with_suffix(".log.1"))
        except OSError:
            pass
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"\n--- {datetime.now().isoformat()} | {APP_NAME} {APP_VERSION} ---\n")
            traceback.print_exception(exc_type, exc, tb, file=fh)
        return path
    except Exception:  # noqa: BLE001 - dziennik nie może wywrócić aplikacji
        return None


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
        "favorite": bool(prompt.favorite),
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
                # Cienka ramka w kolorze obramowania, akcent dopiero po
                # wejściu w pole — bez tego „szara obwódka" dominuje widok.
                "highlightbackground": colors.get("control_border", colors["muted"]),
                "highlightcolor": colors["accent"],
                "padx": 8,
                "pady": 6,
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
    if "manus" in lowered:
        return "Manus"
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


# --- etykiety wartości dla interfejsu --------------------------------------
#
# Tłumaczymy wyłącznie to, co widać na ekranie. W pliku `promptbase.json`
# i w ładunku wysyłanym do n8n zostają wartości kanoniczne (polskie), bo
# zmiana języka interfejsu nie może zmienić kontraktu danych ani zepsuć
# bibliotek zapisanych wcześniej. Funkcje `*_from_display` przyjmują zarówno
# etykietę przetłumaczoną, jak i kanoniczną — dzięki temu starsze dane
# i pliki importowane z zewnątrz nadal się dopasowują.

ALL_FILTER = "Wszystkie"


def _translate_value(value: str) -> str:
    from pbcore import i18n

    return i18n.t(value)


def all_filter_label() -> str:
    """Etykieta „wszystkie" w filtrach (sentinel w warstwie widoku)."""
    return _translate_value(ALL_FILTER)


def status_display(key: str) -> str:
    return _translate_value(STATUSES.get(key, key))


def status_display_values() -> list[str]:
    return [status_display(key) for key in STATUSES]


def status_key_from_display(label: str) -> str:
    from pbcore import i18n

    for key, canonical in STATUSES.items():
        if label == key or label in i18n.value_aliases(canonical):
            return key
    return status_key_from_label(label)


def format_display(value: str) -> str:
    return _translate_value(value) if value in FORMATS else value


def format_display_values() -> list[str]:
    return [format_display(value) for value in FORMATS]


def format_from_display(label: str) -> str:
    from pbcore import i18n

    for value in FORMATS:
        if label in i18n.value_aliases(value):
            return value
    return label


def sort_display_values() -> list[str]:
    return [_translate_value(label) for label in SORT_OPTIONS]


def sort_key_from_display(label: str) -> str:
    from pbcore import i18n

    for canonical, key in SORT_OPTIONS.items():
        if label in i18n.value_aliases(canonical):
            return key
    return "newest"


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


