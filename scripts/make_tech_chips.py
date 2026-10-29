#!/usr/bin/env python3
"""Generate pixel-art tiles and category headers for the "Tech Stack" section.

Each tech becomes a tile SVG: a pixel icon (48px = 24x24 grid at 2x) on top
and a monospace label (12px, brand colour) below. Every tile is CELL (88px)
wide, so the icons of all four categories sit on one aligned grid no matter
which row they are in; labels that would overflow their cell are condensed
with SVG textLength instead of widening it.

Each category also gets a header SVG (pixelarticon + bold label, fixed 60px)
so the four groups line up on the same columns as well.

Every icon comes from the *official* logo, never hand-drawn: the source SVG is
rasterised at high resolution, downsampled onto a 24x24 grid and re-coloured
from the logo's own palette (up to 4 flat colours), so the pixel version keeps
the brand's real shapes and colours. Wordmark logos are cropped to their mark
(MySQL -> the dolphin alone) and line-art logos are lightly bolded so a thin
stroke survives the 24px grid. Light and dark variants are referenced from
README.md via <picture>.

Icon sources (scripts/brand-icons/, trademarks belong to their owners):
  - simple-icons 15  springboot, fastapi, langchain, langgraph, vuedotjs,
                     javascript, typescript, redis, elasticsearch, minio (CC0)
  - devicon          java (Duke cup), python (two-tone snake)         (MIT)
  - spring.io        spring-cloud, spring-ai (official project SVG)
  - element-plus     ep-small.svg (official mark, 44x44 mark only)
  - gilbarbara/logos mysql-full.svg (official wordmark; the dolphin mark is
                     cropped out by TECHS options)
  - pixelarticons    package / cpu / code / database for the group headers

Usage:  python3 scripts/make_tech_chips.py            # regenerate tiles
        python3 scripts/make_tech_chips.py --readme   # + rewrite README block
        edit TECHS / GROUPS below to add or rename a tech or category

Requires: pillow, numpy, svglib, reportlab, rlPyCairo.
"""

import colorsys
import hashlib
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "ui" / "row"
SRC_DIR = ROOT / "scripts" / "brand-icons"
GRID_CACHE = ROOT / "scripts" / "tech-icon-grids.json"

# ---------------------------------------------------------------------------
# Tile geometry (all units are SVG user units = CSS px on GitHub)
# ---------------------------------------------------------------------------
GRID = 24            # pixel grid for icons
THRESHOLD = 0.40     # alpha cutoff when snapping the logo onto the grid
SCALE = 2            # integer upscale of the grid - keeps pixel edges crisp
ICON = GRID * SCALE  # 48
PAD = 3              # tile padding (also bakes in tile spacing)
LABEL_SIZE = 12      # auxiliary label under the icon
LABEL_GAP = 3        # icon bottom -> label top
LABEL_ASCENT = 10    # baseline offset inside the label box
LABEL_BOX = 14       # label line box height
# Every tile has the same width, so icons line up in one grid across rows.
# A row is ONE image (header A + 4 tiles + header B + 4 tiles), not a run of
# inline <picture>s: GitHub wraps an over-long line of inline images, which is
# exactly what happened at 88px (8 tiles + 2 headers + spacers = 872px, wider
# than the ~840px README column). One image cannot wrap - it is scaled down
# instead - so the row is composed here at 824px, safely inside the column.
CELL = 86
ROW_GAP = 16         # gap between the two category groups inside a row
GROUP_ICON = 24      # category header: pixelarticon size
GROUP_W = 60         # category header: fixed width -> identical columns
TILE_H = PAD + ICON + LABEL_GAP + LABEL_BOX + PAD      # 73
LABEL_BASELINE = PAD + ICON + LABEL_GAP + LABEL_ASCENT  # 65
# Monospace advance widths across viewers range ~0.55-0.61em; budget the
# widest so text never overflows the tile on any system.
CHAR_EM = 0.62
FONT_STACK = "SFMono-Regular, Consolas, Menlo, 'Liberation Mono', monospace"
# Labels sit on the page background, so they get a flat shift toward the
# page's opposite extreme (dark labels on white, light labels on black).
LABEL_SHIFT = {"light": -0.42, "dark": 0.52}

# ---------------------------------------------------------------------------
# Tech table: (group, [(display name, slug, brand colour, logo file[, fill holes])])
# options dict (optional): crop=(x0,y0,x1,y1) fractions of the render, used to
# cut one element out of a wordmark logo (MySQL -> the dolphin alone);
# thicken=fraction of the render width, which bolds line-art logos (MySQL's
# dolphin is a single thin stroke) just enough to survive the 24px grid.
# ---------------------------------------------------------------------------
TECHS = [
    ("Java", [
        ("Java", "java", "ED8B00", "java.svg"),
        ("Spring Boot", "spring-boot", "6DB33F", "si-springboot.svg"),
        ("Spring Cloud", "spring-cloud", "6DB33F", "spring-cloud.svg"),
        ("Spring AI", "spring-ai", "6DB33F", "spring-ai.svg"),
    ]),
    ("AI", [
        ("Python", "python", "3776AB", "python-original.svg"),
        ("FastAPI", "fastapi", "009688", "si-fastapi.svg"),
        ("LangChain", "langchain", "1C3C3C", "si-langchain.svg"),
        ("LangGraph", "langgraph", "1C3C3C", "si-langgraph.svg"),
    ]),
    ("Web", [
        ("Vue", "vue", "4FC08D", "si-vue.svg"),
        ("JavaScript", "javascript", "F7DF1E", "si-javascript.svg"),
        ("TypeScript", "typescript", "3178C6", "si-typescript.svg"),
        ("Element Plus", "element-plus", "409EFF", "ep-small.svg"),
    ]),
    ("Data", [
        ("MySQL", "mysql", "4479A1", "mysql-full.svg", {"crop": (0.5, 0.0, 1.0, 0.53), "thicken": 0.016}),
        ("Redis", "redis", "DC382D", "si-redis.svg"),
        ("Elasticsearch", "elasticsearch", "005571", "si-elasticsearch.svg"),
        ("MinIO", "minio", "C72E49", "si-minio.svg"),
    ]),
]

# ---------------------------------------------------------------------------
# Colour helpers (plain RGB math, no dependencies)
# ---------------------------------------------------------------------------

def _hex_to_rgb(h):
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def mix(hex_a, hex_b, t):
    """t=0 -> a, t=1 -> b"""
    a, b = _hex_to_rgb(hex_a), _hex_to_rgb(hex_b)
    return _rgb_to_hex(tuple(a[i] * (1 - t) + b[i] * t for i in range(3)))


def shift(hex_color, t):
    """t<0 darken toward black, t>0 lighten toward white."""
    return mix(hex_color, "000000", -t) if t < 0 else mix(hex_color, "ffffff", t)


def luminance(rgb):
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255.0


def theme_color(rgb, theme):
    """Keep the logo's own colour, only clamp lightness for page contrast.

    Hue and saturation are preserved, so multi-colour logos (Java's cup,
    Python's two-tone snake) stay recognisable in both themes.
    """
    h, l, s = colorsys.rgb_to_hls(*(c / 255.0 for c in rgb))
    if theme == "light":
        l = min(l, 0.62)
    else:
        l = max(l, 0.60)
    return tuple(c * 255.0 for c in colorsys.hls_to_rgb(h, l, s))


# ---------------------------------------------------------------------------
# Rasterisation (needs svglib + reportlab + rlPyCairo + Pillow + numpy)
# ---------------------------------------------------------------------------

NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?")


def _resolve_gradients(svg_text):
    """Flatten gradients to their first stop colour (svglib keeps them flat)."""
    stops = {}
    for match in re.finditer(r"<(linear|radial)Gradient[^>]*id=\"([^\"]+)\"[^>]*>([\s\S]*?)</\1Gradient>", svg_text):
        found = re.findall(r"stop-color=\"(#[0-9a-fA-F]{3,8})\"", match.group(3))
        if found:
            stops[match.group(2)] = found[0]

    def apply(match):
        return f'fill="{stops[match.group(1)]}"' if match.group(1) in stops else match.group(0)

    svg_text = re.sub(r'fill="url\(#([^"]+)\)"', apply, svg_text)
    return re.sub(r"<(linear|radial)Gradient[\s\S]*?</\1Gradient>", "", svg_text)


def _inline_class_fills(svg_text):
    """svglib ignores <style>; turn .cls-N{fill:#hex} into inline fill attrs."""
    style = re.search(r"<style[^>]*>([\s\S]*?)</style>", svg_text)
    if not style:
        return svg_text
    mapping = {}
    for selector, body in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", style.group(1)):
        found = re.search(r"fill:\s*(#[0-9a-fA-F]{3,8})", body)
        if found:
            mapping[selector] = found.group(1)
    if not mapping:
        return svg_text

    def apply(match):
        tag = match.group(0)
        cls = re.search(r'class="([^"]+)"', tag)
        if not cls or "fill=" in tag:
            return tag
        name = cls.group(1).split()[0]
        if name not in mapping:
            return tag
        fill = f' fill="{mapping[name]}"'
        return tag[: -2] + fill + tag[-2:] if tag.endswith("/>") else tag[:-1] + fill + ">"

    svg_text = re.sub(r"<path[^>]*>", apply, svg_text)
    return re.sub(r"<style[\s\S]*?</style>", "", svg_text)


def _render(svg_text):
    """Render an SVG to a high-resolution RGBA image (colour preserved)."""
    from reportlab.graphics import renderPM
    from svglib.svglib import svg2rlg

    tmp = SRC_DIR / ".tmp-flat.svg"
    tmp.write_text(svg_text, encoding="utf-8")
    try:
        drawing = svg2rlg(str(tmp))
        if drawing is None:
            raise RuntimeError("svglib could not parse icon")
        return renderPM.drawToPIL(drawing, dpi=576, bg=None, backendFmt="ARGB")
    finally:
        tmp.unlink(missing_ok=True)


def _prepare(img, opts):
    """Crop a wordmark down to its mark and bold line art before sampling."""
    import numpy as np
    from PIL import Image

    crop = opts.get("crop")
    if crop:
        w, h = img.size
        img = img.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
    thicken = opts.get("thicken")
    if not thicken:
        return img

    arr = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    mask = arr[..., 3] > 128
    if not mask.any():
        return img
    grow = mask.copy()
    for _ in range(max(1, round(img.size[0] * thicken))):
        step = grow.copy()
        step[1:, :] |= grow[:-1, :]
        step[:-1, :] |= grow[1:, :]
        step[:, 1:] |= grow[:, :-1]
        step[:, :-1] |= grow[:, 1:]
        grow = step
    dominant = np.median(arr[mask][:, :3], axis=0).astype(np.uint8)
    out = arr.copy()
    out[grow] = (*dominant, 255)
    return Image.fromarray(out, mode="RGBA")


def _downsample(img, opts=None):
    """Logo -> GRID x GRID RGBA array, premultiplied so edges stay clean."""
    import numpy as np
    from PIL import Image

    alpha = img.convert("RGBA").split()[3]
    bbox = alpha.getbbox()
    if not bbox:
        raise RuntimeError("icon rendered empty")
    img = img.convert("RGBA").crop(bbox)
    if opts:
        img = _prepare(img, opts)
        bbox = img.split()[3].getbbox()
        if bbox:
            img = img.crop(bbox)
    w, h = img.size
    s = min(GRID / w, GRID / h)
    nw, nh = max(1, round(w * s)), max(1, round(h * s))

    arr = np.asarray(img, dtype=np.float32) / 255.0
    prem = Image.fromarray((arr[..., :3] * arr[..., 3:3 + 1] * 255).astype(np.uint8))
    alpha_img = Image.fromarray((arr[..., 3] * 255).astype(np.uint8))
    prem = np.asarray(prem.resize((nw, nh), Image.LANCZOS), dtype=np.float32) / 255.0
    alpha_s = np.asarray(alpha_img.resize((nw, nh), Image.LANCZOS), dtype=np.float32) / 255.0

    canvas = np.zeros((GRID, GRID, 4), dtype=np.float32)
    ox, oy = (GRID - nw) // 2, (GRID - nh) // 2
    safe = np.maximum(alpha_s, 1e-4)
    rgb = prem / safe[..., None]
    canvas[oy:oy + nh, ox:ox + nw, :3] = np.clip(rgb, 0, 1)
    canvas[oy:oy + nh, ox:ox + nw, 3] = alpha_s
    return canvas


def _quantise(canvas, max_colors=4):
    """Snap the cell colours to the logo's own flat palette (tiny k-means)."""
    import numpy as np

    mask = canvas[..., 3] > THRESHOLD
    pixels = canvas[mask][:, :3] * 255.0
    if len(pixels) == 0:
        raise RuntimeError("icon vanished on the pixel grid")

    # seed with the most common colours, then refine (deterministic)
    rounded = np.round(pixels / 16).astype(int)
    uniq, counts = np.unique(rounded, axis=0, return_counts=True)
    seeds = uniq[np.argsort(-counts)][:max_colors].astype(np.float32) * 16
    centers = seeds.copy()
    for _ in range(12):
        dist = ((pixels[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        nearest = dist.argmin(1)
        for k in range(len(centers)):
            group = pixels[nearest == k]
            if len(group):
                centers[k] = group.mean(0)

    grid = [[None] * GRID for _ in range(GRID)]
    for y in range(GRID):
        for x in range(GRID):
            if not mask[y, x]:
                continue
            color = canvas[y, x, :3] * 255.0
            k = int(((centers - color) ** 2).sum(1).argmin())
            grid[y][x] = tuple(int(round(c)) for c in centers[k])
    return grid


def _default_fill(svg_text, brand):
    """simple-icons paths carry no fill; give them the tech's brand colour."""

    def apply(match):
        tag = match.group(0)
        if re.search(r"fill\s*[=:]", tag):
            return tag
        fill = f' fill="#{brand}"'
        return tag[: -2] + fill + tag[-2:] if tag.endswith("/>") else tag[:-1] + fill + ">"

    svg_text = re.sub(r"<path[^>]*>", apply, svg_text)
    return svg_text.replace("<svg ", f'<svg fill="#{brand}" ', 1)


def _logo_text(path, brand):
    svg_text = path.read_text(encoding="utf-8")
    return _default_fill(_inline_class_fills(_resolve_gradients(svg_text)), brand)


def _cache_key(path, spec_name):
    digest = hashlib.sha1(path.read_bytes()).hexdigest()[:12]
    return f"{spec_name}|g{GRID}|t{THRESHOLD}|k{4}|{digest}"


def build_grids():
    """Return {tech name: colour grid}. Rasterise, falling back to the cache."""
    cache = {}
    if GRID_CACHE.exists():
        cache = json.loads(GRID_CACHE.read_text(encoding="utf-8"))
    grids, fresh, reused = {}, {}, {}
    for _group, entries in TECHS:
        for entry in entries:
            name, _slug, brand, filename = entry[:4]
            opts = entry[4] if len(entry) > 4 else {}
            path = SRC_DIR / filename
            key = _cache_key(path, name) + f"|{json.dumps(opts, sort_keys=True)}|c{CELL}"
            try:
                grid = _quantise(_downsample(_render(_logo_text(path, brand)), opts))
                fresh[key] = [[list(c) if c else None for c in row] for row in grid]
            except Exception as e:  # missing deps/sources -> cache
                print(f"  rasterize {name}: {type(e).__name__}: {e}")
                if key not in cache:
                    raise SystemExit(f"no cached grid for {name!r} and rasterisation failed")
                reused[key] = cache[key]
                grid = [[tuple(c) if c else None for c in row] for row in cache[key]]
            grids[name] = grid
    if fresh:
        merged = dict(cache)
        merged.update(fresh)
        GRID_CACHE.write_text(json.dumps(merged, indent=1), encoding="utf-8")
    print(f"grids: {len(fresh)} rasterised, {len(reused)} from cache")
    return grids


# ---------------------------------------------------------------------------
# Tile rendering
# ---------------------------------------------------------------------------

def text_width(name):
    return math.ceil(len(name) * LABEL_SIZE * CHAR_EM)


def tile_width(_name):
    """Every tile is CELL wide so the icons form one aligned grid."""
    return CELL


def label_attrs(name):
    """Condense (never widen) a label that would overflow its cell."""
    box = CELL - 2 * PAD
    if text_width(name) <= box:
        return ""
    return f' textLength="{box}" lengthAdjust="spacingAndGlyphs"'


def icon_rects(grid, x0, y0, theme):
    """Merge horizontal runs of same-colour cells into compact rects."""
    runs = {}
    for y, row in enumerate(grid):
        x = 0
        while x < len(row):
            cell = row[x]
            if cell:
                x2 = x
                while x2 < len(row) and row[x2] == cell:
                    x2 += 1
                color = _rgb_to_hex(theme_color(cell, theme))
                runs.setdefault(color, []).append(
                    (x0 + x * SCALE, y0 + y * SCALE, (x2 - x) * SCALE, SCALE)
                )
                x = x2
            else:
                x += 1
    parts = []
    for color, rects in runs.items():
        body = "".join(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}"/>' for rx, ry, rw, rh in rects)
        parts.append(f'<g fill="#{color}">{body}</g>')
    return "".join(parts)


def tile_fragment(name, brand, grid, theme, x):
    """One tech tile drawn at x: pixel icon + label centred under it."""
    icon_x = x + (CELL - ICON) // 2
    text_c = shift(brand, LABEL_SHIFT[theme])
    return (
        f'<g shape-rendering="crispEdges">{icon_rects(grid, icon_x, PAD, theme)}</g>'
        f'<text x="{x + CELL / 2:g}" y="{LABEL_BASELINE}" text-anchor="middle"{label_attrs(name)} '
        f'font-family="{FONT_STACK}" font-size="{LABEL_SIZE}" fill="#{text_c}">'
        f'{escape(name)}</text>'
    )


# ---------------------------------------------------------------------------
# Category headers: pixelarticon + label, fixed width so every row shares the
# same column grid (the four headers are the only variable-width thing left).
# ---------------------------------------------------------------------------
GROUPS = {
    "Java": ("package.svg", "java"),
    "AI": ("cpu.svg", "ai"),
    "Web": ("code.svg", "web"),
    "Data": ("database.svg", "data"),
}
GROUP_DIR = ROOT / "assets" / "ui" / "group"
GROUP_INK = {"light": "#57606a", "dark": "#9198a1"}


def header_fragment(group, theme, x):
    """Category header (pixelarticon + bold label) drawn at x."""
    filename, _slug = GROUPS[group]
    svg_text = (ROOT / "assets" / "ui" / filename).read_text(encoding="utf-8")
    paths = "".join(re.findall(r"<path[^>]*/>|<path[^>]*>[\s\S]*?</path>", svg_text))
    paths = re.sub(r'\sfill="[^"]*"', "", paths)
    ink = GROUP_INK[theme]
    top = (PAD + ICON - GROUP_ICON) // 2      # centre on the icon band
    return (
        f'<g transform="translate({x},{top})" fill="{ink}" shape-rendering="crispEdges">{paths}</g>'
        f'<text x="{x + GROUP_ICON + 4}" y="{top + 16}" font-family="{FONT_STACK}" '
        f'font-size="11" font-weight="700" fill="{ink}">{escape(group)}</text>'
    )


def row_width(groups):
    return len(groups) * GROUP_W + sum(len(entries) for _g, entries in groups) * CELL \
        + ROW_GAP * (len(groups) - 1)


def render_row(groups, grids, theme):
    """One row = one SVG, so the two categories can never be split by wrapping."""
    x, parts = 0, []
    for index, (group, entries) in enumerate(groups):
        if index:
            x += ROW_GAP
        parts.append(header_fragment(group, theme, x))
        x += GROUP_W
        for entry in entries:
            name, _slug, brand = entry[:3]
            parts.append(tile_fragment(name, brand, grids[name], theme, x))
            x += CELL
    width = row_width(groups)
    alt = " / ".join(f"{g}: " + ", ".join(e[0] for e in entries) for g, entries in groups)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{TILE_H}" '
        f'viewBox="0 0 {width} {TILE_H}" role="img">\n'
        f'  <title>{escape(alt)}</title>\n'
        f'  {"".join(parts)}\n'
        f'</svg>\n'
    )
def rows():
    return [TECHS[i:i + 2] for i in range(0, len(TECHS), 2)]


def row_slug(groups):
    return "-".join(GROUPS[g][1] for g, _e in groups)


def main():
    grids = build_grids()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for group_pair in rows():
        slug = row_slug(group_pair)
        for theme in ("light", "dark"):
            path = OUT_DIR / f"{slug}-{theme}.svg"
            path.write_text(render_row(group_pair, grids, theme), encoding="utf-8")
            written.append((path, row_width(group_pair)))
    expected = {f"{row_slug(r)}-{t}.svg" for r in rows() for t in ("light", "dark")}
    for old in OUT_DIR.glob("*.svg"):
        if old.name not in expected:
            old.unlink()
    # tiles and standalone headers are inlined into the rows now
    for stale in (ROOT / "assets" / "ui" / "tech", ROOT / "assets" / "ui" / "group"):
        if stale.is_dir():
            for f in stale.glob("*.svg"):
                f.unlink()
            stale.rmdir()
    for path, width in written:
        print(f"  {path.relative_to(ROOT)}  {width}x{TILE_H}  {path.stat().st_size // 1024}KB")


# ---------------------------------------------------------------------------
# README block
# ---------------------------------------------------------------------------
README_HEAD = '<h2 align="left"><img src="./assets/ui/server.svg"'
README_PATH = ROOT / "README.md"


def _picture(light, dark, alt, attrs):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}">'
            f'<img src="{light}"{attrs} alt="{alt}"></picture>')


def readme_section():
    """The Tech Stack block: two rows, two categories each, one image per row.

    Composing a row into a single SVG is what keeps it on one line - inline
    <picture> runs get wrapped by GitHub once they exceed the column width,
    while a single image is simply scaled down.
    """
    lines = ['<h2 align="left"><img src="./assets/ui/server.svg" width="24" height="24" '
             'align="absmiddle" alt="Stack" /> Tech Stack</h2>', ""]
    for group_pair in rows():
        slug = row_slug(group_pair)
        alt = " / ".join(f"{g}: " + ", ".join(e[0] for e in entries) for g, entries in group_pair)
        lines += [
            '<p align="left">' + _picture(f"./assets/ui/row/{slug}-light.svg",
                                          f"./assets/ui/row/{slug}-dark.svg", alt, "") + "</p>",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def write_readme():
    text = README_PATH.read_text(encoding="utf-8")
    head = text[: text.index(README_HEAD)]
    README_PATH.write_text(head + readme_section(), encoding="utf-8")
    print(f"updated {README_PATH.relative_to(ROOT)} Tech Stack block")


if __name__ == "__main__":
    import sys

    main()
    if "--readme" in sys.argv:
        write_readme()
