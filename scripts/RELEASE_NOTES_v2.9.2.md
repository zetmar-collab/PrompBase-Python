## PrompBase Python 2.9.2

🎉 **PrompBase jest dostępny w Microsoft Store!**

[Zainstaluj z Microsoft Store](https://apps.microsoft.com/store/detail/9NZQZN1XFHPH?cid=DevShareMCLPCS)
— automatyczne aktualizacje, instalacja jednym kliknięciem.

To wydanie wprowadza zmiany wymagane przez certyfikację Microsoft Store.

### Zgłaszanie treści wygenerowanych przez AI (zasada 11.16)

- Każde okno wyniku asystenta AI (Ulepsz / Przetłumacz / Dostosuj) ma teraz
  przycisk **„⚠ Zgłoś treść”** — pozwala zgłosić nieodpowiedni wynik modelu
- Zgłoszenie zawiera oryginalny prompt, wynik AI, użyty silnik i model
- Deklaracja generatywnej AI zaznaczona w Partner Center

### Dystrybucja zgodna z zasadami Store (zasada 10.1.5)

- Wersja sklepowa (MSIX) automatycznie ukrywa pozycje promujące pobieranie
  oprogramowania poza Store: *Pomoc → Pobierz najnowszą wersję*,
  *Pomoc → Cennik (Free / Pro)* oraz *Narzędzia → Paczki promptów Pro*
- W wersji EXE / instalatorze z GitHub te pozycje działają bez zmian
- Wykrywanie środowiska przez Win32 `GetCurrentPackageFullName()`
  (`pbcore.core.is_msix_package()`), pokryte testami

### Skąd pobrać

| Wersja | Link |
|--------|------|
| Microsoft Store (zalecane) | [apps.microsoft.com](https://apps.microsoft.com/store/detail/9NZQZN1XFHPH?cid=DevShareMCLPCS) |
| Instalator Windows | `PrompBase-2.9.2-Setup.exe` poniżej |
| Przenośny EXE + ZIP | `PrompBase.exe` / `PrompBase-2.9.2-Windows.zip` poniżej |

### Pobierz

https://github.com/zetmar-collab/PrompBase-Python/releases
