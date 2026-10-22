#!/usr/bin/env python3
"""Refresh the profile's open-source PR section using the GitHub API.

Adapted from wuyak/wuyak's update_prs.py: keeps the race-safe search /
pagination, per-project star fetching, and the SVG timeline-card rendering
(Pixelarticon icons by Gerrit Halfmann, MIT), with these changes:

- one card per project instead of one flat card, so each project keeps its
  own intro prose and its list stays collapsible (<details>)
- the card shows every PR (merged / open / closed), with the status carried
  by the right-hand label: merged -> green date, open -> amber OPEN,
  closed -> muted CLOSED
- manual prose lives in scripts/repo_notes.json so code updates never
  clobber it
- fixed UTC+8 timezone (works without the system tz database)

The script only rewrites the region between the OPEN_SOURCE_PRS markers in
README.md and the SVGs under assets/. Generated region layout:

    > As of <date>: <N> PRs across <M> projects, <K> merged.

    <h3 align="left">
      <a href="..."><img title badge /></a>
      <a href=".../stargazers"><img stars badge /></a>
    </h3>

    > <about>                  # from repo_notes.json (optional)

    **What I did**: <did>      # from repo_notes.json (optional)

    <details>
    <summary>N PRs · ✅ X merged · 🟡 Y open · ⛔ Z closed (click to expand)</summary>

    <a href="...">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="./assets/<slug>-dark.svg">
      <img src="./assets/<slug>-light.svg" width="100%" alt="...">
    </picture>
    </a>

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
# Badge colours assigned to projects in order of PR count (descending).
BADGE_COLORS = ["4A154B", "0A66C2", "2E7D32", "C72C48", "1C3C6C", "6DB33F", "FF6B6B", "409EFF"]
# Projects to showcase (comma-separated, overridable via PROFILE_REPOS).
# Only PRs to these repositories appear in the section; add a repo here (and
# to scripts/repo_notes.json for its intro text) to feature more projects.
DEFAULT_REPOS = "apache/shenyu,agentic-ai-java/argi"


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
    """Star count per project, drawn on each card row (cached for STARS_TTL)."""
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


def badge_label(repo):
    """Shields.io badge label: literal dashes need '--', slashes are encoded."""
    return quote(repo.replace("-", "--"), safe="")


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


def render_card(prs, slug, projects, dark=False):
    """One SVG timeline card for a single project (light or dark theme)."""
    bg, text, muted, line, green = ('#0d1117', '#e6edf3', '#9dada8', '#334740', '#58c9aa') if dark else (
        '#ffffff', '#26322f', '#52625d', '#dfe7e4', '#16866e')
    amber = '#d29922' if dark else '#9a6700'
    merged = sum(1 for pr in prs if pr["state"] == "merged")
    opened = sum(1 for pr in prs if pr["state"] == "open")
    header = f"{len(prs)} PRS · {merged} MERGED"
    if opened:
        header += f" · {opened} OPEN"
    height = 100 + max(1, len(prs)) * 62
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img">',
        f'<title>{slug.replace("--", "/")} open-source contributions</title>',
        '<!-- Pixelarticon icons: Gerrit Halfmann, MIT. -->',
        f'<rect width="1000" height="{height}" fill="{bg}"/>',
        '<style>text{font-family:Inter,"Segoe UI",Arial,sans-serif}.mono{font-family:SFMono-Regular,Consolas,"Liberation Mono",Menlo,monospace}</style>',
        f'<text x="36" y="36" fill="{text}" font-size="14" font-weight="700">{header}</text>',
        f'<text x="964" y="36" text-anchor="end" class="mono" fill="{green}" font-size="12" font-weight="700">AUTO-SYNC</text>',
        f'<path d="M36 56H964" stroke="{line}"/>',
    ]
    if len(prs) > 1:
        parts.append(f'<path d="M66 101V{101 + (len(prs) - 1) * 62}" stroke="{muted}" stroke-opacity="0.4" stroke-width="2"/>')
    for index, pr in enumerate(prs):
        y = 101 + index * 62
        category = kind(pr["title"])
        label = category.upper() if category != "other" else "PR"
        title = pr["title"] if len(pr["title"]) <= 76 else pr["title"][:75].rstrip() + "…"
        if pr["state"] == "merged":
            right, right_color = f"[ {label} ] {fmt_date(pr['merged_at'])}", green
        elif pr["state"] == "open":
            right, right_color = f"[ {label} ] OPEN", amber
        else:
            right, right_color = f"[ {label} ] CLOSED", muted
        parts += [
            f'<rect x="48" y="{y - 18}" width="36" height="36" rx="3" fill="{bg}" stroke="{muted}" stroke-opacity="0.4"/>',
            f'<g transform="translate(54 {y - 12})" fill="{text}">',
        ]
        parts.extend(f'<path d="{path}"/>' for path in ICONS["SVG_ICONS"][category])
        parts += [
            '</g>',
            f'<text x="104" y="{y - 4}" fill="{text}" font-size="15" font-weight="700">{html.escape(pr["repo"])} <tspan fill="{muted}" font-weight="400">/ #{pr["number"]}</tspan></text>',
            f'<text x="104" y="{y + 18}" fill="{muted}" font-size="13">{html.escape(title)}</text>',
            f'<text x="762" y="{y + 6}" text-anchor="end" class="mono" fill="{text}" font-size="16" font-weight="700">{stars_label(projects[pr["repo"]]["stars"])}</text>',
            f'<path d="{ICONS["STAR_ICON"]}" transform="translate(770 {y - 12})" fill="{text}"/>',
            f'<text x="964" y="{y + 5}" text-anchor="end" class="mono" fill="{right_color}" font-size="12" font-weight="700">{right}</text>',
        ]
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def render_repo_block(repo, prs, stars, notes, color, slug, username):
    label = badge_label(repo)
    merged = sum(1 for pr in prs if pr["state"] == "merged")
    opened = sum(1 for pr in prs if pr["state"] == "open")
    closed = len(prs) - merged - opened
    bits = [f"{len(prs)} PRs", f"✅ {merged} merged"]
    if opened:
        bits.append(f"🟡 {opened} open")
    if closed:
        bits.append(f"⛔ {closed} closed")
    repo_prs_url = f"https://github.com/{repo}/pulls?q=is%3Apr+author%3A{username}+is%3Amerged"

    lines = [
        '<h3 align="left">',
        f'  <a href="https://github.com/{repo}"><img src="https://img.shields.io/badge/{label}-{color}?style=flat-square" alt="{repo}" /></a>',
        f'  <a href="https://github.com/{repo}/stargazers"><img src="https://img.shields.io/github/stars/{repo}?style=flat-square" alt="{repo} stars" /></a>',
        '</h3>',
        '',
    ]
    note = notes.get(repo, {})
    if note.get("about"):
        lines += [f"> {note['about']}", '']
    if note.get("did"):
        lines += [f"**What I did**: {note['did']}", '']
    lines += [
        "<details>",
        f"<summary>{' · '.join(bits)} &nbsp;(click to expand)</summary>",
        "",
        f'<a href="{repo_prs_url}">',
        "<picture>",
        f'  <source media="(prefers-color-scheme: dark)" srcset="./assets/{slug}-dark.svg">',
        f'  <img src="./assets/{slug}-light.svg" width="100%" alt="{repo}: {len(prs)} PRs, {merged} merged">',
        "</picture>",
        "</a>",
        "",
        f"[View all merged PRs in {repo} →]({repo_prs_url})",
        "",
        "</details>",
    ]
    return "\n".join(lines)


def render(prs, projects, notes, username):
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    by_repo = {}
    for pr in prs:
        by_repo.setdefault(pr["repo"], []).append(pr)
    repos_sorted = sorted(by_repo.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    merged_total = sum(1 for pr in prs if pr["state"] == "merged")

    search_url = "https://github.com/pulls?" + urlencode({"q": search_query(username) + " is:merged"})
    lines = [
        f"> As of {today}: **{len(prs)} PRs** submitted across **{len(by_repo)} projects**, **{merged_total} merged**.",
        "",
    ]
    for index, (repo, repo_prs) in enumerate(repos_sorted):
        color = BADGE_COLORS[index % len(BADGE_COLORS)]
        slug = repo.replace("/", "--")
        lines.append(render_repo_block(repo, repo_prs, projects[repo]["stars"], notes, color, slug, username))
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
    return before + START + "\n" + generated + "\n" + END + after


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

    updated = update_readme(current, render(prs, projects, notes, username))
    if updated != current:
        README_PATH.write_text(updated, encoding="utf-8")

    by_repo = {}
    for pr in prs:
        by_repo.setdefault(pr["repo"], []).append(pr)
    ASSETS_DIR.mkdir(exist_ok=True)
    for repo, repo_prs in by_repo.items():
        slug = repo.replace("/", "--")
        for theme in ("light", "dark"):
            (ASSETS_DIR / f"{slug}-{theme}.svg").write_text(
                render_card(repo_prs, slug, projects, dark=theme == "dark"), encoding="utf-8"
            )

    merged_total = sum(1 for pr in prs if pr["state"] == "merged")
    print(f"Profile updated: {len(prs)} PRs ({merged_total} merged) across {len(repos)} projects, "
          f"{len(by_repo) * 2} SVGs written to assets/")


if __name__ == "__main__":
    main()
