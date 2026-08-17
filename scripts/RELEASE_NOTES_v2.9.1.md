## PrompBase Python 2.9.1

Poprawki wykryte po instalacji pakietu MSIX z prawdziwą, dużą biblioteką
promptów w trybie English.

### Poprawki tłumaczeń

- 34 brakujące klucze w katalogu i18n (Copy, History, Pin, Sort, Light/Dark/
  Graphite, kroki checklisty „Pierwsze kroki” itd.) — pokazywały się po
  polsku mimo owinięcia w `t()`, bo brakowało wpisu w słowniku
- Kroki checklisty w oknie głównym wcale nie przechodziły przez tłumaczenie
  (druga, zduplikowana kopia tych samych etykiet)
- **Pasek tytułu okna** zawsze pokazywał się po polsku, nawet z zapisanym
  `language=en` — kolejność inicjalizacji ustawiała tytuł przed wczytaniem
  zapisanego języka z `promptbase.json`

### Nowe testy regresyjne

- `tests/test_i18n_coverage.py` — automatyczny audyt: każde wywołanie
  tłumaczenia musi mieć wpis w katalogu
- `tests/test_app_smoke.py` — buduje prawdziwe okno w obu językach,
  łapie regresje kolejności inicjalizacji

### MSIX — rozdzielenie Store / test

- `scripts/build_msix.ps1 -Sign` tworzy teraz **osobny** plik
  `*-Test.msix` do sideloadingu — plik dla Partner Center (`.msix` bez
  `-Test`) **nigdy nie jest podpisywany**, zgodnie z wymaganiami Store
- Podpisywanie używa istniejącego certyfikatu testowego z magazynu
  systemowego zamiast tworzyć nowy przy każdym uruchomieniu

### Pobierz

https://github.com/zetmar-collab/PrompBase-Python/releases
