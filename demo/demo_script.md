# Demo Script

## Goal

Show how a proposed trade is evaluated before execution by a dedicated risk layer.

## Steps

1. Start the API with `python scripts/run_api.py`.
2. Open Swagger at `http://127.0.0.1:8000/docs`.
3. Run `GET /health` to confirm the service is live.
4. Run `POST /evaluate_trade` with a balanced input from `demo/example_requests.http`.
5. Highlight the returned action, risk score, factor breakdown, and rule results.
6. Run `POST /replay` to show batch evaluation over sample history.
7. Explain that this repository is intentionally disconnected from live brokers, exchanges, and proprietary execution logic.