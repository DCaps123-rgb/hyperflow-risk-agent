# Hackathon Submission Context

## Project Name

HyperFlow Risk Agent

## Short Description (≤ 150 characters)

Real-time risk intelligence and control layer for automated trading systems. Evaluate, explain, and govern every trade before execution.

## Long Description

HyperFlow Risk Agent is a production-architecture safety layer that sits between trading signal generation and order execution. It evaluates every proposed trade against a set of hard risk rules, computes a deterministic risk score, and returns one of four control actions — ALLOW, SCALE_DOWN, BLOCK, or KILL_SWITCH — with a full factor-level explanation.

The system is intentionally honest about what it is: a rule-governed control layer with transparent, auditable logic. It does not pretend to be a predictive ML oracle. The current version uses a deterministic weighted scorer. ML scoring is the planned next evolution, and the architecture is designed to accommodate it without breaking existing clients.

Key characteristics:
- **Deterministic and auditable** — same input always produces same output; every decision is logged
- **Explainable by default** — every response includes the reason, rule outcomes, and factor breakdown
- **Configurable via environment** — all thresholds are externalized with safe defaults
- **25 tests passing** — covering engine invariants, rule correctness, idempotency, explainability, and API
- **Live dashboard** — dark glassmorphism single-page command center at `/dashboard`
- **Docker-ready** — `docker-compose up` and the API is running

## Technology Tags

`python` `fastapi` `pydantic` `risk-management` `trading` `algorithmic-trading` `explainable-ai` `rule-engine` `rest-api` `docker` `pytest` `jsonl`

## Judging Alignment

| Judging Criterion | HyperFlow Response |
|---|---|
| **Technical Depth** | Deterministic risk pipeline with 7 hard rules, weighted scorer, 4-tier action resolution, JSONL audit log, and full explainability layer |
| **Innovation** | Dedicated pre-execution risk layer is rare in open-source trading tooling; most systems have no safety brain |
| **Completeness** | 25/25 tests passing; Docker-ready; live dashboard; Swagger docs; full README; replay capability |
| **Real-world Applicability** | Architecture mirrors production risk management patterns (hard rules + model layer + action resolution) |
| **Code Quality** | Pydantic v2 schemas; lru_cache config; JSONL ledger; idempotency tests; determinism invariants |
| **Presentation** | Live dark glassmorphism dashboard; comprehensive demo script; architecture diagram; pitch deck outline |
| **Explainability** | Every decision returns reason, factor breakdown, and rule outcomes — no black box |
| **Honesty** | No fake ML model — `BaselineRiskModel.is_available()` always `False`; docs state what is and is not included |

## Submission Links

- **Repository**: https://github.com/DCaps123-rgb/hyperflow-risk-agent
- **Stable tag**: `demo-stable-c93401d`
- **Submission tag**: `submission-ready-v1`
- **Branch**: `submission-lockdown`

## Local Demo Command

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then open:
- Dashboard: http://127.0.0.1:8000/dashboard
- Swagger UI: http://127.0.0.1:8000/docs
- API data: http://127.0.0.1:8000/api/dashboard
