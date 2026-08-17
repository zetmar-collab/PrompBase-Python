#!/usr/bin/env python3
"""Generuje obrazy MSIX (Square44x44Logo, Square150x150Logo, Wide310x150Logo,
StoreLogo, SplashScreen) z istniejącej ikony assets/promptbase-512.png.

Uruchom: python scripts/generate_msix_assets.py
Wynik: msix/Assets/*.png
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "promptbase-512.png"
OUT_DIR = ROOT / "msix" / "Assets"

# (nazwa pliku, szerokość, wysokość, margines jako ułamek krótszego boku)
TARGETS = [
    ("Square44x44Logo.png", 44, 44, 0.12),
    ("Square150x150Logo.png", 150, 150, 0.16),
    ("Wide310x150Logo.png", 310, 150, 0.14),
    ("StoreLogo.png", 50, 50, 0.12),
    ("SplashScreen.png", 620, 300, 0.22),
]

# Tło marki (zgodne z motywem "grafit" aplikacji).
BG = (26, 28, 34, 255)


def make_asset(source: Image.Image, width: int, height: int, margin_ratio: float) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), BG)
    short_side = min(width, height)
    margin = int(short_side * margin_ratio)
    target_h = height - 2 * margin
    target_w = width - 2 * margin
    scale = min(target_w / source.width, target_h / source.height)
    new_size = (max(1, int(source.width * scale)), max(1, int(source.height * scale)))
    resized = source.resize(new_size, Image.LANCZOS)
    x = (width - new_size[0]) // 2
    y = (height - new_size[1]) // 2
    canvas.paste(resized, (x, y), resized)
    return canvas


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Brak pliku źródłowego: {SOURCE}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGBA")
    for name, w, h, margin in TARGETS:
        asset = make_asset(source, w, h, margin)
        out_path = OUT_DIR / name
        asset.save(out_path)
        print(f"Zapisano {out_path} ({w}x{h})")


if __name__ == "__main__":
    main()
