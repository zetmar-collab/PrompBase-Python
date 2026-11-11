"""Integracja z n8n: konfiguracja webhooka i wysylka promptow."""
from __future__ import annotations

import json
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib import request
from urllib.error import HTTPError, URLError

from pbcore.core import *  # noqa: F401,F403
from pbcore.dialogs import *  # noqa: F401,F403
from pbcore.i18n import t


class N8nMixin:
    """Wysylka do n8n i konfiguracja adresu webhooka.

    Domieszka do PrompBaseApp — korzysta z `self.store`, `self.root`
    i pozostalych pol glownego okna.
    """

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
        self.save_store()
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
                body = response.read(ai.MAX_RESPONSE_BYTES).decode("utf-8", errors="replace").strip()
        except HTTPError as exc:
            detail = exc.read(ai.MAX_ERROR_BYTES).decode("utf-8", errors="replace").strip() if exc.fp else ""
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

    def _confirm_imported_n8n_url(self, candidate) -> str:
        """Adres webhooka z cudzego pliku ustawiamy dopiero po potwierdzeniu.

        Kopia zapasowa niesie `n8n_url`, a walidacja wymaga tylko http(s)
        i tekstu „/webhook" — czyli przechodzi dowolny cudzy serwer. Wcześniej
        podmiana była cicha, więc udostępniony plik mógł po imporcie
        przekierować wysyłkę wszystkich promptów gdzie indziej.
        """
        new_url = str(candidate or "").strip()
        current = str(self.store.n8n_url or "")
        if not new_url or new_url == current:
            return current
        accepted = messagebox.askyesno(
            APP_NAME,
            t('Plik zawiera adres webhooka n8n:\n\n')
            + new_url
            + t('\n\nPrompty wysyłane do n8n trafią pod ten adres.\nUstawić go?'),
            parent=self.root,
        )
        return new_url if accepted else current
