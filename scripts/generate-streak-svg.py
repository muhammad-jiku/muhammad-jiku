#!/usr/bin/env python3
"""Generates generated/streak-stats.svg — total/current/longest contribution
streaks, computed from GitHub's own GraphQL contribution calendar. Replaces
the streak-stats.demolab.com embed for the same reason as the rest of this
folder: nothing here should depend on a third-party service's uptime or
shared-quota errors.
Run with GH_USERNAME and GITHUB_TOKEN set in the environment (both provided
automatically inside GitHub Actions).
"""
import datetime
import json
import os
import urllib.request

USERNAME = os.environ.get("GH_USERNAME", "muhammad-jiku")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = "generated"
START_YEAR = 2020

THEME = {
    "bg": "#1a1b27",
    "border": "#30354f",
    "title": "#7aa2f7",
    "text": "#c0caf5",
    "muted": "#565f89",
    "accent": "#bb9af7",
    "divider": "#30354f",
}

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_all_days(username):
    """GitHub's contributionsCollection only accepts spans up to one year,
    so full history since START_YEAR is fetched one calendar year at a
    time and merged — the same technique real streak-tracking tools use.
    """
    today = datetime.date.today()
    days = []
    for year in range(START_YEAR, today.year + 1):
        start = datetime.date(year, 1, 1)
        end = min(datetime.date(year, 12, 31), today)
        if start > today:
            break
        variables = {
            "login": username,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        }
        payload = graphql(QUERY, variables)
        weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for week in weeks:
            days.extend(week["contributionDays"])

    # Dedupe (year-boundary queries can overlap by a day) and sort
    # chronologically so streak-walking below is well-defined.
    by_date = {d["date"]: d["contributionCount"] for d in days}
    return sorted(by_date.items())


def compute_streaks(sorted_days):
    total = sum(count for _, count in sorted_days)

    # Longest streak — the longest run of consecutive nonzero days
    # anywhere in the history.
    longest_len, longest_range = 0, (None, None)
    run_start, run_len = None, 0
    for date_str, count in sorted_days:
        if count > 0:
            if run_len == 0:
                run_start = date_str
            run_len += 1
            if run_len > longest_len:
                longest_len = run_len
                longest_range = (run_start, date_str)
        else:
            run_len = 0

    # Current streak — the trailing run of nonzero days ending at the most
    # recent day, tolerating today itself still being zero (the day isn't
    # over yet), matching how streak-stats.demolab.com itself behaves.
    current_len, current_range = 0, (None, None)
    idx = len(sorted_days) - 1
    if idx >= 0 and sorted_days[idx][1] == 0:
        idx -= 1
    end_date = sorted_days[idx][0] if idx >= 0 else None
    while idx >= 0 and sorted_days[idx][1] > 0:
        current_len += 1
        start_date = sorted_days[idx][0]
        idx -= 1
    current_range = (start_date, end_date) if current_len else (None, None)

    first_date = sorted_days[0][0] if sorted_days else None
    return {
        "total": total,
        "total_range": (first_date, "Present"),
        "current": current_len,
        "current_range": current_range,
        "longest": longest_len,
        "longest_range": longest_range,
    }


def fmt_date(date_str, with_year=True):
    d = datetime.date.fromisoformat(date_str)
    pattern = "%b %-d, %Y" if with_year else "%b %-d"
    return d.strftime(pattern) if os.name != "nt" else d.strftime(pattern.replace("%-d", "%#d"))


def fmt_range(range_tuple, with_year=True):
    """Matches the real streak-stats.demolab.com card's own formatting,
    confirmed against a live screenshot of it: the current streak never
    shows a year on either side ("Aug 31 - Sep 2"), while total/longest
    always show the full year on every real date ("Dec 26, 2024 - Mar 4,
    2025"), with "Present" as-is when that's the end of the range.
    """
    start, end = range_tuple
    if not start:
        return "—"
    if end == "Present":
        return f"{fmt_date(start)} - Present"
    return f"{fmt_date(start, with_year)} - {fmt_date(end, with_year)}"


def build_streak_svg(stats):
    width, height = 495, 165
    col_width = width / 3

    columns = [
        ("Total Contributions", stats["total"], fmt_range(stats["total_range"])),
        ("Current Streak", stats["current"], fmt_range(stats["current_range"], with_year=False)),
        ("Longest Streak", stats["longest"], fmt_range(stats["longest_range"])),
    ]

    parts = []
    for i, (label, value, date_range) in enumerate(columns):
        cx = col_width * i + col_width / 2
        parts.append(f'''
    <text x="{cx:.1f}" y="70" fill="{THEME['accent']}" font-size="32" font-weight="700" text-anchor="middle">{value}</text>
    <text x="{cx:.1f}" y="100" fill="{THEME['text']}" font-size="13" text-anchor="middle">{label}</text>
    <text x="{cx:.1f}" y="120" fill="{THEME['muted']}" font-size="11" text-anchor="middle">{date_range}</text>''')
        if i > 0:
            x = col_width * i
            parts.append(f'<line x1="{x:.1f}" y1="30" x2="{x:.1f}" y2="{height - 20}" stroke="{THEME["divider"]}" />')

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{THEME['bg']}" stroke="{THEME['border']}" />
  <g font-family="'Segoe UI', Ubuntu, Sans-Serif">{''.join(parts)}
  </g>
</svg>'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    days = fetch_all_days(USERNAME)
    stats = compute_streaks(days)

    with open(os.path.join(OUT_DIR, "streak-stats.svg"), "w", encoding="utf-8") as f:
        f.write(build_streak_svg(stats))

    print(f"Wrote {OUT_DIR}/streak-stats.svg — total={stats['total']} current={stats['current']} longest={stats['longest']}")


if __name__ == "__main__":
    main()
