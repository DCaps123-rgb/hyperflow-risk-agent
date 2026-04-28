from risk_agent.explainability import build_explanation


def test_explainability_returns_meaningful_reason() -> None:
    explanation = build_explanation(
        "BLOCK",
        0.82,
        {"confidence": 0.4, "spread_penalty": 0.2, "session_modifier": 1.2},
        [
            {
                "name": "minimum_confidence",
                "passed": False,
                "message": "Confidence is below minimum threshold.",
                "severity": "block",
            }
        ],
    )
    assert "blocked" in explanation["reason"].lower()
    assert explanation["factors"]["confidence"] == 0.4
    assert explanation["rule_results"][0]["name"] == "minimum_confidence"