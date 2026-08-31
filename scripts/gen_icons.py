"""One-off script that generates the PWA icon set. Not run at deploy
time — output is committed to static/. Re-run manually if the mark
needs to change: `python scripts/gen_icons.py`.
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "downloader" / "static" / "downloader" / "img"
OUT.mkdir(parents=True, exist_ok=True)

BG = (15, 23, 42, 255)       # matches --bg
ACCENT = (34, 211, 172, 255)  # matches --accent


def draw_mark(size, canvas, color, scale=1.0):
    draw = ImageDraw.Draw(canvas)
    cx, cy = size / 2, size / 2
    u = size / 512 * scale

    stem_w = 46 * u
    stem_top = cy - 140 * u
    stem_bottom = cy + 10 * u
    draw.rounded_rectangle(
        [cx - stem_w / 2, stem_top, cx + stem_w / 2, stem_bottom],
        radius=stem_w / 2,
        fill=color,
    )

    head_half_w = 80 * u
    head_top = cy - 10 * u
    head_tip = cy + 100 * u
    draw.polygon(
        [
            (cx - head_half_w, head_top),
            (cx + head_half_w, head_top),
            (cx, head_tip),
        ],
        fill=color,
    )

    bar_w = 240 * u
    bar_h = 38 * u
    bar_cy = cy + 160 * u
    draw.rounded_rectangle(
        [cx - bar_w / 2, bar_cy - bar_h / 2, cx + bar_w / 2, bar_cy + bar_h / 2],
        radius=bar_h / 2,
        fill=color,
    )


def rounded_bg(size, radius_ratio=0.22):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=BG)
    return img


def make_standard(size):
    img = rounded_bg(size)
    draw_mark(size, img, ACCENT)
    return img


def make_maskable(size):
    # Maskable icons get cropped to arbitrary shapes by the OS, so keep
    # the glyph inside the ~80% "safe zone" and fill edge-to-edge.
    img = Image.new("RGBA", (size, size), BG)
    draw_mark(size, img, ACCENT, scale=0.7)
    return img


def make_apple_touch(size=180):
    # iOS composites this on an opaque background itself; no alpha, no
    # rounding (the OS applies its own corner mask).
    img = Image.new("RGB", (size, size), BG[:3])
    draw_mark(size, img, ACCENT[:3])
    return img


make_standard(512).save(OUT / "icon-512.png")
make_standard(192).save(OUT / "icon-192.png")
make_maskable(512).save(OUT / "icon-maskable-512.png")
make_apple_touch(180).save(OUT / "apple-touch-icon.png")
make_standard(32).convert("RGB").save(OUT / "favicon.png")

print("Icons written to", OUT)
