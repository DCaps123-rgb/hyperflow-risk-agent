from __future__ import annotations

from pathlib import Path
from typing import Any

from risk_agent.constants import SESSION_RISK_MODIFIERS
from risk_agent.features import clamp


class BaselineRiskModel:
    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path) if model_path else None

    def is_available(self) -> bool:
        return bool(self.model_path and self.model_path.exists())

    def predict(self, features: dict[str, Any]) -> float:
        return score_trade(features)[0]


def score_trade(features: dict[str, Any]) -> tuple[float, dict[str, float]]:
    confidence = float(features["confidence"])
    volatility = float(features["volatility_ratio"])
    spread_ratio = float(features["spread_ratio"])
    stop_distance_ratio = float(features["stop_distance_ratio"])
    open_pressure = float(features["open_position_pressure"])
    daily_loss_pressure = float(features["daily_loss_ratio"])
    session = str(features["session"])
    session_modifier = SESSION_RISK_MODIFIERS.get(session, 1.2)

    confidence_risk = 1.0 - confidence
    volatility_penalty = volatility * 0.30
    spread_penalty = spread_ratio * 0.20
    stop_loss_penalty = (1.0 - min(stop_distance_ratio / 0.02, 1.0)) * 0.15
    position_penalty = open_pressure * 0.15
    daily_loss_penalty = daily_loss_pressure * 0.15
    session_penalty = (session_modifier - 0.85) * 0.20

    raw_score = (
        confidence_risk * 0.35
        + volatility_penalty
        + spread_penalty
        + stop_loss_penalty
        + position_penalty
        + daily_loss_penalty
        + session_penalty
    )
    risk_score = clamp(raw_score, 0.0, 1.0)
    factors = {
        "confidence": round(confidence, 4),
        "volatility_penalty": round(volatility_penalty, 4),
        "spread_penalty": round(spread_penalty, 4),
        "session_modifier": round(session_modifier, 4),
        "stop_loss_penalty": round(stop_loss_penalty, 4),
        "position_penalty": round(position_penalty, 4),
        "daily_loss_penalty": round(daily_loss_penalty, 4),
    }
    return risk_score, factors