## PrompBase Python 2.7

Wydanie skupione na **niezawodności, jakości kodu i dystrybucji**. Brak zmian
w formacie danych — biblioteki z 2.6 działają bez migracji.

### Niezawodność danych

- **Rotacja kopii zapasowych** — przy każdym zapisie biblioteki trzymanych jest
  do 5 wersji (`promptbase.json.bak1`…`bak5`) zamiast jednej nadpisywanej.
  Powtórne uszkodzenie danych nie skasuje już jedynej kopii.

### Instalator Windows

- Nowy **instalator** `PrompBase-2.7-Setup.exe` (Inno Setup): instalacja
  per-user bez uprawnień administratora, skróty w menu Start i opcjonalnie na
  pulpicie, wbudowany deinstalator.
- Budowa: `scripts/build_installer.ps1` (po `scripts/build_windows.ps1`).

### Architektura kodu

- Monolit `promptbase.py` (~3000 linii) rozbity na czytelny pakiet **`pbcore/`**:
  - `core` — stałe i funkcje czyste (bez GUI)
  - `models` — `Prompt`, `PromptStore`
  - `dialogs` — okna dialogowe
  - `app` — `PrompBaseApp` i `main()`
- `promptbase.py` to teraz cienki punkt wejścia re-eksportujący publiczne API —
  `import promptbase` oraz `python promptbase.py` działają jak dotychczas.
- Nadal **tylko biblioteka standardowa** w runtime (Tkinter).

### Jakość i testy

- **38 testów `pytest`** dla logiki bez GUI (placeholdery, import PWA/CSV,
  `PromptStore`, rotacja backupów, n8n URL, modele).
- Konfiguracja **`pyproject.toml`** (metadata, `ruff`, `pytest`) — `ruff check`
  bez uwag.
- Automatyzacje Claude Code w `.claude/` (hooki ochrony danych i lintu,
  skill `gen-test`, subagent do refaktoru).

### Paczka dystrybucyjna

`scripts/build_windows.ps1` tworzy:

- `dist/PrompBase.exe`
- `dist/PrompBase-2.7-Windows.zip` (EXE + landing + docs + START.txt + models.json)

`scripts/build_installer.ps1` tworzy dodatkowo:

- `dist/PrompBase-2.7-Setup.exe`

CI (`.github/workflows/build-release.yml`) buduje EXE, paczkę ZIP i instalator.

### Pobierz

https://github.com/zetmar-collab/PrompBase-Python/releases
