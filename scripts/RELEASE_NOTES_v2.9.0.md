## PrompBase Python 2.9.0

### Język interfejsu — Polski / English

- **Widok → Język → Polski / English** — nowy przełącznik w menu
- Menu odświeża się natychmiast; pełny efekt na resztę interfejsu (etykiety,
  przyciski, nagłówki listy) po ponownym uruchomieniu aplikacji
- Wybór języka zapisywany w `promptbase.json`
- **Prompty systemowe wysyłane do AI** (Ulepsz prompt, Przetłumacz, Dostosuj
  do platformy) są teraz w tym samym języku co interfejs — model dostaje
  instrukcje po angielsku, gdy UI jest w `English`, zamiast zawsze po polsku
- **Przykładowe prompty** przy pierwszym uruchomieniu / „Załaduj przykłady”
  też zależą od języka
- Świadomy wyjątek: etykiety statusu (Nowy/Osobiste/Praca/Uniwersalne) i
  sentinel filtra „Wszystkie” **nie** są tłumaczone — status trafia też do
  payloadu wysyłanego przez integrację n8n, więc zmiana języka nie może cicho
  zmienić kontraktu danych ani zepsuć filtrowania

### Pakiet MSIX (Microsoft Store)

- Nowy skrypt `scripts/build_msix.ps1` — buduje `dist/PrompBase-2.9.0.msix`
  gotowy do wysyłki w [Partner Center](https://partner.microsoft.com/dashboard)
- Tożsamość pakietu: `MarekZettel-zetmar.PrompBase`
  (publisher: Marek Zettel - zetmar)
- Opcja `-Sign` — podpisuje pakiet lokalnym certyfikatem testowym do
  sideloadingu (do testów, nie do Store — Store podpisuje ponownie)
- CI buduje teraz też `.msix` obok EXE, ZIP i instalatora

### Pobierz

https://github.com/zetmar-collab/PrompBase-Python/releases
