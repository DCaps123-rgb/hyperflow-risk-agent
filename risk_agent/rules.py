from __future__ import annotations

from typing import Any

from risk_agent.constants import SESSION_RISK_MODIFIERS


def _result(name: str, passed: bool, message: str, severity: str = "block") -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "message": message,
        "severity": severity,
    }


def evaluate_rules(features: dict[str, Any], config: Any) -> list[dict[str, Any]]:
    account_equity = max(float(features["account_equity"]), 1.0)
    daily_loss_ratio = float(features["daily_loss"]) / account_equity
    results = [
        _max_daily_loss(daily_loss_ratio, config.max_daily_loss_pct),
        _max_open_positions(int(features["open_positions"]), config.max_open_positions),
        _max_lot_size(float(features["lot_size"]), config.max_lot_size),
        _minimum_confidence(float(features["confidence"]), config.min_confidence),
        _spread_limit(float(features["spread"]), config.max_spread),
        _stop_loss_required(bool(features["has_valid_stop_loss"])),
        _session_filter(str(features["session"])),
    ]
    return results


def _max_daily_loss(daily_loss_ratio: float, threshold: float) -> dict[str, Any]:
    passed = daily_loss_ratio <= threshold
    message = (
        "Daily loss is within permitted threshold."
        if passed
        else "Daily loss exceeds configured risk limit."
    )
    return _result("max_daily_loss", passed, message)


def _max_open_positions(open_positions: int, limit: int) -> dict[str, Any]:
    passed = open_positions <= limit
    message = (
        "Open position count is within permitted threshold."
        if passed
        else "Open position count exceeds configured limit."
    )
    return _result("max_open_positions", passed, message)


def _max_lot_size(lot_size: float, max_lot_size: float) -> dict[str, Any]:
    if lot_size <= max_lot_size:
        return _result("max_lot_size", True, "Lot size is within configured limit.", severity="scale")
    if lot_size <= max_lot_size * 1.5:
        return _result(
            "max_lot_size",
            False,
            "Lot size exceeds preferred limit and should be scaled down.",
            severity="scale",
        )
    return _result("max_lot_size", False, "Lot size materially exceeds configured limit.")


def _minimum_confidence(confidence: float, threshold: float) -> dict[str, Any]:
    passed = confidence >= threshold
    message = (
        "Confidence meets minimum threshold."
        if passed
        else "Confidence is below minimum threshold."
    )
    return _result("minimum_confidence", passed, message)


def _spread_limit(spread: float, max_spread: float) -> dict[str, Any]:
    passed = spread <= max_spread
    message = "Spread is within limit." if passed else "Spread exceeds configured limit."
    return _result("spread_limit", passed, message)


def _stop_loss_required(has_valid_stop_loss: bool) -> dict[str, Any]:
    message = (
        "Stop loss is present and valid."
        if has_valid_stop_loss
        else "Stop loss is missing or invalid."
    )
    return _result("stop_loss_required", has_valid_stop_loss, message)


def _session_filter(session: str) -> dict[str, Any]:
    if session not in SESSION_RISK_MODIFIERS:
        return _result("session_filter", False, "Session is unsupported.")
    if session == "OFF_HOURS":
        return _result(
            "session_filter",
            False,
            "Session is weak and should be treated cautiously.",
            severity="scale",
        )
    return _result("session_filter", True, "Session quality is acceptable.", severity="scale")