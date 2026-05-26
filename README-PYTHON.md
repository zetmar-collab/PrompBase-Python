# PrompBase Python v2.0

Autor: Marek Zettel

Lokalna wersja aplikacji PrompBase przepisana z PWA HTML/JavaScript na Python + Tkinter.

## Uruchamianie

Windows:

```bat
Start-PrompBase-Windows.bat
```

Skrót na pulpicie z ikoną Windows:

```powershell
powershell -ExecutionPolicy Bypass -File Create-Windows-Shortcut.ps1
```

macOS:

```bash
chmod +x Start-PrompBase-macOS.command
./Start-PrompBase-macOS.command
```

Bezpośrednio:

```bash
python promptbase.py
```

## Ikony

- Windows: `assets/promptbase.ico`
- macOS: `assets/promptbase.icns`
- PNG pomocnicze: `assets/promptbase-128.png`, `assets/promptbase-256.png`, `assets/promptbase-512.png`

Ikony można odtworzyć poleceniem:

```bash
python generate_icons.py
```

## Dane

Aplikacja zapisuje bibliotekę lokalnie:

- Windows: `%APPDATA%\PrompBase\promptbase.json`
- macOS: `~/Library/Application Support/PrompBase/promptbase.json`
- Linux: `~/.local/share/PrompBase/promptbase.json`

## Przeniesione funkcje

- dodawanie, edycja, usuwanie i podgląd promptów
- pola: nazwa, status, format, model AI, zastosowanie, komentarz, treść
- wyszukiwanie pełnotekstowe
- filtry po statusie, modelu i zastosowaniu
- sortowanie: najnowsze, najstarsze, A -> Z, Z -> A
- przypięte prompty
- kopiowanie promptu do schowka
- import i eksport CSV zgodny z wersją PWA
- konfiguracja webhooka n8n
- wysyłka pojedynczego promptu lub synchronizacja całej biblioteki do n8n
- tryb jasny i ciemny zapisywany w ustawieniach

Wersja Python nie wymaga serwera HTTP, Service Workera ani przeglądarkowego `localStorage`.
