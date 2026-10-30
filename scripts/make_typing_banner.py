#!/usr/bin/env python3
"""Render the README header as a pixel-art typewriter GIF.

The banner used to be readme-typing-svg: a third-party service that renders a
Google Font at run time, so the glyph edges were smooth vectors - "pixel font",
not actual pixels. This script draws the headline from a 5x8 bitmap font, one
frame per typed character, and upscales with NEAREST, so every pixel of the
result is a hard-edged square that matches the Tech Stack sprites.

Two lines instead of one: a single 41-character run was 771px wide and 42px
tall, a letterbox strip that dominated the page. Split in two the banner is
483x75 - narrower and roughly 1/3 the aspect ratio. The GIF deliberately has
no loop extension, so it types once and freezes on the finished line.

Output: assets/ui/typing.gif + assets/ui/typing-dark.gif (transparent), two
files because a GIF's palette is baked in and the page needs one ink per theme.

Usage:  python3 scripts/make_typing_banner.py
Requires: pillow
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "ui"

LINES = ["Hi, I'm konlue.", "Walking in AI Full-Stack."]

GLYPH_W, GLYPH_H = 5, 8      # 5x8 cell; rows 0-6 above the baseline, row 7 below
TRACKING = 1                 # blank column between glyphs
LINE_GAP = 3                 # blank rows between the two lines
SCALE = 3                    # 1x pixel -> 3x3 screen px
PAD = 3                      # 1x padding around the whole banner
CURSOR_W = 4
CURSOR_TOP, CURSOR_BOTTOM = 0, 6   # cursor spans the text box, not the descender

TYPE_MS = 55                 # per character
LEAD_MS = 400                # cursor waiting before it starts typing
NEWLINE_MS = 260             # beat between line 1 and line 2
HOLD_MS = 900                # fully typed, cursor still on
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


def text_pixels(text, y_offset=0):
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
                    pixels.add((x0 + x, y + y_offset))
    return pixels


def line_top(index):
    """Top (1x) of the index-th line's cell."""
    return index * (GLYPH_H + LINE_GAP)


def cursor_pixels(line, index):
    top = line_top(line)
    x0 = char_cell(index)
    return {(x0 + x, top + y) for x in range(CURSOR_W) for y in range(CURSOR_TOP, CURSOR_BOTTOM + 1)}


def canvas_1x():
    """1x banner size: the longest line plus one trailing cell for the cursor."""
    width = char_cell(max(len(line) for line in LINES)) + CURSOR_W + 1 + 2 * PAD
    height = line_top(len(LINES) - 1) + GLYPH_H + 2 * PAD
    return width, height


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
    """(line, visible characters, cursor on, duration ms) - the typing script."""
    steps = [(0, 0, True, LEAD_MS)]
    for line_index, line in enumerate(LINES):
        if line_index:                       # cursor drops to the next line
            steps.append((line_index, 0, True, NEWLINE_MS))
        for count in range(1, len(line) + 1):
            steps.append((line_index, count, True, TYPE_MS))
    last = (len(LINES) - 1, len(LINES[-1]), True, HOLD_MS)
    steps.append(last)                        # beat before the blink
    for on in (False, True, False, True):
        steps.append((last[0], last[1], on, BLINK_MS))
    return steps


def build(theme):
    size = canvas_1x()
    frames, durations = [], []
    for line_index, count, cursor_on, delay in timeline():
        pixels = set()
        for done in range(line_index):         # earlier lines stay on screen
            pixels |= text_pixels(LINES[done], line_top(done))
        pixels |= text_pixels(LINES[line_index][:count], line_top(line_index))
        if cursor_on:
            pixels |= cursor_pixels(line_index, count)
        frames.append(render_frame(pixels, size, COLORS[theme]))
        durations.append(delay)

    name = "typing.gif" if theme == "light" else "typing-dark.gif"
    path = OUT_DIR / name
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        disposal=2,
        optimize=True,
        transparency=0,
        # no `loop` kwarg on purpose: Pillow only writes the NETSCAPE loop
        # extension when it is asked to, so the GIF types once and stops.
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
