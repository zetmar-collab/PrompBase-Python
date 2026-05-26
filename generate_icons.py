#!/usr/bin/env python3
"""Generate Windows and macOS icons for PrompBase."""

from __future__ import annotations

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "assets"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def make_icon(size: int) -> Image.Image:
    scale = 4
    canvas_size = size * scale
    radius = max(4, int(canvas_size * 0.22))

    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    pixels = gradient.load()

    start = (124, 106, 247)
    end = (74, 158, 255)
    for y in range(canvas_size):
        for x in range(canvas_size):
            t = (x + y) / (2 * (canvas_size - 1))
            pixels[x, y] = (
                lerp(start[0], end[0], t),
                lerp(start[1], end[1], t),
                lerp(start[2], end[2], t),
                255,
            )

    mask = Image.new("L", (canvas_size, canvas_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, canvas_size - 1, canvas_size - 1), radius=radius, fill=255)
    image.alpha_composite(Image.composite(gradient, Image.new("RGBA", gradient.size), mask))

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((0, 0, canvas_size - 1, canvas_size - 1), radius=radius, fill=(255, 255, 255, 16))

    def p(x: float, y: float) -> tuple[int, int]:
        return int(x * canvas_size / 512), int(y * canvas_size / 512)

    bolt = [p(296, 80), p(188, 272), p(264, 272), p(216, 432), p(356, 216), p(276, 216), p(326, 80)]
    shadow = [(x + int(canvas_size * 0.018), y + int(canvas_size * 0.018)) for x, y in bolt]
    draw.polygon(shadow, fill=(25, 28, 40, 70))
    draw.polygon(bolt, fill=(245, 255, 255, 255))

    # Soft mint highlight in the lower part of the bolt.
    highlight = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(highlight, "RGBA")
    hdraw.polygon([p(264, 272), p(216, 432), p(356, 216), p(306, 216)], fill=(106, 247, 184, 105))
    image.alpha_composite(highlight)

    draw = ImageDraw.Draw(image, "RGBA")
    stroke_width = max(1, canvas_size // 180)
    draw.line(bolt + [bolt[0]], fill=(255, 255, 255, 80), width=stroke_width, joint="curve")
    draw.ellipse((*p(126, 146), *p(154, 174)), fill=(255, 255, 255, 64))
    draw.ellipse((*p(362, 350), *p(382, 370)), fill=(106, 247, 184, 140))
    draw.ellipse((*p(373, 133), *p(387, 147)), fill=(255, 255, 255, 50))

    return image.resize((size, size), Image.Resampling.LANCZOS)


def png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def write_icns(images: dict[int, Image.Image], path: Path) -> None:
    # PNG-based ICNS chunks supported by modern macOS.
    chunks = [
        ("ic07", 128),
        ("ic08", 256),
        ("ic09", 512),
        ("ic10", 1024),
    ]
    payload = bytearray()
    for chunk_type, size in chunks:
        data = png_bytes(images[size])
        payload += chunk_type.encode("ascii")
        payload += struct.pack(">I", len(data) + 8)
        payload += data

    path.write_bytes(b"icns" + struct.pack(">I", len(payload) + 8) + payload)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    images = {size: make_icon(size) for size in [*SIZES, 512, 1024]}

    for size, image in images.items():
        if size in (128, 256, 512):
            image.save(OUT_DIR / f"promptbase-{size}.png")

    images[256].save(OUT_DIR / "promptbase.ico", sizes=[(s, s) for s in SIZES])
    write_icns(images, OUT_DIR / "promptbase.icns")
    print(f"Generated icons in {OUT_DIR}")


if __name__ == "__main__":
    main()
