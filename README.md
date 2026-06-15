# PrompBase Python

**Przestań szukać promptów w notatkach.** Lokalna biblioteka promptów AI dla **Windows** i **macOS** — znajdź, skopiuj, wklej do ChatGPT lub Claude w kilka sekund.

Autor: [Marek Zettel](https://github.com/zetmar-collab)

Bez konta, bez serwera — dane zapisują się na Twoim komputerze.

## Pobierz (główne CTA)

**[Pobierz PrompBase.exe na Windows](https://github.com/zetmar-collab/PrompBase-Python/releases)** — nie wymaga instalacji Pythona.

Strona produktu (landing): otwórz plik [`landing/index.html`](landing/index.html) w przeglądarce lub w aplikacji: **Pomoc → Strona produktu**.

## Dla kogo

Marketerzy, copywriterzy i twórcy treści, którzy mają **więcej niż kilkanaście promptów** i tracą czas na ich szukanie. Opcjonalnie: programiści i użytkownicy **n8n** (webhook).

## Co zyskujesz

- **Czas** — wyszukiwanie z podświetleniem zamiast przewijania plików
- **Jakość** — te same sprawdzone prompty ze zmiennymi `[TEMAT]`
- **Prywatność** — JSON lokalnie w `%APPDATA%\PrompBase\`

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

## Budowa EXE i paczki ZIP (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Wynik:

- `dist\PrompBase.exe`
- `dist\PrompBase-2.6-Windows.zip` — EXE + landing + docs + `models.json` (do GitHub Releases)

Po rozpakowaniu ZIP: przeczytaj `START.txt`, opcjonalnie `Otworz-landing.bat`.

## Funkcje (v2.6)

- **Kopiuj i użyj w AI** — główna akcja (Ctrl+Shift+A): kopiowanie + otwarcie ChatGPT/Claude/Gemini/Manus
- Nowy prompt pod `Ctrl+N`; edycja zapisem `Ctrl+Enter`
- Obsługa platform AI: ChatGPT, Claude, Gemini, Perplexity, Copilot, **Manus**
- Edytowalna lista modeli przez `models.json` (bez przebudowy aplikacji)
- Przewodnik startowy przy pierwszym uruchomieniu + checklista „Pierwsze kroki”
- Przykładowe prompty: marketing, kod, n8n
- Motywy: jasny, ciemny, **grafit**
- Biblioteka: edycja, duplikowanie, historia (5 wersji), przypinanie
- Bezpieczny, atomowy zapis biblioteki (ochrona przed uszkodzeniem pliku)
- Import/eksport CSV, JSON, **PWA**
- Eksport do Google Drive / OneDrive
- Integracja **n8n**

Pełna lista: zobacz [PRICING.md](PRICING.md) (Free vs plan Pro w przygotowaniu).

## Gdzie są dane

| System  | Ścieżka |
|---------|---------|
| Windows | `%APPDATA%\PrompBase\promptbase.json` |
| macOS   | `~/Library/Application Support/PrompBase/promptbase.json` |
| Linux   | `~/.local/share/PrompBase/promptbase.json` |

## Import z PWA (przeglądarka)

Szczegóły w aplikacji: **Plik → Import z PWA** (instrukcja w oknie dialogowym).

Skrót: F12 → Application → Local Storage → `promptLibrary`, lub w konsoli: `copy(localStorage.getItem('promptLibrary'))`.

## n8n

1. Workflow z węzłem **Webhook**
2. **Narzędzia → Konfiguracja n8n** — Production URL
3. Test / pojedynczy prompt / sync

## Licencja

Projekt udostępniony publicznie. Kod do użytku osobistego i edukacyjnego.
