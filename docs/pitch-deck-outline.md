# Pitch Deck Outline — HyperFlow Risk Agent

12 slides. Presentation time: 3–5 minutes.

---

## Slide 1 — Title

**HyperFlow Risk Agent**

*The safety brain between trading signals and execution.*

- Your name / team name
- Hackathon name + date
- GitHub: https://github.com/DCaps123-rgb/hyperflow-risk-agent

---

## Slide 2 — The Problem

**Trading systems don't know when to stop.**

- Strategies generate signals. They don't govern risk.
- No dedicated control layer = accounts blow up on bad sessions.
- Most open-source trading tools have no safety brain.

Visual: diagram showing signal → direct execution (no guardrail)

---

## Slide 3 — The Solution

**HyperFlow is the risk intelligence and control layer.**

> "Most trading bots focus on finding entries. HyperFlow focuses on whether a trade should be allowed to execute at all."

- Sits between signal generation and order execution
- Evaluates every trade before it fires
- Returns: ALLOW / SCALE_DOWN / BLOCK / KILL_SWITCH

---

## Slide 4 — Architecture

```
Trading Strategy
      │
      ▼
HyperFlow Risk Agent
  ├── Feature Normalization
  ├── 7 Hard Rules
  ├── Risk Scorer
  ├── Action Resolution
  └── Explainability
      │
      ▼
Execution Layer (conditionally fires)
```

**Deterministic. Auditable. Explainable.**

---

## Slide 5 — The Four Actions

| Action | Score | Meaning |
|---|---|---|
| ALLOW | < 0.45 | Execute at full size |
| SCALE_DOWN | 0.45–0.69 | Execute at reduced lot |
| BLOCK | 0.70–0.89 | Reject this trade |
| KILL_SWITCH | ≥ 0.90 | Halt all trading |

> "BLOCK rejects a trade. KILL_SWITCH tells the whole system to stop."

---

## Slide 6 — Hard Rules (Non-Negotiable)

7 rules run on every trade:

1. Max daily loss exceeded?
2. Too many open positions?
3. Lot size too large?
4. Confidence too low?
5. Spread too wide?
6. Stop loss missing or invalid?
7. Toxic session?

**Rules cannot be overridden by the strategy or the scorer.**

---

## Slide 7 — Explainability

Every decision returns:

```json
{
  "action": "BLOCK",
  "risk_score": 0.65,
  "reason": "Trade blocked by hard risk rule: minimum_confidence.",
  "factors": { "confidence": 0.35, "spread_penalty": 0.12 },
  "rule_results": [{ "name": "minimum_confidence", "passed": false }]
}
```

**No black box. Every decision is auditable.**

---

## Slide 8 — Live Dashboard

Screenshot of `/dashboard` — dark glassmorphism command center.

Features:
- Real-time risk posture gauge
- Score sparkline
- Action distribution
- Live decision feed
- Auto-refresh every 10 seconds

---

## Slide 9 — Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic v2 |
| Config | Environment-backed (`HFRA_` prefix) |
| Logging | JSONL append-only ledger |
| Testing | pytest — 25 tests passing |
| Container | Docker + docker-compose |
| Dashboard | Vanilla JS + CSS glassmorphism |

---

## Slide 10 — Honesty Statement

> "The current version is intentionally honest: it does not pretend a predictive ML model is loaded."

- `BaselineRiskModel.is_available()` always returns `False`
- Scorer is deterministic and rule-weighted
- ML is the *next* evolution, not a pretend current feature

---

## Slide 11 — Roadmap

| Version | Feature |
|---|---|
| v1.1 | Outcome logging + label collection |
| v1.2 | `BaselineRiskModel` trained on decisions |
| v1.3 | Adaptive thresholds from model confidence |
| v2.0 | Broker adapter (paper trading mode) |

> "ML advises; risk rules govern."

---

## Slide 12 — Call to Action

**Run it right now:**

```bash
git clone https://github.com/DCaps123-rgb/hyperflow-risk-agent.git
cd hyperflow-risk-agent
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open: http://127.0.0.1:8000/dashboard

**HyperFlow: The safety brain your trading system is missing.**
