#!/usr/bin/env python3
"""Render a contact sheet of all tech tiles (both themes) for visual review.

Replicates the exact tile geometry and colour rules from make_tech_chips.py
using PIL, laid out the way README.md shows the section (two groups per row,
uniform 90px cells so every icon sits on the same grid).
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_tech_chips as M  # noqa: E402

S = 3  # supersample factor for crisp output
FONT_PATH = "C:/Windows/Fonts/consola.ttf"
FONT_BOLD = "C:/Windows/Fonts/consolab.ttf"
FONT_UI = "C:/Windows/Fonts/segoeuib.ttf"
OUT = ROOT / ".tech-chips-review.png"

GITHUB_LIGHT_BG = "#ffffff"
GITHUB_DARK_BG = "#0d1117"


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def draw_label(img, text, cx, baseline, color, size, font_path, box=None):
    """Centred label; squeezed horizontally when it would overflow its cell."""
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size * S)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    width = right - left
    if box is None or width <= box * S:
        draw.text((cx * S, baseline * S), text, font=font, fill=color, anchor="ms")
        return
    pad_h = bottom - top + 8
    patch = Image.new("RGBA", (width + 4, pad_h), (0, 0, 0, 0))
    ImageDraw.Draw(patch).text((2 - left, 4 - top), text, font=font, fill=color)
    patch = patch.resize((int(box * S), pad_h), Image.LANCZOS)
    img.paste(patch, (int((cx - box / 2) * S), int(baseline * S) - pad_h + 4 + top), patch)


def draw_tile(img, x, y, name, brand, grid, theme):
    draw = ImageDraw.Draw(img)
    width = M.tile_width(name)
    ix = (width - M.ICON) // 2
    for gy, row in enumerate(grid):
        for gx, cell in enumerate(row):
            if not cell:
                continue
            cx, cy = x + ix + gx * M.SCALE, y + M.PAD + gy * M.SCALE
            color = hx(M._rgb_to_hex(M.theme_color(cell, theme)))
            draw.rectangle([cx * S, cy * S, (cx + M.SCALE) * S - 1, (cy + M.SCALE) * S - 1], fill=color)
    draw_label(img, name, x + width / 2, y + M.LABEL_BASELINE,
               hx(M.shift(brand, M.LABEL_SHIFT[theme])), M.LABEL_SIZE, FONT_PATH, box=M.CELL - 2 * M.PAD)
    return width


def draw_group(img, x, y, name, theme):
    """Header stand-in: fixed 60px slot, pixel-icon box + bold label."""
    draw = ImageDraw.Draw(img)
    ink = hx(M.GROUP_INK[theme])
    draw.rectangle([x * S, y * S, (x + M.GROUP_ICON) * S, (y + M.GROUP_ICON) * S], outline=ink, width=1)
    draw_label(img, name, x + M.GROUP_ICON + 4 + 13, y + 16, ink, 11, FONT_BOLD, box=26)
    return M.GROUP_W


def main():
    grids = M.build_grids()
    font_h = ImageFont.truetype(FONT_UI, 15 * S)
    font_note = ImageFont.truetype(FONT_PATH, 11 * S)

    margin, group_gap = 24, 24
    rows = [M.TECHS[i:i + 2] for i in range(0, len(M.TECHS), 2)]
    row_w = max(
        sum(M.GROUP_W + sum(M.tile_width(e[0]) for e in entries) for _g, entries in pair) + group_gap
        for pair in rows
    )
    W = margin * 2 + row_w
    H = 2000 * S

    img = Image.new("RGB", (W * S, H), hx(GITHUB_LIGHT_BG))
    y = margin
    for theme, page_bg in (("light", GITHUB_LIGHT_BG), ("dark", GITHUB_DARK_BG)):
        ImageDraw.Draw(img).rectangle([0, (y - 8) * S, W * S, H], fill=hx(page_bg))
        heading = ("Tech Stack — LIGHT (as on GitHub light)" if theme == "light"
                   else "Tech Stack — DARK (as on GitHub dark)")
        ImageDraw.Draw(img).text((margin * S, y * S), heading, font=font_h,
                                 fill=hx("#1f2328" if theme == "light" else "#e6edf3"))
        y += 30
        for pair in rows:
            x = margin
            for group, entries in pair:
                draw_group(img, x, y + 24, group, theme)
                x += M.GROUP_W
                for entry in entries:
                    x += draw_tile(img, x, y, entry[0], entry[2], grids[entry[0]], theme)
                x += group_gap
            y += M.TILE_H + 22
        y += 14

    note = (f"geometry/colours identical to assets/ui/tech/*.svg ({M.GRID}x{M.GRID} grid @{M.SCALE}x "
            f"icons, uniform {M.CELL}px cells, Consolas {M.LABEL_SIZE}px labels, 3x supersample)")
    ImageDraw.Draw(img).text((margin * S, (y + 4) * S), note, font=font_note, fill=hx("#59636e"))
    img = img.crop((0, 0, W * S, (y + 28) * S))
    img.save(OUT)
    print(f"wrote {OUT.relative_to(ROOT)} ({img.size[0]}x{img.size[1]})")


if __name__ == "__main__":
    main()
