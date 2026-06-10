#!/usr/bin/env python3
"""Fleet telemetry conformance validator.

Fetches every system's public ``/api/stats`` endpoint (and optional benchmark
artifact endpoint) and validates the response against the contract defined in
``TELEMETRY_SCHEMA.md``. Stdlib-only, so it runs in CI with no dependencies.

Usage::

    python3 scripts/verify_telemetry.py                  # validate the whole fleet
    python3 scripts/verify_telemetry.py --only evalops   # one system
    python3 scripts/verify_telemetry.py --strict         # header warnings -> errors
    python3 scripts/verify_telemetry.py --json           # machine-readable report
    python3 scripts/verify_telemetry.py --no-artifacts   # skip benchmark endpoints

Exit code is non-zero if any system violates a hard contract rule. The contract
forbids non-200 responses from ``/api/stats`` under any circumstance, so a 5xx is
itself a failure.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "fleet.json"

VALID_MODES = frozenset({"live", "showcase"})
VALID_WORKLOADS = frozenset({"production", "benchmark"})
VALID_STATUSES = frozenset({"operational", "degraded", "down"})
ENVELOPE_FIELDS = ("system", "mode", "status", "schema_version", "generated_at", "metrics")
EXPECTED_SCHEMA_VERSION = 1
DEFAULT_TIMEOUT = 15.0
USER_AGENT = "fleet-telemetry-verifier/1.0 (+https://github.com/IgnazioDS/IgnazioDS)"


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" | "warn"
    message: str


@dataclass(frozen=True)
class Result:
    slug: str
    url: str
    http_status: int | None
    issues: tuple[Issue, ...]

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


# --- fetching ---------------------------------------------------------------

def fetch(url: str, timeout: float) -> tuple[int, dict[str, str], str]:
    """GET a URL, returning (status, lowercased-headers, body). HTTP errors are
    returned (not raised) because the contract reasons about their status code."""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, headers, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        headers = {k.lower(): v for k, v in (exc.headers.items() if exc.headers else [])}
        return exc.code, headers, body


# --- pure validators (each returns a fresh list of Issues) ------------------

def validate_envelope(payload: dict[str, Any], slug: str) -> list[Issue]:
    issues: list[Issue] = []
    for key in ENVELOPE_FIELDS:
        if key not in payload:
            issues.append(Issue("error", f"missing required envelope field '{key}'"))

    system = payload.get("system")
    if system is not None and system != slug:
        issues.append(Issue("error", f"system field '{system}' does not match registry slug '{slug}'"))

    mode = payload.get("mode")
    if mode is not None and mode not in VALID_MODES:
        issues.append(Issue("error", f"mode '{mode}' not in {sorted(VALID_MODES)}"))

    status = payload.get("status")
    if status is not None and status not in VALID_STATUSES:
        issues.append(Issue("error", f"status '{status}' not in {sorted(VALID_STATUSES)}"))

    version = payload.get("schema_version")
    if version is not None and version != EXPECTED_SCHEMA_VERSION:
        issues.append(Issue("error", f"schema_version {version!r} != {EXPECTED_SCHEMA_VERSION}"))

    if "metrics" in payload and not isinstance(payload["metrics"], dict):
        issues.append(Issue("error", "metrics must be a JSON object"))
    return issues


def validate_mode_workload(payload: dict[str, Any], cfg: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    mode = payload.get("mode")
    expected_mode = cfg.get("expected_mode")
    if expected_mode and mode and mode != expected_mode:
        if expected_mode == "live" and mode == "showcase":
            issues.append(Issue("error", "regression: registry expects live workload but endpoint reports showcase"))
        else:
            issues.append(Issue("warn", f"mode '{mode}' differs from registry expectation '{expected_mode}' (update fleet.json if this is an intentional graduation)"))

    workload = payload.get("workload")
    if mode == "live":
        if workload is None:
            issues.append(Issue("error", "Tier-A (mode=live) response must declare a 'workload'"))
        elif workload not in VALID_WORKLOADS:
            issues.append(Issue("error", f"workload '{workload}' not in {sorted(VALID_WORKLOADS)}"))
        else:
            expected_workload = cfg.get("expected_workload")
            if expected_workload and workload != expected_workload:
                issues.append(Issue("warn", f"workload '{workload}' differs from registry expectation '{expected_workload}'"))
    elif mode == "showcase" and workload is not None:
        issues.append(Issue("warn", "showcase (Tier-B) responses should omit 'workload'"))
    return issues


def validate_metrics(payload: dict[str, Any], cfg: dict[str, Any]) -> list[Issue]:
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        return []  # already reported by validate_envelope
    return [
        Issue("error", f"metrics missing required key '{key}'")
        for key in cfg.get("required_metrics", [])
        if key not in metrics
    ]


def validate_timestamp(payload: dict[str, Any]) -> list[Issue]:
    raw = payload.get("generated_at")
    if not isinstance(raw, str):
        return []  # absence already reported by validate_envelope
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return [Issue("error", f"generated_at '{raw}' is not a valid ISO-8601 timestamp")]
    return []


def validate_headers(headers: dict[str, str], strict: bool) -> list[Issue]:
    sev = "error" if strict else "warn"
    issues: list[Issue] = []
    if headers.get("access-control-allow-origin") != "*":
        issues.append(Issue(sev, "Access-Control-Allow-Origin should be '*' (contract requires public CORS)"))
    if "cache-control" not in headers:
        issues.append(Issue(sev, "missing Cache-Control header (contract: public, max-age=30, stale-while-revalidate=60)"))
    content_type = headers.get("content-type", "")
    if "application/json" not in content_type:
        issues.append(Issue(sev, f"Content-Type '{content_type}' is not application/json"))
    return issues


# --- composition ------------------------------------------------------------

def validate_stats(cfg: dict[str, Any], timeout: float, strict: bool) -> Result:
    slug = cfg["slug"]
    url = cfg["url"].rstrip("/") + cfg.get("stats_path", "/api/stats")
    try:
        status, headers, body = fetch(url, timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Result(slug, url, None, (Issue("error", f"request failed: {exc!r}"),))

    issues: list[Issue] = []
    if status != 200:
        issues.append(Issue("error", f"expected HTTP 200, got {status} (contract forbids non-200 from /api/stats)"))
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        issues.append(Issue("error", f"response is not valid JSON: {exc}"))
        return Result(slug, url, status, tuple(issues))

    issues += validate_envelope(payload, slug)
    issues += validate_mode_workload(payload, cfg)
    issues += validate_metrics(payload, cfg)
    issues += validate_timestamp(payload)
    issues += validate_headers(headers, strict)
    return Result(slug, url, status, tuple(issues))


def validate_artifact(cfg: dict[str, Any], timeout: float) -> Result:
    slug = f"{cfg['slug']}:artifact"
    url = cfg["url"].rstrip("/") + cfg["artifact_path"]
    try:
        status, _headers, body = fetch(url, timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Result(slug, url, None, (Issue("error", f"request failed: {exc!r}"),))

    issues: list[Issue] = []
    if status != 200:
        issues.append(Issue("error", f"expected HTTP 200, got {status} (artifact endpoint must never 5xx)"))
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        return Result(slug, url, status, (Issue("error", f"response is not valid JSON: {exc}"),))

    if payload.get("system") != cfg["slug"]:
        issues.append(Issue("error", f"artifact system '{payload.get('system')}' != '{cfg['slug']}'"))
    expected_type = cfg.get("benchmark_type")
    if expected_type and payload.get("benchmark_type") != expected_type:
        issues.append(Issue("error", f"benchmark_type '{payload.get('benchmark_type')}' != '{expected_type}'"))
    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        issues.append(Issue("error", f"schema_version {payload.get('schema_version')!r} != {EXPECTED_SCHEMA_VERSION}"))
    if not isinstance(payload.get("generated_at"), str):
        issues.append(Issue("error", "artifact missing 'generated_at'"))
    return Result(slug, url, status, tuple(issues))


# --- reporting --------------------------------------------------------------

def print_human(results: list[Result]) -> None:
    for res in results:
        mark = "✓" if res.ok else "✗"
        http = f"HTTP {res.http_status}" if res.http_status is not None else "no response"
        print(f"{mark} {res.slug:<26} {http:<12} {res.url}")
        for issue in res.issues:
            tag = "ERROR" if issue.severity == "error" else "warn "
            print(f"    [{tag}] {issue.message}")
    failed = [r for r in results if not r.ok]
    warned = sum(1 for r in results for i in r.issues if i.severity == "warn")
    print()
    print(f"{len(results) - len(failed)}/{len(results)} systems conformant, "
          f"{len(failed)} failing, {warned} warning(s).")


def to_dict(res: Result) -> dict[str, Any]:
    return {
        "slug": res.slug,
        "url": res.url,
        "ok": res.ok,
        "http_status": res.http_status,
        "issues": [{"severity": i.severity, "message": i.message} for i in res.issues],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the eleventh.dev fleet telemetry contract.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH, help="path to fleet.json")
    parser.add_argument("--only", help="validate a single system by slug")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--strict", action="store_true", help="treat header warnings as errors")
    parser.add_argument("--no-artifacts", action="store_true", help="skip benchmark artifact endpoints")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    args = parser.parse_args(argv)

    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"failed to load registry {args.registry}: {exc}", file=sys.stderr)
        return 2

    systems = registry.get("systems", [])
    if args.only:
        systems = [s for s in systems if s["slug"] == args.only]
        if not systems:
            print(f"no system with slug '{args.only}' in {args.registry}", file=sys.stderr)
            return 2

    results: list[Result] = []
    for cfg in systems:
        results.append(validate_stats(cfg, args.timeout, args.strict))
        if not args.no_artifacts and cfg.get("artifact_path"):
            results.append(validate_artifact(cfg, args.timeout))

    if args.json:
        print(json.dumps({"results": [to_dict(r) for r in results]}, indent=2))
    else:
        print_human(results)

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
