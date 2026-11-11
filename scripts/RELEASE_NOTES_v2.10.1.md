## PrompBase Python 2.10.1

Wydanie poprawkowe po 2.10.0 — bezpieczeństwo importu, niezawodność i drobne
poprawki interfejsu. Wszystkie funkcje z 2.10.0 (Excel, sprawdzanie pisowni,
nowy wygląd) bez zmian.

### Bezpieczeństwo

- **Import z PWA pyta o adres webhooka n8n.** Wcześniej adres z pliku był
  ustawiany po cichu w obu trybach importu (zastąp i dopisz). Teraz obie ścieżki
  importu — kopia zapasowa i PWA — pokazują adres i czekają na zgodę.
- **Import XLSX odrzuca dokumenty z deklaracją DTD w każdym kodowaniu.**
  Poprzedni filtr szukał w bajtach napisu `<!DOCTYPE` i omijał go plik w UTF-16.
  Teraz sprawdza to parser, który czyta dokument tak samo jak reszta programu.
- **Limit komórek w arkuszu liczony razem z dopełnieniem.** Plik 1,4 MB potrafił
  zająć ok. 440 MB pamięci; teraz jest odrzucany przy ok. 60 MB.
- Adres komórki spoza zakresu Excela (kolumny do XFD) jest odrzucany —
  spreparowany plik 2 kB nie zawiesza już aplikacji.
- Odpowiedzi HTTP (OpenRouter, Ollama, n8n) mają limit rozmiaru.

### Niezawodność

- **Dziennik błędów** w `%APPDATA%\PrompBase\error.log` — wersja okienkowa nie
  ma konsoli, więc awarie były dotąd niewidoczne.
- Nieudany zapis biblioteki (np. pełny dysk) jest zgłaszany użytkownikowi.
- Import dużego arkusza działa w tle i nie zamraża okna.
- Błędna data w importowanej kopii nie przerywa już całego importu.
- Import pliku wyeksportowanego z programu zapisuje status jako wartość
  kanoniczną — wcześniej taki prompt wysyłał do n8n złą wartość i znikał
  z filtra w interfejsie angielskim.
- Import XLSX czyta pierwszy arkusz według kolejności ze skoroszytu.

### Język i wygląd

- Statusy, formaty, sortowanie i filtr „Wszystkie" są tłumaczone w interfejsie
  angielskim. W pliku i w danych dla n8n zostają wartości kanoniczne.
- Eksport CSV/XLSX używa języka interfejsu; import rozpoznaje oba zapisy.
- Kontrast tekstu i krawędzi pól spełnia WCAG AA we wszystkich motywach.
  Pola wyboru i przełączniki mają większy cel kliknięcia.
- Naprawiono ucinany nagłówek kolumny „Pin".

### Pobieranie

| Co | Plik |
| --- | --- |
| Instalator Windows | `PrompBase-2.10.1-Setup.exe` poniżej |
| Przenośny EXE + ZIP | `PrompBase.exe` / `PrompBase-2.10.1-Windows.zip` poniżej |
| Microsoft Store | https://apps.microsoft.com/store/detail/9NZQZN1XFHPH |
