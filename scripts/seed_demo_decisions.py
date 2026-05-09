"""seed_demo_decisions.py — Demo data seeder for HyperFlow Risk Agent.

Generates representative risk decisions directly through the risk engine
(no broker connection, no live trades, no external API calls).

Writes results to logs/decisions.jsonl so the dashboard shows varied data.

Run from the project root:
    python scripts/seed_demo_decisions.py

Outcomes generated:
    ALLOW      — clean trade, all rules pass, low risk score
    SCALE_DOWN — marginal trade (off-hours session triggers scale rule)
    BLOCK      — rule violation (low confidence blocks the trade)
    KILL_SWITCH — NOT generated. See note below.

Note on KILL_SWITCH:
    KILL_SWITCH fires only when (a) no block or scale rules fail AND
    (b) risk_score >= 0.90.  When all block rules are satisfied (confidence >= 0.55,
    spread <= 25, daily_loss <= 5%, open_positions <= 3, valid stop loss), the
    theoretical maximum risk score is approximately 0.72–0.78.  That range falls
    in BLOCK territory (0.70–0.90), not KILL_SWITCH (>= 0.90).  Additionally,
    any scale-rule failure (e.g., OFF_HOURS session) short-circuits to SCALE_DOWN
    before the score threshold is evaluated.  KILL_SWITCH is therefore unreachable
    with the current rule configuration and honest inputs.  It is kept in the
    codebase as the intended signal for future scenarios where the scorer is
    replaced with an ML model that can produce extreme scores independently of
    the hard rules.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path when run directly.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings
from risk_agent.engine import RiskEngine

_LOG_PATH = ROOT / "logs" / "decisions.jsonl"

# ---------------------------------------------------------------------------
# Demo trade definitions
# ---------------------------------------------------------------------------

_DEMO_TRADES: list[dict] = [
    # --- ALLOW: clean BTCUSD long during London session --------------------
    {
        "_label": "ALLOW — clean BTCUSD BUY",
        "symbol": "BTCUSD",
        "direction": "BUY",
        "confidence": 0.72,
        "entry_price": 78000.0,
        "stop_loss": 77500.0,
        "take_profit": 79500.0,
        "lot_size": 0.05,
        "account_equity": 10000.0,
        "daily_loss": 0.0,
        "open_positions": 1,
        "volatility": 0.25,
        "spread": 10.0,
        "session": "LONDON",
    },
    # --- ALLOW: EURUSD sell during overlap session -------------------------
    {
        "_label": "ALLOW — EURUSD SELL overlap",
        "symbol": "EURUSD",
        "direction": "SELL",
        "confidence": 0.80,
        "entry_price": 1.0850,
        "stop_loss": 1.0870,
        "take_profit": 1.0810,
        "lot_size": 0.10,
        "account_equity": 15000.0,
        "daily_loss": 200.0,
        "open_positions": 2,
        "volatility": 0.18,
        "spread": 8.0,
        "session": "OVERLAP",
    },
    # --- SCALE_DOWN: OFF_HOURS session triggers scale rule ----------------
    {
        "_label": "SCALE_DOWN — off-hours session scale rule",
        "symbol": "USDJPY",
        "direction": "BUY",
        "confidence": 0.60,
        "entry_price": 155.0,
        "stop_loss": 154.5,
        "take_profit": 156.0,
        "lot_size": 0.08,
        "account_equity": 10000.0,
        "daily_loss": 0.0,
        "open_positions": 1,
        "volatility": 0.20,
        "spread": 12.0,
        "session": "OFF_HOURS",
    },
    # --- SCALE_DOWN: lot size in scale zone (0.25 < size <= 0.375) --------
    {
        "_label": "SCALE_DOWN — lot size in scale zone",
        "symbol": "GBPUSD",
        "direction": "SELL",
        "confidence": 0.65,
        "entry_price": 1.2650,
        "stop_loss": 1.2680,
        "take_profit": 1.2590,
        "lot_size": 0.30,
        "account_equity": 10000.0,
        "daily_loss": 0.0,
        "open_positions": 2,
        "volatility": 0.22,
        "spread": 14.0,
        "session": "NEW_YORK",
    },
    # --- BLOCK: confidence below minimum threshold (0.55) -----------------
    {
        "_label": "BLOCK — confidence below minimum",
        "symbol": "BTCUSD",
        "direction": "BUY",
        "confidence": 0.40,
        "entry_price": 78000.0,
        "stop_loss": 77000.0,
        "take_profit": 80000.0,
        "lot_size": 0.05,
        "account_equity": 10000.0,
        "daily_loss": 0.0,
        "open_positions": 1,
        "volatility": 0.30,
        "spread": 15.0,
        "session": "LONDON",
    },
    # --- BLOCK: spread exceeds limit (> 25 pips) --------------------------
    {
        "_label": "BLOCK — spread too wide",
        "symbol": "EXOTIC_PAIR",
        "direction": "BUY",
        "confidence": 0.70,
        "entry_price": 1.500,
        "stop_loss": 1.480,
        "take_profit": 1.540,
        "lot_size": 0.05,
        "account_equity": 10000.0,
        "daily_loss": 0.0,
        "open_positions": 1,
        "volatility": 0.15,
        "spread": 45.0,
        "session": "LONDON",
    },
    # --- BLOCK: daily loss limit breached (> 5% of equity) ----------------
    {
        "_label": "BLOCK — daily loss limit breached",
        "symbol": "ETHUSD",
        "direction": "BUY",
        "confidence": 0.68,
        "entry_price": 3500.0,
        "stop_loss": 3450.0,
        "take_profit": 3600.0,
        "lot_size": 0.05,
        "account_equity": 10000.0,
        "daily_loss": 600.0,   # 6% of equity — exceeds 5% limit
        "open_positions": 1,
        "volatility": 0.20,
        "spread": 12.0,
        "session": "NEW_YORK",
    },
    # --- BLOCK: missing stop loss -----------------------------------------
    {
        "_label": "BLOCK — stop loss missing",
        "symbol": "XAUUSD",
        "direction": "BUY",
        "confidence": 0.75,
        "entry_price": 2300.0,
        "stop_loss": 0.0,   # no stop loss
        "take_profit": 2350.0,
        "lot_size": 0.05,
        "account_equity": 10000.0,
        "daily_loss": 0.0,
        "open_positions": 0,
        "volatility": 0.10,
        "spread": 8.0,
        "session": "LONDON",
    },
]


def _append_decision(trade: dict, decision: dict) -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": {k: v for k, v in trade.items() if not k.startswith("_")},
        "decision": decision,
        "version": "0.1.0",
        "_demo_seed": True,
    }
    with _LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def main() -> None:
    settings = Settings()
    engine = RiskEngine(settings)

    print("HyperFlow Risk Agent — Demo Seeder")
    print("=" * 60)
    print(f"Writing to: {_LOG_PATH}")
    print()

    action_counts: dict[str, int] = {}

    for trade in _DEMO_TRADES:
        label = trade.get("_label", "")
        payload = {k: v for k, v in trade.items() if not k.startswith("_")}
        decision = engine.evaluate(payload)
        _append_decision(trade, decision)

        action = decision["action"]
        action_counts[action] = action_counts.get(action, 0) + 1

        score = decision["risk_score"]
        print(f"  [{action:12s}]  score={score:.4f}  {label}")

    print()
    print("Action distribution:")
    for action, count in sorted(action_counts.items()):
        print(f"  {action:12s}: {count}")

    print()
    print("Note: KILL_SWITCH was not seeded — see module docstring for why.")
    print("Done. Refresh the dashboard to see seeded data.")


if __name__ == "__main__":
    main()
