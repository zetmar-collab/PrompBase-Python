"""Silniki AI dla PrompBase: OpenRouter (chmura) i Ollama (lokalnie).

Runtime stdlib-only — HTTP przez urllib, tak jak integracja n8n.
Logika budowania żądań i parsowania odpowiedzi jest oddzielona od I/O,
dzięki czemu testy nie potrzebują sieci.

Klucz OpenRouter czytany jest ze zmiennej środowiskowej OPENROUTER_API_KEY —
nie trafia do promptbase.json ani do repozytorium.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError

from pbcore import i18n
from pbcore.core import APP_NAME, APP_VERSION, app_data_dir

# --- konfiguracja silników -------------------------------------------------

ENGINE_OPENROUTER = "openrouter"
ENGINE_OLLAMA = "ollama"

ENGINES = {
    ENGINE_OPENROUTER: "OpenRouter (chmura)",
    ENGINE_OLLAMA: "Ollama (lokalnie)",
}

OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_DEFAULT_MODEL = "anthropic/claude-sonnet-4.5"

OLLAMA_DEFAULT_HOST = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.1"

AI_HTTP_TIMEOUT = 120
AI_MAX_TOKENS = 2000

# --- akcje AI --------------------------------------------------------------

ACTION_IMPROVE = "improve"
ACTION_TRANSLATE = "translate"
ACTION_ADAPT = "adapt"

AI_ACTIONS = {
    ACTION_IMPROVE: "Ulepsz prompt",
    ACTION_TRANSLATE: "Przetłumacz",
    ACTION_ADAPT: "Dostosuj do platformy",
}

# Platformy docelowe dla akcji „dostosuj" wraz z ich charakterystyką.
ADAPT_TARGETS = {
    "ChatGPT": (
        "Zoptymalizuj pod ChatGPT (OpenAI): jasna rola systemowa, konkretne "
        "instrukcje krok po kroku, określony format wyjścia."
    ),
    "Claude": (
        "Zoptymalizuj pod Claude (Anthropic): czytelna struktura z sekcjami, "
        "znaczniki XML dla bloków (np. <kontekst>, <zadanie>), wyraźne zasady."
    ),
    "Gemini": (
        "Zoptymalizuj pod Gemini (Google): zwięzły kontekst na początku, "
        "precyzyjne polecenie, jasno wskazany oczekiwany rezultat."
    ),
    "Midjourney": (
        "Przekształć w prompt obrazowy Midjourney: opis sceny frazami "
        "oddzielonymi przecinkami, styl, oświetlenie, kompozycja, jakość; "
        "na końcu parametry (np. --ar 16:9 --v 6). Bez zdań rozkazujących."
    ),
    "Perplexity": (
        "Zoptymalizuj pod Perplexity: research-owe, precyzyjne pytanie "
        "nastawione na źródła i fakty."
    ),
    "Copilot": (
        "Zoptymalizuj pod GitHub Copilot: kontekst techniczny, język "
        "programowania, oczekiwane API i styl kodu."
    ),
}

# Angielskie odpowiedniki charakterystyk platform — używane, gdy UI działa
# po angielsku, żeby model dostawał instrukcje w jednym języku.
ADAPT_TARGETS_EN = {
    "ChatGPT": (
        "Optimise for ChatGPT (OpenAI): a clear system role, concrete "
        "step-by-step instructions, an explicit output format."
    ),
    "Claude": (
        "Optimise for Claude (Anthropic): readable structure with sections, "
        "XML tags for blocks (e.g. <context>, <task>), explicit rules."
    ),
    "Gemini": (
        "Optimise for Gemini (Google): concise context up front, a precise "
        "instruction, a clearly stated expected result."
    ),
    "Midjourney": (
        "Turn this into a Midjourney image prompt: describe the scene as "
        "comma-separated phrases, style, lighting, composition, quality; "
        "put parameters at the end (e.g. --ar 16:9 --v 6). No imperative sentences."
    ),
    "Perplexity": (
        "Optimise for Perplexity: a research-oriented, precise question "
        "aimed at sources and facts."
    ),
    "Copilot": (
        "Optimise for GitHub Copilot: technical context, programming "
        "language, expected API and code style."
    ),
}

TRANSLATE_LANGUAGES = ["angielski", "polski", "niemiecki", "hiszpański", "francuski"]
TRANSLATE_LANGUAGES_EN = ["English", "Polish", "German", "Spanish", "French"]

# Nazwy języków docelowych podajemy modelowi po angielsku, gdy UI jest po
# angielsku — inaczej instrukcja mieszałaby dwa języki.
_LANGUAGE_TO_EN = {
    "angielski": "English",
    "polski": "Polish",
    "niemiecki": "German",
    "hiszpański": "Spanish",
    "francuski": "French",
}

# Wspólna zasada dla wszystkich akcji — model ma zwrócić sam prompt.
_BASE_RULES = (
    "Jesteś ekspertem od inżynierii promptów. Zwróć WYŁĄCZNIE gotowy prompt, "
    "bez komentarzy, bez wyjaśnień, bez otaczających znaczników kodu. "
    "Zachowaj wszystkie zmienne w nawiasach kwadratowych (np. [TEMAT]) "
    "dokładnie w niezmienionej formie."
)

_BASE_RULES_EN = (
    "You are an expert prompt engineer. Return ONLY the finished prompt, "
    "with no commentary, no explanations and no surrounding code fences. "
    "Keep every square-bracket variable (e.g. [TEMAT]) exactly unchanged."
)


def build_system_prompt(
    action: str,
    *,
    target: str = "",
    language: str = "",
    ui_language: str = "",
) -> str:
    """Instrukcja systemowa dla wybranej akcji AI.

    `ui_language` decyduje o języku samej instrukcji: przy "en" model dostaje
    prompt systemowy po angielsku. Domyślnie bierzemy język interfejsu.
    """
    lang_ui = ui_language or i18n.get_language()
    english = lang_ui == i18n.LANG_EN

    if english:
        if action == ACTION_TRANSLATE:
            raw = (language or "English").strip()
            lang = _LANGUAGE_TO_EN.get(raw, raw)
            return (
                f"{_BASE_RULES_EN} Translate the prompt below into: {lang}. "
                "Preserve the meaning, tone and structure of the original."
            )
        if action == ACTION_ADAPT:
            name = (target or "ChatGPT").strip()
            hint = ADAPT_TARGETS_EN.get(name, f"Optimise for the {name} platform.")
            return f"{_BASE_RULES_EN} {hint}"
        return (
            f"{_BASE_RULES_EN} Improve the prompt below: sharpen the role and goal, "
            "add missing context, define the response format and reduce ambiguity. "
            "Do not change the language of the original."
        )

    if action == ACTION_TRANSLATE:
        lang = (language or "angielski").strip()
        return (
            f"{_BASE_RULES} Przetłumacz poniższy prompt na język: {lang}. "
            "Zachowaj sens, ton i strukturę oryginału."
        )
    if action == ACTION_ADAPT:
        name = (target or "ChatGPT").strip()
        hint = ADAPT_TARGETS.get(name, f"Zoptymalizuj pod platformę {name}.")
        return f"{_BASE_RULES} {hint}"
    # ACTION_IMPROVE (domyślna)
    return (
        f"{_BASE_RULES} Ulepsz poniższy prompt: doprecyzuj rolę i cel, dodaj "
        "brakujący kontekst, określ format odpowiedzi i ogranicz "
        "dwuznaczności. Nie zmieniaj języka oryginału."
    )


def translate_languages() -> list[str]:
    """Lista języków tłumaczenia w języku interfejsu."""
    return list(TRANSLATE_LANGUAGES_EN if i18n.is_english() else TRANSLATE_LANGUAGES)


def action_labels() -> dict[str, str]:
    """Etykiety akcji AI w języku interfejsu."""
    return {key: i18n.t(label) for key, label in AI_ACTIONS.items()}


def engine_labels() -> dict[str, str]:
    """Nazwy silników w języku interfejsu."""
    return {key: i18n.t(label) for key, label in ENGINES.items()}


def clean_ai_output(text: str) -> str:
    """Usuwa opakowanie ```...``` i puste marginesy z odpowiedzi modelu."""
    value = (text or "").strip()
    if not value.startswith("```"):
        return value
    lines = value.splitlines()
    if len(lines) < 2:
        return value
    lines = lines[1:]  # pierwsza linia to ``` lub ```json itp.
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


# --- budowanie żądań (czyste funkcje, testowalne bez sieci) ----------------

def openrouter_payload(model: str, system_prompt: str, content: str) -> dict:
    return {
        "model": model or OPENROUTER_DEFAULT_MODEL,
        "max_tokens": AI_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    }


def ollama_payload(model: str, system_prompt: str, content: str) -> dict:
    return {
        "model": model or OLLAMA_DEFAULT_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
    }


def parse_openrouter_response(data: dict) -> str:
    """Wyciąga treść z odpowiedzi OpenRouter (format OpenAI chat)."""
    choices = (data or {}).get("choices") or []
    if not choices:
        raise AiError("OpenRouter nie zwrócił odpowiedzi (puste 'choices').")
    message = choices[0].get("message") or {}
    return clean_ai_output(str(message.get("content") or ""))


def parse_ollama_response(data: dict) -> str:
    """Wyciąga treść z odpowiedzi Ollama (/api/chat)."""
    message = (data or {}).get("message") or {}
    text = message.get("content")
    if text is None:
        text = (data or {}).get("response")  # /api/generate — zgodność
    if text is None:
        raise AiError("Ollama nie zwróciła treści odpowiedzi.")
    return clean_ai_output(str(text))


def normalize_ollama_host(host: str) -> str:
    value = (host or "").strip().rstrip("/")
    if not value:
        return OLLAMA_DEFAULT_HOST
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    return value


def api_key_file() -> Path:
    """Ścieżka pliku z kluczem — osobno od promptbase.json.

    Klucz celowo NIE trafia do promptbase.json, bo ten plik jest kopiowany do
    kopii zapasowych i eksportowany do Google Drive / OneDrive — klucz
    wyciekłby razem z nimi.
    """
    return app_data_dir() / "openrouter.key"


def load_stored_api_key() -> str:
    path = api_key_file()
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def save_stored_api_key(key: str) -> None:
    """Zapisuje klucz (pusty = usuwa plik)."""
    path = api_key_file()
    value = (key or "").strip()
    if not value:
        try:
            path.unlink()
        except OSError:
            pass
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    # Na Windows ogranicz dostęp do bieżącego użytkownika (best effort).
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def openrouter_api_key() -> str:
    """Klucz API: najpierw zmienna środowiskowa, potem zapisany w ustawieniach.

    Zmienna ma pierwszeństwo, żeby dało się nadpisać klucz bez zmiany ustawień
    (np. inny klucz na czas testów).
    """
    from_env = (os.environ.get(OPENROUTER_API_KEY_ENV) or "").strip()
    return from_env or load_stored_api_key()


def api_key_source() -> str:
    """Skąd pochodzi aktywny klucz: 'env', 'plik' albo '' (brak)."""
    if (os.environ.get(OPENROUTER_API_KEY_ENV) or "").strip():
        return "env"
    return "plik" if load_stored_api_key() else ""


class AiError(Exception):
    """Błąd komunikacji z silnikiem AI — komunikat jest gotowy dla użytkownika."""


# --- warstwa I/O -----------------------------------------------------------

def _post_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    base_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
        "User-Agent": f"{APP_NAME}/{APP_VERSION}",
    }
    base_headers.update(headers)
    req = request.Request(url, data=data, headers=base_headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        detail = ""
        if exc.fp:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise AiError(f"Błąd HTTP {exc.code}: {detail or exc.reason}") from exc
    except TimeoutError as exc:
        raise AiError(f"Przekroczono limit czasu ({timeout}s).") from exc
    except URLError as exc:
        raise AiError(f"Brak połączenia: {exc.reason or exc}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise AiError("Otrzymano odpowiedź, która nie jest poprawnym JSON.") from exc


def run_openrouter(model: str, system_prompt: str, content: str, *, timeout: int = AI_HTTP_TIMEOUT) -> str:
    key = openrouter_api_key()
    if not key:
        raise AiError(
            "Brak klucza API. Ustaw zmienną środowiskową "
            f"{OPENROUTER_API_KEY_ENV} i uruchom aplikację ponownie.\n\n"
            "Klucz zdobędziesz na https://openrouter.ai/keys"
        )
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://github.com/zetmar-collab/PrompBase-Python",
        "X-Title": APP_NAME,
    }
    data = _post_json(OPENROUTER_URL, openrouter_payload(model, system_prompt, content), headers, timeout)
    if isinstance(data, dict) and data.get("error"):
        message = (data["error"] or {}).get("message") if isinstance(data["error"], dict) else data["error"]
        raise AiError(f"OpenRouter: {message}")
    return parse_openrouter_response(data)


def run_ollama(
    model: str,
    system_prompt: str,
    content: str,
    *,
    host: str = OLLAMA_DEFAULT_HOST,
    timeout: int = AI_HTTP_TIMEOUT,
) -> str:
    url = f"{normalize_ollama_host(host)}/api/chat"
    try:
        data = _post_json(url, ollama_payload(model, system_prompt, content), {}, timeout)
    except AiError as exc:
        if "Brak połączenia" in str(exc):
            raise AiError(
                f"Nie można połączyć się z Ollamą ({normalize_ollama_host(host)}).\n\n"
                "Sprawdź, czy aplikacja Ollama jest uruchomiona."
            ) from exc
        raise
    if isinstance(data, dict) and data.get("error"):
        raise AiError(f"Ollama: {data['error']}")
    return parse_ollama_response(data)


def list_ollama_models(host: str = OLLAMA_DEFAULT_HOST, *, timeout: int = 10) -> list[str]:
    """Modele zainstalowane lokalnie (puste, gdy Ollama nie odpowiada)."""
    url = f"{normalize_ollama_host(host)}/api/tags"
    req = request.Request(url, headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        return []
    return parse_ollama_models(data)


def parse_ollama_models(data: dict) -> list[str]:
    """Nazwy modeli z /api/tags — tylko te, które potrafią generować tekst."""
    models = (data or {}).get("models") or []
    names: list[str] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("model") or "").strip()
        if not name:
            continue
        caps = item.get("capabilities")
        # Modele czysto embeddingowe nie nadają się do przepisywania promptów.
        if isinstance(caps, list) and caps and "completion" not in caps:
            continue
        if name not in names:
            names.append(name)
    return names


def resolve_ollama_model(model: str, host: str = OLLAMA_DEFAULT_HOST) -> str:
    """Zwraca model, który faktycznie jest zainstalowany w Ollamie.

    Domyślna nazwa (np. llama3.1) często nie jest pobrana na danym komputerze —
    zamiast błędu wybieramy pierwszy dostępny model generacyjny.
    """
    installed = list_ollama_models(host)
    if not installed:
        return model  # brak kontaktu z Ollamą — niech zdecyduje warstwa wyżej
    wanted = (model or "").strip()
    if wanted in installed:
        return wanted
    # Dopasowanie po prefiksie: "llama3.1" pasuje do "llama3.1:8b".
    for name in installed:
        if wanted and name.split(":")[0] == wanted.split(":")[0]:
            return name
    return installed[0]


def run_ai_action(
    *,
    engine: str,
    action: str,
    content: str,
    model: str = "",
    target: str = "",
    language: str = "",
    host: str = OLLAMA_DEFAULT_HOST,
    timeout: int = AI_HTTP_TIMEOUT,
) -> str:
    """Wykonuje akcję AI wybranym silnikiem i zwraca sam prompt."""
    text = (content or "").strip()
    if not text:
        raise AiError("Prompt jest pusty — nie ma czego przetwarzać.")

    system_prompt = build_system_prompt(action, target=target, language=language)
    if engine == ENGINE_OLLAMA:
        model = resolve_ollama_model(model, host)
        result = run_ollama(model, system_prompt, text, host=host, timeout=timeout)
    elif engine == ENGINE_OPENROUTER:
        result = run_openrouter(model, system_prompt, text, timeout=timeout)
    else:
        raise AiError(f"Nieznany silnik AI: {engine}")

    if not result.strip():
        raise AiError("Model zwrócił pustą odpowiedź. Spróbuj ponownie lub zmień model.")
    return result
