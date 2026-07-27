---
name: refactor-splitter
description: Pomaga bezpiecznie rozbić monolit promptbase.py na pakiet bez zmiany zachowania. Użyj gdy trzeba wydzielić moduły (models, dialogs, app, helpers) z zachowaniem testów.
tools: Read, Grep, Glob, Edit, Write, Bash
---

# refactor-splitter — bezpieczny podział promptbase.py

`promptbase.py` to jeden plik ~3000 linii. Twoim zadaniem jest wydzielanie
modułów **małymi, weryfikowalnymi krokami**, nigdy hurtem.

## Docelowa struktura (propozycja)

```
promptbase/
  __init__.py        # eksport main, APP_VERSION
  constants.py       # THEMES, STATUSES, presety, stałe
  helpers.py         # funkcje czyste (placeholders, daty, n8n, modele)
  models.py          # dataklasa Prompt, PromptStore
  dialogs.py         # *Dialog(Toplevel)
  app.py             # PrompBaseApp
  __main__.py        # main()
```

Zachowaj cienki `promptbase.py` re-eksportujący publiczne API, aby
`import promptbase as pb` (używane w testach) nadal działało.

## Twarde zasady

1. **Stdlib only** w runtime — bez nowych zależności pip (patrz `.cursorrules`).
2. **Nie psuj importu PWA** (`promptLibrary`) ani formatu `promptbase.json`.
3. **UI po polsku**, wersja w `APP_VERSION`.
4. Po KAŻDYM kroku uruchom `python -m pytest` i `python -m ruff check` — muszą być
   zielone, zanim przejdziesz dalej.
5. Jeden krok = jeden spójny moduł. Commit-owalny sam w sobie.

## Kolejność (od najniższego ryzyka)

1. `helpers.py` — funkcje czyste bez zależności od GUI (są już pokryte testami).
2. `constants.py` — słowniki i presety.
3. `models.py` — `Prompt`, `PromptStore`.
4. `dialogs.py` — klasy dialogów.
5. `app.py` — `PrompBaseApp`.
6. `__main__.py` + cienki `promptbase.py`.

## Weryfikacja końcowa

- `python -m pytest` — zielony
- `python -m ruff check` — czysty
- `python -c "import promptbase; print(promptbase.APP_VERSION)"`
- Build EXE nadal działa (`scripts/build_windows.ps1`) — sprawdź, że PyInstaller
  znajduje punkt wejścia.
