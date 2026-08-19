#!/usr/bin/env python3
"""
render_heatmap_svg.py — render data/contributions.json as the classic
53-week x 7-day calendar of rounded, colored boxes. Reveals once with a
diagonal, line-after-line slide-down, then freezes (no looping "glow").

Usage:
    python scripts/render_heatmap_svg.py [data/contributions.json] [contrib-heatmap.svg]
"""
import json
import os
import sys
from datetime import datetime, timedelta

STATIC = os.environ.get("STATIC") == "1"

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
# none -> brightest (level 5 is a neon top end, brighter than GitHub's own 4)

CELL = 11
GAP = 3
LEFT_PAD = 34
TOP_PAD = 46
RIGHT_PAD = 20
BOTTOM_PAD = 46
BG = "#0d1117"
FRAME_ACCENT = "#30363d"
DIM = "#6e7681"

STAGGER = 0.012   # seconds between successive boxes on the diagonal
DUR = 0.5


def level_from_count(count, max_count):
    if count <= 0:
        return 0
    if max_count <= 0:
        return 1
    ratio = count / max_count
    if ratio > 0.75:
        return 5
    if ratio > 0.5:
        return 4
    if ratio > 0.25:
        return 3
    if ratio > 0.05:
        return 2
    return 1


def build_grid(days):
    """Lay days into 53 columns x 7 rows, aligned like GitHub (columns=weeks)."""
    if not days:
        return [], None

    parsed = [(datetime.strptime(d["date"], "%Y-%m-%d").date(), d["count"]) for d in days]
    parsed.sort()
    last_date = parsed[-1][0]

    # end the grid on the most recent Saturday (GitHub week ends Sat)
    end = last_date
    while end.weekday() != 5:  # Monday=0 ... Saturday=5
        end += timedelta(days=1)
    start = end - timedelta(weeks=52, days=6)

    by_date = {d: c for d, c in parsed}
    max_count = max((c for _, c in parsed), default=0)

    weeks = []
    cur = start
    while cur <= end:
        week = []
        for _ in range(7):
            count = by_date.get(cur, 0)
            week.append({"date": cur.isoformat(), "count": count, "level": level_from_count(count, max_count)})
            cur += timedelta(days=1)
        weeks.append(week)

    return weeks, max_count


def month_labels(weeks):
    labels = []
    seen_month = None
    for wi, week in enumerate(weeks):
        d = datetime.strptime(week[0]["date"], "%Y-%m-%d").date()
        if d.month != seen_month:
            labels.append((wi, d.strftime("%b")))
            seen_month = d.month
    return labels


def build_svg(payload, out_path):
    days = payload.get("days", [])
    stats = payload.get("stats", {})
    username = payload.get("username", "")

    weeks, max_count = build_grid(days)
    n_weeks = len(weeks)

    width = LEFT_PAD + n_weeks * (CELL + GAP) + RIGHT_PAD
    height = TOP_PAD + 7 * (CELL + GAP) + BOTTOM_PAD

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
    parts.append(
        '<circle cx="20" cy="20" r="5" fill="#ff5f56"/>'
        '<circle cx="38" cy="20" r="5" fill="#ffbd2e"/>'
        '<circle cx="56" cy="20" r="5" fill="#27c93f"/>'
    )
    parts.append(
        f'<text x="{width/2:.1f}" y="24" font-size="11" fill="{DIM}" text-anchor="middle">'
        f'rik@github: ~$ ./contributions.sh{" --user " + username if username else ""}</text>'
    )
    parts.append(f'<line x1="0" y1="34" x2="{width}" y2="34" stroke="{FRAME_ACCENT}"/>')

    # month labels
    for wi, label in month_labels(weeks):
        x = LEFT_PAD + wi * (CELL + GAP)
        parts.append(f'<text x="{x:.1f}" y="{TOP_PAD-8}" font-size="10" fill="{DIM}">{label}</text>')

    # day-of-week labels (Mon/Wed/Fri)
    dow_labels = {1: "Mon", 3: "Wed", 5: "Fri"}
    for row, label in dow_labels.items():
        y = TOP_PAD + row * (CELL + GAP) + CELL - 1
        parts.append(f'<text x="4" y="{y:.1f}" font-size="9" fill="{DIM}">{label}</text>')

    # diagonal stagger: order by (col + row) so it slides in top-left to bottom-right
    order = []
    for wi, week in enumerate(weeks):
        for ri, day in enumerate(week):
            order.append((wi, ri, day))
    order.sort(key=lambda t: (t[0] + t[1], t[0]))

    for idx, (wi, ri, day) in enumerate(order):
        x = LEFT_PAD + wi * (CELL + GAP)
        y = TOP_PAD + ri * (CELL + GAP)
        color = PALETTE[day["level"]]
        delay = idx * STAGGER
        if STATIC:
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{color}">'
                f'<title>{day["count"]} contributions on {day["date"]}</title>'
                f'</rect>'
            )
        else:
            parts.append(
                f'<rect x="{x:.1f}" y="{y - 6:.1f}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{color}" opacity="0">'
                f'<animate attributeName="y" from="{y-6:.1f}" to="{y:.1f}" begin="{delay:.3f}s" '
                f'dur="{DUR}s" fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
                f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" '
                f'dur="{DUR}s" fill="freeze"/>'
                f'<title>{day["count"]} contributions on {day["date"]}</title>'
                f'</rect>'
            )

    total_anim = (len(order) - 1) * STAGGER + DUR if order else 0

    # legend: Less -> More
    legend_y = height - 22
    legend_x = width - RIGHT_PAD - 5 * (CELL + GAP) - 60
    parts.append(f'<text x="{legend_x-32:.1f}" y="{legend_y+CELL-1:.1f}" font-size="10" fill="{DIM}">Less</text>')
    for i, c in enumerate(PALETTE[:6]):
        lx = legend_x + i * (CELL + GAP)
        parts.append(f'<rect x="{lx:.1f}" y="{legend_y:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{c}"/>')
    parts.append(
        f'<text x="{legend_x + 6*(CELL+GAP) + 6:.1f}" y="{legend_y+CELL-1:.1f}" '
        f'font-size="10" fill="{DIM}">More</text>'
    )

    # stats footer, bottom-left, fades in once the grid finishes
    total = stats.get("total", sum(d["count"] for w in weeks for d in w))
    streak = stats.get("current_streak", 0)
    longest = stats.get("longest_streak", 0)
    footer = f'{total:,} contributions in the last year  ·  current streak {streak}d  ·  longest {longest}d'
    if STATIC:
        parts.append(f'<text x="{LEFT_PAD}" y="{legend_y+CELL-1:.1f}" font-size="10.5" fill="{DIM}">{footer}</text>')
    else:
        parts.append(
            f'<text x="{LEFT_PAD}" y="{legend_y+CELL-1:.1f}" font-size="10.5" fill="{DIM}" opacity="0">{footer}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{total_anim:.3f}s" dur="0.4s" fill="freeze"/>'
            f'</text>'
        )

    parts.append('</svg>')

    with open(out_path, "w") as f:
        f.write("\n".join(parts))
    print(f"wrote {out_path}  ({n_weeks} weeks, total={total}, ~{total_anim:.1f}s anim)")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/contributions.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"
    with open(src) as f:
        payload = json.load(f)
    build_svg(payload, dst)
