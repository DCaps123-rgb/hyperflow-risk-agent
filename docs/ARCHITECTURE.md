# Architecture

## Components

- `app/main.py`: FastAPI entrypoint exposing health, version, evaluation, and replay endpoints.
- `app/config.py`: Environment-backed configuration for risk thresholds and file paths.
- `app/schemas.py`: Pydantic request and response models.
- `risk_agent/features.py`: Normalizes raw trade inputs into deterministic features.
- `risk_agent/rules.py`: Applies hard risk checks that can block or scale a trade.
- `risk_agent/scorer.py`: Produces a deterministic risk score between `0.0` and `1.0`.
- `risk_agent/explainability.py`: Builds clear reasons and factor breakdowns.
- `risk_agent/engine.py`: Orchestrates features, rules, score, and action selection.
- `risk_agent/replay.py`: Runs batch evaluation across JSONL sample records.

## Data Flow

1. The API receives a `TradeIntent` payload.
2. The engine normalizes the payload into safe feature values.
3. Hard rules run first and identify block or scale conditions.
4. The scorer computes a lightweight aggregate risk score.
5. The engine maps rule results and score thresholds to a final action.
6. Explainability adds a readable reason and factor-level context.
7. The API returns the decision and appends a JSONL log record.

## Design Notes

- The repository is mock-data only and contains no live execution integrations.
- The score is deterministic so the first hackathon version is easy to inspect and test.
- The model directory is reserved for future optional baseline or learned risk models.