from __future__ import annotations

from typing import Any

from risk_agent.constants import (
    ACTION_ALLOW,
    ACTION_BLOCK,
    ACTION_KILL_SWITCH,
    ACTION_SCALE_DOWN,
)
from risk_agent.explainability import build_explanation
from risk_agent.features import build_features
from risk_agent.rules import evaluate_rules
from risk_agent.scorer import score_trade


class RiskEngine:
    def __init__(self, config: Any) -> None:
        self.config = config

    def evaluate(self, trade_intent: dict[str, Any]) -> dict[str, Any]:
        features = build_features(trade_intent)
        rule_results = evaluate_rules(features, self.config)
        risk_score, factors = score_trade(features)

        action = self._resolve_action(rule_results, risk_score)
        allowed = action in {ACTION_ALLOW, ACTION_SCALE_DOWN}
        lot_multiplier = self._lot_multiplier(action)

        explanation = build_explanation(action, risk_score, factors, rule_results)
        return {
            "allowed": allowed,
            "action": action,
            "risk_score": round(risk_score, 4),
            "lot_multiplier": lot_multiplier,
            "reason": explanation["reason"],
            "factors": explanation["factors"],
            "rule_results": explanation["rule_results"],
        }

    def _resolve_action(self, rule_results: list[dict[str, Any]], risk_score: float) -> str:
        if any(not rule["passed"] and rule["severity"] == "block" for rule in rule_results):
            return ACTION_BLOCK
        if any(not rule["passed"] and rule["severity"] == "scale" for rule in rule_results):
            return ACTION_SCALE_DOWN
        if risk_score < 0.45:
            return ACTION_ALLOW
        if risk_score < 0.70:
            return ACTION_SCALE_DOWN
        if risk_score < 0.90:
            return ACTION_BLOCK
        return ACTION_KILL_SWITCH

    @staticmethod
    def _lot_multiplier(action: str) -> float:
        if action == ACTION_ALLOW:
            return 1.0
        if action == ACTION_SCALE_DOWN:
            return 0.5
        return 0.0