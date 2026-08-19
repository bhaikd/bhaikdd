#!/usr/bin/env python3
"""
make_info_card.py — hand-authored neofetch-style SVG info panel.
Fades/slides each line in on a short stagger, like it's printing next
to the ASCII portrait. STATIC=1 emits a frozen (already-visible) frame
for local Quick Look previews.

Usage:
    python scripts/make_info_card.py [info-card.svg]
    STATIC=1 python scripts/make_info_card.py
"""
import os
import sys

WIDTH, HEIGHT = 620, 460
BG = "#0d1117"
FRAME_ACCENT = "#30363d"
LABEL_COLOR = "#79c0ff"
VALUE_COLOR = "#c9d1d9"
DIM = "#6e7681"
ACCENT = "#8fd3a3"

TITLE_BAR_H = 34
PAD_X = 26
LINE_H = 30

STATIC = os.environ.get("STATIC") == "1"

ROWS = [
    ("whoami", "Rik", "big"),
    ("Now", "AI/ML student @ Sikkim Manipal University", "row"),
    ("Roles", "Google Gemini Student Ambassador · GDG Kolkata", "row"),
    ("Stack", "TypeScript/React · Next.js · Python · Prisma/Postgres · Supabase", "row"),
    ("Building", "Joga Bonita — full-stack FIFA WC26 platform w/ AI + ML predictions", "row"),
    ("Building", "SentinelStay — crisis coordination platform, Gemini-powered", "row"),
    ("Highlights", "ML Cardiovascular Risk Diagnostic Pipeline", "row"),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(out_path: str):
    parts = []
    parts.append(
        f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
    )
    parts.append(f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>')
    parts.append(
        f'<rect x="0.5" y="0.5" width="{WIDTH-1}" height="{HEIGHT-1}" rx="10" '
        f'fill="none" stroke="{FRAME_ACCENT}" stroke-width="1"/>'
    )
    parts.append(
        '<circle cx="20" cy="20" r="5" fill="#ff5f56"/>'
        '<circle cx="38" cy="20" r="5" fill="#ffbd2e"/>'
        '<circle cx="56" cy="20" r="5" fill="#27c93f"/>'
    )
    parts.append(
        f'<text x="{WIDTH/2}" y="24" font-size="11" fill="{DIM}" text-anchor="middle">'
        f'rik@github: ~$ ./whoami --neofetch</text>'
    )
    parts.append(f'<line x1="0" y1="{TITLE_BAR_H}" x2="{WIDTH}" y2="{TITLE_BAR_H}" stroke="{FRAME_ACCENT}"/>')

    y = TITLE_BAR_H + 46
    stagger = 0.16
    dur = 0.45

    def group_open(delay):
        if STATIC:
            return '<g opacity="1">'
        return (
            f'<g opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.2f}s" '
            f'dur="{dur}s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'from="-10 0" to="0 0" begin="{delay:.2f}s" dur="{dur}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
        )

    for i, (label, value, kind) in enumerate(ROWS):
        delay = i * stagger
        if kind == "big":
            block = (
                f'{group_open(delay)}'
                f'<text x="{PAD_X}" y="{y}" font-size="26" font-weight="700" fill="{ACCENT}">'
                f'&gt; {esc(value)}_</text>'
                f'</g>'
            )
            y += LINE_H + 14
            parts.append(f'<line x1="{PAD_X}" y1="{y-30}" x2="{WIDTH-PAD_X}" y2="{y-30}" stroke="{FRAME_ACCENT}"/>')
        else:
            label_txt = f'{label}'
            block = (
                f'{group_open(delay)}'
                f'<text x="{PAD_X}" y="{y}" font-size="14" fill="{LABEL_COLOR}">{esc(label_txt)}</text>'
                f'<text x="{PAD_X+118}" y="{y}" font-size="13.5" fill="{VALUE_COLOR}">{esc(value)}</text>'
                f'</g>'
            )
            y += LINE_H
        parts.append(block)

    # color swatch strip at the bottom, like real neofetch output
    y += 14
    swatches = ["#0d1117", "#ff5f56", "#27c93f", "#ffbd2e", "#79c0ff", "#8fd3a3", "#c9d1d9", "#ffffff"]
    sw_delay = len(ROWS) * stagger
    for i, c in enumerate(swatches):
        sx = PAD_X + i * 26
        op = '1' if STATIC else '0'
        extra = "" if STATIC else (
            f'<animate attributeName="opacity" from="0" to="1" '
            f'begin="{sw_delay + i*0.03:.2f}s" dur="0.3s" fill="freeze"/>'
        )
        parts.append(f'<rect x="{sx}" y="{y}" width="22" height="18" rx="3" fill="{c}" opacity="{op}">{extra}</rect>')

    with open(out_path, "w") as f:
        f.write("\n".join(parts) + "\n</svg>\n")
    print(f"wrote {out_path}{' (static)' if STATIC else ''}")


if __name__ == "__main__":
    dst = sys.argv[1] if len(sys.argv) > 1 else "info-card.svg"
    build_svg(dst)
