"""Asystent AI w oknie glownym: ulepszanie, tlumaczenie, dostosowanie."""
from __future__ import annotations

import webbrowser
from tkinter import messagebox

from pbcore import ai
from pbcore.ai_dialogs import AiResultDialog
from pbcore.core import *  # noqa: F401,F403
from pbcore.dialogs import *  # noqa: F401,F403
from pbcore.i18n import t


class AiAssistantMixin:
    """Akcje asystenta AI.

    Domieszka do PrompBaseApp — korzysta z `self.store`, `self.root`
    i pozostalych pol glownego okna.
    """

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
            self.save_store()
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
            self.save_store()
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
