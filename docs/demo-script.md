# Demo Script — HyperFlow Risk Agent

## Format

2–3 minute live demo or recorded walkthrough. No slides required — show the running system.

---

## Setup (before recording)

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Have open in browser:
1. [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard) — live dashboard
2. [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) — Swagger UI

---

## Script

### Scene 1 — The Problem (20 seconds)

> "Automated trading systems are really good at generating signals. What they're not so good at is knowing when to *stop*. A strategy that works 60% of the time can still blow an account if it fires on bad days, toxic sessions, or when risk thresholds are already breached. Most systems have no dedicated control layer between signal and execution."

> "HyperFlow does not try to be a magic trading bot. It is the safety brain between trading signals and execution."

---

### Scene 2 — The Dashboard (30 seconds)

*Switch to browser, show dashboard at `/dashboard`.*

> "This is the HyperFlow risk command center. It shows live risk posture, score history, action distribution, the top risk drivers, and a live feed of recent decisions."

> "Right now we can see [read posture from gauge] as the current posture, with an average risk score of [read from gauge]. All of this is driven by real evaluations logged to a JSONL ledger."

---

### Scene 3 — Send a Trade (60 seconds)

*Switch to Swagger UI at `/docs`, open `POST /evaluate_trade`.*

> "Let's send a clean trade. BTCUSD BUY, confidence 0.67, stop loss set, normal spread, one open position."

```json
{
  "symbol": "BTCUSD",
  "direction": "BUY",
  "confidence": 0.67,
  "entry_price": 78000.0,
  "stop_loss": 77500.0,
  "take_profit": 79000.0,
  "lot_size": 0.05,
  "account_equity": 10000.0,
  "daily_loss": 0.0,
  "open_positions": 1,
  "volatility": 0.32,
  "spread": 12.5,
  "session": "LONDON"
}
```

*Execute. Show response.*

> "ALLOW. Risk score 0.36. All seven hard rules passed. The lot multiplier is 1.0 — full size. And you can see exactly why: here's the reason, here are the factors, here are the rule outcomes. No black box."

*Now send a bad trade — low confidence, wide spread.*

```json
{
  "symbol": "XAUUSD",
  "direction": "SELL",
  "confidence": 0.35,
  "entry_price": 2400.0,
  "stop_loss": 2420.0,
  "take_profit": 2380.0,
  "lot_size": 0.30,
  "account_equity": 10000.0,
  "daily_loss": 0.04,
  "open_positions": 3,
  "volatility": 0.8,
  "spread": 30.0,
  "session": "SYDNEY"
}
```

> "BLOCK. The hard rules caught it — minimum confidence failed, spread is too wide, lot size exceeds the limit. The system did not just say no — it told us exactly *which* rules fired and *why*."

---

### Scene 4 — The Architecture (20 seconds)

> "Under the hood, every trade goes through five stages: feature normalization, hard rule evaluation, risk scoring, action resolution, and explainability. The pipeline is fully deterministic — same input, same output, every time. Every decision is appended to a JSONL audit ledger."

> "There is no pretend ML model. The current scorer is rule-weighted. ML scoring is the next planned phase — and the architecture is ready for it."

---

### Scene 5 — Close (10 seconds)

> "ML advises. Risk rules govern. HyperFlow is the safety brain your trading system is missing."

---

## Key Lines (use verbatim)

- "HyperFlow does not try to be a magic trading bot. It is the safety brain between trading signals and execution."
- "ML advises; risk rules govern."
- "The current version is intentionally honest: it does not pretend a predictive ML model is loaded."
- "No black box — every decision comes with a reason, factor breakdown, and rule outcomes."

---

## Backup Demo (if live fails)

Run replay:
```bash
python scripts/replay_demo.py
```

Or use pre-recorded screenshots in `demo/screenshots/`.
