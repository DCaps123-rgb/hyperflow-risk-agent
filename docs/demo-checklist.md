# Demo Checklist — HyperFlow Risk Agent

Use this checklist before recording or presenting. Check every item.

---

## Pre-Demo Setup

### Environment

- [ ] Python 3.11+ installed and active
- [ ] Virtual environment activated (`.venv`)
- [ ] `pip install -r requirements.txt` completed
- [ ] All 25 tests passing: `python -m pytest`
- [ ] Server starting cleanly: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

### Browser Tabs (open before recording)

- [ ] Tab 1: [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard) — live risk dashboard
- [ ] Tab 2: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) — Swagger UI
- [ ] Tab 3: [http://127.0.0.1:8000/api/dashboard](http://127.0.0.1:8000/api/dashboard) — JSON response (optional)

### Data

- [ ] `logs/decisions.jsonl` has at least a few entries (run a few `/evaluate_trade` calls first)
- [ ] Dashboard shows real data (not empty state)

---

## Demo Flow Checklist

### Scene 1 — Problem Statement (20s)

- [ ] Stated the problem: trading systems have no control layer
- [ ] Said the key line: *"HyperFlow does not try to be a magic trading bot. It is the safety brain between trading signals and execution."*

### Scene 2 — Dashboard (30s)

- [ ] Showed live risk posture gauge
- [ ] Read posture and score aloud
- [ ] Mentioned: auto-refresh every 10 seconds, live feed, action distribution

### Scene 3 — ALLOW Trade (60s)

- [ ] Sent clean BTCUSD BUY trade via Swagger
- [ ] Showed response: ALLOW, risk_score ~0.36, lot_multiplier 1.0
- [ ] Read the reason string aloud
- [ ] Highlighted rule_results (all passed)

### Scene 4 — BLOCK Trade (30s)

- [ ] Sent bad trade (low confidence, wide spread, high lot size)
- [ ] Showed response: BLOCK
- [ ] Identified which rules failed

### Scene 5 — Architecture (20s)

- [ ] Explained 5-stage pipeline
- [ ] Said: *"same input, same output, every time — deterministic"*
- [ ] Said: *"no pretend ML model"*

### Scene 6 — Close (10s)

- [ ] Said: *"ML advises; risk rules govern."*
- [ ] Showed GitHub URL

---

## Submission Checklist

### Code

- [ ] All 25 tests passing on `submission-lockdown` branch
- [ ] `python -m pytest` → green
- [ ] No secrets or API keys committed
- [ ] No fake trained model files committed
- [ ] `LICENSE` file present (MIT)

### Documentation

- [ ] `README.md` fully rewritten with all sections
- [ ] `docs/submission.md` — judging alignment table
- [ ] `docs/demo-script.md` — 2–3 minute video script
- [ ] `docs/pitch-deck-outline.md` — 12 slides
- [ ] `docs/judging-positioning.md` — 12 Q&A
- [ ] `docs/future-ml-roadmap.md` — ML evolution plan
- [ ] `docs/deployment.md` — local + Docker instructions
- [ ] `docs/ARCHITECTURE.md` — up to date
- [ ] `docs/RISK_LOGIC.md` — up to date
- [ ] `docs/API.md` — up to date

### Git

- [ ] All changes committed
- [ ] `submission-lockdown` branch pushed to origin
- [ ] `demo-stable-c93401d` tag pushed
- [ ] `submission-ready-v1` tag pushed and pushed to origin

### Platform Submission (manual)

- [ ] Repository URL submitted on hackathon platform
- [ ] Short description entered (≤ 150 chars)
- [ ] Long description pasted from `docs/submission.md`
- [ ] Tech tags entered
- [ ] Demo video uploaded (or YouTube link)
- [ ] Cover image or screenshot uploaded
- [ ] Team members listed

---

## Emergency Backup

If the live server fails:

```bash
# Restart server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# If port blocked
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# Docker fallback
docker-compose up

# Replay demo (offline)
python scripts/replay_demo.py
```

Pre-recorded screenshots are in `demo/screenshots/`.
