from app.config import Settings
from risk_agent.features import build_features
from risk_agent.rules import evaluate_rules


def test_low_confidence_blocks_trade() -> None:
    features = build_features(
        {
            "symbol": "BTCUSD",
            "direction": "BUY",
            "confidence": 0.30,
            "entry_price": 78000.0,
            "stop_loss": 77500.0,
            "take_profit": 79000.0,
            "lot_size": 0.05,
            "account_equity": 10000.0,
            "daily_loss": 0.0,
            "open_positions": 1,
            "volatility": 0.2,
            "spread": 10.0,
            "session": "LONDON",
        }
    )
    results = evaluate_rules(features, Settings())
    assert any(rule["name"] == "minimum_confidence" and not rule["passed"] for rule in results)


def test_missing_stop_loss_blocks_trade() -> None:
    features = build_features(
        {
            "symbol": "BTCUSD",
            "direction": "BUY",
            "confidence": 0.75,
            "entry_price": 78000.0,
            "stop_loss": 0.0,
            "lot_size": 0.05,
            "account_equity": 10000.0,
            "spread": 10.0,
            "session": "LONDON",
        }
    )
    results = evaluate_rules(features, Settings())
    assert any(rule["name"] == "stop_loss_required" and not rule["passed"] for rule in results)


def test_high_spread_blocks_trade() -> None:
    features = build_features(
        {
            "symbol": "BTCUSD",
            "direction": "BUY",
            "confidence": 0.75,
            "entry_price": 78000.0,
            "stop_loss": 77500.0,
            "lot_size": 0.05,
            "account_equity": 10000.0,
            "spread": 40.0,
            "session": "LONDON",
        }
    )
    results = evaluate_rules(features, Settings())
    assert any(rule["name"] == "spread_limit" and not rule["passed"] for rule in results)