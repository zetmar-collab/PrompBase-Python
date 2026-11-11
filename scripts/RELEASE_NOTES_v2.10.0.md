## PrompBase Python 2.10.0

Trzy nowe rzeczy: arkusze Excela, sprawdzanie pisowni i odświeżony wygląd.

### Import i eksport XLSX (Excel)

`Plik → Import XLSX (Excel)…` wczytuje arkusz z promptami razem z kategoriami,
`Plik → Eksport XLSX (Excel)…` zapisuje całą bibliotekę do `.xlsx`.

- Kolumny rozpoznawane po nazwie, po polsku i po angielsku (`Prompt`, `Treść`,
  `Content`, `Kategoria`, `Zastosowanie`, `Styl`, `Tagi`, `Ikona`, `Numer`,
  `ID`, `Model`…). Kolejność kolumn nie ma znaczenia.
- Gdy arkusz nie ma kolumny „Nazwa”, nazwa promptu składana jest z ikony,
  kategorii i numeru — np. `🌸 Anime – postacie #1`.
- Przed importem widać, które kolumny zostały rozpoznane i ile jest kategorii;
  można dopisać do biblioteki albo ją zastąpić.
- Czytnik i zapis napisane **wyłącznie na bibliotece standardowej** (XLSX to ZIP
  z plikami XML) — aplikacja nadal nie ma żadnych zależności w czasie działania.
- Pliki z deklaracją DTD są odrzucane (ochrona przed bombą encyjną), działają
  też limity rozmiaru po dekompresji i liczby wierszy.

Sprawdzone na prawdziwym arkuszu z 571 wierszami oraz w Microsoft Excel:
emoji, znaki wymagające ucieczki w XML, wielolinijkowe treści i polskie znaki
przechodzą w obie strony bez zmian.

### Sprawdzanie pisowni

Błędy są podkreślane na czerwono podczas tworzenia i edycji promptu,
tak jak w LibreOffice.

- **Prawy przycisk myszy** na podkreślonym słowie: propozycje poprawek,
  „Dodaj do słownika”, „Ignoruj wszędzie”, włącznik i wybór języka.
- Używa **słowników Hunspell** (`.dic` + `.aff`) — tych samych, co LibreOffice,
  Firefox i Thunderbird. Polski i angielski działają od razu, jeśli takie
  słowniki są już w systemie.
- **Inne języki**: „Język pisowni… → Zainstaluj słownik…” i wskazanie pobranego
  pliku `.dic`. Słowniki nie są dołączane do instalatora (licencje) — trafiają
  do `%APPDATA%\PrompBase\dictionaries\`.
- `[ZMIENNE]`, adresy URL i fragmenty w backtickach nie są sprawdzane.
- Słownik wczytywany jest w tle, więc okno edycji otwiera się natychmiast
  nawet przy polskim słowniku (ponad 300 tys. form podstawowych).

### Odświeżony interfejs

- Płaskie kontrolki zamiast trójwymiarowych fazek; krawędzie to teraz włosowe
  ramki, a panele stoją na jasnych „kartach”.
- Spójna skala typograficzna (Segoe UI Variable, jeśli jest w systemie).
- Wyższe wiersze listy i delikatne pasy co drugi wiersz.
- Akcje w panelu podglądu w układzie 4×2 — wcześniej osiem przycisków w jednym
  rzędzie się nie mieściło i napisy były przycinane („Duplik”, „Histori”).
- Szersze okno startowe i kolumny dzielące się dostępnym miejscem, więc
  „Zastosowanie” i „Format” nie są ucinane.
- Wybór motywu (Jasny / Ciemny / Grafit) w jednym rzędzie — „Grafit” nie
  zachodzi już pod przycisk nowego promptu.

### Bezpieczeństwo i niezawodność

- **Import XLSX nie da się już zawiesić** spreparowanym plikiem — adres komórki
  poza zakresem Excela (kolumny do XFD) jest odrzucany. Wcześniej plik o rozmiarze
  2 kB potrafił zamrozić aplikację na stałe.
- **Import kopii zapasowej pyta o adres webhooka n8n** zamiast po cichu
  podmieniać go na adres z pliku.
- Odpowiedzi HTTP (OpenRouter, Ollama, n8n) mają limit rozmiaru.
- **Dziennik błędów** w `%APPDATA%\PrompBase\error.log` — wersja okienkowa nie
  ma konsoli, więc awarie były dotąd niewidoczne. Użytkownik dostaje komunikat
  ze ścieżką do pliku.
- Nieudany zapis biblioteki (np. pełny dysk) jest zgłaszany, a nie ignorowany.
- Import dużego arkusza działa w tle i nie zamraża okna.
- Błędna data w importowanej kopii nie przerywa już całego importu.
- Import pliku wyeksportowanego z programu zapisuje status jako wartość
  kanoniczną (`praca`), a nie etykietę (`Praca`) — wcześniej taki prompt wysyłał
  do n8n złą wartość i znikał z filtra w interfejsie angielskim.
- Import XLSX czyta pierwszy arkusz według kolejności ze skoroszytu.
- Pamięć podręczna słowników jest ograniczona do dwóch pozycji.

### Interfejs i język

- Statusy, formaty, sortowanie i filtr „Wszystkie” są tłumaczone w interfejsie
  angielskim. W pliku i w danych dla n8n zostają wartości kanoniczne.
- Eksport CSV/XLSX używa języka interfejsu; import rozpoznaje oba zapisy.
- Kontrast tekstu i krawędzi pól spełnia WCAG AA we wszystkich trzech motywach
  (stonowany tekst miał 4,44:1, krawędź pola 1,27:1). Pola wyboru i przełączniki
  mają większy cel kliknięcia.

### Pozostałe

- Wczytywanie słowników nie blokuje wątku interfejsu.
- Audyt tłumaczeń wykrywa moduły automatycznie i szuka napisów, które
  w ogóle pominęły `t()`.
- `app.py` rozdzielono na moduły (`app_io`, `app_n8n`, `app_ai`) — bez zmiany
  zachowania.

### Pobieranie

| Co | Plik |
| --- | --- |
| Instalator Windows | `PrompBase-2.10.0-Setup.exe` poniżej |
| Przenośny EXE + ZIP | `PrompBase.exe` / `PrompBase-2.10.0-Windows.zip` poniżej |
| Microsoft Store | https://apps.microsoft.com/store/detail/9NZQZN1XFHPH |
