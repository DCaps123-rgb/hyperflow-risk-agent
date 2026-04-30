from risk_agent.explainability import build_explanation, explain_decision


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


# ── explain_decision tests ─────────────────────────────────────────────────────

_SAMPLE_FACTORS = {
    "confidence": 0.67,
    "volatility_penalty": 0.096,
    "spread_penalty": 0.025,
    "session_modifier": 0.9,
    "stop_loss_penalty": 0.1019,
    "position_penalty": 0.015,
    "daily_loss_penalty": 0.0,
}

_SAMPLE_RULES_ALL_PASS = [
    {"name": "max_daily_loss", "passed": True, "message": "Within threshold."},
    {"name": "minimum_confidence", "passed": True, "message": "Confidence OK."},
    {"name": "stop_loss_required", "passed": True, "message": "Stop loss present."},
]

_SAMPLE_RULES_WITH_FAIL = [
    {"name": "minimum_confidence", "passed": False, "message": "Confidence below threshold."},
    {"name": "spread_limit", "passed": False, "message": "Spread exceeds limit."},
    {"name": "stop_loss_required", "passed": True, "message": "Stop loss present."},
]


def test_explain_decision_allow() -> None:
    result = explain_decision({
        "action": "ALLOW",
        "risk_score": 0.36,
        "factors": _SAMPLE_FACTORS,
        "rule_results": _SAMPLE_RULES_ALL_PASS,
        "lot_multiplier": 1.0,
    })
    assert "narrative" in result
    assert "passed" in result["narrative"].lower()
    assert result["risk_level"] == "LOW"
    assert result["failed_rules"] == []
    assert "No action required" in result["recommendation"]
    assert result["explainer_version"].startswith("1.")
    assert isinstance(result["contributing_factors"], list)
    assert len(result["contributing_factors"]) == len(_SAMPLE_FACTORS)


def test_explain_decision_block() -> None:
    result = explain_decision({
        "action": "BLOCK",
        "risk_score": 0.75,
        "factors": _SAMPLE_FACTORS,
        "rule_results": _SAMPLE_RULES_WITH_FAIL,
        "lot_multiplier": 0.0,
    })
    assert "blocked" in result["narrative"].lower()
    assert result["risk_level"] == "HIGH"
    assert len(result["failed_rules"]) == 2
    assert "Minimum Confidence" in result["failed_rules"][0]
    assert result["recommendation"] != ""


def test_explain_decision_kill_switch() -> None:
    result = explain_decision({
        "action": "KILL_SWITCH",
        "risk_score": 0.93,
        "factors": _SAMPLE_FACTORS,
        "rule_results": _SAMPLE_RULES_WITH_FAIL,
        "lot_multiplier": 0.0,
    })
    assert "kill-switch" in result["narrative"].lower()
    assert result["risk_level"] == "CRITICAL"
    assert result["explainer_version"].startswith("1.")


def test_explain_decision_scale_down() -> None:
    result = explain_decision({
        "action": "SCALE_DOWN",
        "risk_score": 0.58,
        "factors": _SAMPLE_FACTORS,
        "rule_results": _SAMPLE_RULES_ALL_PASS,
        "lot_multiplier": 0.5,
    })
    assert "50%" in result["narrative"]
    assert result["risk_level"] == "MEDIUM"
    assert "scaled" in result["recommendation"].lower()


def test_explain_decision_missing_factors_graceful() -> None:
    """explain_decision must not raise when optional fields are absent."""
    result = explain_decision({"action": "ALLOW", "risk_score": 0.30})
    assert result["narrative"] != ""
    assert result["risk_level"] == "LOW"
    assert result["failed_rules"] == []
    assert result["contributing_factors"] == []
