from __future__ import annotations

from typing import Any

from risk_agent.constants import (
    ACTION_ALLOW,
    ACTION_BLOCK,
    ACTION_KILL_SWITCH,
    ACTION_SCALE_DOWN,
)

_FACTOR_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    "confidence": ("signal confidence", "lower confidence increases risk"),
    "volatility_penalty": ("market volatility", "high volatility increases risk"),
    "spread_penalty": ("spread cost", "wide spreads increase risk"),
    "session_modifier": ("session quality", "off-hours sessions increase risk"),
    "stop_loss_penalty": ("stop loss quality", "missing or wide stop loss increases risk"),
    "position_penalty": ("open position count", "more open positions increase risk"),
    "daily_loss_penalty": ("daily loss ratio", "drawdown approaching limit increases risk"),
}

_RULE_FIX_MAP: dict[str, str] = {
    "minimum confidence": "Improve signal quality or wait for a higher-confidence setup.",
    "stop loss required": "Always set a valid stop loss before submitting a trade.",
    "spread limit": "Avoid trading during high-spread conditions or widen the spread threshold.",
    "max daily loss": "Daily loss limit reached — stop trading until the next session.",
    "max open positions": "Close an existing position before opening a new one.",
    "max lot size": "Reduce lot size to within the configured limit.",
    "session filter": "Trade only during approved sessions (LONDON, NEW_YORK, ASIA, OVERLAP).",
}


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


# ── AI Risk Explainer (template-based, no external API) ───────────────────────

def _classify_risk_level(risk_score: float) -> str:
    if risk_score < 0.45:
        return "LOW"
    if risk_score < 0.70:
        return "MEDIUM"
    if risk_score < 0.90:
        return "HIGH"
    return "CRITICAL"


def _build_factor_sentences(factors: dict[str, Any]) -> list[str]:
    sentences: list[str] = []
    for key, value in factors.items():
        label, context = _FACTOR_DESCRIPTIONS.get(key, (key.replace("_", " "), ""))
        if isinstance(value, float):
            sentences.append(
                f"{label.title()} contributed {value:.3f} to the risk score ({context})."
            )
        else:
            sentences.append(f"{label.title()} = {value} ({context}).")
    return sentences


def _build_narrative(
    action: str,
    risk_score: float,
    risk_level: str,
    failed: list[dict[str, Any]],
    lot_multiplier: float,
) -> str:
    score_pct = int(risk_score * 100)
    if action == ACTION_KILL_SWITCH:
        return (
            f"This trade triggered the kill-switch at a risk score of {risk_score:.2f} ({score_pct}%). "
            "The aggregate risk is extreme and the trade has been rejected outright. "
            "No position sizing adjustment can make this trade acceptable under current conditions."
        )
    if action == ACTION_BLOCK:
        rule_phrase = (
            f" by hard rule '{failed[0]['name']}'" if failed else ""
        )
        return (
            f"This trade was blocked{rule_phrase} with a risk score of {risk_score:.2f} ({score_pct}%). "
            f"The risk level is classified as {risk_level}. "
            "Hard risk rules protect account equity and cannot be overridden by signal confidence alone."
        )
    if action == ACTION_SCALE_DOWN:
        scale_pct = int(lot_multiplier * 100)
        return (
            f"This trade was approved with reduced sizing ({scale_pct}% of requested lot size). "
            f"The risk score of {risk_score:.2f} ({score_pct}%) indicates elevated but manageable risk. "
            "Scaling down preserves exposure to the trade opportunity while limiting downside."
        )
    return (
        f"This trade passed all hard risk checks with a score of {risk_score:.2f} ({score_pct}%). "
        f"Risk level is classified as {risk_level}. "
        "All rule gates were satisfied and the trade may proceed at full size."
    )


def _build_recommendation(
    action: str,
    failed: list[dict[str, Any]],
    risk_score: float,
) -> str:
    if action in (ACTION_KILL_SWITCH, ACTION_BLOCK):
        if not failed:
            return (
                f"Review overall risk exposure — aggregate score of {risk_score:.2f} is too high. "
                "Wait for better market conditions."
            )
        rule_name = failed[0]["name"].replace("_", " ")
        return _RULE_FIX_MAP.get(
            rule_name,
            f"Correct the '{rule_name}' rule violation before re-submitting.",
        )
    if action == ACTION_SCALE_DOWN:
        return "Accept the scaled position or address elevated risk factors before requesting full size."
    return "No action required. Trade is within safe risk parameters."


def explain_decision(decision_payload: dict[str, Any]) -> dict[str, Any]:
    """Generate a template-based, human-readable narrative for a risk decision.

    This function is entirely deterministic and makes no external API calls.
    It never modifies risk_score, action, or rule_results.

    Parameters
    ----------
    decision_payload:
        The full decision dict as returned by ``RiskEngine.evaluate()`` or the
        ``/evaluate_trade`` endpoint.  Required keys: ``action``,
        ``risk_score``, ``factors``, ``rule_results``, ``lot_multiplier``.

    Returns
    -------
    dict with keys:
        narrative, risk_level, contributing_factors, failed_rules,
        recommendation, explainer_version
    """
    action: str = str(decision_payload.get("action", ACTION_ALLOW))
    risk_score: float = float(decision_payload.get("risk_score", 0.0))
    factors: dict[str, Any] = dict(decision_payload.get("factors", {}))
    rule_results: list[dict[str, Any]] = list(decision_payload.get("rule_results", []))
    lot_multiplier: float = float(decision_payload.get("lot_multiplier", 1.0))

    risk_level = _classify_risk_level(risk_score)
    failed = [r for r in rule_results if not r.get("passed", True)]

    return {
        "narrative": _build_narrative(action, risk_score, risk_level, failed, lot_multiplier),
        "risk_level": risk_level,
        "contributing_factors": _build_factor_sentences(factors),
        "failed_rules": [
            f"{r['name'].replace('_', ' ').title()}: {r.get('message', '')}"
            for r in failed
        ],
        "recommendation": _build_recommendation(action, failed, risk_score),
        "explainer_version": "1.0.0-template",
    }