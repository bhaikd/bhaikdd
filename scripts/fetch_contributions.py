#!/usr/bin/env python3
"""
fetch_contributions.py — scrape the public contribution-calendar HTML
fragment GitHub serves at /users/<username>/contributions (the same
fragment the profile page itself uses) and write data/contributions.json
with raw days plus derived stats. No GraphQL, no personal access token.

Usage:
    python scripts/fetch_contributions.py [username]
"""
import json
import os
import sys
from datetime import datetime, date

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_USERNAME", "bhaikd")
URL_TMPL = "https://github.com/users/{user}/contributions"


def fetch_html(username: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (profile-readme-bot)"}
    resp = requests.get(URL_TMPL.format(user=username), headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_days(html: str):
    soup = BeautifulSoup(html, "html.parser")
    days = []

    # GitHub renders each day as a <td> (older markup) or <rect>/<td> with
    # data-date + either a data-level or data-count attribute depending on
    # markup version. Handle both defensively.
    cells = soup.select("td.ContributionCalendar-day, td[data-date]")
    if not cells:
        cells = soup.select("rect[data-date], [data-date]")

    for cell in cells:
        d = cell.get("data-date")
        if not d:
            continue
        level = cell.get("data-level")
        count_attr = cell.get("data-count")
        tooltip_id = cell.get("id")
        count = None
        if count_attr is not None:
            try:
                count = int(count_attr)
            except ValueError:
                count = None
        if count is None:
            # fall back to parsing the tooltip text ("N contributions on ...")
            tt = None
            if tooltip_id:
                tt = soup.select_one(f'tool-tip[for="{tooltip_id}"]')
            text = tt.get_text(strip=True) if tt else cell.get("aria-label", "")
            if text.lower().startswith("no contributions"):
                count = 0
            else:
                digits = "".join(ch for ch in text.split(" ")[0] if ch.isdigit())
                count = int(digits) if digits else 0
        try:
            level = int(level) if level is not None else None
        except ValueError:
            level = None

        days.append({"date": d, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    return days


def derive_stats(days):
    if not days:
        return {}

    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"])

    # current streak: walk backwards from the most recent day with data
    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    monthly = {}
    for d in days:
        month = d["date"][:7]  # YYYY-MM
        monthly[month] = monthly.get(month, 0) + d["count"]

    return {
        "total": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly,
    }


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else USERNAME
    try:
        html = fetch_html(username)
        days = parse_days(html)
        if not days:
            raise ValueError("no contribution cells parsed from response")
    except Exception as e:
        print(f"warning: live fetch failed ({e}); writing empty calendar", file=sys.stderr)
        days = []

    stats = derive_stats(days)
    out = {
        "username": username,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "days": days,
        "stats": stats,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/contributions.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"wrote data/contributions.json  ({len(days)} days, total={stats.get('total', 0)})")


if __name__ == "__main__":
    main()
