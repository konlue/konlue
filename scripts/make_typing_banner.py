#!/usr/bin/env python3
"""Render the README header as a pixel-art typewriter GIF.

The banner used to be readme-typing-svg: a third-party service that renders a
Google Font at run time, so the glyph edges were smooth vectors - "pixel font",
not actual pixels. This script draws the headline from a 5x8 bitmap font, one
frame per typed character, and upscales with NEAREST, so every pixel of the
result is a hard-edged square that matches the Tech Stack sprites.

Output: assets/ui/typing.gif + assets/ui/typing-dark.gif (transparent), two
files because a GIF's palette is baked in and the page needs one ink per theme.

Usage:  python3 scripts/make_typing_banner.py
Requires: pillow
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "ui"

TEXT = "Hi, I'm konlue. Walking in AI Full-Stack."

GLYPH_W, GLYPH_H = 5, 8      # 5x8 cell; rows 0-6 above the baseline, row 7 below
TRACKING = 1                 # blank column between glyphs
SCALE = 3                    # 1x pixel -> 3x3 screen px
PAD = 3                      # 1x padding around the whole banner
CURSOR_W = 4
CURSOR_TOP, CURSOR_BOTTOM = 0, 6   # cursor spans the text box, not the descender

TYPE_MS = 60                 # per character
LEAD_MS = 420                # cursor waiting before it starts typing
HOLD_MS = 700                # fully typed, cursor still on
BLINK_MS = 420               # cursor off/on cycle at the end

COLORS = {
    "light": (0x09, 0x69, 0xDA),
    "dark": (0x58, 0xA6, 0xFF),
}

# 5x8 bitmap font, one glyph per line, rows separated by "/". Rows are
# top-aligned, so a 7-row glyph simply leaves the descender row empty. Only the
# printable ASCII the banner needs is defined; unknown characters fall back to
# "?" rather than crashing.
FONT = {
    " ": "...../...../...../...../...../...../.....",
    "!": "..#../..#../..#../..#../..#../...../..#..",
    "'": "..#../..#../...../...../...../...../.....",
    "(": "...#./..#../..#../..#../..#../..#../...#.",
    ")": ".#.../..#../..#../..#../..#../..#../.#...",
    "+": "...../..#../..#../#####/..#../..#../.....",
    ",": "...../...../...../...../...../..##./..##./.#...",
    "-": "...../...../...../.###./...../...../.....",
    ".": "...../...../...../...../...../.##../.##..",
    "/": "....#/....#/...#./..#../.#.../#..../#....",
    ":": "...../.##../.##../...../.##../.##../.....",
    "?": ".###./#...#/....#/...#./..#../...../..#..",
    "0": ".###./#...#/#..##/#.#.#/##..#/#...#/.###.",
    "1": "..#../.##../..#../..#../..#../..#../.###.",
    "2": ".###./#...#/....#/...#./..#../.#.../#####",
    "3": "####./....#/....#/.###./....#/....#/####.",
    "4": "...#./..##./.#.#./#..#./#####/...#./...#.",
    "5": "#####/#..../####./....#/....#/#...#/.###.",
    "6": "..##./.#.../#..../####./#...#/#...#/.###.",
    "7": "#####/....#/...#./..#../.#.../.#.../.#...",
    "8": ".###./#...#/#...#/.###./#...#/#...#/.###.",
    "9": ".###./#...#/#...#/.####/....#/...#./.##..",
    "A": "..#../.#.#./#...#/#...#/#####/#...#/#...#",
    "B": "####./#...#/#...#/####./#...#/#...#/####.",
    "C": ".###./#...#/#..../#..../#..../#...#/.###.",
    "D": "####./#...#/#...#/#...#/#...#/#...#/####.",
    "E": "#####/#..../#..../####./#..../#..../#####",
    "F": "#####/#..../#..../####./#..../#..../#....",
    "G": ".###./#...#/#..../#.###/#...#/#...#/.###.",
    "H": "#...#/#...#/#...#/#####/#...#/#...#/#...#",
    "I": ".###./..#../..#../..#../..#../..#../.###.",
    "J": "..###/...#./...#./...#./...#./#..#./.##..",
    "K": "#...#/#..#./#.#../##.../#.#../#..#./#...#",
    "L": "#..../#..../#..../#..../#..../#..../#####",
    "M": "#...#/##.##/#.#.#/#...#/#...#/#...#/#...#",
    "N": "#...#/##..#/#.#.#/#..##/#...#/#...#/#...#",
    "O": ".###./#...#/#...#/#...#/#...#/#...#/.###.",
    "P": "####./#...#/#...#/####./#..../#..../#....",
    "Q": ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#",
    "R": "####./#...#/#...#/####./#.#../#..#./#...#",
    "S": ".####/#..../#..../.###./....#/....#/####.",
    "T": "#####/..#../..#../..#../..#../..#../..#..",
    "U": "#...#/#...#/#...#/#...#/#...#/#...#/.###.",
    "V": "#...#/#...#/#...#/#...#/#...#/.#.#./..#..",
    "W": "#...#/#...#/#...#/#.#.#/#.#.#/##.##/#...#",
    "X": "#...#/#...#/.#.#./..#../.#.#./#...#/#...#",
    "Y": "#...#/#...#/.#.#./..#../..#../..#../..#..",
    "Z": "#####/....#/...#./..#../.#.../#..../#####",
    "a": "...../...../.###./....#/.####/#...#/.####",
    "b": "#..../#..../####./#...#/#...#/#...#/####.",
    "c": "...../...../.###./#..../#..../#..../.###.",
    "d": "....#/....#/.####/#...#/#...#/#...#/.####",
    "e": "...../...../.###./#...#/#####/#..../.###.",
    "f": "..##./.#.../####./.#.../.#.../.#.../.#...",
    "g": "...../...../.####/#...#/#...#/.####/....#/.###.",
    "h": "#..../#..../####./#...#/#...#/#...#/#...#",
    "i": "..#../...../.##../..#../..#../..#../.###.",
    "j": "...#./...../..##./...#./...#./...#./...#./##...",
    "k": "#..../#..../#..#./#.#../##.../#.#../#..#.",
    "l": ".##../..#../..#../..#../..#../..#../.###.",
    "m": "...../...../##.#./#.#.#/#.#.#/#.#.#/#.#.#",
    "n": "...../...../####./#...#/#...#/#...#/#...#",
    "o": "...../...../.###./#...#/#...#/#...#/.###.",
    "p": "...../...../####./#...#/#...#/####./#..../#....",
    "q": "...../...../.####/#...#/#...#/.####/....#/....#",
    "r": "...../...../#.##./##..#/#..../#..../#....",
    "s": "...../...../.####/#..../.###./....#/####.",
    "t": ".#.../.#.../####./.#.../.#.../.#.../..##.",
    "u": "...../...../#...#/#...#/#...#/#...#/.####",
    "v": "...../...../#...#/#...#/#...#/.#.#./..#..",
    "w": "...../...../#...#/#...#/#.#.#/#.#.#/.#.#.",
    "x": "...../...../#...#/.#.#./..#../.#.#./#...#",
    "y": "...../...../#...#/#...#/#...#/.####/....#/.###.",
    "z": "...../...../#####/...#./..#../.#.../#####",
}


def char_cell(index):
    """Left edge (1x) of the index-th character cell."""
    return index * (GLYPH_W + TRACKING)


def text_pixels(text):
    """Set of 1x (x, y) coordinates covered by the glyphs."""
    pixels = set()
    for index, char in enumerate(text):
        rows = FONT.get(char, FONT["?"]).split("/")
        if len(rows) > GLYPH_H:                      # a stray tall glyph
            rows = rows[:GLYPH_H]
        x0 = char_cell(index)
        for y, row in enumerate(rows):
            for x, mark in enumerate(row):
                if mark == "#":
                    pixels.add((x0 + x, y))
    return pixels


def cursor_pixels(index):
    x0 = char_cell(index)
    return {(x0 + x, y) for x in range(CURSOR_W) for y in range(CURSOR_TOP, CURSOR_BOTTOM + 1)}


def canvas_1x():
    """1x banner size: the text plus one trailing cell for the cursor."""
    width = char_cell(len(TEXT)) + CURSOR_W + 1 + 2 * PAD
    return width, GLYPH_H + 2 * PAD


def render_frame(pixels, size, color):
    """1x pixel set -> P-mode frame (index 0 transparent, index 1 = ink)."""
    w1, h1 = size
    mask = Image.new("1", (w1, h1), 0)
    for x, y in pixels:
        mask.putpixel((x + PAD, y + PAD), 1)
    big = mask.resize((w1 * SCALE, h1 * SCALE), Image.NEAREST)

    frame = Image.new("P", big.size, 0)
    frame.putpalette([0, 0, 0, *color] + [0, 0, 0] * 254)
    frame.paste(1, (0, 0), big)
    return frame


def timeline():
    """(visible characters, cursor on, duration ms) - the typing script."""
    steps = [(0, True, LEAD_MS)]
    for count in range(1, len(TEXT) + 1):
        steps.append((count, True, TYPE_MS))
    steps.append((len(TEXT), True, HOLD_MS))          # beat before the blink
    for on in (False, True, False, True):
        steps.append((len(TEXT), on, BLINK_MS))
    return steps


def build(theme):
    size = canvas_1x()
    frames, durations = [], []
    for count, cursor_on, delay in timeline():
        pixels = text_pixels(TEXT[:count])
        if cursor_on:
            pixels |= cursor_pixels(count)
        frames.append(render_frame(pixels, size, COLORS[theme]))
        durations.append(delay)

    name = "typing.gif" if theme == "light" else "typing-dark.gif"
    path = OUT_DIR / name
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=True,
        transparency=0,
    )
    w, h = frames[0].size
    print(f"  {path.relative_to(ROOT)}  {w}x{h}  {len(frames)} frames  {path.stat().st_size // 1024}KB")


def main():
    bad = [(char, rows) for char, rows in FONT.items()
           if any(len(row) != GLYPH_W for row in rows.split("/"))]
    if bad:
        raise SystemExit(f"bad glyph widths: {bad}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for theme in ("light", "dark"):
        build(theme)


if __name__ == "__main__":
    main()
