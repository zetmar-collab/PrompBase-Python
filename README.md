# PrompBase Python

Darmowa lokalna biblioteka promptów AI dla **Windows** i **macOS** (Python + Tkinter).  
Autor: [Marek Zettel](https://github.com/zetmar-collab)

Bez konta, bez serwera — dane zapisują się na Twoim komputerze. Zgodność importu/eksportu z wersją PWA (przeglądarka).

## Pobieranie (Windows)

W [Releases](https://github.com/zetmar-collab/PrompBase-Python/releases) pobierz **PrompBase.exe** — nie wymaga instalacji Pythona.

## Uruchomienie ze źródeł

**Windows**

```bat
Start-PrompBase-Windows.bat
```

**macOS**

```bash
chmod +x Start-PrompBase-macOS.command
./Start-PrompBase-macOS.command
```

**Bezpośrednio**

```bash
python promptbase.py
```

## Budowa EXE (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Wynik: `dist\PrompBase.exe`

## Funkcje (v2.4)

- Biblioteka promptów: dodawanie, edycja, duplikowanie, historia (5 wersji)
- Modele AI: GPT-5.5, Claude Opus 4.7, Gemini 3.5 i inne (lista w aplikacji)
- Szybkie otwieranie: ChatGPT, Claude, Gemini, Perplexity, Copilot
- Tagi i filtry (status, model, zastosowanie, tag)
- Wyszukiwanie z podświetleniem frazy w podglądzie
- Zmienne w promptach `[TEMAT]` — uzupełnianie przy kopiowaniu
- Import/eksport CSV, JSON, **PWA** (localStorage `promptLibrary`)
- **Eksport do chmury** — folder Google Drive / OneDrive (synchronizacja desktop)
- Integracja **n8n** (webhook: test, pojedynczy prompt, sync)
- Tryb jasny / ciemny

## Gdzie są dane

| System  | Ścieżka |
|---------|---------|
| Windows | `%APPDATA%\PrompBase\promptbase.json` |
| macOS   | `~/Library/Application Support/PrompBase/promptbase.json` |
| Linux   | `~/.local/share/PrompBase/promptbase.json` |

## Import z PWA (przeglądarka)

1. F12 → Application → Local Storage → skopiuj `promptLibrary`  
   lub w konsoli: `copy(localStorage.getItem('promptLibrary'))`
2. W aplikacji: **Plik → Import z PWA (przeglądarka)...**

Eksport do PWA: **Plik → Eksport dla PWA** — wklej wartość z powrotem w Local Storage.

## n8n

1. W n8n utwórz workflow z węzłem **Webhook**
2. W PrompBase: **Narzędzia → Konfiguracja n8n** — wklej Production URL
3. **Testuj webhook** → rozgałęzienie po polu `type`: `test` | `single_prompt` | `sync`

## Licencja

Projekt udostępniony publicznie przez autora. Kod źródłowy do użytku osobistego i edukacyjnego.
