from __future__ import annotations

from typing import Any

from risk_agent.constants import (
    ACTION_ALLOW,
    ACTION_BLOCK,
    ACTION_KILL_SWITCH,
    ACTION_SCALE_DOWN,
)


def build_reason(action: str, rule_results: list[dict[str, Any]], risk_score: float) -> str:
    failed_rules = [rule for rule in rule_results if not rule["passed"] and rule["severity"] == "block"]
    scale_rules = [rule for rule in rule_results if not rule["passed"] and rule["severity"] == "scale"]

    if action == ACTION_KILL_SWITCH:
        return "Trade triggered kill-switch protection due to extreme aggregate risk."
    if failed_rules:
        return f"Trade blocked by hard risk rule: {failed_rules[0]['name']}."
    if action == ACTION_SCALE_DOWN or scale_rules:
        return "Trade is viable but should be scaled down because risk conditions are elevated."
    if action == ACTION_BLOCK:
        return f"Trade blocked because aggregate risk score is too high at {risk_score:.2f}."
    return "Trade passed all hard risk checks with acceptable model risk."


def build_explanation(
    action: str,
    risk_score: float,
    factors: dict[str, float],
    rule_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "reason": build_reason(action, rule_results, risk_score),
        "factors": factors,
        "rule_results": [
            {
                "name": rule["name"],
                "passed": rule["passed"],
                "message": rule["message"],
            }
            for rule in rule_results
        ],
    }