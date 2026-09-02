#!/usr/bin/env python3
"""Generates one self-hosted, shields.io-style SVG per badge referenced in
README.md, using real brand icons sourced once from simple-icons (bundled
as scripts/data/simple-icons.json — MIT licensed, no live fetch needed at
generation time). Replaces every img.shields.io/badge/... embed with a
local file, for the same reason as the rest of this folder.

Unlike the other generators here, this one also rewrites README.md itself
(shields.io URLs never change on their own — there's nothing to
regenerate daily about them, just badge files to produce once and a
one-time set of README references to update).
"""
import json
import os
import re
import urllib.parse

OUT_DIR = os.path.join("generated", "badges")
ICONS_PATH = os.path.join("scripts", "data", "simple-icons.json")
README_PATH = "README.md"

FONT_FAMILY = "Verdana,Geneva,DejaVu Sans,sans-serif"
DEFAULT_LABEL_BG = "#555555"


def load_icons():
    with open(ICONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def slugify(*parts):
    text = "-".join(p for p in parts if p).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def char_width(font_size):
    return font_size * 0.6


def build_badge_svg(icons, label, value, color, logo, logo_color, large):
    font_size = 14 if large else 11
    height = 28 if large else 20
    pad = 12 if large else 10
    cw = char_width(font_size)
    icon_size = 15 if large else 11
    icon_gap = icon_size + 6 if logo else 0

    value_color = f"#{color}" if not color.startswith("#") else color
    label_bg = DEFAULT_LABEL_BG if value else value_color

    label_width = round(len(label) * cw + pad * 2 + icon_gap)
    segments = [(label, label_bg, label_width)]
    if value:
        value_width = round(len(value) * cw + pad * 2)
        segments.append((value, value_color, value_width))

    total_width = sum(w for _, _, w in segments)

    parts = [f'<rect width="{total_width}" height="{height}" rx="3" fill="{segments[0][1]}" />']
    x = 0
    for i, (text, bg, w) in enumerate(segments):
        if i > 0:
            parts.append(f'<rect x="{x}" width="{w}" height="{height}" fill="{bg}" />')
        x += w

    icon_path = icons.get(logo) if logo else None
    if icon_path:
        icon_x = pad
        icon_y = (height - icon_size) / 2
        # simple-icons glyphs are drawn on a 24x24 viewBox — scaled down
        # to icon_size via a nested <svg>, simpler and more reliable than
        # hand-computing a transform matrix per icon.
        parts.append(
            f'<svg x="{icon_x:.1f}" y="{icon_y:.1f}" width="{icon_size}" height="{icon_size}" '
            f'viewBox="0 0 24 24"><path fill="{logo_color}" d="{icon_path}" /></svg>'
        )

    text_y = height / 2 + font_size * 0.35
    x = 0
    for i, (text, bg, w) in enumerate(segments):
        text_x = x + w / 2 + (icon_gap / 2 if i == 0 and icon_path else 0)
        parts.append(
            f'<text x="{text_x:.1f}" y="{text_y:.1f}" fill="#ffffff" text-anchor="middle" '
            f'font-family="{FONT_FAMILY}" font-size="{font_size}" font-weight="600">{escape_xml(text)}</text>'
        )
        x += w

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}">
  {''.join(parts)}
</svg>'''


def escape_xml(value):
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


BADGE_URL_RE = re.compile(
    r'https://img\.shields\.io/badge/([^"\'\s?)]+)(\?[^"\'\s)]*)?'
)


def parse_badge_url(match):
    path = urllib.parse.unquote(match.group(1))
    query = match.group(2) or ""
    params = urllib.parse.parse_qs(query.lstrip("?"))

    segments = path.split("-")
    color = segments[-1]
    if len(segments) >= 3:
        label = segments[0]
        value = "-".join(segments[1:-1])
    else:
        label = segments[0]
        value = None

    logo = params.get("logo", [None])[0]
    logo_color = params.get("logoColor", ["white"])[0]
    large = params.get("style", [""])[0] == "for-the-badge"
    return label, value, color, logo, logo_color, large


# The header row (next to Profile views / Experience) wants the footer's
# solid-color, brand-name-only look — not the header's original two-tone
# label:value style — but at the same small height as its neighboring
# badges, not the footer's larger `style=for-the-badge` height. Neither
# combination exists among the badges actually embedded in the README, so
# these are generated explicitly rather than discovered by parsing it.
HEADER_BADGES = [
    ("header-portfolio.svg", "Portfolio", "jikmunn", "0e75b6", "vercel"),
    ("header-linkedin.svg", "LinkedIn", None, "0077B5", "linkedin"),
    ("header-facebook.svg", "Facebook", None, "1877F2", "facebook"),
    ("header-whatsapp.svg", "WhatsApp", None, "25D366", "whatsapp"),
    ("header-gmail.svg", "Gmail", None, "D14836", "gmail"),
]


def generate_header_badges(icons):
    for filename, label, value, color, logo in HEADER_BADGES:
        svg = build_badge_svg(icons, label, value, color, logo, "white", large=False)
        with open(os.path.join(OUT_DIR, filename), "w", encoding="utf-8") as out:
            out.write(svg)


def main():
    icons = load_icons()
    os.makedirs(OUT_DIR, exist_ok=True)
    generate_header_badges(icons)

    with open(README_PATH, encoding="utf-8") as f:
        readme = f.read()

    seen = {}

    def replace(match):
        full_url = match.group(0)
        label, value, color, logo, logo_color, large = parse_badge_url(match)

        filename = slugify(label, value or "") + ("-large" if large else "") + ".svg"
        if filename not in seen:
            svg = build_badge_svg(icons, label, value, color, logo, logo_color, large)
            with open(os.path.join(OUT_DIR, filename), "w", encoding="utf-8") as out:
                out.write(svg)
            seen[filename] = True

        return f"{OUT_DIR}/{filename}".replace("\\", "/")

    new_readme = BADGE_URL_RE.sub(replace, readme)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_readme)

    print(f"Wrote {len(seen)} badge SVGs to {OUT_DIR}/ and rewrote {README_PATH}")


if __name__ == "__main__":
    main()
