"""Model danych: Prompt i PromptStore."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pbcore import i18n
from pbcore.core import *  # noqa: F401,F403


def _as_timestamp(value) -> int:
    """Znacznik czasu z niezaufanych danych; przy śmieciach — teraz.

    Pole `created` w cudzej kopii zapasowej bywa datą tekstową albo
    słownikiem. Wcześniej `int()` rzucało wyjątkiem i przerywało import
    całej biblioteki, a w wersji okienkowej nie było tego nawet widać.
    """
    if value is None or isinstance(value, bool):
        return now_ms()
    try:
        return int(value)
    except (TypeError, ValueError):
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
    favorite: bool = False
    created: int = field(default_factory=now_ms)
    id: str = field(default_factory=lambda: f"p_{uuid.uuid4().hex[:12]}")
    history: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Prompt:
        history_raw = data.get("history", [])
        history: list[dict] = []
        if isinstance(history_raw, list):
            history = [item for item in history_raw if isinstance(item, dict)][:PROMPT_HISTORY_MAX]
        return cls(
            id=str(data.get("id") or f"p_{uuid.uuid4().hex[:12]}"),
            name=str(data.get("name") or data.get("Nazwa") or "").strip(),
            content=str(data.get("content") or data.get("Treść Promptu") or data.get("Tresc Promptu") or "").strip(),
            # Z pliku może przyjść klucz („praca"), etykieta polska („Praca")
            # albo angielska („Work") — w danych trzymamy zawsze klucz.
            # Bez tego prompt z importu wysyłał do n8n etykietę zamiast klucza
            # i znikał z filtra w interfejsie angielskim.
            status=status_key_from_display(str(data.get("status") or "nowy").strip() or "nowy"),
            format=format_from_display(str(data.get("format") or "tekst").strip() or "tekst"),
            model=str(data.get("model") or data.get("Model AI") or "").strip(),
            zastosowanie=str(data.get("zastosowanie") or data.get("Zastosowanie") or "").strip(),
            tags=parse_tags_value(data.get("tags") or data.get("Tagi") or data.get("tagi") or ""),
            comment=str(data.get("comment") or data.get("Komentarz") or "").strip(),
            pinned=bool(data.get("pinned", False)),
            favorite=bool(data.get("favorite", False)),
            created=_as_timestamp(data.get("created")),
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
            "favorite": self.favorite,
            "created": self.created,
        }
        if self.history:
            payload["history"] = self.history[:PROMPT_HISTORY_MAX]
        return payload


def _sample_prompts_pl() -> list[Prompt]:
    return [
        Prompt(
            name="Post LinkedIn — marketing",
            status="praca",
            format="tekst",
            model="GPT-5.5",
            zastosowanie="marketing",
            tags="social, polski",
            content=(
                "Napisz post na LinkedIn po polsku. Ton: ekspercki, ale przystępny.\n\n"
                "Temat: [TEMAT]\nGrupa docelowa: [ODBIORCA]\nCall to action: [CTA]"
            ),
            comment="Przykład dla marketerów — użyj „Kopiuj i użyj w AI”",
            pinned=True,
        ),
        Prompt(
            name="Analiza kodu Python",
            status="praca",
            format="kod",
            model="Claude Opus 4.7",
            zastosowanie="kodowanie",
            tags="kod",
            content=(
                "Jesteś senior developerem Python. Przeanalizuj poniższy kod pod kątem "
                "błędów, wydajności, refaktoryzacji, PEP8 i bezpieczeństwa.\n\n```python\n[KOD]\n```"
            ),
            comment="Dla programistów — otwórz Claude po skopiowaniu",
        ),
        Prompt(
            name="n8n — opis zadania do workflow",
            status="uniwersalne",
            format="tekst",
            model="GPT-5.5 Mini",
            zastosowanie="automatyzacja",
            tags="n8n, szablon",
            content=(
                "Przygotuj zwięzły opis kroku automatyzacji n8n.\n\n"
                "Cel workflow: [CEL]\nWejście: [WEJSCIE]\nWyjście: [WYJSCIE]"
            ),
            comment="Wyślij do n8n z menu Narzędzia po skonfigurowaniu webhooka",
        ),
        Prompt(
            name="Korektor ortografii PL",
            status="uniwersalne",
            format="tekst",
            model="Claude Sonnet 4.6",
            zastosowanie="pisanie",
            tags="polski",
            content=(
                "Popraw błędy ortograficzne, interpunkcyjne i stylistyczne w tekście. "
                "Zachowaj oryginalny styl i sens.\n\nTekst do korekty:\n[TEKST]"
            ),
            comment="Uniwersalny szablon — dobre na start",
        ),
    ]


def _sample_prompts_en() -> list[Prompt]:
    return [
        Prompt(
            name="LinkedIn post — marketing",
            status="praca",
            format="tekst",
            model="GPT-5.5",
            zastosowanie="marketing",
            tags="social, english",
            content=(
                "Write a LinkedIn post in English. Tone: expert but approachable.\n\n"
                "Topic: [TOPIC]\nTarget audience: [AUDIENCE]\nCall to action: [CTA]"
            ),
            comment='Example for marketers — use "Copy and use in AI"',
            pinned=True,
        ),
        Prompt(
            name="Python code review",
            status="praca",
            format="kod",
            model="Claude Opus 4.7",
            zastosowanie="kodowanie",
            tags="code",
            content=(
                "You are a senior Python developer. Review the code below for "
                "bugs, performance, refactoring opportunities, PEP8 and security.\n\n```python\n[CODE]\n```"
            ),
            comment="For developers — open Claude after copying",
        ),
        Prompt(
            name="n8n — workflow step description",
            status="uniwersalne",
            format="tekst",
            model="GPT-5.5 Mini",
            zastosowanie="automatyzacja",
            tags="n8n, template",
            content=(
                "Write a concise description of an n8n automation step.\n\n"
                "Workflow goal: [GOAL]\nInput: [INPUT]\nOutput: [OUTPUT]"
            ),
            comment="Send to n8n from the Tools menu once the webhook is configured",
        ),
        Prompt(
            name="English proofreader",
            status="uniwersalne",
            format="tekst",
            model="Claude Sonnet 4.6",
            zastosowanie="pisanie",
            tags="english",
            content=(
                "Fix spelling, punctuation and style issues in the text below. "
                "Keep the original style and meaning.\n\nText to proofread:\n[TEXT]"
            ),
            comment="Universal template — good starting point",
        ),
    ]


# Puste "language" = wykryj z języka interfejsu przy pierwszym użyciu.
DEFAULT_SPELL_SETTINGS: dict = {"enabled": True, "language": ""}


class PromptStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.prompts: list[Prompt] = []
        self.n8n_url = ""
        self.theme = "jasny"
        self.language = i18n.DEFAULT_LANGUAGE
        self.cloud_folders: dict[str, str] = {"google_drive": "", "onedrive": ""}
        self.onboarding_done = False
        self.checklist: dict[str, bool] = dict(DEFAULT_CHECKLIST)
        # Ustawienia silników AI (bez klucza API — ten czytamy ze środowiska).
        self.ai_settings: dict[str, str] = dict(DEFAULT_AI_SETTINGS)
        # Sprawdzanie pisowni: włączone + kod słownika Hunspell (np. "pl_PL").
        self.spell_settings: dict = dict(DEFAULT_SPELL_SETTINGS)
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

        legacy_list = isinstance(data, list)
        if legacy_list:
            raw_prompts = data
            self.n8n_url = ""
            stored_cloud: dict = {}
            self.onboarding_done = bool(data)
        else:
            raw_prompts = data.get("prompts", [])
            self.n8n_url = data.get("n8n_url", "")
            self.theme = data.get("theme", "jasny")
            self.language = data.get("language", i18n.DEFAULT_LANGUAGE)
            stored_cloud = data.get("cloud_folders", {}) or {}
            self.onboarding_done = bool(data.get("onboarding_done", False))
            merged = dict(DEFAULT_CHECKLIST)
            if isinstance(data.get("checklist"), dict):
                merged.update({k: bool(v) for k, v in data["checklist"].items() if k in merged})
            self.checklist = merged
            ai_stored = data.get("ai_settings")
            if isinstance(ai_stored, dict):
                self.ai_settings = {
                    key: str(ai_stored.get(key, default) or default)
                    for key, default in DEFAULT_AI_SETTINGS.items()
                }
            spell_stored = data.get("spell_settings")
            if isinstance(spell_stored, dict):
                self.spell_settings = {
                    "enabled": bool(spell_stored.get("enabled", True)),
                    "language": str(spell_stored.get("language", "") or "").strip(),
                }
            if raw_prompts and "onboarding_done" not in data:
                self.onboarding_done = True
        if self.theme not in THEMES:
            self.theme = "jasny"
        if self.language not in i18n.LANGUAGES:
            self.language = i18n.DEFAULT_LANGUAGE
        i18n.set_language(self.language)

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
            "language": self.language,
            "cloud_folders": self.cloud_folders,
            "onboarding_done": self.onboarding_done,
            "checklist": self.checklist,
            "ai_settings": self.ai_settings,
            "spell_settings": self.spell_settings,
            "prompts": [prompt.to_dict() for prompt in self.prompts],
        }

    def mark_checklist(self, key: str) -> None:
        if key in self.checklist and not self.checklist[key]:
            self.checklist[key] = True
            self.save()

    def complete_onboarding(self) -> None:
        self.onboarding_done = True
        self.save()

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

    def _rotate_backups(self) -> None:
        """Utrzymuj kilka rotowanych kopii .bak.N (1 = najnowsza).

        Pojedynczy backup nie chroni, gdy uszkodzenie danych powtórzy się i
        nadpisze jedyną kopię. Rotacja zachowuje PROMPT_BACKUP_KEEP wersji.
        """
        if not self.path.exists():
            return
        keep = PROMPT_BACKUP_KEEP
        oldest = self.path.with_suffix(f".json.bak{keep}")
        try:
            if oldest.exists():
                oldest.unlink()
        except OSError:
            pass
        for index in range(keep - 1, 0, -1):
            src = self.path.with_suffix(f".json.bak{index}")
            dst = self.path.with_suffix(f".json.bak{index + 1}")
            if src.exists():
                try:
                    os.replace(src, dst)
                except OSError:
                    pass
        try:
            shutil.copy2(self.path, self.path.with_suffix(".json.bak1"))
        except OSError:
            pass

    def save(self) -> None:
        payload = self.to_payload()
        self._rotate_backups()
        # Zapis atomowy: najpierw plik tymczasowy, potem os.replace — przerwany
        # zapis nie uszkodzi promptbase.json.
        tmp_path = self.path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, self.path)

    def sample_data(self, *, force: bool = False) -> None:
        if self.prompts and not force:
            return
        samples = _sample_prompts_en() if i18n.is_english() else _sample_prompts_pl()
        for index, prompt in enumerate(samples):
            prompt.created = now_ms() - index * 3600 * 1000
        self.prompts = samples
        self.save()




def prompts_from_pwa_data(data) -> tuple[list[Prompt], str, str]:
    raw_prompts, n8n_url, theme = parse_pwa_import_data(data)
    prompts = [Prompt.from_dict(item) for item in raw_prompts if isinstance(item, dict)]
    return prompts, n8n_url, theme
