#!/usr/bin/env python3
"""Generates generated/trophies.svg from the GitHub REST API — a self-hosted
substitute for github-profile-trophy.vercel.app, which frequently returns
402/503 once its shared free-tier quota is exhausted. Run with GH_USERNAME
and GITHUB_TOKEN set in the environment (both provided automatically inside
GitHub Actions).
"""
import datetime
import json
import os
import urllib.request

USERNAME = os.environ.get("GH_USERNAME", "muhammad-jiku")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

THEME = {
    "bg": "#1a1b27",
    "border": "#30354f",
    "title": "#7aa2f7",
    "text": "#c0caf5",
    "muted": "#565f89",
}

TIER_COLORS = {
    "NONE": "#414868",
    "BRONZE": "#cd7f32",
    "SILVER": "#c0c0c0",
    "GOLD": "#ffd700",
    "PLATINUM": "#7df9ff",
}


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


def tier_for(value, bronze, silver, gold, platinum):
    if value >= platinum:
        return "PLATINUM"
    if value >= gold:
        return "GOLD"
    if value >= silver:
        return "SILVER"
    if value >= bronze:
        return "BRONZE"
    return "NONE"


def build_trophies_svg(user, non_fork_repos):
    stars = sum(r.get("stargazers_count", 0) for r in non_fork_repos)
    forks = sum(r.get("forks_count", 0) for r in non_fork_repos)
    followers = user.get("followers", 0)
    repo_count = user.get("public_repos", 0)
    languages = {r.get("language") for r in non_fork_repos if r.get("language")}
    created = datetime.datetime.strptime(user["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    years = max((datetime.datetime.utcnow() - created).days // 365, 0)

    trophies = [
        ("⭐", "Stars", stars, tier_for(stars, 5, 20, 50, 100)),
        ("👥", "Followers", followers, tier_for(followers, 5, 15, 30, 60)),
        ("📦", "Repositories", repo_count, tier_for(repo_count, 10, 30, 60, 120)),
        ("🍴", "Forks", forks, tier_for(forks, 1, 5, 15, 30)),
        ("🧠", "Languages", len(languages), tier_for(len(languages), 3, 5, 7, 10)),
        ("📅", "Years Active", years, tier_for(years, 1, 2, 3, 5)),
    ]

    card_w, card_h, gap = 130, 100, 10
    width = card_w * len(trophies) + gap * (len(trophies) - 1)
    height = card_h

    cards = []
    for i, (icon, label, value, tier) in enumerate(trophies):
        x = i * (card_w + gap)
        color = TIER_COLORS[tier]
        cards.append(f'''
    <g transform="translate({x}, 0)">
      <rect x="0.5" y="0.5" width="{card_w - 1}" height="{card_h - 1}" rx="8" fill="{THEME['bg']}" stroke="{color}" stroke-width="1.5" />
      <text x="{card_w / 2}" y="30" text-anchor="middle" font-size="22">{icon}</text>
      <text x="{card_w / 2}" y="55" text-anchor="middle" fill="{THEME['text']}" font-size="20" font-weight="700" font-family="'Segoe UI', Ubuntu, Sans-Serif">{value}</text>
      <text x="{card_w / 2}" y="72" text-anchor="middle" fill="{THEME['muted']}" font-size="11" font-family="'Segoe UI', Ubuntu, Sans-Serif">{label}</text>
      <text x="{card_w / 2}" y="88" text-anchor="middle" fill="{color}" font-size="10" font-weight="700" letter-spacing="1" font-family="'Segoe UI', Ubuntu, Sans-Serif">{tier}</text>
    </g>''')

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{''.join(cards)}
</svg>'''


def main():
    os.makedirs("generated", exist_ok=True)

    user = http_get(f"https://api.github.com/users/{USERNAME}")
    repos = fetch_all_repos(USERNAME)
    non_fork_repos = [r for r in repos if not r.get("fork") and not r.get("archived")]

    with open(os.path.join("generated", "trophies.svg"), "w", encoding="utf-8") as f:
        f.write(build_trophies_svg(user, non_fork_repos))

    print("Wrote generated/trophies.svg")


if __name__ == "__main__":
    main()
