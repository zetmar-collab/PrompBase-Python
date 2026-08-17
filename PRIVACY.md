# Polityka prywatności — PrompBase

Ostatnia aktualizacja: 17.08.2026

PrompBase to lokalna aplikacja desktopowa (Windows/macOS). Nie wymaga konta,
nie zbiera telemetrii ani danych analitycznych i nie wysyła danych na żadne
serwery należące do autora aplikacji.

## Gdzie przechowywane są dane

Biblioteka promptów jest zapisywana **wyłącznie lokalnie** na Twoim komputerze,
w pliku JSON:

- Windows: `%APPDATA%\PrompBase\promptbase.json`
- macOS: `~/Library/Application Support/PrompBase/promptbase.json`

Autor aplikacji nie ma dostępu do tych danych i nie są one nigdzie
przesyłane automatycznie.

## Opcjonalne funkcje wysyłające dane do stron trzecich

Poniższe funkcje są **wyłącznie opcjonalne** i wymagają świadomej akcji
użytkownika (kliknięcia przycisku):

### Asystent AI (OpenRouter)

Jeśli użytkownik skonfiguruje klucz API OpenRouter i użyje funkcji „Ulepsz
prompt”, „Przetłumacz” lub „Dostosuj do platformy”, treść wybranego promptu
jest wysyłana do [OpenRouter](https://openrouter.ai) w celu przetworzenia
przez wybrany model AI. Podlega to polityce prywatności OpenRouter oraz
dostawcy wybranego modelu. Klucz API jest przechowywany lokalnie w osobnym
pliku (`openrouter.key`), nigdy w bibliotece promptów, nigdy w kopiach
zapasowych.

### Asystent AI (Ollama)

Alternatywnie użytkownik może korzystać z lokalnie zainstalowanej Ollamy —
w tym trybie żadne dane nie opuszczają komputera użytkownika.

### Integracja n8n (opcjonalna)

Jeśli użytkownik skonfiguruje webhook n8n (własny, samodzielnie hostowany
lub w chmurze), może ręcznie wysłać wybrane prompty pod wskazany adres URL.
Ta funkcja jest domyślnie wyłączona i wymaga ręcznej konfiguracji adresu
URL przez użytkownika.

## Dane, których PrompBase nie zbiera

- Brak kont użytkowników
- Brak telemetrii, analityki ani śledzenia użycia
- Brak reklam
- Brak danych lokalizacyjnych, kontaktów ani innych danych systemowych

## Kontakt

Pytania dotyczące prywatności: zgłoszenie na
[GitHub Issues](https://github.com/zetmar-collab/PrompBase-Python/issues).
