# Public Telemetry Schema

This document is the canonical contract for the Production Telemetry panel
on [https://eleventh.dev](https://eleventh.dev). The widget on the homepage
polls each system's `/api/stats` endpoint every 30 seconds and renders the
returned values into a public, auditable dashboard.

The data exposed by these endpoints must be **real, persistent across cold
starts, and never artificially inflated**. The credibility of the entire
panel depends on that constraint. Repos that cannot meet the Tier-A workload
contract honestly report `mode: "showcase"` and the narrower Tier-B contract
instead — see [Tiers](#tiers) below.

## Endpoint

Every system in the fleet exposes a public, unauthenticated GET endpoint:

```
GET /api/stats
```

For FastAPI-rooted projects on Vercel, the path is `/api/stats`. For static
showcase projects with a serverless function added at `api/stats.py`,
Vercel's auto-detection registers the same path. The path is canonical.

## Required headers

```
Content-Type:                  application/json
Cache-Control:                 public, max-age=30, stale-while-revalidate=60
Access-Control-Allow-Origin:   *
Access-Control-Allow-Methods:  GET, OPTIONS
Access-Control-Allow-Headers:  Content-Type
```

Wildcard origin is intentional: the response contains aggregate, non-PII
metrics only. CORS preflight (`OPTIONS /api/stats`) returns HTTP 204 with
the same CORS headers.

## Response envelope

All responses share this top-level shape, regardless of tier:

```json
{
  "system":            "<slug>",
  "mode":              "live" | "showcase",
  "status":            "operational" | "degraded" | "down",
  "last_deployed_at":  "<ISO-8601>" | null,
  "metrics":           { ... },
  "schema_version":    1,
  "generated_at":      "<ISO-8601>"
}
```

`mode` is the explicit signal to the homepage widget about which Tier
contract to render. If absent, the widget treats the system as `live`.

`status` enum:

- `operational` — system is processing the workload it represents, all
  dependencies reachable, metrics are fresh.
- `degraded` — a dependency (database, GitHub API, queue, etc.) is
  unreachable. The endpoint serves last-good-cache or zeroed metrics. The
  JSON contract stays valid; **the endpoint never returns HTTP 5xx**.
- `down` — reserved. In practice the endpoint emits `degraded` because if
  the function itself were down it would not respond at all.

`schema_version` MUST be `1`. Any future incompatible change bumps this
number and is documented at the bottom of this file with a migration path.

`generated_at` is the ISO-8601 timestamp of the response, UTC, `Z` suffix.
This is the source of truth for the widget's "last updated" display.

## Tiers

A system is in **Tier A** (`mode: "live"`) when it is processing real
production workload. A system is in **Tier B** (`mode: "showcase"`) when
the deployed Vercel app is a public landing page or scaffold and there is
no real workload to count yet.

Tier-B systems do not fabricate workload counters. They report honest
GitHub-derived signals about the codebase instead, until promoted.

### Tier A — live workload

`mode: "live"` (or `mode` omitted, defaulting to live).

```json
{
  "system":            "nexusrag",
  "mode":              "live",
  "status":            "operational",
  "uptime_pct_30d":    99.94,
  "last_deployed_at":  "<ISO-8601>",
  "last_active_at":    "<ISO-8601>",
  "metrics":           { /* per-system, see below */ },
  "schema_version":    1,
  "generated_at":      "<ISO-8601>"
}
```

`uptime_pct_30d` is a float `0.0`–`100.0`, rolled up over the trailing 30
days, rounded to two decimal places. Source: per-system self-pinger every
5 minutes, or Vercel deployment-status approximation if pinging is too
invasive. The chosen method MUST be documented in the system's README.

`last_active_at` is the ISO-8601 timestamp of the most recent successful
piece of real work (last query served, last runbook step completed, last
eval run, etc.). Distinct from `generated_at` (when the response itself
was assembled).

#### Per-system Tier-A metrics

Each system exposes a different `metrics` shape. Counters are sanity-capped
to prevent runaway exposure (see [Anti-goals](#anti-goals)). The shapes:

##### `system: "nexusrag"`

RAG pipeline (FastAPI + LangGraph + pgvector + Vertex AI).

```json
"metrics": {
  "queries_total":      <int>,    // all-time, capped 10_000_000
  "queries_24h":        <int>,    // capped 1_000_000
  "queries_7d":         <int>,
  "p50_latency_ms":     <int>,    // median end-to-end query latency, last 24h
  "p95_latency_ms":     <int>,
  "avg_retrieval_size": <int>,    // average chunks retrieved per query
  "indexed_chunks":     <int>     // current vector index size
}
```

##### `system: "runbook-orchestrator"`

Durable execution layer for AI runbooks.

```json
"metrics": {
  "runbooks_total":              <int>,
  "runbooks_active_now":         <int>,    // currently executing
  "runbooks_completed_24h":      <int>,
  "runbooks_failed_24h":         <int>,
  "approvals_pending":           <int>,    // human-in-the-loop gates waiting
  "avg_completion_time_seconds": <int>
}
```

##### `system: "evalops"`

Local-first eval harness with regression tracking.

```json
"metrics": {
  "eval_runs_total":         <int>,
  "eval_runs_24h":           <int>,
  "last_pass_rate":          <float>,    // 0.0 to 1.0, last completed run
  "rolling_pass_rate_7d":    <float>,
  "regressions_caught_30d":  <int>,
  "experiments_tracked":     <int>       // unique experiments registered
}
```

##### `system: "repo-rag-debugger"`

Source-aware debugging assistant. RAG over codebases.

```json
"metrics": {
  "codebases_indexed":  <int>,
  "debug_sessions_24h": <int>,
  "queries_24h":        <int>,
  "p50_latency_ms":     <int>,
  "fixes_proposed_24h": <int>     // grounded fix suggestions returned
}
```

##### `system: "revenue-signal-copilot"`

Lead-intelligence and account-scoring.

```json
"metrics": {
  "accounts_total":         <int>,
  "accounts_scored_24h":    <int>,
  "signals_detected_24h":   <int>,
  "high_priority_accounts": <int>     // above a configurable score threshold
}
```

##### `system: "data-quality-watchtower"`

Schema-drift and anomaly monitor.

```json
"metrics": {
  "datasets_monitored":     <int>,
  "checks_run_24h":         <int>,
  "anomalies_detected_24h": <int>,
  "schema_drifts_30d":      <int>,
  "last_check_at":          "<ISO-8601>"
}
```

### Tier B — showcase deploy

`mode: "showcase"` is **mandatory** when the Vercel app is a public landing
page rather than a system processing production workload. The homepage
widget branches on `mode` and renders Tier-B tiles with a different visual
treatment so the differentiation reads as intentional.

```json
{
  "system":            "<slug>",
  "mode":              "showcase",
  "status":            "operational",
  "last_deployed_at":  "<ISO-8601>",
  "last_commit_at":    "<ISO-8601>",
  "metrics": {
    "commits_30d":      <int>,
    "commits_total":    <int>,
    "primary_language": "<string>",
    "repo_stars":       <int>,
    "lines_of_code":    <int>    // optional; omit if cannot be sourced cleanly
  },
  "schema_version":    1,
  "generated_at":      "<ISO-8601>"
}
```

`last_commit_at` is sourced from the GitHub API (`/repos/.../commits?
per_page=1`). `commits_30d` and `commits_total` are sourced via the
GitHub Link header's `rel="last"` page number with `per_page=1`. These
calls happen inside a 5-minute module-scope cache to stay under
GitHub's 60-req/hr unauthenticated rate limit.

`lines_of_code` is sourced from a build-time JSON artifact written by
`scripts/compute_telemetry_static.py` and committed at deploy time. If
LOC cannot be sourced cleanly, **omit the field** rather than estimate.

## Persistence

Tier-A counters MUST survive cold starts. In order of preference:

1. **Existing Postgres** (NexusRAG has pgvector, so a `query_log` table
   alongside the vector chunks is the cleanest). Aggregate on read.
2. **Vercel KV** (Redis-compatible, integration via Vercel dashboard,
   exposes `KV_REST_API_URL` / `KV_REST_API_TOKEN`).
3. **SQLite with a Vercel filesystem mount** (last resort; cold-start
   penalty makes this slower than KV).

In-memory counters that reset on cold start are forbidden. The widget
displays "queries_24h" and similar values; if they reset every few minutes,
the credibility argument falls apart.

## Safety caps

Every counter MUST be clamped to a sanity cap before being returned. If a
metric exceeds the cap, log internally and emit the cap value. Recommended
caps:

| metric                  | cap         |
|-------------------------|-------------|
| `queries_total`         | 10_000_000  |
| `queries_24h`           | 1_000_000   |
| `commits_total`         | 1_000_000   |
| `commits_30d`           | 100_000     |
| `lines_of_code`         | 10_000_000  |
| `repo_stars`            | 1_000_000   |
| `runbooks_total`        | 1_000_000   |
| `eval_runs_total`       | 1_000_000   |
| `accounts_total`        | 10_000_000  |
| `datasets_monitored`    | 1_000_000   |

## Privacy

- Aggregate counts only. **No** user IDs, email addresses, IPs, prompt
  text, model outputs, or API keys MAY appear in any field.
- Internal error messages MUST NOT be exposed. If an underlying dependency
  fails, return `status: "degraded"` and zero out the affected metrics.

## Rate limiting

Tier-A endpoints SHOULD be rate-limited to 120 requests per minute per IP
using whatever mechanism the project already provides. Beyond the limit,
return HTTP 429.

Tier-B endpoints don't require explicit rate limiting; the 5-minute
module-scope cache effectively bounds upstream call volume.

## Anti-goals

- Do **not** seed plausible-looking values to make tiles fuller. Tier-B's
  whole reason for existing is to be honest about which systems are running
  real workload.
- Do **not** return zeros for activity-style metrics on Tier-B systems.
  Use GitHub-derived metrics (about the codebase, not about workload that
  does not happen) as the honest substitute.
- Do **not** return HTTP 5xx from `/api/stats` under any circumstance. If
  everything is on fire, return HTTP 200 with `status: "degraded"` and
  zeroed metrics.
- Do **not** require authentication on `/api/stats`. The whole point is
  unauthenticated, public proof.
- Do **not** expose the endpoint behind a CDN that strips CORS headers
  (some Vercel edge configs do this; verify after deploy).

## Verification across the fleet

After all six repos are instrumented and merged, this curl loop checks
the entire fleet:

```bash
for url in \
  https://nexusrag-lyart.vercel.app \
  https://agent-runbook-orchestrator.vercel.app \
  https://evalops-workbench.vercel.app \
  https://repo-rag-debugger.vercel.app \
  https://revenue-signal-copilot.vercel.app \
  https://data-quality-watchtower.vercel.app
do
  echo "=== $url ==="
  curl -s -w "\nHTTP %{http_code}\n" "$url/api/stats" | head -50
  echo
done
```

Every system MUST return HTTP 200 with valid JSON matching
`schema_version: 1`.

## Schema versioning

Current version: **1**.

Any field rename, type change, or required-field addition MUST bump
`schema_version`. Field additions that the widget can ignore safely are
allowed without a bump. The widget MUST treat unknown fields as
forward-compatible and ignore them rather than failing parse.
