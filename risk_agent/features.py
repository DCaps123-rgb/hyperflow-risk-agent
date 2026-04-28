from __future__ import annotations

from typing import Any

from risk_agent.constants import EPSILON, SESSION_RISK_MODIFIERS


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _to_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def build_features(trade_intent: dict[str, Any]) -> dict[str, float | str | bool]:
    confidence = clamp(_to_float(trade_intent.get("confidence"), 0.0), 0.0, 1.0)
    entry_price = max(_to_float(trade_intent.get("entry_price"), 0.0), 0.0)
    stop_loss = max(_to_float(trade_intent.get("stop_loss"), 0.0), 0.0)
    take_profit = max(_to_float(trade_intent.get("take_profit"), 0.0), 0.0)
    lot_size = clamp(_to_float(trade_intent.get("lot_size"), 0.0), 0.0, 100.0)
    account_equity = max(_to_float(trade_intent.get("account_equity"), 0.0), EPSILON)
    daily_loss = clamp(_to_float(trade_intent.get("daily_loss"), 0.0), 0.0, account_equity)
    open_positions = clamp(_to_float(trade_intent.get("open_positions"), 0.0), 0.0, 100.0)
    volatility = clamp(_to_float(trade_intent.get("volatility"), 0.0), 0.0, 5.0)
    spread = clamp(_to_float(trade_intent.get("spread"), 0.0), 0.0, 1000.0)

    session = str(trade_intent.get("session") or "OFF_HOURS").upper()
    if session not in SESSION_RISK_MODIFIERS:
        session = "OFF_HOURS"

    stop_distance = abs(entry_price - stop_loss) if stop_loss > 0.0 and entry_price > 0.0 else 0.0
    stop_distance_ratio = clamp(stop_distance / max(entry_price, EPSILON), 0.0, 1.0)
    daily_loss_ratio = clamp(daily_loss / max(account_equity, EPSILON), 0.0, 1.0)
    open_position_pressure = clamp(open_positions / 10.0, 0.0, 1.0)
    spread_ratio = clamp(spread / 100.0, 0.0, 1.0)
    volatility_ratio = clamp(volatility / 1.0, 0.0, 1.0)

    return {
        "symbol": str(trade_intent.get("symbol") or "UNKNOWN").upper(),
        "direction": str(trade_intent.get("direction") or "BUY").upper(),
        "session": session,
        "confidence": confidence,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "lot_size": lot_size,
        "account_equity": account_equity,
        "daily_loss": daily_loss,
        "open_positions": open_positions,
        "volatility": volatility,
        "spread": spread,
        "stop_distance": stop_distance,
        "stop_distance_ratio": stop_distance_ratio,
        "daily_loss_ratio": daily_loss_ratio,
        "open_position_pressure": open_position_pressure,
        "spread_ratio": spread_ratio,
        "volatility_ratio": volatility_ratio,
        "has_valid_stop_loss": stop_loss > 0.0 and entry_price > 0.0 and stop_loss != entry_price,
    }