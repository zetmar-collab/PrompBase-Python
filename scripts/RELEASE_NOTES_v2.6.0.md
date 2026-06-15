## PrompBase Python 2.6

### Poprawki i UX

- Skrót **Nowy prompt** tylko na `Ctrl+N` (usunięty przypadkowy goły klawisz `n`)
- `Delete` usuwa prompt wyłącznie z listy — nie podczas pisania w polu wyszukiwania ani w polach edycji
- `Ctrl+Enter` zapisuje prompt w oknie edycji
- Przyciski platform AI (ChatGPT, Claude, Gemini, Perplexity, Copilot, Manus) przeniesione do osobnego, drugiego rzędu pod polem modelu

### Nowy model / platforma

- **Manus** (https://manus.im/app) jako model AI: przycisk w edytorze, pozycja w menu AI oraz automatyczne wykrywanie platformy

### Niezawodność danych

- Atomowy zapis biblioteki (plik tymczasowy + zamiana) — przerwany zapis nie uszkodzi `promptbase.json`
- Jednoprzebiegowa podmiana pól `[TEMAT]`, `[TEKST]` — brak kaskadowych podmian

### Konfiguracja modeli

- Lista modeli czytana z opcjonalnego `models.json` (obok aplikacji) — aktualizacja bez przebudowy; przy braku/uszkodzeniu pliku używana jest lista wbudowana

### Paczka dystrybucyjna

`scripts/build_windows.ps1` tworzy:

- `dist/PrompBase.exe`
- `dist/PrompBase-2.6-Windows.zip` (EXE + landing + docs + START.txt + models.json)

### Pobierz

https://github.com/zetmar-collab/PrompBase-Python/releases
