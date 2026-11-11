# PrompBase Python

[![Microsoft Store](https://img.shields.io/badge/Microsoft%20Store-Pobierz-0078D4?logo=microsoft&logoColor=white)](https://apps.microsoft.com/store/detail/9NZQZN1XFHPH?cid=DevShareMCLPCS)

**Przestań szukać promptów w notatkach.** Lokalna biblioteka promptów AI dla **Windows** i **macOS** — znajdź, skopiuj, wklej do ChatGPT lub Claude w kilka sekund.

Autor: [Marek Zettel](https://github.com/zetmar-collab)

Bez konta, bez serwera — dane zapisują się na Twoim komputerze.

## Pobierz (główne CTA)

**[Zainstaluj z Microsoft Store](https://apps.microsoft.com/store/detail/9NZQZN1XFHPH?cid=DevShareMCLPCS)** — automatyczne aktualizacje, instalacja jednym kliknięciem.

Alternatywnie: **[pobierz instalator lub EXE z GitHub Releases](https://github.com/zetmar-collab/PrompBase-Python/releases)** — nie wymaga instalacji Pythona.

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
- `dist\PrompBase-2.10.0-Windows.zip` — EXE + landing + docs + `models.json` (do GitHub Releases)

Po rozpakowaniu ZIP: przeczytaj `START.txt`, opcjonalnie `Otworz-landing.bat`.

### Instalator (Setup.exe)

Po zbudowaniu EXE zbuduj instalator (wymaga [Inno Setup](https://jrsoftware.org/isdl.php)):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

Wynik: `dist\PrompBase-2.10.0-Setup.exe` — instalacja per-user (bez administratora),
skróty w menu Start i opcjonalnie na pulpicie, deinstalator.

### Pakiet MSIX (Microsoft Store)

Po zbudowaniu EXE zbuduj paczkę `.msix` (wymaga Windows SDK — `makeappx.exe`,
zwykle zainstalowany z Visual Studio lub [samodzielnie](https://aka.ms/windowssdk)):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_msix.ps1
```

Wynik: `dist\PrompBase-2.10.0.msix` — wyślij ten plik w
[Partner Center](https://partner.microsoft.com/dashboard) (Microsoft Store
podpisuje paczkę ponownie przy publikacji, więc lokalny podpis nie jest
wymagany). Tożsamość pakietu: `MarekZettel-zetmar.PrompBase`
(publisher: Marek Zettel - zetmar).

Aby przetestować instalację lokalnie (sideload) przed wysyłką do Store, dodaj
`-Sign` — skrypt utworzy certyfikat testowy i podpisze paczkę:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_msix.ps1 -Sign
```

## Testy i lint (dla programistów)

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check
```

## Funkcje (v2.10.0)

### Import i eksport XLSX (Excel)

- **Plik → Import XLSX (Excel)…** wczytuje arkusz z promptami razem
  z kategoriami; **Plik → Eksport XLSX (Excel)…** zapisuje całą bibliotekę
- Nagłówki rozpoznawane po nazwie (PL i EN): `Prompt`/`Treść`/`Content`,
  `Kategoria`/`Zastosowanie`, `Styl`/`Tagi`, `Ikona`, `Numer`, `ID`, `Model`…
  Kolejność kolumn nie ma znaczenia
- Gdy arkusz nie ma kolumny „Nazwa", nazwa promptu jest składana z ikony,
  kategorii i numeru (`🌸 Anime – postacie #1`), żeby lista była czytelna
- Przed importem aplikacja pokazuje rozpoznane kolumny i liczbę kategorii
- Czytnik i zapis są **w czystej bibliotece standardowej** (XLSX to ZIP + XML),
  bez `openpyxl` — aplikacja nadal nie ma zależności w czasie działania
- Bezpieczeństwo: pliki z deklaracją DTD są odrzucane (ochrona przed bombą
  encyjną, na którą `ElementTree` jest podatny), obowiązują też limity
  rozmiaru po dekompresji i liczby wierszy (ochrona przed zip-bombą)

### Sprawdzanie pisowni

- Błędy podkreślane na czerwono w oknie tworzenia i edycji promptu,
  jak w LibreOffice; **prawy przycisk myszy** daje propozycje poprawek,
  „Dodaj do słownika" i „Ignoruj wszędzie"
- Czyta **słowniki Hunspell** (`.dic` + `.aff`) — te same, których używają
  LibreOffice, Firefox i Thunderbird. Polski i angielski działają od razu,
  jeśli w systemie są już zainstalowane słowniki
- **Inne języki**: prawy przycisk → „Język pisowni…" → „Zainstaluj słownik…"
  i wskazanie pobranego pliku `.dic`. Słowniki nie są dołączane do repozytorium
  ani do instalatora (licencje) — są wyszukiwane w systemie lub dodawane
  przez użytkownika do `%APPDATA%\PrompBase\dictionaries\`
- Pomijane są `[ZMIENNE]`, adresy URL i fragmenty w backtickach — nie są
  podkreślane jako literówki
- Słownik użytkownika (`Dodaj do słownika`) zapisywany trwale;
  wybór języka i włącznik zapamiętywane w `promptbase.json`
- Kodowanie słownika czytane z nagłówka `SET` — prawdziwe słowniki **nie są**
  w UTF-8 (polski to ISO-8859-2), bez tego polskie znaki byłyby zniekształcone

### Odświeżony interfejs

- Płaskie kontrolki zamiast trójwymiarowych fazek motywu `clam`;
  rolę krawędzi przejęły włosowe ramki, panele stoją na jasnych „kartach"
- Spójna skala typograficzna (Segoe UI Variable, gdy jest w systemie)
- Wyższe wiersze listy i delikatne pasy co drugi wiersz
- Akcje w panelu podglądu ułożone 4×2 — wcześniej osiem przycisków w jednym
  rzędzie nie mieściło się i Tk przycinał napisy („Duplik", „Histori")
- Szersze okno startowe i kolumny dzielące się dostępnym miejscem, dzięki
  czemu „Zastosowanie" i „Format" nie są ucinane
- Smukłe paski przewijania, wyraźny stan po najechaniu i fokus na akcencie

### Zgodność z Microsoft Store

Wersja sklepowa (MSIX) automatycznie dostosowuje się do zasad Store:

- **Zgłaszanie treści AI** — każde okno wyniku asystenta AI ma przycisk
  „⚠ Zgłoś treść”, wymagany przez zasadę 11.16 (Live Generative AI Content)
- **Deklaracja generatywnej AI** zaznaczona w Partner Center
- W wersji z Store ukryte są pozycje promujące dystrybucję poza sklepem
  (pobieranie z GitHub, cennik Pro) — zasada 10.1.5; w wersji EXE/instalatorze
  działają normalnie. Wykrywanie przez `is_msix_package()`.

### Język interfejsu

- **Widok → Język → Polski / English** — przełącza menu natychmiast; pełny efekt
  (etykiety, przyciski, nagłówki listy) po ponownym uruchomieniu aplikacji
- Wybór zapisywany w `promptbase.json`
- **Prompty systemowe wysyłane do AI** (ulepszanie, tłumaczenie, dostosowanie do
  platformy) są w tym samym języku co interfejs — po angielsku dla `English`
- **Przykładowe prompty** przy pierwszym uruchomieniu też zależą od języka
- Świadomie **nie** tłumaczone: etykiety statusu (Nowy/Praca/…) — bo zasilają
  też payload wysyłany do n8n, i sentinel filtra „Wszystkie” — zmiana języka
  nie może cicho zmienić kontraktu danych ani zepsuć filtrowania

### Asystent AI

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
