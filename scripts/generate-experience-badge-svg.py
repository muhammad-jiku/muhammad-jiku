#!/usr/bin/env python3
"""Generates generated/experience-badge.svg — a flat, shields.io-style badge
showing years of professional experience, computed from START_YEAR rather
than hand-updated every year. Self-hosted for the same reason as the other
scripts in this folder: nothing here should depend on a third-party
service's uptime or billing.
"""
import datetime
import os

OUT_DIR = "generated"
START_YEAR = 2020

# Matches the badge color already used for the Portfolio/streak-stats/
# profile-views badges elsewhere in the README (#0e75b6), so this one
# doesn't introduce a fifth color into the header badge row.
LABEL_BG = "#555555"
VALUE_BG = "#0e75b6"
TEXT_COLOR = "#ffffff"

LABEL_TEXT = "Experience"


def char_width(font_size):
    # Verdana averages ~0.6x its font-size per character — the same rough
    # heuristic shields.io itself uses to lay out badges without a real
    # font-metrics engine.
    return font_size * 0.6


def build_badge_svg(value_text):
    font_size = 11
    pad = 10
    cw = char_width(font_size)

    label_width = round(len(LABEL_TEXT) * cw + pad * 2)
    value_width = round(len(value_text) * cw + pad * 2)
    total_width = label_width + value_width
    height = 20

    label_text_x = label_width / 2
    value_text_x = label_width + value_width / 2
    text_y = height / 2 + font_size * 0.35

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}">
  <linearGradient id="smooth" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1" />
    <stop offset="1" stop-opacity=".1" />
  </linearGradient>
  <clipPath id="round">
    <rect width="{total_width}" height="{height}" rx="3" fill="#fff" />
  </clipPath>
  <g clip-path="url(#round)">
    <rect width="{label_width}" height="{height}" fill="{LABEL_BG}" />
    <rect x="{label_width}" width="{value_width}" height="{height}" fill="{VALUE_BG}" />
    <rect width="{total_width}" height="{height}" fill="url(#smooth)" />
  </g>
  <g fill="{TEXT_COLOR}" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="{font_size}">
    <text x="{label_text_x}" y="{text_y}">{LABEL_TEXT}</text>
    <text x="{value_text_x}" y="{text_y}">{value_text}</text>
  </g>
</svg>'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    years = datetime.date.today().year - START_YEAR
    value_text = f"{years}+ Years"

    with open(os.path.join(OUT_DIR, "experience-badge.svg"), "w", encoding="utf-8") as f:
        f.write(build_badge_svg(value_text))

    print(f"Wrote {OUT_DIR}/experience-badge.svg ({value_text})")


if __name__ == "__main__":
    main()
