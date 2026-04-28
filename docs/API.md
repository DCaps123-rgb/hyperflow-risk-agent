# API

Base URL: `http://127.0.0.1:8000`

## GET /health

Returns service status.

Response:

```json
{
  "status": "ok"
}
```

## GET /version

Returns application name and version.

## POST /evaluate_trade

Evaluates a single trade intent.

Example request:

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

Response fields:

- `allowed`: whether the trade can proceed in some form
- `action`: final decision
- `risk_score`: aggregate risk score
- `lot_multiplier`: recommended size multiplier
- `reason`: readable explanation
- `factors`: scoring factors
- `rule_results`: individual rule outcomes

## POST /replay

Runs the bundled replay dataset and returns aggregate counts and average risk score.

## Docs

Swagger UI is available at `http://127.0.0.1:8000/docs`.