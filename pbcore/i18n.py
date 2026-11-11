"""Lokalizacja PrompBase: polski (domyślny) i angielski.

Kluczem tłumaczenia jest **polski tekst źródłowy**, a `t()` przy braku wpisu
zwraca go bez zmian. Dzięki temu pominięte tłumaczenie pokazuje polski napis
zamiast wywalać aplikację — i można lokalizować przyrostowo.

Język wybiera użytkownik (menu Widok → Język); ustawienie zapisujemy w
promptbase.json. Wpływa też na wewnętrzne prompty systemowe wysyłane do AI
(patrz pbcore/ai.py) — w wersji angielskiej model dostaje instrukcje po
angielsku.
"""

from __future__ import annotations

LANG_PL = "pl"
LANG_EN = "en"

LANGUAGES = {
    LANG_PL: "Polski",
    LANG_EN: "English",
}

DEFAULT_LANGUAGE = LANG_PL

# Bieżący język procesu. Trzymany modułowo, bo napisy pobierają dziesiątki
# miejsc w UI i przekazywanie kontekstu wszędzie byłoby hałasem.
_current = DEFAULT_LANGUAGE


def set_language(lang: str) -> str:
    """Ustawia język; nieznana wartość cofa do domyślnego."""
    global _current
    _current = lang if lang in LANGUAGES else DEFAULT_LANGUAGE
    return _current


def get_language() -> str:
    return _current


def is_english() -> bool:
    return _current == LANG_EN


def language_label(lang: str) -> str:
    return LANGUAGES.get(lang, LANGUAGES[DEFAULT_LANGUAGE])


# --- katalog tłumaczeń: polski tekst źródłowy -> angielski ------------------

_EN: dict[str, str] = {
    # --- menu główne -------------------------------------------------------
    "Plik": "File",
    "Edycja": "Edit",
    "Widok": "View",
    "Narzędzia": "Tools",
    "Pomoc": "Help",
    "Asystent AI": "AI assistant",
    "Język": "Language",
    "Nowy prompt": "New prompt",
    "Import CSV...": "Import CSV...",
    "Import XLSX (Excel)...": "Import XLSX (Excel)...",
    "Eksport XLSX (Excel)...": "Export XLSX (Excel)...",
    "Import XLSX": "Import XLSX",
    "Eksport XLSX": "Export XLSX",
    "Import CSV, XLSX lub JSON": "Import CSV, XLSX or JSON",
    "CSV, XLSX i JSON": "CSV, XLSX and JSON",
    "Obsługiwane rozszerzenia: .csv, .xlsx, .json": "Supported extensions: .csv, .xlsx, .json",
    "Rozpoznane kolumny: ": "Recognised columns: ",
    "Kategorie: ": "Categories: ",
    " promptów z XLSX.": " prompts from XLSX.",
    "\n\nTak = dopisz\nNie = zastąp bibliotekę\nAnuluj": (
        "\n\nYes = append\nNo = replace the library\nCancel"
    ),
    "Import z PWA (przeglądarka)...": "Import from PWA (browser)...",
    "Instrukcja importu PWA": "PWA import guide",
    "Eksport CSV...": "Export CSV...",
    "Kopia zapasowa JSON...": "JSON backup...",
    "Przywróć z JSON...": "Restore from JSON...",
    "Eksport dla PWA (przeglądarka)...": "Export for PWA (browser)...",
    "Eksport do chmury (Drive / OneDrive)...": "Export to cloud (Drive / OneDrive)...",
    "Szybki import pliku CSV/JSON...": "Quick import CSV/JSON file...",
    "Pokaż plik danych": "Show data file",
    "Otwórz folder danych": "Open data folder",
    "Zakończ": "Exit",
    "Ulepsz prompt": "Improve prompt",
    "Przetłumacz prompt": "Translate prompt",
    "Dostosuj do platformy": "Adapt to platform",
    "Konfiguracja AI...": "AI configuration...",
    "Status silników AI": "AI engine status",
    "Konfiguracja n8n...": "n8n configuration...",
    "Testuj webhook n8n": "Test n8n webhook",
    "Wyślij zaznaczony do n8n": "Send selected to n8n",
    "Synchronizuj bibliotekę do n8n": "Sync library to n8n",
    "Eksportuj JSON dla n8n...": "Export JSON for n8n...",
    "Paczki promptów Pro (wkrótce)...": "Pro prompt packs (coming soon)...",
    "Tryb jasny": "Light theme",
    "Tryb ciemny": "Dark theme",
    "Motyw grafit": "Graphite theme",
    "Przewodnik startowy": "Getting started guide",
    "Szybki start (PDF/MD)": "Quick start (PDF/MD)",
    "Pomoc i skróty": "Help and shortcuts",
    "Strona produktu": "Product page",
    "Pobierz najnowszą wersję": "Download latest version",
    "Cennik (Free / Pro)": "Pricing (Free / Pro)",
    # --- główne okno -------------------------------------------------------
    " - Biblioteka Promptów AI": " - AI Prompt Library",
    "Znajdź prompt · skopiuj · wklej do AI": "Find a prompt · copy · paste into AI",
    "+ Nowy Prompt": "+ New Prompt",
    "Szukaj": "Search",
    "Wyczyść filtry": "Clear filters",
    "Przypięte": "Pinned",
    "Otwórz przypięty": "Open pinned",
    "★ Tylko ulubione": "★ Favourites only",
    "★ Ulubiony": "★ Favourite",
    "Kopiuj i użyj w AI": "Copy and use in AI",
    "Załaduj przykłady": "Load examples",
    "Usuń": "Delete",
    "Edytuj": "Edit",
    "Duplikuj": "Duplicate",
    "Historia wersji": "Version history",
    "Podgląd": "Preview",
    "Treść": "Content",
    "Wybierz prompt": "Select a prompt",
    "Wybierz prompt z listy": "Select a prompt from the list",
    "Pierwsze kroki": "First steps",
    "Import pliku": "Import file",
    "Kliknij, aby wczytać\nCSV lub JSON": "Click to load\nCSV or JSON",
    "Obsługiwane rozszerzenia: .csv, .json": "Supported extensions: .csv, .json",
    "Biblioteka jest pusta.\nDodaj pierwszy prompt lub załaduj gotowe przykłady.": (
        "Your library is empty.\nAdd your first prompt or load the ready-made examples."
    ),
    "Wybierz prompt z listy po lewej, potem użyj „Kopiuj i użyj w AI”.": (
        'Select a prompt on the left, then use "Copy and use in AI".'
    ),
    "Kliknij wiersz po lewej lub użyj „Kopiuj i użyj w AI”.": (
        'Click a row on the left or use "Copy and use in AI".'
    ),
    "Brak promptów": "No prompts",
    "bez tagów": "no tags",
    "bez modelu": "no model",
    "bez kategorii": "no category",
    "Segoe UI": "Segoe UI",
    # --- przyciski AI ------------------------------------------------------
    "✨ Ulepsz": "✨ Improve",
    "🌐 Przetłumacz": "🌐 Translate",
    "🎯 Dostosuj…": "🎯 Adapt…",
    "AI z modelu ↗": "AI from model ↗",
    "Otwórz ": "Open ",
    "Kopiuj prompt i otwórz ": "Copy prompt and open ",
    "Dostosuj do ": "Adapt to ",
    # --- statusy / komunikaty ---------------------------------------------
    "Prompt zapisany.": "Prompt saved.",
    "Prompt zaktualizowany.": "Prompt updated.",
    "Prompt usunięty.": "Prompt deleted.",
    "Prompt skopiowany do schowka.": "Prompt copied to clipboard.",
    "Skopiowano prompt z metadanymi.": "Prompt with metadata copied.",
    "Przypięto prompt.": "Prompt pinned.",
    "Odpięto prompt.": "Prompt unpinned.",
    "Dodano do ulubionych.": "Added to favourites.",
    "Usunięto z ulubionych.": "Removed from favourites.",
    "Najpierw wybierz prompt z listy.": "Select a prompt from the list first.",
    "Ten prompt nie ma treści.": "This prompt has no content.",
    "Załadowano przykładowe prompty.": "Example prompts loaded.",
    "Biblioteka jest pusta.": "The library is empty.",
    "Brak promptów do eksportu.": "No prompts to export.",
    "Otwarto stronę pobrań.": "Downloads page opened.",
    "Otwarto instrukcję importu PWA.": "PWA import guide opened.",
    "Otwarto szybki start.": "Quick start opened.",
    "Otwarto cennik.": "Pricing opened.",
    "Otwarto stronę produktu (landing).": "Product page (landing) opened.",
    "Otwarto dokumentację na GitHub.": "Documentation opened on GitHub.",
    "Otwarto dokumentację online.": "Online documentation opened.",
    "Otwarto folder: ": "Folder opened: ",
    "Eksport dla PWA — skopiowano do schowka.": "PWA export — copied to clipboard.",
    "Motyw zmieniony: ": "Theme changed: ",
    # --- zgłaszanie treści AI (Microsoft Store 11.16) ----------------------
    "⚠ Zgłoś problem": "⚠ Report an issue",
    "Zgłoś nieodpowiednią treść": "Report inappropriate content",
    "Zgłoś treść wygenerowaną przez AI, która jest nieodpowiednia, szkodliwa lub błędna. Zgłoszenie zapisujemy lokalnie na Twoim komputerze — możesz je potem wysłać do autora aplikacji.": (
        "Report AI-generated content that is inappropriate, harmful or incorrect. "
        "The report is saved locally on your computer — you can then send it to "
        "the app author."
    ),
    "Rodzaj problemu": "Type of issue",
    "Opis (opcjonalnie)": "Description (optional)",
    "Zapisz zgłoszenie": "Save report",
    "Treść obraźliwa lub nienawistna": "Offensive or hateful content",
    "Treść seksualna lub nieodpowiednia dla nieletnich": "Sexual content or content unsuitable for minors",
    "Przemoc lub niebezpieczne instrukcje": "Violence or dangerous instructions",
    "Nieprawdziwe lub wprowadzające w błąd informacje": "False or misleading information",
    "Naruszenie prywatności lub praw autorskich": "Privacy or copyright violation",
    "Inny problem": "Other issue",
    "Nie udało się zapisać zgłoszenia:\n": "Could not save the report:\n",
    "Zgłoszenie zapisane lokalnie:\n": "Report saved locally:\n",
    "\n\nCzy chcesz teraz otworzyć stronę zgłoszeń GitHub, aby przesłać je autorowi aplikacji?": (
        "\n\nWould you like to open the GitHub issues page now to send it to the app author?"
    ),
    "Język zmieniony. Uruchom ponownie PrompBase, aby zastosować zmianę we wszystkich oknach.": (
        "Language changed. Restart PrompBase to apply the change everywhere."
    ),
    "Wyświetlono ": "Showing ",
    " promptów": " prompts",
    " promptów.": " prompts.",
    " promptów | ": " prompts | ",
    " modeli | ": " models | ",
    " przypiętych | dziś dodano: ": " pinned | added today: ",
    " | Format: ": " | Format: ",
    " | Model: ": " | Model: ",
    " | tagi: ": " | tags: ",
    " | Zapis: ": " | Saved: ",
    "Skopiowano „": 'Copied "',
    "” i otwarto ": '" and opened ',
    "Utworzono kopię: „": 'Copy created: "',
    "Zaimportowano z pliku: ": "Imported from file: ",
    "Przywrócono ": "Restored ",
    " promptów z kopii zapasowej.": " prompts from backup.",
    "Eksport gotowy: ": "Export ready: ",
    "Kopia zapasowa zapisana: ": "Backup saved: ",
    "Eksport chmury: ": "Cloud export: ",
    # --- dialogi / tytuły --------------------------------------------------
    "Edytuj prompt": "Edit prompt",
    "Uzupełnij zmienne": "Fill in variables",
    "Uzupełnij zmienne przed kopiowaniem": "Fill in variables before copying",
    "Uzupełnij zmienne w treści": "Fill in variables in the content",
    "Kopiuj uzupełniony": "Copy filled in",
    "Zapisz": "Save",
    "Anuluj": "Cancel",
    "Zamknij": "Close",
    "Dalej": "Next",
    "Wstecz": "Back",
    "Nazwa": "Name",
    "Status": "Status",
    "Data": "Date",
    "Format": "Format",
    "Model AI": "AI model",
    "Zastosowanie": "Use case",
    "Tagi": "Tags",
    "(po przecinku)": "(comma separated)",
    "Komentarz": "Comment",
    "Eksport do chmury": "Export to cloud",
    "Folder synchronizacji": "Sync folder",
    "Eksportuj teraz": "Export now",
    "Przeglądaj...": "Browse...",
    "Plik zostanie zapisany w: ": "The file will be saved in: ",
    "Wybierz folder Google Drive / OneDrive": "Select Google Drive / OneDrive folder",
    "Wybierz folder synchronizacji chmury.": "Select a cloud sync folder.",
    "Podany folder nie istnieje.": "The specified folder does not exist.",
    "Nie wykryto folderu — wybierz ręcznie katalog synchronizacji.": (
        "No folder detected — pick the sync directory manually."
    ),
    "Zapisano w chmurze (folder synchronizacji):\n\n": "Saved to cloud (sync folder):\n\n",
    "Zapisano też plik:\n": "Also saved file:\n",
    "Historia — ": "History — ",
    "Wersje (najnowsza na górze):": "Versions (newest first):",
    "Przywróć zaznaczoną": "Restore selected",
    "Wybierz wersję do przywrócenia.": "Select a version to restore.",
    "Brak zapisanych wersji.\nHistoria powstaje przy każdej edycji promptu (do 5 wersji).": (
        "No saved versions.\nHistory is created on every prompt edit (up to 5 versions)."
    ),
    "Przywrócić wersję z ": "Restore the version from ",
    "?\nObecna treść zostanie zapisana w historii.": (
        "?\nThe current content will be saved to history."
    ),
    "Przywrócono wersję promptu „": 'Restored prompt version "',
    "Podaj nazwę promptu.": "Enter a prompt name.",
    "Wklej treść promptu.": "Paste the prompt content.",
    "Uzupełnij pola: ": "Fill in the fields: ",
    "Usunąć prompt „": 'Delete prompt "',
    "Zastąpić obecną bibliotekę przykładowymi promptami?\nObecne wpisy zostaną usunięte.": (
        "Replace the current library with example prompts?\nExisting entries will be removed."
    ),
    # --- onboarding --------------------------------------------------------
    "Witaj w PrompBase": "Welcome to PrompBase",
    "Twoja biblioteka promptów AI — lokalnie na dysku, bez konta i bez chmury.\n\nZa chwilę skopiujesz gotowy przykład i wkleisz go do ChatGPT lub Claude. To zajmie około 30 sekund.": (
        "Your AI prompt library — stored locally, no account and no cloud.\n\n"
        "In a moment you will copy a ready-made example and paste it into ChatGPT "
        "or Claude. It takes about 30 seconds."
    ),
    "Krok 1: wybierz prompt": "Step 1: pick a prompt",
    "Po lewej zobaczysz przykłady (marketing, kod, n8n).\n\nKliknij wiersz na liście — treść pojawi się w podglądzie po prawej.": (
        "On the left you will see examples (marketing, code, n8n).\n\n"
        "Click a row in the list — the content appears in the preview on the right."
    ),
    "Krok 2: Kopiuj i użyj w AI": "Step 2: Copy and use in AI",
    "Użyj dużego przycisku „Kopiuj i użyj w AI”.\n\nAplikacja skopiuje treść (z uzupełnieniem pól [TEMAT] jeśli trzeba) i otworzy sugerowaną platformę w przeglądarce.": (
        'Use the big "Copy and use in AI" button.\n\nThe app copies the content '
        "(filling in fields such as [TEMAT] when needed) and opens the suggested "
        "platform in your browser."
    ),
    "Gotowe — Twoja kolej": "All set — your turn",
    "Import CSV i eksport są w menu Plik.\nPomoc: klawisz ? lub menu Pomoc.\n\nDodaj własny prompt przyciskiem „+ Nowy Prompt”.": (
        "CSV import and export live in the File menu.\nHelp: the ? key or the Help menu.\n\n"
        'Add your own prompt with the "+ New Prompt" button.'
    ),
    # --- import / eksport --------------------------------------------------
    "Import z PrompBase PWA": "Import from PrompBase PWA",
    "Import CSV lub JSON": "Import CSV or JSON",
    "Import CSV": "Import CSV",
    "Eksport CSV": "Export CSV",
    "Eksport dla PWA": "Export for PWA",
    "Kopia zapasowa JSON": "JSON backup",
    "Przywróć z JSON": "Restore from JSON",
    "CSV i JSON": "CSV and JSON",
    "Wszystkie pliki": "All files",
    # Import kopii zapasowej
    'Plik zawiera adres webhooka n8n:\n\n': 'The file contains an n8n webhook address:\n\n',
    '\n\nPrompty wysyłane do n8n trafią pod ten adres.\nUstawić go?': '\n\nPrompts sent to n8n will go to this address.\nUse it?',
    # Blok kopiowany do schowka / podglad historii
    'Status: ': 'Status: ',
    'Zastosowanie: ': 'Use case: ',
    # Praca w tle
    'Wczytuję arkusz…': 'Loading the spreadsheet…',
    'Import przerwany.': 'Import stopped.',
    'Operacja nie powiodła się.': 'The operation failed.',
    # Nieudany zapis biblioteki
    'Nie udało się zapisać biblioteki:\n\n': 'Could not save your library:\n\n',
    '\n\nZmiana działa tylko do zamknięcia programu. Zwolnij miejsce na dysku lub zamknij program blokujący plik i zapisz ponownie.': '\n\nThe change lasts only until you close the app. Free up disk space or close the program locking the file, then save again.',
    'BŁĄD: nie udało się zapisać biblioteki.': 'ERROR: the library was not saved.',
    # Dziennik błędów
    'Wystąpił nieoczekiwany błąd:\n\n': 'An unexpected error occurred:\n\n',
    '\n\nSzczegóły zapisano w pliku:\n': '\n\nDetails were saved to:\n',
    # Sprawdzanie pisowni (Hunspell)
    'Język pisowni': 'Spelling language',
    'Język pisowni…': 'Spelling language…',
    'Wybierz język sprawdzania pisowni:': 'Choose the spell checking language:',
    'Słowniki w formacie Hunspell (.dic + .aff), takie jak w LibreOffice.': 'Hunspell dictionaries (.dic + .aff), the same as in LibreOffice.',
    'Zainstaluj słownik…': 'Install dictionary…',
    'Zainstalowano słownik: ': 'Dictionary installed: ',
    'Wybierz plik słownika (.dic)': 'Select a dictionary file (.dic)',
    'Słownik Hunspell': 'Hunspell dictionary',
    'Wybierz': 'Select',
    '(bez sprawdzania)': '(no spell checking)',
    '(brak propozycji)': '(no suggestions)',
    'Dodaj do słownika': 'Add to dictionary',
    'Ignoruj wszędzie': 'Ignore everywhere',
    'Sprawdzanie pisowni: wyłącz': 'Spell checking: turn off',
    'Sprawdzanie pisowni: włącz': 'Spell checking: turn on',
    "Brak poprawnych promptów w pliku.": "No valid prompts in the file.",
    "W kopii nie ma poprawnych promptów.": "The backup contains no valid prompts.",
    "Nie znaleziono poprawnych promptów w CSV.": "No valid prompts found in the CSV.",
    "Nie znaleziono poprawnych promptów w danych PWA.": "No valid prompts found in the PWA data.",
    "Nieprawidłowy format kopii zapasowej.": "Invalid backup format.",
    "Nie można wczytać pliku JSON:\n": "Cannot load the JSON file:\n",
    "Nie można odczytać pliku:\n": "Cannot read the file:\n",
    "Nieprawidłowy JSON:\n": "Invalid JSON:\n",
    "Błąd JSON:\n": "JSON error:\n",
    "Wklej dane z localStorage lub wczytaj plik JSON.": (
        "Paste data from localStorage or load a JSON file."
    ),
    "Wybierz eksport PWA": "Select PWA export",
    "Kopiuj polecenie do konsoli": "Copy console command",
    "Wczytaj plik JSON...": "Load JSON file...",
    "Pełna instrukcja": "Full guide",
    "Importuj": "Import",
    # --- n8n ---------------------------------------------------------------
    "Konfiguracja n8n": "n8n configuration",
    "Konfiguracja n8n zapisana.": "n8n configuration saved.",
    "Test webhooka n8n zakończony pomyślnie.": "n8n webhook test finished successfully.",
    "Testuj": "Test",
    "Podaj poprawny URL webhooka przed testem.": "Enter a valid webhook URL before testing.",
    "Test wymaga uruchomionej aplikacji PrompBase.": "The test requires PrompBase to be running.",
    "Przykład: https://twoja-instancja.app.n8n.cloud/webhook/prompbase": (
        "Example: https://your-instance.app.n8n.cloud/webhook/prompbase"
    ),
    "✓ Adres wygląda poprawnie (http/https + /webhook/).": (
        "✓ The address looks correct (http/https + /webhook/)."
    ),
    "✗ Wymagany pełny URL z fragmentem /webhook/ w ścieżce.": (
        "✗ A full URL containing /webhook/ in the path is required."
    ),
    "Brak przypiętych promptów do synchronizacji.": "No pinned prompts to sync.",
    "Zaznacz prompt na liście, który chcesz wysłać do n8n.": (
        "Select the prompt you want to send to n8n."
    ),
    "Wysłano „": 'Sent "',
    "” do n8n.": '" to n8n.',
    "Synchronizacja OK: ": "Sync OK: ",
    "Eksport JSON dla n8n": "JSON export for n8n",
    "Zapisano JSON dla n8n: ": "JSON for n8n saved: ",
    "Błąd połączenia z n8n.": "n8n connection error.",
    "Timeout połączenia z n8n.": "n8n connection timeout.",
    "Błąd n8n: HTTP ": "n8n error: HTTP ",
    "n8n zwrócił błąd HTTP ": "n8n returned HTTP error ",
    "n8n zwrócił nieoczekiwany status HTTP ": "n8n returned an unexpected HTTP status ",
    "Nie udało się połączyć z n8n:\n": "Could not connect to n8n:\n",
    " — odpowiedź: ": " — response: ",
    "Nie udało się otworzyć folderu:\n": "Could not open the folder:\n",
    # --- AI: konfiguracja i wynik -----------------------------------------
    "Konfiguracja AI": "AI configuration",
    "Silnik AI": "AI engine",
    "Model OpenRouter": "OpenRouter model",
    "Klucz OpenRouter": "OpenRouter key",
    "Pokaż": "Show",
    "Wyczyść": "Clear",
    "Host Ollama": "Ollama host",
    "Model Ollama": "Ollama model",
    "Wykryj modele Ollama": "Detect Ollama models",
    "Język tłumaczeń": "Translation language",
    "Oryginał": "Original",
    "Wynik AI": "AI result",
    "Zastąp treść": "Replace content",
    "Zapisz jako nowy": "Save as new",
    "Pracuję… to może potrwać kilkanaście sekund.": "Working… this may take a few seconds.",
    "Wysyłam zapytanie do modelu…": "Sending the request to the model…",
    "Gotowe. Wybierz, co zrobić z wynikiem.": "Done. Choose what to do with the result.",
    "Nie udało się wykonać akcji.": "The action could not be completed.",
    "Nieoczekiwany błąd: ": "Unexpected error: ",
    "Znaleziono modeli: ": "Models found: ",
    "Nie znaleziono modeli. Sprawdź, czy Ollama jest uruchomiona, a następnie pobierz model, np. w terminalu:\n\n    ollama pull llama3.1": (
        "No models found. Check that Ollama is running, then pull a model, e.g. in a terminal:"
        "\n\n    ollama pull llama3.1"
    ),
    "Aktywny silnik: ": "Active engine: ",
    "  Klucz API: ": "  API key: ",
    "  Dostępne: ": "  Available: ",
    "wykryty (zmienna ": "detected (variable ",
    "wykryty (ustawienia: ": "detected (settings: ",
    "wykryty ze zmiennej ": "detected from variable ",
    " (ma pierwszeństwo)": " (takes precedence)",
    "zapisany w ustawieniach": "saved in settings",
    "BRAK — wpisz go w Konfiguracja AI": "MISSING — enter it in AI configuration",
    "BRAK": "MISSING",
    "działa — modeli: ": "running — models: ",
    "brak odpowiedzi": "no response",
    "Wskazówka: ": "Hint: ",
    "Tłumaczenie ": "Translation ",
    ": treść zaktualizowana (poprzednia wersja w historii).": (
        ": content updated (previous version kept in history)."
    ),
    ": zapisano jako nowy prompt.": ": saved as a new prompt.",
    "Zapisano konfigurację AI (": "AI configuration saved (",
    "Ollama — działa lokalnie, bez klucza i bez wysyłania danych do sieci. Upewnij się, że aplikacja Ollama jest uruchomiona, i wybierz zainstalowany model (przycisk „Wykryj modele Ollama”).": (
        "Ollama — runs locally, with no key and without sending data over the network. "
        "Make sure the Ollama app is running and pick an installed model "
        '(the "Detect Ollama models" button).'
    ),
    "OpenRouter — klucz API: ": "OpenRouter — API key: ",
    ".\nKlucz możesz wpisać powyżej (zapisujemy go w osobnym pliku ": (
        ".\nYou can enter the key above (we store it in a separate file "
    ),
    " w folderze danych, poza promptbase.json — dzięki temu nie trafia do kopii zapasowych ani eksportu do chmury).\nAlternatywnie ustaw zmienną środowiskową ": (
        " in the data folder, outside promptbase.json — so it never lands in backups "
        "or cloud exports).\nAlternatively set the environment variable "
    ),
    ". Klucz zdobędziesz na https://openrouter.ai/keys": (
        ". You can get a key at https://openrouter.ai/keys"
    ),
    # --- pozostałe ---------------------------------------------------------
    "PrompBase - pomoc": "PrompBase - help",
    "PrompBase — szybki start": "PrompBase — quick start",
    "Plik danych:\n": "Data file:\n",
    "\n\nOstatnia kopia automatyczna:\n": "\n\nLatest automatic backup:\n",
    "\nStrona produktu: ": "\nProduct page: ",
    "Zaznacz prompt, aby zobaczyć historię wersji.": "Select a prompt to see its version history.",
    "Zaznacz prompt, aby otworzyć sugerowaną platformę AI.": (
        "Select a prompt to open the suggested AI platform."
    ),
    "Nie rozpoznano platformy dla modelu „": 'No platform recognised for the model "',
    "”.\nUżyj przycisków ChatGPT, Claude lub Gemini.": (
        '".\nUse the ChatGPT, Claude or Gemini buttons.'
    ),
    "Brak zaznaczonego promptu. Otwieram ": "No prompt selected. Opening ",
    " bez kopiowania treści.": " without copying content.",
    " w przeglądarce.": " in the browser.",
    "Payload ma ok. ": "The payload is about ",
    " KB (": " KB (",
    " promptów). Kontynuować wysyłkę?": " prompts). Continue sending?",
    "Przekroczono limit czasu (": "Timed out after (",
    "s). Sprawdź URL i czy workflow n8n jest aktywny.": (
        "s). Check the URL and whether the n8n workflow is active."
    ),
    "Skopiowano do schowka:\n\n": "Copied to clipboard:\n\n",
    "\n\nWklej w konsoli przeglądarki (F12) i naciśnij Enter.\nPotem wklej wynik w pole poniżej.": (
        "\n\nPaste it into the browser console (F12) and press Enter.\n"
        "Then paste the result into the field below."
    ),
    "Masz bibliotekę w starej wersji przeglądarkowej (PWA)?\n\n1. Otwórz PrompBase w Chrome lub Edge.\n2. Naciśnij F12 → zakładka Console (Konsola).\n3. Kliknij „Kopiuj polecenie” poniżej, wklej w konsoli Enter.\n4. Wklej skopiowany JSON tutaj (Ctrl+V) lub wczytaj plik .json.": (
        "Do you have a library in the old browser version (PWA)?\n\n"
        "1. Open PrompBase in Chrome or Edge.\n"
        "2. Press F12 → the Console tab.\n"
        '3. Click "Copy console command" below, paste it in the console and press Enter.\n'
        "4. Paste the copied JSON here (Ctrl+V) or load a .json file."
    ),
    "Skopiowano JSON do schowka.\n\nW przeglądarce (F12 → Application → Local Storage):\nwklej jako wartość klucza „promptLibrary”\n\n": (
        "JSON copied to clipboard.\n\nIn the browser (F12 → Application → Local Storage):\n"
        'paste it as the value of the "promptLibrary" key\n\n'
    ),
    "Prompt zawiera pola w nawiasach [TEMAT], [TEKST] itd.\nUzupełnij je przed skopiowaniem:": (
        "The prompt contains bracketed fields such as [TEMAT], [TEKST].\n"
        "Fill them in before copying:"
    ),
    "URL webhooka n8n (węzeł Webhook → Production URL):": (
        "n8n webhook URL (Webhook node → Production URL):"
    ),
    "Kopia trafia do folderu synchronizowanego z chmurą\n(podfolder ": (
        "The copy goes to a cloud-synced folder\n(subfolder "
    ),
    "/). Wymagany Google Drive Desktop lub OneDrive.": (
        "/). Google Drive Desktop or OneDrive is required."
    ),
    "Nieprawidłowy URL webhooka.\n\nUżyj adresu Production URL z węzła Webhook w n8n.": (
        "Invalid webhook URL.\n\nUse the Production URL from the Webhook node in n8n."
    ),
    "Nieprawidłowy URL webhooka.\n\nAdres musi zaczynać się od http:// lub https:// i zawierać ścieżkę /webhook/ (np. https://twoja-instancja.app.n8n.cloud/webhook/prompbase).": (
        "Invalid webhook URL.\n\nThe address must start with http:// or https:// and contain "
        "the /webhook/ path (e.g. https://your-instance.app.n8n.cloud/webhook/prompbase)."
    ),
    "Test połączenia z Biblioteki Promptów AI (PrompBase Python)": (
        "Connection test from the AI Prompt Library (PrompBase Python)"
    ),
    "Tak = dopisz nowe prompty\nNie = zastąp całą bibliotekę\nAnuluj = przerwij import": (
        "Yes = append new prompts\nNo = replace the whole library\nCancel = abort import"
    ),
    " promptów.\n\nTak = dopisz\nNie = zastąp bibliotekę\nAnuluj": (
        " prompts.\n\nYes = append\nNo = replace the library\nCancel"
    ),
    " promptów z PWA.\n\nTak = dopisz do biblioteki\nNie = zastąp całą bibliotekę\nAnuluj": (
        " prompts from PWA.\n\nYes = append to the library\nNo = replace the whole library\nCancel"
    ),
    " promptów.\n\nTak = dopisz do biblioteki\nNie = zastąp całą bibliotekę (i ustawienia z pliku)\nAnuluj": (
        " prompts.\n\nYes = append to the library\nNo = replace the whole library "
        "(and settings from the file)\nCancel"
    ),
    " promptów z PWA.": " prompts from PWA.",
    " promptów. Pominięto duplikatów: ": " prompts. Duplicates skipped: ",
    "Co wysłać do n8n?\n\nTak — cała biblioteka\nNie — tylko przypięte prompty\nAnuluj — przerwij": (
        "What should be sent to n8n?\n\nYes — the whole library\nNo — pinned prompts only\n"
        "Cancel — abort"
    ),
    "Zapis JSON dla n8n:\n\nTak — cała biblioteka\nNie — tylko przypięte\nAnuluj": (
        "JSON export for n8n:\n\nYes — the whole library\nNo — pinned only\nCancel"
    ),
    "Paczki promptów Pro — w przygotowaniu\n\nPlan obejmuje gotowe zestawy (marketing, kod, automatyzacja) bez wymuszania konta w chmurze.\n\nWersja Free zawiera pełną bibliotekę i wszystkie funkcje aplikacji.\nSzczegóły: ": (
        "Pro prompt packs — in preparation\n\nThe plan includes ready-made sets (marketing, "
        "code, automation) without forcing a cloud account.\n\nThe Free version contains the "
        "full library and all app features.\nDetails: "
    ),
    "PrompBase v": "PrompBase v",
    "\nAutor: ": "\nAuthor: ",
    "\nDokumentacja: ": "\nDocs: ",
    "\nPobierz: ": "\nDownload: ",
    "\n\nGłówna akcja: „Kopiuj i użyj w AI” — kopiuje prompt i otwiera platformę.\nPrzewodnik startowy: menu Pomoc.\n\nSkróty:\nCtrl+N - nowy prompt\nCtrl+D - duplikuj prompt\nCtrl+Enter - edytuj zaznaczony\nCtrl+Shift+A - kopiuj i użyj w AI (główna akcja)\nCtrl+Shift+C - kopiuj z metadanymi\n/ lub Ctrl+F - wyszukiwanie\nDelete - usuń zaznaczony\nCtrl+I - import CSV\nCtrl+E - eksport CSV\nCtrl+Shift+N - konfiguracja n8n\n\nPlik -> Kopia zapasowa JSON / Przywróć z JSON\nPlik -> Import z PWA / Eksport dla PWA\nPlik -> Eksport do chmury (folder Google Drive lub OneDrive)\nTagi — filtrowanie i pole w edycji (po przecinku)\nKopiowanie — uzupełnia [TEMAT], [TEKST] jeśli są w prompcie\nSzukaj — podświetla frazę w podglądzie treści\nHistoria — do 5 wersji przy edycji\nPrzy zapisie tworzona jest kopia promptbase.json.bak\n\nMenu AI oraz przyciski ChatGPT / Claude / Gemini:\nkopiują zaznaczony prompt do schowka i otwierają stronę modelu.\n\nn8n (Narzędzia):\n- skonfiguruj URL webhooka (/webhook/ w adresie)\n- Testuj webhook — wysyła type: test\n- Wyślij zaznaczony — type: single_prompt\n- Synchronizuj — type: sync (cała biblioteka lub przypięte)\n- Eksportuj JSON — ten sam format bez wysyłki HTTP\n\nWidok -> Tryb jasny/ciemny zmienia wygląd aplikacji.\nDane są zapisywane lokalnie w pliku JSON. Import/eksport CSV jest zgodny z wersją PWA.": (
        "\n\nMain action: \"Copy and use in AI\" — copies the prompt and opens the platform.\n"
        "Getting started guide: Help menu.\n\nShortcuts:\n"
        "Ctrl+N - new prompt\nCtrl+D - duplicate prompt\nCtrl+Enter - edit selected\n"
        "Ctrl+Shift+A - copy and use in AI (main action)\nCtrl+Shift+C - copy with metadata\n"
        "/ or Ctrl+F - search\nDelete - delete selected\nCtrl+I - import CSV\n"
        "Ctrl+E - export CSV\nCtrl+Shift+N - n8n configuration\n\n"
        "File -> JSON backup / Restore from JSON\n"
        "File -> Import from PWA / Export for PWA\n"
        "File -> Export to cloud (Google Drive or OneDrive folder)\n"
        "Tags — filtering and a comma-separated field in the editor\n"
        "Copying — fills in [TEMAT], [TEKST] if present in the prompt\n"
        "Search — highlights the phrase in the content preview\n"
        "History — up to 5 versions kept while editing\n"
        "A promptbase.json.bak copy is created on every save\n\n"
        "AI menu and the ChatGPT / Claude / Gemini buttons:\n"
        "copy the selected prompt to the clipboard and open the model's page.\n\n"
        "n8n (Tools):\n"
        "- configure the webhook URL (/webhook/ in the address)\n"
        "- Test webhook — sends type: test\n"
        "- Send selected — type: single_prompt\n"
        "- Sync — type: sync (whole library or pinned only)\n"
        "- Export JSON — the same format without an HTTP request\n\n"
        "View -> Light/Dark mode changes the app's appearance.\n"
        "Data is stored locally in a JSON file. CSV import/export matches the PWA version."
    ),
    # --- audyt pokrycia: krótkie etykiety i separatory pominięte w pierwszym
    # przebiegu (odnalezione po instalacji pakietu MSIX z prawdziwą biblioteką) --
    " z ": " of ",
    "Autor: ": "Author: ",
    "Ciemny": "Dark",
    "Filtry": "Filters",
    "Grafit": "Graphite",
    "Historia": "History",
    "Historia…": "History…",
    "Jasny": "Light",
    "Kopiuj": "Copy",
    "Otwarto ": "Opened ",
    "Plik: ": "File: ",
    "Przypnij": "Pin",
    "Silnik": "Engine",
    "Sortuj": "Sort",
    "Ulepszony": "Improved",
    "Wersja ": "Version ",
    "Wybierz…": "Choose…",
    "Zaimportowano ": "Imported ",
    "Znaleziono ": "Found ",
    "\nZnaleziono ": "\nFound ",
    "1. Wybierz prompt z listy": "1. Pick a prompt from the list",
    "2. Skopiuj treść do schowka": "2. Copy the content to the clipboard",
    "3. Otwórz ChatGPT / Claude": "3. Open ChatGPT / Claude",
    "4. Dodaj własny prompt": "4. Add your own prompt",
    # Separatory i symbole bez tłumaczenia — identity, tylko żeby audyt
    # pokrycia (tests/test_i18n_coverage.py) nie zgłaszał ich jako braku.
    " | ": " | ",
    ".": ".",
    ").": ").",
    ".\n\n": ".\n\n",
    ")": ")",
    " — ": " — ",
    " ↗": " ↗",
    "”.": '".',
    "”?": '"?',
    "○ ": "○ ",
    "AI": "AI",
    "n8n": "n8n",
    " (HTTP ": " (HTTP ",
    "Tag": "Tag",
}

# Statusy i słowniki wartości (osobno, bo używane też przy filtrach).
_EN_VALUES: dict[str, str] = {
    "Nowy": "New",
    "Osobiste": "Personal",
    "Praca": "Work",
    "Uniwersalne": "Universal",
    "tekst": "text",
    "kod": "code",
    "zdjecie/screen": "image/screen",
    "Wszystkie": "All",
    # Naglowki eksportu CSV/XLSX — nazwy dobrane tak, zeby import je rozpoznal
    "Data Utworzenia": "Created",
    "Treść Promptu": "Content",
    "Najnowsze": "Newest",
    "Najstarsze": "Oldest",
    "A -> Z": "A -> Z",
    "Z -> A": "Z -> A",
    "angielski": "English",
    "polski": "Polish",
    "niemiecki": "German",
    "hiszpański": "Spanish",
    "francuski": "French",
}


def t(text: str) -> str:
    """Tłumaczy tekst UI; brak wpisu = zwraca oryginał (bezpieczny fallback)."""
    if _current == LANG_PL:
        return text
    if text in _EN:
        return _EN[text]
    return _EN_VALUES.get(text, text)


def tv(value: str) -> str:
    """Tłumaczy wartość słownikową (status, format, język) — jak `t`."""
    return t(value)


def value_aliases(value: str) -> tuple[str, ...]:
    """Wszystkie znane zapisy wartości: kanoniczny i angielski.

    Niezależne od bieżącego języka — plik wyeksportowany po angielsku musi
    dać się zaimportować także w sesji polskiej i odwrotnie.
    """
    english = _EN_VALUES.get(value)
    return (value, english) if english and english != value else (value,)


def catalog_size() -> int:
    """Liczba wpisów w katalogu — używane w testach spójności."""
    return len(_EN) + len(_EN_VALUES)
