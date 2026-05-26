# Ignazio De Santis

> Most AI systems fail somewhere between a working demo and a working system.
> Retrieval that drifts, agents that don't recover, evaluation that catches nothing.
> I work in that gap.

Backend systems, retrieval, agents, evaluation. I build reliable AI systems for teams that have outgrown the prototype phase: RAG with measurable retrieval quality, agent workflows with state and approval gates, FastAPI backends purpose-built for LLM products, and the evaluation layer most teams skip between prototype and production.

**Available for contract work.**
[ignaziodesantis.com](https://ignaziodesantis.com/) · [eleventh.dev](https://eleventh.dev/) · [LinkedIn](https://www.linkedin.com/in/ignaziodesantis) · [Email](mailto:ignazio.desantis.dev@gmail.com)

**Stack:** Python · FastAPI · LangGraph · pgvector · Anthropic Claude · React · TypeScript · Next.js · Tauri · Rust

---

### Flagship · private

| System | What it is |
|--------|------------|
| **Orion** | Single-node, operator-supervised AI freelance agent powered by the Anthropic Claude API. End-to-end execution pipeline (Scout → Qualify → Propose → Execute → Deliver → Follow-up) across three tracks: enterprise, engineering, webdev. Closed-loop intelligence layer: prompt-drift detection, active-learning queue, Monte Carlo deal predictions, Bayesian pricing calibration, per-LLM-call cost attribution. Python 3.12 · FastAPI · SQLite · Anthropic SDK · React · Stripe. *Private repo.* |

---

### Capabilities · public systems

Four engineering capabilities. Each row links to its source repo.

| # | Capability | System |
|---|------------|--------|
| 01 | **Retrieval Contracts for RAG Systems** — Hybrid retrieval (pgvector + BM25) with reranking, instrumented end-to-end. Built for the gap between a demo that retrieves and a system that survives the next 10,000 queries. | NexusRAG |
| 02 | **LLM Agent Infrastructure** — Multi-step agent workflows on LangGraph with persistent state, tool orchestration, approval gates, retry logic, and deterministic evaluation. | agent-runbook-orchestrator |
| 03 | **FastAPI Backends for AI Products** — Async FastAPI backends purpose-built for LLM-powered apps. pgvector, Alembic migrations, health checks, operational readiness on day one. | langgraph-fastapi-starter |
| 04 | **AI Reliability Engineering** — Deterministic evaluation frameworks, structured output validation, cost and latency observability, regression detection. The layer most teams skip between prototype and production. | evalops-workbench |

Plus: **SentinelID** — passkey-style face authentication system. On-device CV for identity verification, liveness detection, and anti-spoofing. Desktop app (Tauri/Rust) + web dashboard (Next.js + FastAPI).

---

### AI & Agents
| Repo | Description |
|------|-------------|
| evalops-workbench | Local-first evaluation harness for prompts, tools, and agents with regression tracking |
| repo-rag-debugger | Source-aware debugging assistant that indexes codebases and docs to propose grounded fixes |
| spec-to-agent-scaffold | Generates typed Python agent service skeletons from structured product specs |

### Data & Analytics
| Repo | Description |
|------|-------------|
| data-quality-watchtower | Schema drift detection, anomaly monitoring, and dataset validation before pipelines break |
| notebook-pipeline-converter | Converts exploratory notebooks into repeatable, testable batch pipelines |
| api-sync-pipeline | Incremental REST API to SQLite sync engine — cursor pagination, retry/backoff, YAML config |
| marketing-attribution | Multi-touch attribution analysis: last-click vs linear vs time-decay across 17k touchpoints |
| churn-analysis | SaaS customer churn cohort analysis — onboarding signals, channel quality, retention heatmaps |

### Business Automation
| Repo | Description |
|------|-------------|
| revenue-signal-copilot | Lead intelligence and prioritization using public signals and internal notes |
| customer-ops-briefing-bot | Weekly account intelligence agent from CRM activity, meeting notes, and support history |
| lead-aggregator | Multi-feed RSS lead aggregator with keyword scoring, deduplication, and CSV/SQLite export |
| price-monitor | Multi-site e-commerce price monitoring with threshold alerts and CSV reporting |
