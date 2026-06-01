# PrompBase v2.4 — Opis dla naffy.io (Windows EXE)

---

## Tytuł produktu

PrompBase 2.4 — lokalna biblioteka promptów AI dla Windows (bez instalacji)

---

## Krótki opis (do 160 znaków)

Darmowa aplikacja Windows do zarządzania promptami AI. Jeden plik EXE — pobierz i uruchom. Bez instalacji, bez konta, bez chmury. Twoje prompty zostają na Twoim komputerze.

---

## Długi opis

Jeśli regularnie pracujesz z ChatGPT, Claude, Gemini albo innymi narzędziami AI, wiesz, jak szybko prompty rozpraszają się po notatkach, plikach tekstowych i historii czatów. PrompBase to prosta aplikacja desktopowa, która zbiera je wszystkie w jednym miejscu.

Pobierasz jeden plik EXE, klikasz — i gotowe. Nie trzeba instalować Pythona, nic konfigurować, nigdzie się logować. Aplikacja działa lokalnie na Twoim komputerze. Dane zapisują się w pliku JSON na dysku i nigdzie nie wylatują.

### Co możesz robić w PrompBase

Każdy prompt opisujesz modelem AI (GPT-5.5, Claude Opus 4.7, Gemini 3.5 i inne), kategorią zastosowania (pisanie, kodowanie, marketing, SEO, n8n...), statusem i opcjonalnym tagiem. Potem wyszukujesz po dowolnej frazie — aplikacja podświetla trafienia bezpośrednio w podglądzie.

Jeśli prompt ma zmienne w stylu `[TEMAT]` albo `[PRODUKT]`, aplikacja pyta o wartość w momencie kopiowania. Nie musisz nic ręcznie podmieniać.

Bibliotekę możesz eksportować do CSV, JSON albo zsynchronizować z Google Drive lub OneDrive. Działa też import z wersji PWA (przeglądarkowej) — dane przeskakują między urządzeniami bez żadnej rejestracji.

Dla użytkowników n8n: wbudowany webhook pozwala wysłać pojedynczy prompt lub całą bibliotekę do workflow automatyzacji jednym kliknięciem.

### Szybki dostęp do platform AI

Pasek skrótów otwiera ChatGPT, Claude, Gemini, Perplexity i Copilot bezpośrednio z aplikacji. Kopiujesz prompt, klikasz platformę — jesteś gotowy do pracy.

### Historia wersji

Każda edycja promptu zapisuje poprzednią wersję (do 5 wstecz). Możesz wrócić do dowolnego wcześniejszego brzmienia bez utraty danych.

---

## Co dostajesz

- PrompBase.exe — jeden plik, działa od razu na Windows 10/11
- Biblioteka promptów z tagami, filtrami, historią edycji (5 wersji)
- Obsługa modeli: GPT-5.5, Claude Opus 4.7, Gemini 3.5, DeepSeek V3, Grok 3 i inne
- Szybkie otwieranie ChatGPT, Claude, Gemini, Perplexity, Copilot
- Zmienne w promptach `[TEMAT]` — uzupełnianie przy kopiowaniu
- Import/eksport CSV, JSON, PWA (localStorage)
- Synchronizacja z Google Drive i OneDrive
- Integracja z n8n (webhook: test, pojedynczy prompt, pełny sync)
- Tryb jasny i ciemny
- Dane wyłącznie lokalnie — zero chmury, zero logowania

---

## Dla kogo

Dla każdego, kto na co dzień używa narzędzi AI: twórców treści, marketerów, copywriterów, programistów, automatyzatorów n8n, fotografów i przedsiębiorców. Jeśli masz więcej niż kilkanaście promptów i szukasz ich dłużej niż chwilę — PrompBase rozwiązuje ten problem.

---

## Wymagania

- Windows 10 lub 11 (64-bit)
- Brak dodatkowych wymagań — Python NIE jest potrzebny

---

## Jak uruchomić

1. Pobierz plik `PrompBase.exe`
2. Kliknij dwukrotnie
3. Aplikacja uruchamia się od razu

Dane zapisują się automatycznie w: `%APPDATA%\PrompBase\promptbase.json`

---

## Prywatność

PrompBase działa w 100% lokalnie. Żadne dane nie są wysyłane na zewnętrzne serwery. Wyjątek: funkcja n8n działa tylko wtedy, gdy samodzielnie wpiszesz adres swojego webhooka.

---

## Cena

0 zł — darmowa aplikacja open source

---

## Autor

Marek Zettel / Cyfrowy Przyjaciel

