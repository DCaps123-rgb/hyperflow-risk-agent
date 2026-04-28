from __future__ import annotations

from typing import Final

APP_NAME: Final[str] = "HyperFlow Risk Agent"
APP_VERSION: Final[str] = "0.1.0"

ACTION_ALLOW: Final[str] = "ALLOW"
ACTION_SCALE_DOWN: Final[str] = "SCALE_DOWN"
ACTION_BLOCK: Final[str] = "BLOCK"
ACTION_KILL_SWITCH: Final[str] = "KILL_SWITCH"

SUPPORTED_DIRECTIONS: Final[tuple[str, ...]] = ("BUY", "SELL")
SUPPORTED_SESSIONS: Final[tuple[str, ...]] = (
    "ASIA",
    "LONDON",
    "NEW_YORK",
    "OVERLAP",
    "OFF_HOURS",
)

SESSION_RISK_MODIFIERS: Final[dict[str, float]] = {
    "ASIA": 1.05,
    "LONDON": 0.90,
    "NEW_YORK": 0.95,
    "OVERLAP": 0.85,
    "OFF_HOURS": 1.20,
}

MIN_ACCOUNT_EQUITY: Final[float] = 1.0
EPSILON: Final[float] = 1e-9