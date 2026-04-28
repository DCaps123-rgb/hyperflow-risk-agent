from risk_agent.features import build_features


def test_feature_builder_clamps_values() -> None:
    features = build_features(
        {
            "confidence": 4.0,
            "lot_size": -1.0,
            "account_equity": 0.0,
            "daily_loss": 999999.0,
            "open_positions": -3,
            "volatility": 9.0,
            "spread": -10.0,
            "session": "unknown",
        }
    )
    assert features["confidence"] == 1.0
    assert features["lot_size"] == 0.0
    assert features["account_equity"] > 0.0
    assert features["daily_loss"] == features["account_equity"]
    assert features["open_positions"] == 0.0
    assert features["volatility"] == 5.0
    assert features["spread"] == 0.0
    assert features["session"] == "OFF_HOURS"