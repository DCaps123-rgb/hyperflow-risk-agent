"""Phase G: Gate Correctness

Each test exercises exactly one gate or score path and asserts the precise
action, allowed flag, lot_multiplier, and — where applicable — which rule
triggered the outcome and what the score range is.

Design notes
------------
* ``_resolve_action`` priority: block rules → scale rules → score thresholds.
  Tests 1-6 verify block-rule paths; tests 7-8 verify scale-rule paths;
  tests 9-11 verify all three score-based branches; test 12 verifies
  KILL_SWITCH (requires a permissive Settings because the default gates cap
  the achievable score at ~0.75 — below the 0.90 threshold); test 13 verifies
  that block rules win when both a block and a scale rule are violated.
* ``build_explanation`` strips ``severity`` from rule_results, so assertions
  on rule results use only ``name`` and ``passed``.
* Artifacts are emitted for every test to keep the audit trail complete and
  the CI semantic-invariant step green.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import Settings
from risk_agent.constants import (
    ACTION_ALLOW,
    ACTION_BLOCK,
    ACTION_KILL_SWITCH,
    ACTION_SCALE_DOWN,
)
from risk_agent.engine import RiskEngine

# ── Artifact paths (must match CI invariant step) ────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_JOURNAL_PATH = _REPO_ROOT / "lifecycle_journal.jsonl"
_LEDGER_PATH = _REPO_ROOT / "logs" / "idempotency_ledger.json"

# ── Default config (all standard thresholds) ─────────────────────────────────
_DEFAULT = Settings()

# ── Permissive config used ONLY for the kill-switch score test ───────────────
# With default config the maximum achievable score without triggering any rule
# is ~0.75 (in the BLOCK zone).  KILL_SWITCH (≥ 0.90) via the score path
# requires relaxing all gates so that extreme inputs can accumulate freely.
_PERMISSIVE = Settings(
    min_confidence=0.0,
    max_daily_loss_pct=1.0,
    max_open_positions=100,
    max_lot_size=100.0,
    max_spread=1000.0,
)

# ── Base trade — all default-config gates pass cleanly ───────────────────────
_BASE: dict = {
    "symbol": "GATE_BASE",
    "direction": "BUY",
    "confidence": 0.70,
    "entry_price": 100.0,
    "stop_loss": 98.0,
    "take_profit": 104.0,
    "lot_size": 0.01,
    "account_equity": 10000.0,
    "daily_loss": 0.0,
    "open_positions": 0,
    "volatility": 0.10,
    "spread": 5.0,
    "session": "LONDON",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _evaluate(trade: dict, config: Settings | None = None) -> dict:
    return RiskEngine(config or _DEFAULT).evaluate(trade)


def _load_ledger() -> dict:
    if not _LEDGER_PATH.exists():
        return {}
    try:
        return json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def _emit(trade: dict, decision: dict) -> None:
    """Append one journal line and merge one ledger entry (intent_id key)."""
    intent_id = hashlib.sha256(
        json.dumps(trade, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with _JOURNAL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "event": "gate_check",
                    "symbol": trade["symbol"],
                    "action": decision["action"],
                    "intent_id": intent_id,
                }
            )
            + "\n"
        )
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger = _load_ledger()
    ledger[intent_id] = decision["action"]
    _LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def _rule(decision: dict, name: str) -> dict:
    """Return the named rule-result dict from a decision."""
    return next(r for r in decision["rule_results"] if r["name"] == name)


def _all_rules_pass(decision: dict) -> bool:
    return all(r["passed"] for r in decision["rule_results"])


# ─────────────────────────────────────────────────────────────────────────────
# Block-gate tests (severity="block" → ACTION_BLOCK regardless of score)
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_daily_loss_block() -> None:
    """Daily loss / equity > max_daily_loss_pct (0.05) must produce BLOCK."""
    trade = {**_BASE, "symbol": "GATE_DAILY_LOSS", "daily_loss": 600.0}
    # 600 / 10 000 = 0.06  >  0.05 threshold
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_BLOCK
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0

    rule = _rule(decision, "max_daily_loss")
    assert rule["passed"] is False


def test_gate_open_positions_block() -> None:
    """open_positions > max_open_positions (3) must produce BLOCK."""
    trade = {**_BASE, "symbol": "GATE_OPEN_POS", "open_positions": 4}
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_BLOCK
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0

    rule = _rule(decision, "max_open_positions")
    assert rule["passed"] is False


def test_gate_hard_lot_size_block() -> None:
    """lot_size > max_lot_size * 1.5 (0.375) must produce BLOCK.

    The soft band (max_lot_size < lot ≤ max_lot_size * 1.5) produces a scale
    rule; above 1.5× the rule escalates to block severity.
    """
    trade = {**_BASE, "symbol": "GATE_LOT_HARD", "lot_size": 0.50}
    # 0.50  >  0.25 * 1.5 = 0.375  →  block
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_BLOCK
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0

    rule = _rule(decision, "max_lot_size")
    assert rule["passed"] is False


def test_gate_confidence_block() -> None:
    """confidence < min_confidence (0.55) must produce BLOCK."""
    trade = {**_BASE, "symbol": "GATE_CONF", "confidence": 0.40}
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_BLOCK
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0

    rule = _rule(decision, "minimum_confidence")
    assert rule["passed"] is False


def test_gate_spread_block() -> None:
    """spread > max_spread (25.0) must produce BLOCK."""
    trade = {**_BASE, "symbol": "GATE_SPREAD", "spread": 30.0}
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_BLOCK
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0

    rule = _rule(decision, "spread_limit")
    assert rule["passed"] is False


def test_gate_missing_stop_loss_block() -> None:
    """stop_loss = 0 (absent / invalid) must produce BLOCK."""
    trade = {**_BASE, "symbol": "GATE_SL", "stop_loss": 0.0}
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_BLOCK
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0

    rule = _rule(decision, "stop_loss_required")
    assert rule["passed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Scale-gate tests (severity="scale" → ACTION_SCALE_DOWN, no block rule fires)
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_soft_lot_size_scale() -> None:
    """max_lot_size < lot_size ≤ max_lot_size * 1.5 must produce SCALE_DOWN.

    The scale rule fires before the score path is evaluated, so the result
    is SCALE_DOWN regardless of how low the risk score would be.
    """
    trade = {**_BASE, "symbol": "GATE_LOT_SOFT", "lot_size": 0.30}
    # 0.25 < 0.30 ≤ 0.375  →  scale (not block)
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_SCALE_DOWN
    assert decision["allowed"] is True
    assert decision["lot_multiplier"] == 0.5

    rule = _rule(decision, "max_lot_size")
    assert rule["passed"] is False

    # No hard block rule must have fired.
    block_failures = [
        r for r in decision["rule_results"]
        if not r["passed"] and r["name"] != "max_lot_size"
    ]
    assert block_failures == [], (
        f"Unexpected rule failures alongside soft lot-size: {block_failures}"
    )


def test_gate_off_hours_scale() -> None:
    """session = OFF_HOURS must produce SCALE_DOWN (scale rule, not score)."""
    trade = {**_BASE, "symbol": "GATE_OFF_HRS", "session": "OFF_HOURS"}
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert decision["action"] == ACTION_SCALE_DOWN
    assert decision["allowed"] is True
    assert decision["lot_multiplier"] == 0.5

    rule = _rule(decision, "session_filter")
    assert rule["passed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Score-path tests (ALL rules pass → action determined by risk_score thresholds)
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_score_allow() -> None:
    """All rules pass and risk_score < 0.45 must produce ALLOW.

    Constructed score (OVERLAP session, high confidence, zero volatility /
    spread / positions / daily-loss, tight stop):
      confidence_risk       = (1 - 0.90) * 0.35 = 0.035
      all other penalties   = 0.0
      risk_score            = 0.035  →  ALLOW
    """
    trade = {
        **_BASE,
        "symbol": "GATE_SCORE_ALLOW",
        "confidence": 0.90,
        "volatility": 0.0,
        "spread": 0.0,
        "open_positions": 0,
        "daily_loss": 0.0,
        "session": "OVERLAP",   # modifier = 0.85 → session_penalty = 0.0
        "stop_loss": 98.0,      # stop_distance_ratio = 0.02 → penalty = 0.0
    }
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert _all_rules_pass(decision), (
        f"Expected all rules to pass; failures: "
        f"{[r for r in decision['rule_results'] if not r['passed']]}"
    )
    assert decision["action"] == ACTION_ALLOW
    assert decision["allowed"] is True
    assert decision["lot_multiplier"] == 1.0
    assert decision["risk_score"] < 0.45, (
        f"Expected risk_score < 0.45; got {decision['risk_score']}"
    )


def test_gate_score_scale_down() -> None:
    """All rules pass and 0.45 ≤ risk_score < 0.70 must produce SCALE_DOWN.

    Constructed score:
      confidence_risk   = (1 - 0.65) * 0.35 = 0.1225
      volatility        = 0.60 * 0.30        = 0.1800
      spread_ratio      = 0.15 * 0.20        = 0.0300
      stop_loss_penalty = 0.75 * 0.15        = 0.1125  (stop 0.5% from entry)
      position_penalty  = 0.10 * 0.15        = 0.0150
      daily_loss_penalty= 0.02 * 0.15        = 0.0030
      session_penalty   = 0.05 * 0.20        = 0.0100  (LONDON, mod 0.90)
      ───────────────────────────────────────────────
      risk_score ≈ 0.473  →  SCALE_DOWN
    """
    trade = {
        **_BASE,
        "symbol": "GATE_SCORE_SD",
        "confidence": 0.65,
        "volatility": 0.60,
        "spread": 15.0,
        "entry_price": 100.0,
        "stop_loss": 99.5,      # 0.5 / 100 = 0.005 < 0.02 → moderate penalty
        "open_positions": 1,
        "daily_loss": 200.0,    # 200 / 10 000 = 0.02  ≤  0.05 threshold
        "session": "LONDON",
    }
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert _all_rules_pass(decision), (
        f"Expected all rules to pass; failures: "
        f"{[r for r in decision['rule_results'] if not r['passed']]}"
    )
    assert decision["action"] == ACTION_SCALE_DOWN
    assert decision["allowed"] is True
    assert decision["lot_multiplier"] == 0.5
    assert 0.45 <= decision["risk_score"] < 0.70, (
        f"Expected risk_score in [0.45, 0.70); got {decision['risk_score']}"
    )


def test_gate_score_block() -> None:
    """All rules pass and 0.70 ≤ risk_score < 0.90 must produce BLOCK.

    All inputs pushed to the edge of each gate's pass threshold:
      confidence = 0.55  (exactly at min; passes minimum_confidence rule)
      spread     = 25.0  (exactly at max; passes spread_limit rule)
      open_pos   = 3     (exactly at max; passes max_open_positions rule)
      daily_loss = 499   (0.0499 ≤ 0.05; passes max_daily_loss rule)

    Constructed score ≈ 0.749  →  BLOCK (0.70 ≤ 0.749 < 0.90).

    This also demonstrates that identity does not grant a gate exemption: the
    same intent evaluated twice yields BLOCK both times.
    """
    trade = {
        **_BASE,
        "symbol": "GATE_SCORE_BLK",
        "confidence": 0.55,
        "volatility": 1.0,
        "spread": 25.0,
        "entry_price": 100.0,
        "stop_loss": 99.99,     # minimal but valid stop
        "open_positions": 3,
        "daily_loss": 499.0,    # 0.0499  ≤  0.05 threshold
        "session": "ASIA",
    }
    decision = _evaluate(trade)
    _emit(trade, decision)

    assert _all_rules_pass(decision), (
        f"Expected all rules to pass; failures: "
        f"{[r for r in decision['rule_results'] if not r['passed']]}"
    )
    assert decision["action"] == ACTION_BLOCK
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0
    assert 0.70 <= decision["risk_score"] < 0.90, (
        f"Expected risk_score in [0.70, 0.90); got {decision['risk_score']}"
    )

    # Run again — same identity must still produce BLOCK (no score drift).
    decision2 = _evaluate(trade)
    assert decision2["action"] == ACTION_BLOCK, (
        "Second evaluation of identical input produced a different action — "
        "score-path BLOCK is not stable"
    )
    assert decision2["risk_score"] == decision["risk_score"], (
        "Risk score drifted between identical evaluations"
    )


def test_gate_kill_switch() -> None:
    """risk_score ≥ 0.90 with all rules passing must produce KILL_SWITCH.

    With default Settings the maximum achievable score while keeping all gates
    happy is ~0.75 (in the BLOCK zone).  To reach KILL_SWITCH via the score
    path the gates must be relaxed via a permissive Settings override so that
    extreme volatility, spread, positions, and daily-loss inputs can
    accumulate without triggering any block or scale rule.

    Constructed score (ASIA session, all inputs maxed within permissive limits):
      confidence_risk   = 1.00 * 0.35 = 0.35   (confidence = 0.0)
      volatility        = 1.00 * 0.30 = 0.30   (volatility ≥ 1.0)
      spread_penalty    = 1.00 * 0.20 = 0.20   (spread = 100.0)
      stop_loss_penalty ≈ 0.149                  (stop barely above entry)
      position_penalty  = 1.00 * 0.15 = 0.15   (open_positions = 80)
      daily_loss_penalty≈ 0.075                  (daily_loss = 5 000)
      session_penalty   = 0.04                   (ASIA, mod 1.05)
      ───────────────────────────────────────────
      raw ≈ 1.26  →  clamped to 1.0  →  KILL_SWITCH
    """
    trade = {
        **_BASE,
        "symbol": "GATE_KS",
        "confidence": 0.0,
        "volatility": 5.0,
        "spread": 100.0,
        "entry_price": 100.0,
        "stop_loss": 99.99,     # valid but negligible distance
        "open_positions": 80,
        "daily_loss": 5000.0,   # 0.50 × equity  ≤  permissive 1.0 threshold
        "session": "ASIA",      # not OFF_HOURS — avoids the scale rule
    }
    decision = _evaluate(trade, config=_PERMISSIVE)
    _emit(trade, decision)

    assert _all_rules_pass(decision), (
        f"Expected all rules to pass under permissive config; failures: "
        f"{[r for r in decision['rule_results'] if not r['passed']]}"
    )
    assert decision["action"] == ACTION_KILL_SWITCH
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0
    assert decision["risk_score"] >= 0.90, (
        f"Expected risk_score ≥ 0.90; got {decision['risk_score']}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Priority test: block rule wins when both block and scale rules are violated
# ─────────────────────────────────────────────────────────────────────────────

def test_gate_block_overrides_scale() -> None:
    """When both a block rule and a scale rule fail, action must be BLOCK.

    Violations in this trade:
      minimum_confidence (block)  — confidence = 0.40  <  0.55
      session_filter     (scale)  — session = OFF_HOURS
      max_lot_size       (scale)  — lot_size = 0.30  in soft band

    ``_resolve_action`` checks block rules first; scale rules and the score
    path are never reached.
    """
    trade = {
        **_BASE,
        "symbol": "GATE_BLK_PRI",
        "confidence": 0.40,
        "session": "OFF_HOURS",
        "lot_size": 0.30,
    }
    decision = _evaluate(trade)
    _emit(trade, decision)

    # Block must win — not SCALE_DOWN, not ALLOW.
    assert decision["action"] == ACTION_BLOCK, (
        "Block rule did not take priority over concurrent scale violations"
    )
    assert decision["allowed"] is False
    assert decision["lot_multiplier"] == 0.0

    # The triggering block rule must be flagged.
    assert _rule(decision, "minimum_confidence")["passed"] is False

    # Scale rule violations are still present (engine evaluates all rules).
    assert _rule(decision, "session_filter")["passed"] is False
    assert _rule(decision, "max_lot_size")["passed"] is False
