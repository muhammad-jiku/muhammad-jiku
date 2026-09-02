#!/usr/bin/env python3
"""Generates generated/typing.svg — a self-contained, animated "typing"
header, replacing the readme-typing-svg.demolab.com embed. Needs no live
API data (unlike the other generators in this folder) — it's pure SMIL
animation over a fixed set of lines, so this could even be run once and
left alone, but it's wired into the same daily workflow as everything
else for consistency.
"""
import os

OUT_DIR = "generated"

FONT_FAMILY = "'Fira Code', monospace"
FONT_SIZE = 28
FONT_WEIGHT = 600
COLOR = "#0E75B6"
WIDTH = 650
HEIGHT = 50

TYPE_MS_PER_CHAR = 60
ERASE_MS_PER_CHAR = 30
PAUSE_MS = 1000

LINES = [
    "Hi \U0001F44B, I'm Muhammad Azizul Hoque Jiku",
    "Full-Stack Web & Mobile App Developer",
    "Next.js | MERN | PERN | React Native",
    "Building fast, accessible, production-grade apps",
]


def char_width(font_size):
    # Fira Code is monospace, so a fixed per-character width (unlike the
    # heuristic used for the proportional-font badges elsewhere in this
    # folder) is actually accurate here, not just approximate.
    return font_size * 0.6


def escape_xml(value):
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_typing_svg():
    cw = char_width(FONT_SIZE)
    center_x = WIDTH / 2
    baseline_y = HEIGHT / 2 + FONT_SIZE * 0.35

    segments = []
    for line in LINES:
        type_dur = len(line) * TYPE_MS_PER_CHAR
        erase_dur = len(line) * ERASE_MS_PER_CHAR
        segments.append({"line": line, "type": type_dur, "hold": PAUSE_MS, "erase": erase_dur})

    total_ms = sum(s["type"] + s["hold"] + s["erase"] for s in segments)
    total_s = total_ms / 1000

    clip_defs = []
    text_els = []
    t = 0
    for i, seg in enumerate(segments):
        line = seg["line"]
        full_width = len(line) * cw
        # Each line is centered once fully typed, so the reveal has to
        # start from that line's own left edge, not the canvas's — a
        # left-anchored clip rect growing from x=0 would reveal a
        # centered <text> from the wrong side entirely.
        line_x = center_x - full_width / 2
        t_start = t
        t_type_end = t_start + seg["type"]
        t_hold_end = t_type_end + seg["hold"]
        t_erase_end = t_hold_end + seg["erase"]
        t = t_erase_end

        # keyTimes must be strictly increasing and span exactly [0, 1] —
        # the leading 0-width point is only needed once, at t=0 itself,
        # for the very first line; every other line's "closed" state at
        # t=0 is already implied by starting the timeline at width 0.
        key_times = [0]
        values = [0]
        if t_start > 0:
            key_times.append(round(t_start / total_ms, 6))
            values.append(0)
        key_times += [
            round(t_type_end / total_ms, 6),
            round(t_hold_end / total_ms, 6),
            round(t_erase_end / total_ms, 6),
        ]
        values += [full_width, full_width, 0]
        if t_erase_end < total_ms:
            key_times.append(1)
            values.append(0)

        clip_id = f"clip{i}"
        clip_defs.append(f'''
    <clipPath id="{clip_id}">
      <rect x="{line_x:.1f}" y="0" height="{HEIGHT}">
        <animate attributeName="width" dur="{total_s:.3f}s" repeatCount="indefinite"
          keyTimes="{';'.join(str(k) for k in key_times)}"
          values="{';'.join(f'{v:.1f}' for v in values)}" />
      </rect>
    </clipPath>''')

        text_els.append(f'''
    <g clip-path="url(#{clip_id})">
      <text x="{line_x:.1f}" y="{baseline_y:.1f}" fill="{COLOR}" font-family="{FONT_FAMILY}"
        font-size="{FONT_SIZE}" font-weight="{FONT_WEIGHT}" text-anchor="start">{escape_xml(line)}</text>
    </g>''')

    return f'''<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <defs>{''.join(clip_defs)}
  </defs>
  {''.join(text_els)}
</svg>'''


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(os.path.join(OUT_DIR, "typing.svg"), "w", encoding="utf-8") as f:
        f.write(build_typing_svg())

    print(f"Wrote {OUT_DIR}/typing.svg")


if __name__ == "__main__":
    main()
