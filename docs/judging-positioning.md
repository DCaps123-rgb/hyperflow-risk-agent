# Judging Positioning — HyperFlow Risk Agent

Answers to anticipated judging questions, written for clarity and honesty.

---

## 1. What does this project actually do?

HyperFlow Risk Agent is a REST API service that evaluates proposed trades before execution. It applies 7 hard risk rules, computes a deterministic risk score, and returns one of four control actions (ALLOW, SCALE_DOWN, BLOCK, KILL_SWITCH) with a full factor-level explanation. Every decision is logged to an auditable JSONL ledger.

---

## 2. Is there a machine learning model?

No. The current scorer is a deterministic weighted aggregate of risk factors. `BaselineRiskModel.is_available()` always returns `False`. The system is honest about this in every layer — the API, the dashboard, and the docs.

ML scoring is the planned v1.2 evolution. The architecture is explicitly designed to accommodate it — the model directory is reserved, the feature pipeline is already normalized, and the outcome logging infrastructure is the next planned addition.

---

## 3. Why rule-based instead of ML?

Hackathon v1 prioritizes three things: auditability, testability, and demo clarity. A rule engine with explicit thresholds is easier to verify (25 tests), reason about (deterministic output), and demo convincingly than a model that would require training data, inference infrastructure, and a week of iteration. The path to ML is clear and documented in the roadmap.

---

## 4. What is the real-world use case?

Algorithmic trading systems generate order flow from strategy signals. In production systems, a pre-execution risk layer is standard — it sits between the strategy and the broker API, checks circuit breakers, enforces risk limits, and prevents runaway losses. HyperFlow is a standalone, open-source implementation of that layer.

---

## 5. How complete is the implementation?

- 25/25 tests passing (engine, rules, features, explainability, API, invariants, idempotency, gate correctness)
- Full REST API with Swagger docs
- Docker and docker-compose for one-command deployment
- Live dashboard at `/dashboard`
- JSONL decision logging with replay capability
- Complete README, architecture docs, risk logic docs, API reference
- CI badge (GitHub Actions)

---

## 6. What is the KILL_SWITCH for?

`BLOCK` rejects a single trade. `KILL_SWITCH` is a semantically distinct signal that the entire trading system should halt — not just the current trade. It fires when aggregate risk score is ≥ 0.90, indicating conditions severe enough that no trade should execute. The calling system is expected to honor this signal and suspend operations.

---

## 7. How is explainability implemented?

Every `RiskDecision` response includes:
- `reason` — a human-readable explanation of the action
- `factors` — per-factor numeric contributions to the risk score
- `rule_results` — pass/fail outcome for each of the 7 hard rules, with a message

The `risk_agent/explainability.py` module handles `build_reason()` and `build_explanation()`. No external AI API is required for this layer.

---

## 8. How does the dashboard work?

The dashboard at `/dashboard` is a single HTML file served by FastAPI. It fetches from `/api/dashboard` every 10 seconds. The backend reads `logs/decisions.jsonl`, computes aggregates (average score, action counts, top drivers, clusters), and returns a JSON payload. The frontend renders a dark glassmorphism trading command center.

---

## 9. Is this safe to run publicly?

Yes. The repository contains:
- No broker credentials or API keys
- No live execution integrations
- No real account data
- No proprietary strategy logic

All data is mock or demo-generated.

---

## 10. What would you build next?

1. **Outcome logging** — record whether trades that were ALLOWed were profitable
2. **Label builder** — convert outcomes into training labels
3. **BaselineRiskModel** — train a gradient boosted classifier on historical decisions
4. **Model registry** — version and load models with fallback to rule scorer
5. **Broker adapter** — paper trading integration for closed-loop testing

---

## 11. Why JSONL instead of a database?

JSONL is append-only, human-readable, and zero-dependency. It can be replayed with the existing `POST /replay` endpoint. It is the right choice for a demo system. In production, the same log format could feed into a time-series store or event stream.

---

## 12. What is the one line that best describes the project?

> "HyperFlow does not try to be a magic trading bot. It is the safety brain between trading signals and execution."
