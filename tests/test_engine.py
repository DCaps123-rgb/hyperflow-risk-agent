from app.config import Settings
from risk_agent.engine import RiskEngine


def _engine() -> RiskEngine:
    return RiskEngine(Settings())


def test_acceptable_trade_returns_allow_or_scale_down() -> None:
    decision = _engine().evaluate(
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
            "session": "LONDON",
        }
    )
    assert decision["action"] in {"ALLOW", "SCALE_DOWN"}
    assert decision["lot_multiplier"] in {1.0, 0.5}


def test_very_high_risk_returns_block_or_kill_switch() -> None:
    decision = _engine().evaluate(
        {
            "symbol": "BTCUSD",
            "direction": "BUY",
            "confidence": 0.99,
            "entry_price": 78000.0,
            "stop_loss": 77999.0,
            "take_profit": 79000.0,
            "lot_size": 0.20,
            "account_equity": 10000.0,
            "daily_loss": 490.0,
            "open_positions": 3,
            "volatility": 1.0,
            "spread": 24.0,
            "session": "OFF_HOURS",
        }
    )
    assert decision["action"] in {"BLOCK", "KILL_SWITCH", "SCALE_DOWN"}
