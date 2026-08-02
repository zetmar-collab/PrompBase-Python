## PrompBase Python 2.8

Największa aktualizacja funkcjonalna: **wbudowany asystent AI** oraz rozbudowa
biblioteki (ulubione, wyszukiwarka, wersjonowanie). Format danych pozostaje
zgodny — biblioteki z 2.6/2.7 wczytują się bez migracji.

### Asystent AI — dwa silniki

- **OpenRouter** (chmura) — dostęp do Claude, GPT, Gemini, Llama i innych
- **Ollama** (lokalnie) — pełna prywatność, bez wysyłania danych do sieci;
  aplikacja wykrywa zainstalowane modele, a gdy wskazany model nie jest pobrany,
  automatycznie wybiera dostępny

Klucz OpenRouter czytany jest wyłącznie ze zmiennej środowiskowej
`OPENROUTER_API_KEY` — **nie jest zapisywany** w `promptbase.json`.

### Co potrafi AI

- **Ulepsz prompt** (`Ctrl+Shift+I`) — doprecyzowuje rolę, kontekst i format odpowiedzi
- **Przetłumacz** (`Ctrl+Shift+T`) — angielski, polski, niemiecki, hiszpański, francuski
- **Dostosuj do platformy** — ChatGPT, Claude, Gemini, **Midjourney** (prompt obrazowy
  z parametrami `--ar`), Perplexity, Copilot

Każda akcja pokazuje wynik **obok oryginału**, z decyzją: *Zastąp treść*,
*Zapisz jako nowy prompt* albo *Anuluj*. Zmienne w nawiasach (`[TEMAT]`) są
zachowywane, a poprzednia wersja trafia do historii — zmianę da się cofnąć.
Zapytania biegną w tle, więc okno aplikacji nie zamiera.

### Biblioteka

- **Ulubione** (`Ctrl+B`) — kolumna ★, filtr „Tylko ulubione”, ulubione zawsze na górze listy
- **Wyszukiwarka** — wiele słów jednocześnie (warunek AND) oraz frazy w cudzysłowie,
  np. `"post na blog" seo`; przeszukuje nazwę, treść, komentarz, tagi, model i status
- **Wersjonowanie** — historia rozszerzona z 5 do **20 wersji**, z podglądem i przywracaniem
- **Tagowanie** — filtrowanie po tagach wraz z presetami

### Jakość

- **89 testów `pytest`** (z 38), w tym pełne pokrycie warstwy AI bez potrzeby sieci
- `ruff check` bez uwag
- Nowe moduły: `pbcore/ai.py` (silniki) i `pbcore/ai_dialogs.py` (okna AI)
- Runtime nadal **tylko biblioteka standardowa** — HTTP przez `urllib`

### Wymagania

- **Ollama**: zainstaluj z https://ollama.com i pobierz model, np. `ollama pull llama3.2`
- **OpenRouter**: klucz z https://openrouter.ai/keys ustawiony jako zmienna
  środowiskowa `OPENROUTER_API_KEY`

### Paczka dystrybucyjna

- `dist/PrompBase.exe`
- `dist/PrompBase-2.8-Windows.zip` (EXE + landing + docs + START.txt + models.json)
- `dist/PrompBase-2.8-Setup.exe` (instalator per-user)

### Pobierz

https://github.com/zetmar-collab/PrompBase-Python/releases
