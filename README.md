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
- `dist\PrompBase-2.8-Windows.zip` — EXE + landing + docs + `models.json` (do GitHub Releases)

Po rozpakowaniu ZIP: przeczytaj `START.txt`, opcjonalnie `Otworz-landing.bat`.

### Instalator (Setup.exe)

Po zbudowaniu EXE zbuduj instalator (wymaga [Inno Setup](https://jrsoftware.org/isdl.php)):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

Wynik: `dist\PrompBase-2.8-Setup.exe` — instalacja per-user (bez administratora),
skróty w menu Start i opcjonalnie na pulpicie, deinstalator.

## Testy i lint (dla programistów)

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check
```

## Funkcje (v2.8)

### Asystent AI (nowość)

Dwa silniki do wyboru — **OpenRouter** (chmura) i **Ollama** (lokalnie, bez wysyłania danych):

- **Ulepsz prompt** (`Ctrl+Shift+I`) — doprecyzowanie roli, kontekstu i formatu odpowiedzi
- **Przetłumacz** (`Ctrl+Shift+T`) — angielski, polski, niemiecki, hiszpański, francuski
- **Dostosuj do platformy** — ChatGPT, Claude, Gemini, **Midjourney**, Perplexity, Copilot
- Wynik zawsze w oknie podglądu obok oryginału: **Zastąp / Zapisz jako nowy / Anuluj**
- Zmienne `[TEMAT]` są zachowywane; poprzednia treść trafia do historii
- **Menu → Asystent AI → Konfiguracja AI** (wykrywanie modeli Ollamy) i **Status silników**

**Klucz OpenRouter** — dwie drogi (zmienna ma pierwszeństwo):

1. **W ustawieniach**: *Asystent AI → Konfiguracja AI → Klucz OpenRouter* (pole maskowane,
   przyciski „Pokaż” i „Wyczyść”)
2. **Zmienna środowiskowa** `OPENROUTER_API_KEY`

Klucz zapisywany jest w osobnym pliku `openrouter.key` w folderze danych — **nigdy**
w `promptbase.json`, więc nie trafia do kopii zapasowych ani eksportu do Google Drive / OneDrive.

### Biblioteka

- **Ulubione** (`Ctrl+B`) — gwiazdka na liście, filtr „★ Tylko ulubione”, zawsze na górze
- **Wyszukiwarka** — wiele słów naraz (warunek AND) i frazy w cudzysłowie: `"post na blog" seo`;
  przeszukuje nazwę, treść, komentarz, tagi, model i status
- **Wersjonowanie** — historia **20 wersji** z podglądem i przywracaniem
- **Tagowanie** — filtr po tagach + presety
- **Kopiuj i użyj w AI** — główna akcja (Ctrl+Shift+A): kopiowanie + otwarcie ChatGPT/Claude/Gemini/Manus
- Nowy prompt pod `Ctrl+N`; edycja zapisem `Ctrl+Enter`
- Edytowalna lista modeli przez `models.json` (bez przebudowy aplikacji)
- Przewodnik startowy przy pierwszym uruchomieniu + checklista „Pierwsze kroki”
- Motywy: jasny, ciemny, **grafit**
- Edycja, duplikowanie, przypinanie
- Bezpieczny, atomowy zapis + rotacja 5 kopii zapasowych
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
