#!/usr/bin/env python3
"""Generates generated/activity-graph.svg from GitHub's own GraphQL contribution
calendar, so the README's activity chart doesn't depend on any third-party
service's uptime/billing (the previous embed, github-readme-activity-graph.vercel.app,
went down with a 402 DEPLOYMENT_DISABLED — this replaces it with something we own).
Run with GH_USERNAME and GITHUB_TOKEN set in the environment (both provided
automatically inside GitHub Actions).
"""
import json
import os
import urllib.request

USERNAME = os.environ.get("GH_USERNAME", "muhammad-jiku")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = "generated"

# Matches the palette already used by generate-stats-svg.py's cards, so this
# chart sits visually consistent with the rest of the README rather than
# introducing a fourth color scheme.
THEME = {
    "bg": "#1a1b27",
    "border": "#30354f",
    "title": "#7aa2f7",
    "text": "#c0caf5",
    "muted": "#565f89",
    "accent": "#bb9af7",
    "area": "#7aa2f7",
}

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
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


def fetch_contribution_calendar(username):
    body = json.dumps({"query": QUERY, "variables": {"login": username}}).encode("utf-8")
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
        payload = json.loads(resp.read().decode("utf-8"))
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build_activity_graph_svg(calendar):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    # One point per day, in chronological order — a full year, matching
    # what the previous third-party embed showed.
    days = [d for week in weeks for d in week["contributionDays"]]

    width, height = 495, 195
    pad_left, pad_right, pad_top, pad_bottom = 30, 15, 35, 30
    plot_width = width - pad_left - pad_right
    plot_height = height - pad_top - pad_bottom

    counts = [d["contributionCount"] for d in days]
    max_count = max(counts) if counts and max(counts) > 0 else 1
    n = max(len(days) - 1, 1)

    def point(i, count):
        x = pad_left + plot_width * i / n
        y = pad_top + plot_height * (1 - count / max_count)
        return x, y

    points = [point(i, c) for i, c in enumerate(counts)]

    # A smooth-ish area fill under the daily contribution line, closed back
    # down to the baseline — same visual language as the third-party chart
    # it replaces, drawn with plain SVG rather than any charting library.
    line_path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    baseline_y = pad_top + plot_height
    area_path = (
        f"M {points[0][0]:.1f},{baseline_y:.1f} "
        + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        + f" L {points[-1][0]:.1f},{baseline_y:.1f} Z"
    )

    # One tick per month boundary actually present in the data, so the
    # x-axis reads as real dates rather than evenly-spaced guesses.
    month_ticks = []
    seen_months = set()
    for i, d in enumerate(days):
        month_key = d["date"][:7]
        if month_key not in seen_months:
            seen_months.add(month_key)
            month_index = int(d["date"][5:7]) - 1
            x, _ = points[i]
            month_ticks.append((x, MONTH_LABELS[month_index]))

    tick_svg = "".join(
        f'<text x="{x:.1f}" y="{height - 8}" fill="{THEME["muted"]}" font-size="10" text-anchor="middle">{label}</text>'
        for x, label in month_ticks
    )

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{THEME['bg']}" stroke="{THEME['border']}" />
  <text x="25" y="24" fill="{THEME['title']}" font-size="16" font-weight="700" font-family="'Segoe UI', Ubuntu, Sans-Serif">
    Contribution Activity
  </text>
  <text x="470" y="24" fill="{THEME['accent']}" font-size="12" font-weight="700" text-anchor="end" font-family="'Segoe UI', Ubuntu, Sans-Serif">
    {total} total
  </text>
  <path d="{area_path}" fill="{THEME['area']}" fill-opacity="0.25" stroke="none" />
  <path d="{line_path}" fill="none" stroke="{THEME['area']}" stroke-width="1.5" />
  <g font-family="'Segoe UI', Ubuntu, Sans-Serif">{tick_svg}
  </g>
</svg>'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    calendar = fetch_contribution_calendar(USERNAME)

    with open(os.path.join(OUT_DIR, "activity-graph.svg"), "w", encoding="utf-8") as f:
        f.write(build_activity_graph_svg(calendar))

    print(f"Wrote {OUT_DIR}/activity-graph.svg")


if __name__ == "__main__":
    main()
