"""Model danych: Prompt i PromptStore."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from pbcore.core import *  # noqa: F401,F403


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
    def from_dict(cls, data: dict) -> Prompt:
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
        self.onboarding_done = False
        self.checklist: dict[str, bool] = dict(DEFAULT_CHECKLIST)
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
            stored_cloud = data.get("cloud_folders", {}) or {}
            self.onboarding_done = bool(data.get("onboarding_done", False))
            merged = dict(DEFAULT_CHECKLIST)
            if isinstance(data.get("checklist"), dict):
                merged.update({k: bool(v) for k, v in data["checklist"].items() if k in merged})
            self.checklist = merged
            if raw_prompts and "onboarding_done" not in data:
                self.onboarding_done = True
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
            "onboarding_done": self.onboarding_done,
            "checklist": self.checklist,
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
        samples = [
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
        for index, prompt in enumerate(samples):
            prompt.created = now_ms() - index * 3600 * 1000
        self.prompts = samples
        self.save()




def prompts_from_pwa_data(data) -> tuple[list[Prompt], str, str]:
    raw_prompts, n8n_url, theme = parse_pwa_import_data(data)
    prompts = [Prompt.from_dict(item) for item in raw_prompts if isinstance(item, dict)]
    return prompts, n8n_url, theme
