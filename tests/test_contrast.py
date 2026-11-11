"""Kontrast WCAG dla wszystkich motywów — liczony, nie oceniany na oko.

Progi: 4.5:1 dla tekstu (WCAG 1.4.3 AA) i 3:1 dla krawędzi, która pozwala
rozpoznać kontrolkę (WCAG 1.4.11). Dekoracyjne kreski oddzielające karty
celowo NIE są tu sprawdzane — ich kontrast nie jest wymagany, bo karta jest
rozpoznawalna po wypełnieniu, a wyraźna linia psułaby spokojny układ.

Test złapał dwie realne usterki: stonowany tekst miał 4.44:1 na tle okna,
a pole tekstowe na białej karcie było otoczone ramką o kontraście 1.27:1,
czyli praktycznie niewidoczną.
"""

from __future__ import annotations

import pytest

from pbcore.core import THEMES

TEXT_MIN = 4.5          # WCAG 1.4.3 AA, tekst zwykłej wielkości
NON_TEXT_MIN = 3.0      # WCAG 1.4.11, elementy nietekstowe


def _luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    channels = []
    for i in (0, 2, 4):
        value = int(raw[i:i + 2], 16) / 255
        channels.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first: str, second: str) -> float:
    a, b = _luminance(first), _luminance(second)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def test_contrast_helper_matches_known_values():
    """Sam licznik też musi być poprawny — inaczej test niczego nie dowodzi."""
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0, abs=0.01)
    assert contrast("#ffffff", "#ffffff") == pytest.approx(1.0, abs=0.01)
    assert contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.05)


TEXT_PAIRS = [
    ("tekst na tle okna", "text", "bg"),
    ("tekst na karcie", "text", "surface"),
    ("tekst na pasie listy", "text", "row_alt"),
    ("tekst na zaznaczeniu", "text", "select"),
    ("tekst w polu", "text", "field"),
    ("stonowany na tle okna", "muted", "bg"),
    ("stonowany na karcie", "muted", "surface"),
    ("napis na przycisku akcentowym", "accent_text", "accent"),
    ("napis na akcencie po najechaniu", "accent_text", "accent_hover"),
]

NON_TEXT_PAIRS = [
    ("krawędź kontrolki na polu", "control_border", "field"),
    ("krawędź kontrolki na karcie", "control_border", "surface"),
    ("krawędź kontrolki na tle okna", "control_border", "bg"),
    ("akcent jako element graficzny", "accent", "surface"),
    ("obrys fokusu na karcie", "accent", "field"),
]


@pytest.mark.parametrize("theme_name", sorted(THEMES))
@pytest.mark.parametrize("label, fg, bg", TEXT_PAIRS, ids=lambda v: v if isinstance(v, str) else None)
def test_text_contrast_meets_aa(theme_name, label, fg, bg):
    theme = THEMES[theme_name]
    ratio = contrast(theme[fg], theme[bg])
    assert ratio >= TEXT_MIN, (
        f"{theme_name}: {label} — {theme[fg]} na {theme[bg]} daje {ratio:.2f}:1, "
        f"a potrzeba {TEXT_MIN}:1"
    )


@pytest.mark.parametrize("theme_name", sorted(THEMES))
@pytest.mark.parametrize("label, fg, bg", NON_TEXT_PAIRS, ids=lambda v: v if isinstance(v, str) else None)
def test_non_text_contrast_meets_aa(theme_name, label, fg, bg):
    theme = THEMES[theme_name]
    ratio = contrast(theme[fg], theme[bg])
    assert ratio >= NON_TEXT_MIN, (
        f"{theme_name}: {label} — {theme[fg]} na {theme[bg]} daje {ratio:.2f}:1, "
        f"a potrzeba {NON_TEXT_MIN}:1"
    )


@pytest.mark.parametrize("theme_name", sorted(THEMES))
def test_every_theme_defines_all_tokens(theme_name):
    """Brakujący token ujawniłby się dopiero jako wyjątek w działającym oknie."""
    required = {
        "bg", "surface", "border", "control_border", "text", "muted",
        "accent", "accent_hover", "accent_text", "select", "row_alt",
        "field", "search_hit",
    }
    missing = required - set(THEMES[theme_name])
    assert not missing, f"{theme_name}: brakuje tokenów {sorted(missing)}"


@pytest.mark.parametrize("theme_name", sorted(THEMES))
def test_row_banding_is_visible_but_subtle(theme_name):
    """Pasy na liście mają być widoczne, ale nie mogą ciąć układu na paski."""
    theme = THEMES[theme_name]
    ratio = contrast(theme["row_alt"], theme["surface"])
    assert 1.02 <= ratio <= 1.25, f"{theme_name}: pasy dają {ratio:.3f}:1"
