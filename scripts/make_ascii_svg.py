#!/usr/bin/env python3
"""
make_ascii_svg.py — convert source-prepped.png into a monochrome ASCII
portrait that "types" itself in, row by row, using SMIL clip-path wipes.

Usage:
    python scripts/make_ascii_svg.py [source-prepped.png] [avi-ascii.svg]
"""
import sys
from PIL import Image

# bright (sparse) -> dark (dense); leading space clears background to nothing
RAMP = " .`:-=+*cs#%@"
GAMMA = 1.7   # >1 biases mapping toward sparse/light glyphs; only true
              # darks (hair, deep shadow, glasses) reach the dense end

COLS = 100
FONT_W = 6.2       # px per character cell (monospace-ish)
FONT_H = 11.5       # px per row
FILL = "#8fd3a3"    # single light color — no rainbow, keeps it clean
BG = "#0d1117"
FRAME_ACCENT = "#30363d"
ROW_DURATION = 0.55   # seconds for one row's left-to-right wipe
ROW_STAGGER = 0.045    # seconds between successive row starts


def image_to_ascii_rows(path: str, cols: int = COLS):
    img = Image.open(path).convert("L")
    w, h = img.size
    # character cells are taller than wide, so compress rows accordingly
    aspect_correct = 0.46
    rows = max(1, round(cols * (h / w) * aspect_correct))
    img_small = img.resize((cols, rows), Image.LANCZOS)

    ramp_len = len(RAMP)
    out = []
    for y in range(rows):
        line = []
        for x in range(cols):
            v = img_small.getpixel((x, y))  # 0=black .. 255=white
            darkness = (255 - v) / 255
            darkness = darkness ** GAMMA  # push midtones toward sparse end
            idx = int(darkness * (ramp_len - 1))
            line.append(RAMP[idx])
        out.append("".join(line))
    return out


def escape(ch: str) -> str:
    return {"&": "&amp;", "<": "&lt;", ">": "&gt;"}.get(ch, ch)


def build_svg(rows, out_path: str):
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)

    pad_x, pad_top, pad_bottom = 24, 40, 24
    width = n_cols * FONT_W + pad_x * 2
    height = n_rows * FONT_H + pad_top + pad_bottom

    total_anim = (n_rows - 1) * ROW_STAGGER + ROW_DURATION + 0.15

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {width:.1f} {height:.1f}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">'
    )
    parts.append(f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>')
    parts.append(
        f'<rect x="0.5" y="0.5" width="{width-1:.1f}" height="{height-1:.1f}" rx="10" '
        f'fill="none" stroke="{FRAME_ACCENT}" stroke-width="1"/>'
    )
    # terminal title bar dots
    parts.append(
        '<circle cx="20" cy="20" r="5" fill="#ff5f56"/>'
        '<circle cx="38" cy="20" r="5" fill="#ffbd2e"/>'
        '<circle cx="56" cy="20" r="5" fill="#27c93f"/>'
    )
    parts.append(
        f'<text x="{width/2:.1f}" y="24" font-size="11" fill="#6e7681" '
        f'text-anchor="middle">rik@github: ~$ ./portrait.sh</text>'
    )

    text_x = pad_x
    text_y0 = pad_top + FONT_H

    for i, row in enumerate(rows):
        safe_row = "".join(escape(c) for c in row)
        y = text_y0 + i * FONT_H
        row_w = n_cols * FONT_W
        start = i * ROW_STAGGER

        clip_id = f"clip{i}"
        parts.append(f'<clipPath id="{clip_id}">')
        parts.append(f'  <rect x="{text_x - 2:.1f}" y="{y - FONT_H:.1f}" width="0" height="{FONT_H:.1f}">')
        parts.append(
            f'    <animate attributeName="width" from="0" to="{row_w + 4:.1f}" '
            f'begin="{start:.3f}s" dur="{ROW_DURATION}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
        )
        parts.append('  </rect>')
        parts.append('</clipPath>')

        parts.append(f'<g clip-path="url(#{clip_id})">')
        parts.append(
            f'<text x="{text_x:.1f}" y="{y:.1f}" font-size="{FONT_H*0.92:.2f}" '
            f'fill="{FILL}" xml:space="preserve">{safe_row}</text>'
        )
        parts.append('</g>')

        # small block cursor riding the wipe edge, fades out after the row lands
        cursor_x = f'{text_x - 2:.1f}'
        parts.append(
            f'<rect x="0" y="{y - FONT_H + 1.5:.1f}" width="{FONT_W*0.85:.2f}" height="{FONT_H*0.85:.2f}" fill="{FILL}" opacity="0">'
        )
        parts.append(
            f'  <animate attributeName="x" from="{cursor_x}" to="{text_x + row_w:.1f}" '
            f'begin="{start:.3f}s" dur="{ROW_DURATION}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
        )
        parts.append(
            f'  <animate attributeName="opacity" values="0.9;0.9;0" '
            f'keyTimes="0;0.85;1" begin="{start:.3f}s" dur="{ROW_DURATION}s" fill="freeze"/>'
        )
        parts.append('</rect>')

    parts.append(
        f'<text x="{pad_x}" y="{height-8:.1f}" font-size="10" fill="#6e7681" opacity="0">'
        f'rik@github:~$ whoami Rik'
        f'<animate attributeName="opacity" from="0" to="1" begin="{total_anim:.3f}s" dur="0.4s" fill="freeze"/>'
        f'</text>'
    )

    parts.append('</svg>')

    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out_path}  ({n_cols}x{n_rows} chars, {width:.0f}x{height:.0f}px, ~{total_anim:.1f}s anim)")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
    dst = sys.argv[2] if len(sys.argv) > 2 else "avi-ascii.svg"
    rows = image_to_ascii_rows(src)
    build_svg(rows, dst)
