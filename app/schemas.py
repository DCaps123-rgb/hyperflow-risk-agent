from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from risk_agent.constants import SUPPORTED_DIRECTIONS, SUPPORTED_SESSIONS


class TradeIntent(BaseModel):
    symbol: str = Field(..., examples=["BTCUSD"])
    direction: Literal[SUPPORTED_DIRECTIONS[0], SUPPORTED_DIRECTIONS[1]]
    confidence: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    lot_size: float
    account_equity: float
    daily_loss: float = 0.0
    open_positions: int = 0
    volatility: float = 0.0
    spread: float = 0.0
    session: Literal[
        SUPPORTED_SESSIONS[0],
        SUPPORTED_SESSIONS[1],
        SUPPORTED_SESSIONS[2],
        SUPPORTED_SESSIONS[3],
        SUPPORTED_SESSIONS[4],
    ]


class RuleResult(BaseModel):
    name: str
    passed: bool
    message: str


class RiskDecision(BaseModel):
    allowed: bool
    action: str
    risk_score: float
    lot_multiplier: float
    reason: str
    factors: dict[str, float]
    rule_results: list[RuleResult]


class HealthResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    name: str
    version: str


class ReplaySummary(BaseModel):
    total: int
    allowed: int
    scaled_down: int
    blocked: int
    kill_switch: int
    average_risk_score: float