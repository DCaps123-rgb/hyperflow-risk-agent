# Risk Logic

## Hard Rules

- `max_daily_loss`: blocks when `daily_loss / account_equity` exceeds `HFRA_MAX_DAILY_LOSS_PCT`.
- `max_open_positions`: blocks when open positions exceed the configured limit.
- `max_lot_size`: scales down when slightly above the preferred cap and blocks when materially above it.
- `minimum_confidence`: blocks trades below the configured confidence threshold.
- `spread_limit`: blocks trades when spread is too high.
- `stop_loss_required`: blocks trades with missing or invalid stop loss.
- `session_filter`: flags `OFF_HOURS` for scale-down handling and treats supported sessions deterministically.

## Scoring Inputs

The deterministic scorer combines:

- confidence risk
- volatility pressure
- spread pressure
- stop loss distance quality
- open position pressure
- daily loss pressure
- session modifier

The final score is clamped to `0.0` through `1.0`.

## Action Thresholds

- `risk_score < 0.45`: `ALLOW`
- `0.45 <= risk_score < 0.70`: `SCALE_DOWN`
- `0.70 <= risk_score < 0.90`: `BLOCK`
- `risk_score >= 0.90`: `KILL_SWITCH`

## Rule Precedence

Hard blocking rules override the score.

Scale-level rule failures, such as a modest lot oversize or off-hours session, force `SCALE_DOWN` even when the aggregate score is lower.

## Multipliers

- `ALLOW`: `1.0`
- `SCALE_DOWN`: `0.5`
- `BLOCK`: `0.0`
- `KILL_SWITCH`: `0.0`