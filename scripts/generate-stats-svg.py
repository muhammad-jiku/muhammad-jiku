#!/usr/bin/env python3
"""Generates generated/stats.svg and generated/languages.svg from the GitHub REST API,
so the README's stats cards don't depend on any third-party service's uptime/quota.
Run with GH_USERNAME and GITHUB_TOKEN set in the environment (both provided automatically
inside GitHub Actions).
"""
import json
import os
import urllib.request

USERNAME = os.environ.get("GH_USERNAME", "muhammad-jiku")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = "generated"

THEME = {
    "bg": "#1a1b27",
    "border": "#30354f",
    "title": "#7aa2f7",
    "text": "#c0caf5",
    "muted": "#565f89",
    "accent": "#bb9af7",
}

LANGUAGE_COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Python": "#3572A5",
    "PHP": "#4F5D95",
    "Java": "#b07219",
    "Dockerfile": "#384d54",
    "EJS": "#a91e50",
    "Shell": "#89e051",
    "SCSS": "#c6538c",
}
DEFAULT_LANGUAGE_COLOR = "#8b949e"


def http_get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_repos(username):
    repos = []
    page = 1
    while True:
        batch = http_get(f"https://api.github.com/users/{username}/repos?per_page=100&page={page}")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def build_stats_svg(user, non_fork_repos):
    total_stars = sum(r.get("stargazers_count", 0) for r in non_fork_repos)
    total_forks = sum(r.get("forks_count", 0) for r in non_fork_repos)
    rows = [
        ("Public Repos", user.get("public_repos", 0)),
        ("Total Stars Earned", total_stars),
        ("Total Forks", total_forks),
        ("Followers", user.get("followers", 0)),
    ]

    width, height = 495, 195
    row_y_start = 70
    row_gap = 30

    row_svg = []
    for i, (label, value) in enumerate(rows):
        y = row_y_start + i * row_gap
        row_svg.append(f'''
    <text x="25" y="{y}" fill="{THEME['text']}" font-size="14">{label}:</text>
    <text x="470" y="{y}" fill="{THEME['accent']}" font-size="14" font-weight="700" text-anchor="end">{value}</text>''')

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{THEME['bg']}" stroke="{THEME['border']}" />
  <text x="25" y="35" fill="{THEME['title']}" font-size="18" font-weight="700" font-family="'Segoe UI', Ubuntu, Sans-Serif">
    {user.get('name', USERNAME)}'s GitHub Stats
  </text>
  <g font-family="'Segoe UI', Ubuntu, Sans-Serif">{''.join(row_svg)}
  </g>
</svg>'''


def build_languages_svg(non_fork_repos):
    lang_bytes = {}
    for repo in non_fork_repos:
        try:
            langs = http_get(repo["languages_url"])
        except Exception:
            continue
        for lang, num_bytes in langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + num_bytes

    total = sum(lang_bytes.values()) or 1
    top_langs = sorted(lang_bytes.items(), key=lambda kv: -kv[1])[:6]

    width, height = 495, 55 + 32 * max(len(top_langs), 1)
    bar_x, bar_width_max = 25, 445

    bars = []
    y = 55
    for lang, num_bytes in top_langs:
        pct = 100 * num_bytes / total
        bar_width = max(bar_width_max * pct / 100, 3)
        color = LANGUAGE_COLORS.get(lang, DEFAULT_LANGUAGE_COLOR)
        bars.append(f'''
    <text x="{bar_x}" y="{y}" fill="{THEME['text']}" font-size="13">{lang}</text>
    <text x="470" y="{y}" fill="{THEME['muted']}" font-size="12" text-anchor="end">{pct:.1f}%</text>
    <rect x="{bar_x}" y="{y + 6}" width="{bar_width_max}" height="7" rx="3.5" fill="{THEME['border']}" />
    <rect x="{bar_x}" y="{y + 6}" width="{bar_width:.1f}" height="7" rx="3.5" fill="{color}" />''')
        y += 32

    if not top_langs:
        bars.append(f'<text x="25" y="60" fill="{THEME["muted"]}" font-size="13">No language data yet.</text>')

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{THEME['bg']}" stroke="{THEME['border']}" />
  <text x="25" y="35" fill="{THEME['title']}" font-size="18" font-weight="700" font-family="'Segoe UI', Ubuntu, Sans-Serif">
    Most Used Languages
  </text>
  <g font-family="'Segoe UI', Ubuntu, Sans-Serif">{''.join(bars)}
  </g>
</svg>'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    user = http_get(f"https://api.github.com/users/{USERNAME}")
    repos = fetch_all_repos(USERNAME)
    non_fork_repos = [r for r in repos if not r.get("fork") and not r.get("archived")]

    with open(os.path.join(OUT_DIR, "stats.svg"), "w", encoding="utf-8") as f:
        f.write(build_stats_svg(user, non_fork_repos))

    with open(os.path.join(OUT_DIR, "languages.svg"), "w", encoding="utf-8") as f:
        f.write(build_languages_svg(non_fork_repos))

    print(f"Wrote {OUT_DIR}/stats.svg and {OUT_DIR}/languages.svg")


if __name__ == "__main__":
    main()
