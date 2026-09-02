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
# introducing a fourth color scheme. "dot" was briefly GitHub's own
# contribution-graph green, but that clashed against the chart's own blue
# line/area — using the same accent purple as the title/total text instead
# keeps the dots visibly "part of" this chart rather than looking pasted on.
THEME = {
    "bg": "#1a1b27",
    "border": "#30354f",
    "title": "#7aa2f7",
    "text": "#c0caf5",
    "muted": "#565f89",
    "accent": "#bb9af7",
    "area": "#7aa2f7",
    "dot": "#bb9af7",
}

# The reference charts this replaced only ever showed one month; showing a
# full year here made 365 points/dots look congested. Trimmed to the most
# recent window instead — a rolling 30-day view still says something
# meaningful about recent activity without the visual noise.
WINDOW_DAYS = 30

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
    # One point per day, in chronological order, trimmed to the most recent
    # WINDOW_DAYS — the header's own total stays the all-time count from the
    # API, only the plotted line/dots are windowed.
    all_days = [d for week in weeks for d in week["contributionDays"]]
    days = all_days[-WINDOW_DAYS:]

    width, height = 495, 215
    pad_left, pad_right, pad_top, pad_bottom = 44, 15, 42, 46
    plot_width = width - pad_left - pad_right
    plot_height = height - pad_top - pad_bottom
    baseline_y = pad_top + plot_height

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
    area_path = (
        f"M {points[0][0]:.1f},{baseline_y:.1f} "
        + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        + f" L {points[-1][0]:.1f},{baseline_y:.1f} Z"
    )

    # One dot marker per day — now only up to WINDOW_DAYS points, so sized
    # up from the earlier tiny full-year radius (1.3) to something that
    # actually reads as a marker rather than a speck.
    dot_svg = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{THEME["dot"]}" />'
        for x, y in points
    )

    # X-axis reads as a plain day count (1, 5, 10, ... up to WINDOW_DAYS),
    # matching the reference charts' plain-number style. Gridlines are drawn
    # at every day (a noticeably finer mesh now that there are only
    # WINDOW_DAYS of them to draw), labels only every 5th to stay readable.
    label_step = 5
    x_grid_ticks = [(points[i][0], i + 1) for i in range(n + 1)]
    x_label_ticks = [(x, day) for x, day in x_grid_ticks if day == 1 or day % label_step == 0]

    # Vertical gridlines at each day tick, horizontal gridlines at several
    # round contribution-count values — the "square" plot-area grid the
    # reference charts have and this one was missing.
    grid_svg = "".join(
        f'<line x1="{x:.1f}" y1="{pad_top}" x2="{x:.1f}" y2="{baseline_y:.1f}" '
        f'stroke="{THEME["border"]}" stroke-width="0.5" />'
        for x, _ in x_grid_ticks
    )

    y_tick_count = 8
    y_ticks = [round(max_count * i / y_tick_count) for i in range(y_tick_count + 1)]
    y_grid_svg = "".join(
        f'<line x1="{pad_left}" y1="{pad_top + plot_height * (1 - v / max_count):.1f}" '
        f'x2="{width - pad_right}" y2="{pad_top + plot_height * (1 - v / max_count):.1f}" '
        f'stroke="{THEME["border"]}" stroke-width="0.5" />'
        for v in y_ticks
    )
    y_label_svg = "".join(
        f'<text x="{pad_left - 8}" y="{pad_top + plot_height * (1 - v / max_count) + 3:.1f}" '
        f'fill="{THEME["muted"]}" font-size="9" text-anchor="end">{v}</text>'
        for v in y_ticks
    )

    x_label_svg = "".join(
        f'<text x="{x:.1f}" y="{height - pad_bottom + 16}" fill="{THEME["muted"]}" font-size="10" text-anchor="middle">{day}</text>'
        for x, day in x_label_ticks
    )

    y_axis_center = pad_top + plot_height / 2

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{THEME['bg']}" stroke="{THEME['border']}" />
  <text x="25" y="24" fill="{THEME['title']}" font-size="16" font-weight="700" font-family="'Segoe UI', Ubuntu, Sans-Serif">
    Contribution Activity
  </text>
  <text x="470" y="24" fill="{THEME['accent']}" font-size="12" font-weight="700" text-anchor="end" font-family="'Segoe UI', Ubuntu, Sans-Serif">
    {total} total
  </text>
  <text x="470" y="34" fill="{THEME['muted']}" font-size="9" text-anchor="end" font-family="'Segoe UI', Ubuntu, Sans-Serif">
    last {WINDOW_DAYS} days shown
  </text>
  <g font-family="'Segoe UI', Ubuntu, Sans-Serif">
    <rect x="{pad_left}" y="{pad_top}" width="{plot_width}" height="{plot_height}" fill="none" stroke="{THEME['border']}" />
    {grid_svg}{y_grid_svg}
    <path d="{area_path}" fill="{THEME['area']}" fill-opacity="0.25" stroke="none" />
    <path d="{line_path}" fill="none" stroke="{THEME['area']}" stroke-width="1.5" />
    {dot_svg}
    {y_label_svg}
    {x_label_svg}
    <text x="{pad_left + plot_width / 2:.1f}" y="{height - 8}" fill="{THEME['muted']}" font-size="10" text-anchor="middle">Days</text>
    <text x="12" y="{y_axis_center:.1f}" fill="{THEME['muted']}" font-size="10" text-anchor="middle" transform="rotate(-90 12 {y_axis_center:.1f})">Contributions</text>
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
