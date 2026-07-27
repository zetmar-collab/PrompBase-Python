---
name: gen-test
description: Generuj testy pytest dla logiki PrompBase (funkcje czyste, PromptStore, import PWA/CSV). Użyj gdy dodano lub zmieniono logikę bez GUI i trzeba dopisać pokrycie.
disable-model-invocation: true
---

# gen-test — testy pytest dla PrompBase

Skill wspiera pisanie testów dla `promptbase.py`. Runtime aplikacji jest
stdlib-only (Tkinter), więc testujemy **wyłącznie logikę bez GUI**.

## Zasady

1. **Nie twórz okna Tk.** Import `import promptbase as pb` jest bezpieczny —
   moduł nie tworzy `Tk()` przy imporcie. Nie wywołuj `main()`.
2. **Testuj funkcje czyste i `PromptStore`** — nie widżety, dialogi ani metody
   `PrompBaseApp` zależne od `self.root`.
3. Używaj fikstury `tmp_path` dla operacji na plikach (`PromptStore(tmp_path / "promptbase.json")`).
4. Nazwy plików: `tests/test_*.py`. Uruchamiaj: `python -m pytest`.

## Dobrzy kandydaci do testów (logika bez GUI)

- Placeholdery: `extract_placeholders`, `fill_placeholders` (jedno przejście, brak kaskady)
- Tagi: `parse_tags_value`, `tag_list_from_string`
- n8n: `validate_n8n_url`, `normalize_n8n_url`, `prompt_to_n8n_dict`, `n8n_envelope`
- Modele: `merge_model_options`, `load_model_options`, `suggest_ai_platform`
- Daty: `parse_date_to_ms`, `format_date`, `now_ms`
- `Prompt.from_dict` / `to_dict` (klucze PL i EN, limit historii)
- Import: `parse_pwa_import_data`, `prompts_from_pwa_data`
- `PromptStore`: `load` (legacy list, dict, uszkodzony JSON, zły motyw), `save`,
  rotacja backupów (`_rotate_backups`, `PROMPT_BACKUP_KEEP`)
- Statusy: `status_label` / `status_key_from_label` (round-trip)

## Szablon testu

```python
from __future__ import annotations

import json
import pytest
import promptbase as pb


def test_nazwa_opisowa():
    assert pb.funkcja(wejscie) == oczekiwane


@pytest.mark.parametrize("wejscie,oczekiwane", [(..., ...)])
def test_parametryzowany(wejscie, oczekiwane):
    assert pb.funkcja(wejscie) == oczekiwane


def test_z_plikiem(tmp_path):
    store = pb.PromptStore(tmp_path / "promptbase.json")
    store.prompts = [pb.Prompt(name="N", content="C")]
    store.save()
    reloaded = pb.PromptStore(tmp_path / "promptbase.json")
    assert reloaded.prompts[0].name == "N"
```

## Po wygenerowaniu

Zawsze uruchom `python -m pytest` i pokaż wynik. Przy pełnym zestawie dodaj też
`python -m ruff check tests/`.
