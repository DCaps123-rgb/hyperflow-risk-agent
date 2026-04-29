from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from risk_agent.engine import RiskEngine

# Repo root resolved from this file's location — independent of pytest invocation cwd.
# Do NOT replace these with tmp_path: the CI invariant step (ci.yml) checks for these
# files at their exact repo-relative locations.  tmp_path would make that step skip
# validation silently ("No runtime artifacts produced during test run").
_REPO_ROOT = Path(__file__).resolve().parents[1]
_JOURNAL_PATH = _REPO_ROOT / "lifecycle_journal.jsonl"
_LEDGER_PATH = _REPO_ROOT / "logs" / "idempotency_ledger.json"

# Minimal safe trade — well inside every default threshold.
_SAFE_TRADE: dict = {
    "symbol": "DEMO",
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


def test_execution_invariants_artifacts_created() -> None:
    """Run a minimal safe evaluation cycle and emit the runtime artifacts
    required by the CI invariant check.

    - lifecycle_journal.jsonl  (project root, JSONL, appended)
    - logs/idempotency_ledger.json  (JSON object, written atomically)

    No real broker, exchange, or environment dependency is introduced.
    All risk thresholds use the library defaults from Settings().
    """
    config = Settings()
    engine = RiskEngine(config)
    decision = engine.evaluate(_SAFE_TRADE)

    # --- lifecycle_journal.jsonl ----------------------------------------
    with _JOURNAL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "event": "evaluation_cycle",
                    "symbol": _SAFE_TRADE["symbol"],
                    "action": decision["action"],
                    "risk_score": decision["risk_score"],
                }
            )
            + "\n"
        )

    # --- logs/idempotency_ledger.json ------------------------------------
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger: dict = {}
    if _LEDGER_PATH.exists():
        try:
            ledger = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            ledger = {}
    ledger[f"{_SAFE_TRADE['symbol']}:{_SAFE_TRADE['direction']}"] = decision["action"]
    _LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    # --- Assertions ------------------------------------------------------
    assert _JOURNAL_PATH.exists(), "lifecycle_journal.jsonl was not created"
    assert _JOURNAL_PATH.stat().st_size > 0, "lifecycle_journal.jsonl is empty"

    assert _LEDGER_PATH.exists(), "logs/idempotency_ledger.json was not created"
    ledger_data = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    assert isinstance(ledger_data, dict), "logs/idempotency_ledger.json is not a JSON object"
