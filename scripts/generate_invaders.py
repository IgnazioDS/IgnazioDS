#!/usr/bin/env python3
"""Generate the self-playing Space Invaders SVG from real contribution data.

Usage:
  GITHUB_TOKEN=... python scripts/generate_invaders.py --user IgnazioDS \
      --output assets/space-invaders.svg
  python scripts/generate_invaders.py --input contribs.json --output out.svg

The last 55 days of contributions become the 11x5 invader formation
(oldest day = top-left, yesterday-ish = bottom-right). Score counts real
contributions as invaders die; HI-SCORE is the rolling-year total. The
game is seeded by the date, so every day is a different playthrough.
"""

import argparse
import datetime
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from invaders import render, sim  # noqa: E402

GRAPHQL_URL = "https://api.github.com/graphql"
CONTRIB_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
FORMATION_SLOTS = sim.COLS * sim.ROWS


def fetch_calendar(user, token):
    payload = json.dumps({"query": CONTRIB_QUERY, "variables": {"login": user}})
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload.encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "space-invaders-readme",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def extract_days(api_response):
    """Validate the API shape and flatten to a date-ordered day list."""
    try:
        calendar = api_response["data"]["user"]["contributionsCollection"][
            "contributionCalendar"
        ]
        days = [
            {"date": d["date"], "count": int(d["contributionCount"])}
            for week in calendar["weeks"]
            for d in week["contributionDays"]
        ]
        total = int(calendar["totalContributions"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"unexpected GraphQL response shape: {exc!r}") from exc
    if len(days) < FORMATION_SLOTS:
        raise SystemExit(f"need at least {FORMATION_SLOTS} days, got {len(days)}")
    return days, total


def build_svg(days, total, today):
    last = days[-FORMATION_SLOTS:]
    counts = [d["count"] for d in last]
    seed = f"invaders-{today.isoformat()}"
    script = sim.simulate(counts, seed)
    wave = f"{today.timetuple().tm_yday:03d}"
    return render.render(script, counts, hi_score=total, wave_label=wave)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default="IgnazioDS")
    parser.add_argument("--input", help="local GraphQL response JSON (skips API)")
    parser.add_argument("--output", default="assets/space-invaders.svg")
    parser.add_argument("--date", help="override game date YYYY-MM-DD (seed + wave)")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as handle:
            api_response = json.load(handle)
    else:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("set GITHUB_TOKEN (or use --input <file>)")
        api_response = fetch_calendar(args.user, token)

    days, total = extract_days(api_response)
    today = (
        datetime.date.fromisoformat(args.date)
        if args.date
        else datetime.date.today()
    )
    svg = build_svg(days, total, today)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as handle:
        handle.write(svg)
    size_kb = os.path.getsize(args.output) / 1024
    print(f"wrote {args.output} ({size_kb:.0f} KiB, hi-score {total})")


if __name__ == "__main__":
    main()
