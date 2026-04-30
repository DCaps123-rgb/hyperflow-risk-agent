# Deployment Guide — HyperFlow Risk Agent

---

## Local (no Docker)

### Requirements

- Python 3.11 or higher
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/DCaps123-rgb/hyperflow-risk-agent.git
cd hyperflow-risk-agent

# 2. Create virtual environment
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests (must pass before proceeding)
python -m pytest

# 5. Start the API server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`.

### Verify

```bash
# Health check
curl http://127.0.0.1:8000/health

# Version
curl http://127.0.0.1:8000/version

# Evaluate a trade
curl -X POST http://127.0.0.1:8000/evaluate_trade \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

### Open in Browser

| URL | Description |
|---|---|
| http://127.0.0.1:8000/health | Health check |
| http://127.0.0.1:8000/docs | Swagger UI |
| http://127.0.0.1:8000/redoc | ReDoc UI |
| http://127.0.0.1:8000/dashboard | Live risk dashboard |
| http://127.0.0.1:8000/api/dashboard | Dashboard JSON data |

---

## Docker

### Dockerfile

The project includes a minimal `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "scripts/run_api.py"]
```

### Build and Run

```bash
# Build the image
docker build -t hyperflow-risk-agent .

# Run the container
docker run -p 8000:8000 hyperflow-risk-agent
```

### docker-compose

```bash
docker-compose up
```

The `docker-compose.yml` mounts the environment variable `HFRA_LOG_PATH` and exposes port 8000.

---

## Environment Variables

All configuration uses the `HFRA_` prefix. All variables have safe defaults and are optional.

| Variable | Default | Description |
|---|---|---|
| `HFRA_MAX_DAILY_LOSS_PCT` | `0.05` | Maximum daily loss as fraction of equity |
| `HFRA_MAX_OPEN_POSITIONS` | `3` | Maximum concurrent open positions |
| `HFRA_MAX_LOT_SIZE` | `0.25` | Maximum lot size per trade |
| `HFRA_MIN_CONFIDENCE` | `0.55` | Minimum signal confidence |
| `HFRA_MAX_SPREAD` | `25.0` | Maximum spread in pips |
| `HFRA_LOG_PATH` | `logs/decisions.jsonl` | Decision audit log path |

### Set Environment Variables

**Linux / macOS**:
```bash
export HFRA_MAX_DAILY_LOSS_PCT=0.03
export HFRA_LOG_PATH=/data/decisions.jsonl
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Windows (PowerShell)**:
```powershell
$env:HFRA_MAX_DAILY_LOSS_PCT = "0.03"
$env:HFRA_LOG_PATH = "logs/decisions.jsonl"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Docker**:
```bash
docker run -p 8000:8000 \
  -e HFRA_MAX_DAILY_LOSS_PCT=0.03 \
  -e HFRA_LOG_PATH=/app/logs/decisions.jsonl \
  hyperflow-risk-agent
```

---

## Logs

Decision logs are written to `logs/decisions.jsonl` (or the path set by `HFRA_LOG_PATH`).

Format:
```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "request": { "symbol": "BTCUSD", "direction": "BUY", ... },
  "decision": {
    "allowed": true,
    "action": "ALLOW",
    "risk_score": 0.3634,
    "lot_multiplier": 1.0,
    "reason": "Trade passed all hard risk checks with acceptable model risk.",
    "factors": { ... },
    "rule_results": [ ... ]
  },
  "version": "1.0.0"
}
```

Replay logged decisions:

```bash
curl -X POST http://127.0.0.1:8000/replay
```

---

## Production Notes

This is a hackathon demo build. For production deployment:

1. **Use a production ASGI server** — replace `scripts/run_api.py` with `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`
2. **Mount a persistent volume** for `logs/decisions.jsonl` when using Docker
3. **Set resource limits** in docker-compose for memory and CPU
4. **Add TLS termination** via a reverse proxy (nginx, caddy) in front of the API
5. **Rotate log files** — `logs/decisions.jsonl` is append-only and will grow indefinitely

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `uvicorn: command not found` | Use `python -m uvicorn` instead of bare `uvicorn` |
| Port 8000 already in use | Use `--port 8001` or kill the existing process |
| Dashboard shows empty state | Run a few `/evaluate_trade` calls first to populate the log |
| Tests fail with import errors | Ensure virtual environment is activated and `pip install -r requirements.txt` was run |
