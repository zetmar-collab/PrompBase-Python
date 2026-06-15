# PrompBase Python v2.5

Autor: Marek Zettel

Lokalna biblioteka promptów AI (Python + Tkinter). Główna akcja: **Kopiuj i użyj w AI**.

## Pobieranie (użytkownik końcowy)

[GitHub Releases](https://github.com/zetmar-collab/PrompBase-Python/releases) — plik **PrompBase-{wersja}-Windows.zip** (EXE + landing + dokumentacja).

## Uruchamianie (deweloper)

Windows:

```bat
Start-PrompBase-Windows.bat
```

macOS:

```bash
chmod +x Start-PrompBase-macOS.command
./Start-PrompBase-macOS.command
```

```bash
python promptbase.py
```

## Budowa EXE i paczki ZIP

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Wynik:

- `dist\PrompBase.exe`
- `dist\PrompBase-2.5-Windows\` — folder do dystrybucji (EXE, `landing/`, `docs/`, `START.txt`)
- `dist\PrompBase-2.5-Windows.zip`

## Struktura marketing / docs

| Ścieżka | Opis |
|---------|------|
| `landing/index.html` | Strona produktu (motyw grafit) |
| `docs/QUICKSTART.md` | Szybki start |
| `docs/PWA-IMPORT.md` | Import z przeglądarki |
| `OPIS-NAFFY.md` | Opis na marketplace |
| `PRICING.md` | Free / Pro |

## Ikony

```bash
python generate_icons.py
```

- `assets/promptbase.ico` — Windows / EXE

## Dane użytkownika

- Windows: `%APPDATA%\PrompBase\promptbase.json`
- macOS: `~/Library/Application Support/PrompBase/promptbase.json`

## Funkcje (skrót)

- Onboarding + checklista pierwszych kroków
- Motywy: jasny, ciemny, grafit
- n8n, PWA import, chmura Drive/OneDrive
- Historia 5 wersji, zmienne `[TEMAT]`, wyszukiwanie z podświetleniem

Szczegóły: [README.md](README.md)
