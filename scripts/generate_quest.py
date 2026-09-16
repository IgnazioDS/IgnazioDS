#!/usr/bin/env python3
"""Generate the self-playing dark fantasy quest SVG from real contribution data.

Usage:
  GITHUB_TOKEN=... python scripts/generate_quest.py --user IgnazioDS --output quest.svg
  python scripts/generate_quest.py --input contribs.json --output quest.svg --date 2026-09-16

A dark knight fights one monster per active day (the last 24 days with at
least one contribution); tougher monsters mean busier days, the biggest day
is the dragon, and the SOULS counter ends at the real contribution total.
The quest is seeded by the date, so every day plays differently.
"""

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quest import github, roster, sim  # noqa: E402
from quest.svg import document  # noqa: E402

ROSTER_SIZE = 24


def build_svg(days, year_total, today):
    try:
        quest_roster = roster.build(days, year_total, today, size=ROSTER_SIZE)
    except ValueError as exc:
        raise SystemExit(f"cannot build the quest roster: {exc}") from exc
    script = sim.simulate(quest_roster, f"quest-{today.isoformat()}")
    return document.render(script, quest_roster), script


def _load_response(args):
    if args.input:
        try:
            with open(args.input, encoding="utf-8") as handle:
                return github.validate_graphql_body(json.load(handle), args.user)
        except OSError as exc:
            raise SystemExit(f"cannot read {args.input}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{args.input} is not valid JSON: {exc}") from exc
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("set GITHUB_TOKEN (or use --input <file>)")
    return github.fetch_calendar(args.user, token)


def _parse_date(value):
    if not value:
        return datetime.datetime.now(datetime.timezone.utc).date()
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"--date must be YYYY-MM-DD, got {value!r}") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--user", default="IgnazioDS")
    parser.add_argument("--input", help="local GraphQL response JSON (skips the API)")
    parser.add_argument("--output", default="quest.svg")
    parser.add_argument("--date", help="quest date YYYY-MM-DD (seed; days on or after it are excluded)")
    args = parser.parse_args(argv)

    days, year_total = github.extract_days(_load_response(args))
    today = _parse_date(args.date)
    svg, script = build_svg(days, year_total, today)
    try:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(svg)
        size_kb = os.path.getsize(args.output) / 1024
    except OSError as exc:
        raise SystemExit(f"cannot write {args.output}: {exc}") from exc
    souls = script.souls[-1][1]
    print(f"wrote {args.output} ({size_kb:.0f} KiB, {script.duration:.0f}s loop, "
          f"{len(script.encounters)} monsters + wyrm, {souls} souls, year {year_total})")


if __name__ == "__main__":
    main()
