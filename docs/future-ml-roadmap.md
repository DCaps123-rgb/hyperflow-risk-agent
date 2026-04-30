# Future ML Roadmap — HyperFlow Risk Agent

This document describes the planned evolution of the risk scoring layer from the current deterministic rule-weighted scorer to a learned model. The architecture is already designed to support this transition.

---

## Current State (v1.0)

The current scorer (`risk_agent/scorer.py`) is a deterministic weighted aggregate:

```
risk_score = (
    volatility_penalty * w1
  + spread_penalty     * w2
  + stop_loss_penalty  * w3
  + position_penalty   * w4
  + daily_loss_penalty * w5
  + session_modifier   * w6
  - confidence         * w7
)
```

All weights are fixed constants. The scorer is deterministic, fast, and fully testable. `BaselineRiskModel.is_available()` always returns `False`.

**ML advises; risk rules govern.** The hard rules run first and cannot be overridden by any model.

---

## Why Not ML in v1.0?

- No labeled training data exists yet
- A deterministic baseline is easier to test, demo, and reason about
- Pretending to have a model when you don't is worse than being honest

---

## Planned Components

### v1.1 — Outcome Logger

**Module**: `risk_agent/outcome_logger.py`

Records the result of each trade that was ALLOWed or SCALE_DOWN'd. This is the foundation of the training dataset.

```python
def log_outcome(decision_id: str, was_profitable: bool, pnl: float) -> None:
    ...
```

Log format addition to `logs/decisions.jsonl`:
```json
{
  "decision_id": "abc123",
  "outcome": { "profitable": true, "pnl": 45.0, "recorded_at": "2025-01-01T12:00:00Z" }
}
```

---

### v1.1 — Label Builder

**Module**: `risk_agent/label_builder.py`

Combines decision records with outcome records to produce labeled training samples.

```python
def build_labeled_dataset(decisions_path: str, outcomes_path: str) -> list[dict]:
    ...
```

Label schema:
```json
{
  "features": { "volatility": 0.32, "spread": 12.5, "confidence": 0.67, ... },
  "action": "ALLOW",
  "was_profitable": true,
  "pnl": 45.0
}
```

---

### v1.2 — Dataset Builder

**Module**: `risk_agent/dataset_builder.py`

Converts the labeled dataset into train/validation splits in a format ready for `sklearn` or `xgboost`.

```python
def build_train_val_split(labeled_data: list[dict], val_ratio: float = 0.2) -> tuple:
    ...
```

---

### v1.2 — Baseline Model Training

**Script**: `scripts/train_baseline_model.py` (already exists as placeholder)

Train a gradient boosted classifier (XGBoost or LightGBM) on historical decisions.

Target: predict whether a trade will be profitable given features + rule outcomes.

```python
model = XGBClassifier(n_estimators=100, max_depth=4)
model.fit(X_train, y_train)
joblib.dump(model, "models/baseline_risk_model.pkl")
```

Feature vector (16 features):
- `volatility`, `spread`, `confidence`, `lot_size_pct`, `daily_loss_pct`
- `open_positions_pct`, `stop_loss_distance_pct`, `take_profit_distance_pct`
- `session_encoded`, `direction_encoded`
- All 7 rule pass/fail flags (0 or 1)

---

### v1.2 — Model Registry

**Module**: `risk_agent/model_registry.py`

Loads trained models with fallback to rule scorer if no model is available.

```python
class ModelRegistry:
    def load(self, path: str) -> BaselineRiskModel | None:
        ...
    
    def is_available(self) -> bool:
        ...
```

The `BaselineRiskModel` in `models/` is the integration point.

---

### v1.3 — Adaptive Thresholds

Use model confidence intervals to adjust the ALLOW/SCALE_DOWN/BLOCK thresholds dynamically:

- High model confidence → tighten BLOCK threshold
- Low model confidence → rely more heavily on hard rules
- Uncertainty quantification via prediction intervals or calibration

This keeps the hard rules primary and uses the model as an advisory layer.

---

### v2.0 — Closed-Loop Validation

**Module**: `risk_agent/paper_trader.py`

Paper trading integration that:
1. Submits ALLOWed decisions to a paper broker
2. Records actual outcomes
3. Feeds outcomes back into the outcome logger
4. Enables continuous model retraining

This closes the feedback loop and allows the model to learn from its own decisions.

---

## Guiding Principle

> "ML advises; risk rules govern."

No matter how the ML layer evolves, the 7 hard rules run first. A model can influence the risk score and therefore the action threshold, but it cannot override a block-severity rule failure. The hard rules are the non-negotiable safety boundary.

---

## Timeline Estimate

| Phase | Target Version | Key Deliverable |
|---|---|---|
| Outcome logging | v1.1 | `outcome_logger.py`, `label_builder.py` |
| Dataset + training | v1.2 | `dataset_builder.py`, `train_baseline_model.py` (real), `model_registry.py` |
| Adaptive thresholds | v1.3 | Confidence-based threshold adjustment |
| Closed-loop | v2.0 | Paper trading adapter + auto-retrain |
