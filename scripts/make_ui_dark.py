#!/usr/bin/env python3
"""Generate the dark-mode twins of the UI icons in assets/ui/.

GitHub wraps a bare <img> in a link to the file's blob page, but leaves images
inside <picture> alone - so every decorative icon in README.md is emitted as
<picture><source media="(prefers-color-scheme: dark)" srcset="...-dark.svg">.
This script produces the -dark.svg halves by re-inking the light icons with
GitHub's Primer dark palette (the pixelarticons glyphs are flat, single-fill
paths, so a fill swap is enough).

Usage:  python3 scripts/make_ui_dark.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "assets" / "ui"

# light ink -> dark ink (GitHub Primer light/dark pairs)
INK = {
    "#57606a": "#9198a1",   # fg.muted
    "#2da44e": "#3fb950",   # success
    "#bf8700": "#d29922",   # attention
    "#e3b341": "#e3b341",   # star yellow reads fine on both
    "#ea4335": "#f85149",   # danger (Gmail red)
    "#2e7d32": "#3fb950",   # link green
}

ICONS = ("mail", "link", "git-pull-request", "folder", "star",
         "check", "circle", "chevron-down", "server")


def reink(svg_text):
    changed = set()

    def repl(m):
        light = m.group(1).lower()
        dark = INK.get(light)
        if not dark:
            return m.group(0)
        changed.add(light)
        return f'fill="{dark}"'

    out = re.sub(r'fill="(#[0-9a-fA-F]{6})"', repl, svg_text)
    return out, changed


def main():
    written = 0
    for name in ICONS:
        src = SRC_DIR / f"{name}.svg"
        if not src.exists():
            raise SystemExit(f"missing {src.relative_to(ROOT)}")
        text, changed = reink(src.read_text(encoding="utf-8"))
        unknown = [c for c in re.findall(r'fill="(#[0-9a-fA-F]{6})"', text)
                   if c.lower() not in {v.lower() for v in INK.values()}]
        if unknown:
            print(f"  {name}: warning, unmapped fill(s) {sorted(set(unknown))}", file=sys.stderr)
        out = SRC_DIR / f"{name}-dark.svg"
        out.write_text(text, encoding="utf-8")
        written += 1
        print(f"  {out.relative_to(ROOT)}  (re-inked {', '.join(sorted(changed)) or 'nothing'})")
    print(f"wrote {written} dark icons")


if __name__ == "__main__":
    main()
