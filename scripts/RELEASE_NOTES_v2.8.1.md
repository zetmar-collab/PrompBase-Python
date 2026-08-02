## PrompBase Python 2.8.1

Uzupełnienie wydania 2.8: **klucz OpenRouter można teraz wpisać bezpośrednio w aplikacji**,
bez ustawiania zmiennej środowiskowej.

### Klucz API w ustawieniach

- **Asystent AI → Konfiguracja AI → Klucz OpenRouter** — pole maskowane,
  z przyciskami „Pokaż” i „Wyczyść”
- Zmienna środowiskowa `OPENROUTER_API_KEY` nadal działa i **ma pierwszeństwo**
  (przydatne, gdy chcesz tymczasowo użyć innego klucza)
- **Status silników AI** pokazuje, skąd pochodzi aktywny klucz

### Bezpieczeństwo

Klucz zapisywany jest w **osobnym pliku** `openrouter.key` w folderze danych —
świadomie **nie** w `promptbase.json`. Ten plik zasila bowiem kopie zapasowe
i eksport do Google Drive / OneDrive, więc klucz wyciekłby razem z nimi.
Test regresyjny pilnuje, żeby klucz nigdy nie pojawił się w kopii zapasowej.

### Jakość

- 97 testów `pytest` (z 89), `ruff` bez uwag

### Pobierz

https://github.com/zetmar-collab/PrompBase-Python/releases
