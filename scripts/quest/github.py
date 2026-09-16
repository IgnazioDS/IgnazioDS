"""Fetch and validate the GitHub contribution calendar (GraphQL, stdlib only)."""

import datetime
import json
import urllib.error
import urllib.request

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
TIMEOUT_S = 30


def fetch_calendar(user, token):
    payload = json.dumps({"query": CONTRIB_QUERY, "variables": {"login": user}})
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload.encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "eleventh-knight-readme",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        hint = (
            " (bad or expired token?)" if exc.code in (401, 403)
            else " (GitHub API trouble; retry later)" if exc.code >= 500
            else ""
        )
        raise SystemExit(f"GitHub GraphQL: HTTP {exc.code} {exc.reason}{hint}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"cannot reach GitHub GraphQL API: {exc.reason}") from exc
    except TimeoutError as exc:
        raise SystemExit(f"GitHub GraphQL request timed out after {TIMEOUT_S}s") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"GitHub returned a non-JSON response: {exc}") from exc
    return validate_graphql_body(body, user)


def validate_graphql_body(body, user):
    """Surface GraphQL-level errors before shape extraction sees null data."""
    if not isinstance(body, dict):
        raise SystemExit(f"unexpected GraphQL response type: {type(body).__name__}")
    if body.get("errors"):
        messages = "; ".join(
            e.get("message", str(e)) if isinstance(e, dict) else str(e)
            for e in body["errors"]
        )
        raise SystemExit(f"GraphQL errors: {messages}")
    if not isinstance(body.get("data"), dict):
        raise SystemExit("GraphQL response has no data object")
    if body["data"].get("user") is None:
        raise SystemExit(f"GitHub user {user!r} not found (or token cannot see it)")
    return body


def extract_days(api_response):
    """Validate the calendar shape and flatten it to a date-ordered day list + year total."""
    try:
        calendar = api_response["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [
            {"date": datetime.date.fromisoformat(str(d["date"])).isoformat(), "count": int(d["contributionCount"])}
            for week in calendar["weeks"]
            for d in week["contributionDays"]
        ]
        total = int(calendar["totalContributions"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"unexpected GraphQL response shape: {exc!r}") from exc
    if not days:
        raise SystemExit("contribution calendar is empty")
    if any(d["count"] < 0 for d in days) or total < 0:
        raise SystemExit("contribution calendar has negative counts")
    return sorted(days, key=lambda d: d["date"]), total
