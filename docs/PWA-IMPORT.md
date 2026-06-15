# Import z PrompBase PWA (przeglądarka)

## Kiedy tego użyć

Masz bibliotekę promptów w **starej wersji przeglądarkowej** i chcesz przenieść ją do aplikacji Windows (EXE).

## Metoda A — konsola (najprostsza)

1. Otwórz PrompBase PWA w **Chrome** lub **Edge** (ta sama strona, na której zapisywałeś prompty).
2. Naciśnij **F12** → zakładka **Console** (Konsola).
3. W aplikacji desktop: **Plik → Import z PWA** → kliknij **Kopiuj polecenie do konsoli**.
4. Wklej w konsoli przeglądarki i naciśnij **Enter**.
5. W konsoli wpisz (jeśli trzeba): `copy(localStorage.getItem('promptLibrary'))` — już skopiowane przez krok 3.
6. Wróć do PrompBase desktop → wklej JSON w duże pole (**Ctrl+V**).
7. Kliknij **Importuj**.

## Metoda B — Local Storage (ręcznie)

1. F12 → **Application** → **Local Storage** → wybierz domenę PrompBase PWA.
2. Znajdź klucz `promptLibrary`.
3. Skopiuj **całą wartość** (długi tekst JSON).
4. Wklej w oknie importu w aplikacji desktop.

## Metoda C — plik JSON

1. W PWA lub z eksportu zapisz plik `.json` (tablica promptów lub pełny eksport).
2. W desktop: **Import z PWA** → **Wczytaj plik JSON...**

## Po imporcie

- Sprawdź liczbę promptów na liście.
- Opcjonalnie: **Plik → Kopia zapasowa JSON** — dodatkowa kopia na dysku.
- Stara wersja PWA może zostać jako archiwum; pracujesz już w pliku `%APPDATA%\PrompBase\promptbase.json`.

## Problemy

| Problem | Rozwiązanie |
|---------|-------------|
| Pusty import | Upewnij się, że kopiujesz klucz `promptLibrary`, nie inny. |
| Błąd JSON | Skopiuj wartość od pierwszego `[` lub `{` do końca. |
| Brak promptów w PWA | Najpierw otwórz stronę PWA, na której były zapisane dane. |

Powrót: [README](../README.md)
