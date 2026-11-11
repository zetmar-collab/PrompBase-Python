"""Import i eksport biblioteki: CSV, JSON, XLSX, PWA i chmura."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

from pbcore import xlsx
from pbcore.core import *  # noqa: F401,F403
from pbcore.dialogs import *  # noqa: F401,F403
from pbcore.i18n import t


class ImportExportMixin:
    """Wczytywanie i zapisywanie biblioteki w roznych formatach.

    Domieszka do PrompBaseApp — korzysta z `self.store`, `self.root`
    i pozostalych pol glownego okna.
    """

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
            title=t('Import CSV, XLSX lub JSON'),
            filetypes=[
                (t("CSV, XLSX i JSON"), "*.csv;*.xlsx;*.json"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx"),
                ("JSON", "*.json"),
                (t("Wszystkie pliki"), "*.*"),
            ],
        )
        if not path:
            return
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            self._import_csv_path(file_path)
        elif suffix == ".xlsx":
            self._import_xlsx_path(file_path)
        elif suffix == ".json":
            self._import_json_path(file_path)
        else:
            messagebox.showwarning(APP_NAME, t('Obsługiwane rozszerzenia: .csv, .xlsx, .json'), parent=self.root)

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
        self.save_store()
        self.refresh_all()
        self.set_status(f"{t('Zaimportowano z pliku: ')}{source_label}")

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
        self.save_store()
        self.refresh_all()
        self.set_status(f"{t('Zaimportowano ')}{len(valid)}{t(' promptów z PWA.')}")

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
            # Naglowki i etykiety w jezyku interfejsu; import rozpoznaje
            # oba zapisy, wiec plik dziala takze w drugim jezyku.
            writer.writerow([t(name) for name in xlsx.EXPORT_HEADER])
            for prompt in self.store.prompts:
                writer.writerow(
                    [
                        prompt.name,
                        status_display(prompt.status),
                        format_display(prompt.format),
                        prompt.model,
                        prompt.zastosowanie,
                        prompt.tags,
                        format_date(prompt.created),
                        prompt.comment,
                        prompt.content.replace("\n", " ↵ "),
                    ]
                )
        self.set_status(f"{t('Eksport gotowy: ')}{path}")

    def export_xlsx(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=t('Eksport XLSX'),
            defaultextension=".xlsx",
            initialfile=xlsx.default_export_name(),
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        try:
            rows = xlsx.prompts_to_rows(
                self.store.prompts, status_display, format_date, format_display
            )
            xlsx.write_sheet(path, [t(name) for name in xlsx.EXPORT_HEADER], rows)
        except xlsx.XlsxError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self.root)
            return
        self.set_status(f"{t('Eksport gotowy: ')}{path}")

    def import_xlsx(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title=t('Import XLSX'),
            filetypes=[("Excel", "*.xlsx"), (t("Wszystkie pliki"), "*.*")],
        )
        if not path:
            return
        self._import_xlsx_path(Path(path))

    def _import_xlsx_path(self, path: Path) -> None:
        """Wczytuje arkusz w tle — duży plik nie może zamrozić okna."""

        def parse():
            rows = xlsx.read_rows(path)
            return xlsx.rows_to_prompt_dicts(rows)

        def failed(exc) -> None:
            if not isinstance(exc, xlsx.XlsxError):
                log_exception(type(exc), exc, exc.__traceback__)
            messagebox.showerror(APP_NAME, str(exc), parent=self.root)
            self.set_status(t('Import przerwany.'))

        self.run_in_background(
            parse,
            lambda result: self._finish_xlsx_import(result[0], result[1]),
            on_error=failed,
            busy_status=t('Wczytuję arkusz…'),
        )

    def _finish_xlsx_import(self, items: list[dict], mapping: dict) -> None:
        imported = [Prompt.from_dict(item) for item in items]
        if not imported:
            messagebox.showwarning(APP_NAME, t('Brak poprawnych promptów w pliku.'), parent=self.root)
            return

        # Pokazujemy, które kolumny rozpoznaliśmy — przy obcych arkuszach to
        # jedyny sposób, żeby użytkownik zauważył złe dopasowanie przed importem.
        recognised = ", ".join(sorted(mapping)) if mapping else "-"
        categories = sorted({p.zastosowanie for p in imported if p.zastosowanie})
        summary = (
            f"{t('Znaleziono ')}{len(imported)}{t(' promptów.')}\n"
            f"{t('Rozpoznane kolumny: ')}{recognised}\n"
            f"{t('Kategorie: ')}{len(categories)}"
        )
        mode = messagebox.askyesnocancel(
            APP_NAME,
            summary + t("\n\nTak = dopisz\nNie = zastąp bibliotekę\nAnuluj"),
            parent=self.root,
        )
        if mode is None:
            return
        if mode is False:
            self.store.prompts = imported
        else:
            existing = {p.name + "|" + p.content[:80] for p in self.store.prompts}
            fresh = [p for p in imported if p.name + "|" + p.content[:80] not in existing]
            self.store.prompts = fresh + self.store.prompts
        self.save_store()
        self.refresh_all()
        self.set_status(f"{t('Zaimportowano ')}{len(imported)}{t(' promptów z XLSX.')}")

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
            self.store.n8n_url = self._confirm_imported_n8n_url(n8n_url)
            if theme in THEMES:
                self.store.theme = theme
                self.theme_var.set(theme)
                self.apply_theme(save=False)
        else:
            existing = {p.name + "|" + p.content[:80] for p in self.store.prompts}
            fresh = [p for p in valid if p.name + "|" + p.content[:80] not in existing]
            self.store.prompts = fresh + self.store.prompts

        self.save_store()
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

        self.save_store()
        self.refresh_all()
        self.set_status(f"{t('Zaimportowano ')}{len(valid) - skipped}{t(' promptów. Pominięto duplikatów: ')}{skipped}{t('.')}")
