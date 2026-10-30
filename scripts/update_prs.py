#!/usr/bin/env python3
"""Refresh the profile's open-source PR section using the GitHub API.

Adapted from wuyak/wuyak's update_prs.py: keeps the race-safe search /
pagination, the per-project star fetching, and the SVG row rendering
(Pixelarticon icons by Gerrit Halfmann, MIT), with these changes:

- one small SVG per PR row instead of one big card per project: each row is
  wrapped in an <a> linking to the PR, so every row is clickable and jumps
  to its PR page (an <img>-embedded SVG cannot contain live links)
- rows drop the per-row repo name and star count: the card is per-project,
  so both were pure repetition (the project title line shows them once)
- the <summary> line acts as the card header, so there is no separate header
  band; rows stack seamlessly into the card (each row <img> uses align="top"
  to kill the inline descender gap, and the timeline spine runs from the
  first icon's centre to the last icon's centre)
- the project title line uses pixel-art icons + text links (folder / star,
  Pixelarticon) instead of shields badges, and the summary line uses pixel
  icons (check / circle / chevron) instead of emoji, for a unified look
- manual prose lives in scripts/repo_notes.json so code updates never
  clobber it
- fixed UTC+8 timezone (works without the system tz database)

The script only rewrites the region between the OPEN_SOURCE_PRS markers in
README.md and the SVGs under assets/. Generated region layout:

    <h4 align="left">[folder icon] <a><b>owner/repo</b></a> &nbsp;&nbsp;&nbsp;&nbsp; [star icon] <a><b>Nk stars</b></a></h4>

    > <about>                  # from repo_notes.json (optional)

    **What I did**: <did>      # from repo_notes.json (optional)

    <details>
    <summary>N PRs &nbsp;&nbsp;[check] X merged &nbsp;&nbsp;[circle] Y open &nbsp;&nbsp;(&nbsp;click to expand[chevron])</summary>

    <a href="https://github.com/<repo>/pull/<n>">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./assets/<slug>-<n>-dark.svg">
      <img src="./assets/<slug>-<n>-light.svg" width="100%" align="top" alt="#<n> <title> [TYPE] ...">
    </picture>
    </a>
    ... one block per PR, no blank lines between them ...

    [View all merged PRs in <repo> →](...)

    </details>

Requirements: Python 3.9+. GITHUB_TOKEN is optional but raises the API rate
limit; the workflow provides it automatically.
"""

import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- OPEN_SOURCE_PRS:START -->"
END = "<!-- OPEN_SOURCE_PRS:END -->"
NOTES_PATH = ROOT / "scripts" / "repo_notes.json"
ICONS_PATH = ROOT / "scripts" / "pr_icons.json"
STARS_CACHE_PATH = ROOT / "scripts" / "project-stars.json"
README_PATH = ROOT / "README.md"
ASSETS_DIR = ROOT / "assets"
ICONS = json.loads(ICONS_PATH.read_text(encoding="utf-8"))
USER_AGENT = "konlue-profile-updater"
# Fixed UTC+8 (China has no DST) instead of ZoneInfo: works everywhere
# without depending on the system tz database being installed.
TZ = timezone(timedelta(hours=8), "UTC+8")
# Star counts are cached for a day: they change slowly, and caching keeps
# local runs (and many-project setups) well inside the API rate limit.
STARS_TTL = timedelta(hours=24)
# Projects to showcase (comma-separated, overridable via PROFILE_REPOS).
# Only PRs to these repositories appear in the section; add a repo here (and
# to scripts/repo_notes.json for its intro text) to feature more projects.
DEFAULT_REPOS = "apache/shenyu,agentic-ai-java/argi,agentscope-ai/agentscope"
# Row geometry: 1000x62 px per row, stacked seamlessly (background matches
# the GitHub page colour, so no inline-image gaps remain).
ROW_W, ROW_H = 1000, 62
TITLE_MAX = 90  # titles longer than this are truncated with an ellipsis
# Pixel-art icons (Pixelarticon) used in the README chrome around the cards.
# folder/star sit in the project title line (22px, tuned under the 24px
# contact icons so the h4 line stays compact); check/circle/chevron are
# inline with 16px summary text, so they stay smaller.
#
# Every icon is wrapped in <picture>: GitHub wraps a bare <img> in a link to
# the asset's blob page, but leaves images inside <picture> alone. Keep the
# dark twin in sync with scripts/make_ui_dark.py.
def _icon(name, size, alt):
    return (f'<picture><source media="(prefers-color-scheme: dark)" '
            f'srcset="./assets/ui/{name}-dark.svg">'
            f'<img src="./assets/ui/{name}.svg" width="{size}" height="{size}" '
            f'align="absmiddle" alt="{alt}"></picture>')


UI = {
    "folder": _icon("folder", 22, "repository"),
    "star": _icon("star", 22, "stars"),
    "check": _icon("check", 16, "merged"),
    "circle": _icon("circle", 16, "open"),
    "chevron": _icon("chevron-down", 16, "expand"),
}


def search_query(username):
    return f"is:pr is:public author:{username} -user:{username}"


def fetch_prs(username, token):
    """All public PRs authored by the user in repositories they do not own."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    items = []
    total = None
    for page in range(1, 11):
        params = urlencode({
            "q": search_query(username),
            "sort": "created",
            "order": "desc",
            "per_page": 100,
            "page": page,
        })
        request = Request(f"https://api.github.com/search/issues?{params}", headers=headers)
        with urlopen(request, timeout=45) as response:
            data = json.load(response)
        if data.get("incomplete_results") or data["total_count"] > 1000:
            raise RuntimeError("GitHub returned an incomplete search; preserving the existing README")
        total = data["total_count"]
        items.extend(data["items"])
        if len(items) >= total:
            break
        if not data["items"]:
            raise RuntimeError("GitHub pagination ended early; preserving the existing README")
    unique = {item["id"]: item for item in items}
    if total is None or len(unique) != total:
        raise RuntimeError("Search changed during pagination; retry instead of publishing a partial list")
    result = []
    for item in unique.values():
        repo = item["repository_url"].removeprefix("https://api.github.com/repos/")
        if repo.split("/")[0].lower() == username.lower():
            continue  # defensive: -user: should already exclude these
        merged_at = item.get("pull_request", {}).get("merged_at")
        result.append({
            "repo": repo,
            "number": item["number"],
            "title": " ".join(item["title"].split()),
            "url": item["html_url"],
            "state": "merged" if merged_at else item["state"],
            "merged_at": merged_at,
        })
    return result


def fetch_projects(repos, token):
    """Star count per project, shown once next to the project title."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        cache = json.loads(STARS_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    projects = {}
    cache_dirty = False
    for repo in repos:
        entry = cache.get(repo) or {}
        try:
            fetched = datetime.fromisoformat(entry["fetched"])
            fresh = datetime.now(TZ).date() - fetched.date() < STARS_TTL
        except Exception:
            fresh = False
        if fresh:
            projects[repo] = {"stars": entry["stars"]}
            continue
        try:
            with urlopen(Request(f"https://api.github.com/repos/{repo}", headers=headers), timeout=30) as response:
                stars = json.load(response)["stargazers_count"]
            projects[repo] = {"stars": stars}
            cache[repo] = {"stars": stars, "fetched": datetime.now(TZ).date().isoformat()}
            cache_dirty = True
        except Exception as error:
            if "stars" in entry:
                print(f"star fetch failed for {repo} ({type(error).__name__}); using cached value")
                projects[repo] = {"stars": entry["stars"]}
            else:
                raise
    if cache_dirty:
        STARS_CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return projects


def kind(title):
    """Classify a PR by its conventional-commit prefix (wuyak's mapping)."""
    for prefixes, name in ((('fix', 'bug'), 'fix'), (('feat', 'add', 'implement'), 'feat'),
                           (('doc',), 'docs'), (('test',), 'test'),
                           (('ci', 'build', 'chore', 'refactor', 'perf'), 'tool')):
        if title.lower().lstrip().startswith(prefixes):
            return name
    return 'other'


def stars_label(stars):
    for size, suffix in ((1_000_000, 'm'), (1000, 'k')):
        if stars >= size:
            return f"{stars / size:.1f}".rstrip('0').rstrip('.') + suffix
    return str(stars)


def fmt_date(iso):
    if not iso:
        return "—"
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ).strftime("%Y-%m-%d")


def row_status(pr):
    """(right-hand label, colour) for a PR row."""
    category = kind(pr["title"])
    label = category.upper() if category != "other" else "PR"
    if pr["state"] == "merged":
        return f"[ {label} ] {fmt_date(pr['merged_at'])}", "green"
    if pr["state"] == "open":
        return f"[ {label} ] OPEN", "amber"
    return f"[ {label} ] CLOSED", "muted"


def render_row(pr, dark=False, position="middle"):
    """One SVG row (1000x62) for a single PR; the README links the whole row.

    position is "first", "middle" or "last": the timeline spine starts at the
    first icon's centre and ends at the last icon's centre, so the first row
    has no line above its icon and the last row none below it.
    """
    bg, text, muted, line, green = ('#0d1117', '#e6edf3', '#9dada8', '#334740', '#58c9aa') if dark else (
        '#ffffff', '#26322f', '#52625d', '#dfe7e4', '#16866e')
    amber = '#d29922' if dark else '#9a6700'
    right, tone = row_status(pr)
    right_color = {"green": green, "amber": amber, "muted": muted}[tone]
    category = kind(pr["title"])
    title = pr["title"] if len(pr["title"]) <= TITLE_MAX else pr["title"][:TITLE_MAX - 1].rstrip() + "…"

    if position == "first":
        spine = f'<path d="M66 31V{ROW_H}" stroke="{muted}" stroke-opacity="0.4" stroke-width="2"/>'
    elif position == "last":
        spine = '<path d="M66 0V31" stroke="{}" stroke-opacity="0.4" stroke-width="2"/>'.format(muted)
    elif position == "only":
        spine = ""
    else:
        spine = f'<path d="M66 0V{ROW_H}" stroke="{muted}" stroke-opacity="0.4" stroke-width="2"/>'

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ROW_W}" height="{ROW_H}" viewBox="0 0 {ROW_W} {ROW_H}" role="img">',
        f'<title>#{pr["number"]} {pr["title"]}</title>',
        '<!-- Pixelarticon icons: Gerrit Halfmann, MIT. -->',
        f'<rect width="{ROW_W}" height="{ROW_H}" fill="{bg}"/>',
        '<style>text{font-family:Inter,"Segoe UI",Arial,sans-serif}.mono{font-family:SFMono-Regular,Consolas,"Liberation Mono",Menlo,monospace}</style>',
        spine,
        f'<rect x="48" y="13" width="36" height="36" rx="3" fill="{bg}" stroke="{muted}" stroke-opacity="0.4"/>',
        f'<g transform="translate(54 19)" fill="{text}">',
    ]
    parts.extend(f'<path d="{path}"/>' for path in ICONS["SVG_ICONS"][category])
    parts += [
        '</g>',
        f'<text x="104" y="27" fill="{text}" font-size="15" font-weight="700">#{pr["number"]}</text>',
        f'<text x="104" y="49" fill="{muted}" font-size="13">{html.escape(title)}</text>',
        f'<text x="964" y="36" text-anchor="end" class="mono" fill="{right_color}" font-size="12" font-weight="700">{right}</text>',
        '</svg>',
    ]
    return "\n".join(parts) + "\n"


def row_alt(pr):
    right, _ = row_status(pr)
    return f"#{pr['number']} {pr['title']} {right}"


def render_repo_block(repo, prs, stars, notes, slug, username):
    merged = sum(1 for pr in prs if pr["state"] == "merged")
    opened = sum(1 for pr in prs if pr["state"] == "open")
    bits = [f"{len(prs)} PRs", f"{UI['check']} {merged} merged"]
    if opened:
        bits.append(f"{UI['circle']} {opened} open")
    repo_prs_url = f"https://github.com/{repo}/pulls?q=is%3Apr+author%3A{username}+is%3Amerged"

    # project title line: pixel icons + plain text links (no shields badges);
    # the star count is plain bold text (the repo link sits right next to it)
    title_line = (
        f'<h4 align="left">{UI["folder"]} '
        f'<a href="https://github.com/{repo}"><b>{repo}</b></a>'
        f' &nbsp;&nbsp;&nbsp;&nbsp; {UI["star"]} '
        f'<b>{stars_label(stars)}</b></h4>'
    )

    lines = [title_line, ""]
    note = notes.get(repo, {})
    if note.get("about"):
        lines += [f"> {note['about']}", '']
    if note.get("did"):
        lines += [f"**What I did**: {note['did']}", '']

    # One linked row per PR. No blank lines between blocks: they must stay in
    # a single HTML block so the rows stack without paragraph gaps. The
    # align="top" on each image kills the inline descender gap (~4px) that
    # would otherwise break both the stacked background and the timeline spine.
    lines += [
        "<details>",
        f"<summary>{'&nbsp;&nbsp;'.join(bits)} &nbsp;&nbsp;(&nbsp;click to expand{UI['chevron']})</summary>",
        "",
    ]
    for pr in prs:
        lines += [
            f'<a href="{pr["url"]}">',
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="./assets/{slug}-{pr["number"]}-dark.svg">',
            f'  <img src="./assets/{slug}-{pr["number"]}-light.svg" width="100%" align="top" alt="{html.escape(row_alt(pr), quote=True)}">',
            "</picture>",
            "</a>",
        ]
    lines += [
        "",
        f"[View all merged PRs in {repo} →]({repo_prs_url})",
        "",
        "</details>",
    ]
    return "\n".join(lines)


def render(prs, projects, notes, username):
    by_repo = {}
    for pr in prs:
        by_repo.setdefault(pr["repo"], []).append(pr)
    repos_sorted = sorted(by_repo.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    merged_total = sum(1 for pr in prs if pr["state"] == "merged")

    search_url = "https://github.com/pulls?" + urlencode({"q": search_query(username) + " is:merged"})
    lines = []
    for repo, repo_prs in repos_sorted:
        slug = repo.replace("/", "--")
        lines.append(render_repo_block(repo, repo_prs, projects[repo]["stars"], notes, slug, username))
        lines.append("")
    lines.append(f"[View all merged Pull Requests →]({search_url})")
    return "\n".join(lines)


def update_readme(current, generated):
    if current.count(START) != 1 or current.count(END) != 1:
        raise ValueError("README must contain exactly one pair of PR section markers")
    before, rest = current.split(START, 1)
    if END not in rest:
        raise ValueError("README section markers are reversed")
    _, after = rest.split(END, 1)
    return before + START + "\n\n" + generated + "\n" + END + after


def write_row_svgs(by_repo):
    """Write one SVG per PR row (light + dark); drop stale SVGs from older runs."""
    ASSETS_DIR.mkdir(exist_ok=True)
    expected = set()
    for repo, repo_prs in by_repo.items():
        slug = repo.replace("/", "--")
        count = len(repo_prs)
        for index, pr in enumerate(repo_prs):
            if count == 1:
                position = "only"
            elif index == 0:
                position = "first"
            elif index == count - 1:
                position = "last"
            else:
                position = "middle"
            for theme in ("light", "dark"):
                name = f"{slug}-{pr['number']}-{theme}.svg"
                expected.add(name)
                (ASSETS_DIR / name).write_text(
                    render_row(pr, dark=theme == "dark", position=position), encoding="utf-8"
                )
    for old in ASSETS_DIR.glob("*.svg"):
        if old.name not in expected:
            old.unlink()  # stale row from a previous layout
    return len(expected)


def main():
    username = os.environ.get("PROFILE_USER", "konlue").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", username):
        raise ValueError("Invalid GitHub username")
    notes = json.loads(NOTES_PATH.read_text(encoding="utf-8")) if NOTES_PATH.exists() else {}
    current = README_PATH.read_text(encoding="utf-8")
    token = os.environ.get("GITHUB_TOKEN", "")
    prs = fetch_prs(username, token)
    repos_filter = [r.strip() for r in os.environ.get("PROFILE_REPOS", DEFAULT_REPOS).split(",") if r.strip()]
    prs = [pr for pr in prs if pr["repo"] in repos_filter]
    repos = sorted({pr["repo"] for pr in prs})
    projects = fetch_projects(repos, token)

    by_repo = {}
    for pr in prs:
        by_repo.setdefault(pr["repo"], []).append(pr)

    updated = update_readme(current, render(prs, projects, notes, username))
    if updated != current:
        README_PATH.write_text(updated, encoding="utf-8")
    svg_count = write_row_svgs(by_repo)

    merged_total = sum(1 for pr in prs if pr["state"] == "merged")
    print(f"Profile updated: {len(prs)} PRs ({merged_total} merged) across {len(repos)} projects, "
          f"{svg_count} row SVGs written to assets/")


if __name__ == "__main__":
    main()
