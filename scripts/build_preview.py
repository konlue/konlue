#!/usr/bin/env python3
"""Build a local preview of README.md that mimics GitHub's rendering.

Inlines every local ./assets/*.svg as a data URI so the page works offline,
simulates GitHub's markdown metrics (908px column, 16px/1.5, GitHub fonts and
heading rules), and adds a light/dark theme toggle (the <picture> sources are
swapped by JS so both themes can be reviewed in one page).

Usage:  python3 scripts/build_preview.py   ->  .preview.html
"""

import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
OUT = ROOT / ".preview.html"

CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  margin: 0; background: #ffffff; color: #1f2328;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans",
    Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
  font-size: 16px; line-height: 1.5;
}
body.dark { background: #0d1117; color: #e6edf3; color-scheme: dark; }
.wrap { max-width: 908px; margin: 0 auto; padding: 32px 16px 64px; }
h2 { font-size: 24px; font-weight: 600; margin: 24px 0 16px;
     padding-bottom: .3em; border-bottom: 1px solid #d1d9e0; }
body.dark h2 { border-color: #3d444d; }
h4 { font-size: 16px; font-weight: 600; margin: 24px 0 16px; }
p { margin: 0 0 16px; }
a { color: #0969da; text-decoration: none; }
body.dark a { color: #4493f8; }
blockquote { margin: 0 0 16px; padding: 0 1em; color: #59636e;
             border-left: .25em solid #d1d9e0; }
body.dark blockquote { color: #9198a1; border-color: #3d444d; }
img { vertical-align: baseline; max-width: 100%; height: auto; }
details { margin: 0 0 16px; }
summary { cursor: pointer; }
summary::marker { color: #59636e; }
code { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
       "Liberation Mono", monospace; font-size: 85%; padding: .2em .4em;
       background: rgba(129,139,152,.12); border-radius: 6px; }
.toolbar { position: sticky; top: 0; z-index: 9; display: flex; gap: 8px;
  justify-content: flex-end; padding: 8px 16px; background: inherit;
  border-bottom: 1px solid #d1d9e0; }
body.dark .toolbar { border-color: #3d444d; }
.toolbar button { font: inherit; font-size: 13px; padding: 4px 12px;
  border: 1px solid #d1d9e0; border-radius: 6px; background: #f6f8fa;
  color: #1f2328; cursor: pointer; }
body.dark .toolbar button { background: #21262d; border-color: #3d444d; color: #e6edf3; }
"""

JS = """
const btn = document.getElementById('theme-btn');
function apply(dark) {
  document.body.classList.toggle('dark', dark);
  btn.textContent = dark ? 'Light theme' : 'Dark theme';
  document.querySelectorAll('picture').forEach(pic => {
    const img = pic.querySelector('img');
    const src = pic.querySelector('source');
    if (!img || !src) return;
    const light = img.getAttribute('data-light');
    const darkSrc = src.getAttribute('data-dark');
    if (dark && darkSrc) { img.src = darkSrc; }
    else if (light) { img.src = light; }
  });
}
let dark = false;
btn.addEventListener('click', () => { dark = !dark; apply(dark); });
"""


def data_uri(path: Path) -> str:
    mime = {
        ".svg": "image/svg+xml",
        ".gif": "image/gif",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "application/octet-stream")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def inline_assets(html: str) -> str:
    def repl(m):
        rel = m.group(2)
        path = ROOT / rel.lstrip("./")
        if not path.exists():
            print("MISSING:", rel)
            return m.group(0)
        return m.group(1) + data_uri(path) + m.group(3)

    # src="..." and srcset="..." attributes pointing at ./assets/...
    html = re.sub(r'(src=")(\./assets/[^"]+)(")', repl, html)
    html = re.sub(r'(srcset=")(\./assets/[^"]+)(")', repl, html)
    return html


def tag_pictures(html: str) -> str:
    """Tag light/dark sources so the JS toggle can swap them."""
    def repl(m):
        block = m.group(0)
        # remember the data-URI values on the img/source elements
        return block

    # data-light / data-dark attributes for the toggle
    html = re.sub(
        r'<img([^>]*?)src="(data:[^"]+)"([^>]*)>',
        lambda m: f'<img{m.group(1)}src="{m.group(2)}" data-light="{m.group(2)}"{m.group(3)}>',
        html,
    )
    html = re.sub(
        r'<source([^>]*?)srcset="(data:[^"]+)"([^>]*)>',
        lambda m: f'<source{m.group(1)}srcset="{m.group(2)}" data-dark="{m.group(2)}"{m.group(3)}>',
        html,
    )
    return html


def main():
    md = README.read_text(encoding="utf-8")
    body = inline_assets(md)
    body = tag_pictures(body)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>README preview - konlue</title>
<style>{CSS}</style>
</head>
<body>
<div class="toolbar"><button id="theme-btn" type="button">Dark theme</button></div>
<div class="wrap">
{body}
</div>
<script>{JS}</script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
