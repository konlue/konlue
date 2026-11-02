#!/usr/bin/env python3
"""Generate the pixel divider that separates the project cards in README.md.

The PR cards have no visible bottom edge: GitHub gives <details> no margin, the
row SVGs share the page background, and <style>/<class> are stripped by the
sanitizer, so there is no way to add spacing with CSS. The divider solves it
with the canvas itself - a 1000x32 strip whose upper two thirds are transparent
(that空白 is the breathing room <details> cannot provide), with the pixel rule
sitting just above the bottom edge.

Same 1000px canvas as the PR row SVGs, so the rule lines up with the card edges.
The -dark twin is written by make_ui_dark.py, which owns the Primer ink map.

Usage:  python3 scripts/make_divider.py && python3 scripts/make_ui_dark.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "ui" / "divider.svg"

# Dashes stop at x=464 / resume at 536 so the three blocks (481-519) sit on
# clean background; both segments are 464px, i.e. exactly 29 dash cycles, so no
# dash is clipped at either end.
SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="32" viewBox="0 0 1000 32" role="img">
<title>divider</title>
<path d="M0 27H464M536 27H1000" fill="none" stroke="#d1d9e0" stroke-width="2" stroke-dasharray="8 8" shape-rendering="crispEdges"/>
<g fill="#afb8c1" shape-rendering="crispEdges">
<rect x="481" y="24" width="6" height="6"/>
<rect x="497" y="24" width="6" height="6"/>
<rect x="513" y="24" width="6" height="6"/>
</g>
</svg>
"""


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(SVG, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
