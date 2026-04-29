from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from risk_agent.engine import RiskEngine

# Same repo-relative paths as test_execution_invariants.py.
# Do NOT use tmp_path — the CI invariant step checks these exact locations.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_JOURNAL_PATH = _REPO_ROOT / "lifecycle_journal.jsonl"
_LEDGER_PATH = _REPO_ROOT / "logs" / "idempotency_ledger.json"

# Two distinct safe trades — different symbols so the ledger produces separate keys
# and we can assert key-uniqueness across both cycles.
_TRADE_A: dict = {
    "symbol": "DEMO_A",
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

_TRADE_B: dict = {
    "symbol": "DEMO_B",
    "direction": "SELL",
    "confidence": 0.72,
    "entry_price": 200.0,
    "stop_loss": 202.0,
    "take_profit": 196.0,
    "lot_size": 0.01,
    "account_equity": 10000.0,
    "daily_loss": 0.0,
    "open_positions": 0,
    "volatility": 0.10,
    "spread": 5.0,
    "session": "LONDON",
}


def _journal_line_count() -> int:
    """Return number of non-empty lines currently in the journal."""
    if not _JOURNAL_PATH.exists():
        return 0
    return sum(1 for line in _JOURNAL_PATH.read_text(encoding="utf-8").splitlines() if line.strip())


def _load_ledger() -> dict:
    """Return the current ledger dict, or {} if absent / corrupt."""
    if not _LEDGER_PATH.exists():
        return {}
    try:
        return json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def _run_cycle(trade: dict) -> dict:
    """Execute one evaluation cycle, append to journal, merge into ledger.

    Mirrors exactly the emit logic in test_execution_invariants.py so both
    tests write to the same artifacts in a compatible format.
    """
    config = Settings()
    engine = RiskEngine(config)
    decision = engine.evaluate(trade)

    # Append one JSONL line
    with _JOURNAL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "event": "evaluation_cycle",
                    "symbol": trade["symbol"],
                    "action": decision["action"],
                    "risk_score": decision["risk_score"],
                }
            )
            + "\n"
        )

    # Read-modify-write ledger (preserves existing keys)
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger = _load_ledger()
    key = f"{trade['symbol']}:{trade['direction']}"
    ledger[key] = decision["action"]
    _LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    return decision


def test_state_consistency_across_two_cycles() -> None:
    """Verify that two sequential execution cycles produce consistent, non-destructive state.

    Specifically:
    - The journal accumulates entries (no overwrite / truncation).
    - The ledger accumulates keys without duplication.
    - No data written in cycle 1 is lost after cycle 2.
    - The ledger is always a valid JSON object.
    """
    # ── Cycle 1 ──────────────────────────────────────────────────────────
    journal_before = _journal_line_count()
    ledger_before_keys = set(_load_ledger().keys())

    _run_cycle(_TRADE_A)

    journal_after_c1 = _journal_line_count()
    ledger_after_c1 = _load_ledger()
    ledger_after_c1_keys = set(ledger_after_c1.keys())

    # Journal grew by exactly 1 new line
    assert journal_after_c1 == journal_before + 1, (
        f"Cycle 1: journal should have grown by 1 (was {journal_before}, "
        f"now {journal_after_c1})"
    )

    # Ledger is a valid dict
    assert isinstance(ledger_after_c1, dict), "Cycle 1: ledger is not a JSON object"

    # The new key is present
    key_a = f"{_TRADE_A['symbol']}:{_TRADE_A['direction']}"
    assert key_a in ledger_after_c1_keys, f"Cycle 1: key '{key_a}' missing from ledger"

    # No pre-existing keys were removed
    assert ledger_before_keys.issubset(ledger_after_c1_keys), (
        "Cycle 1: ledger lost pre-existing keys — "
        f"missing: {ledger_before_keys - ledger_after_c1_keys}"
    )

    # ── Cycle 2 ──────────────────────────────────────────────────────────
    _run_cycle(_TRADE_B)

    journal_after_c2 = _journal_line_count()
    ledger_after_c2 = _load_ledger()
    ledger_after_c2_keys = set(ledger_after_c2.keys())

    # Journal grew again (no overwrite / truncation between cycles)
    assert journal_after_c2 > journal_after_c1, (
        f"Cycle 2: journal did not grow (still {journal_after_c2} lines)"
    )

    # Every journal line is valid JSON with the required semantic keys
    required_keys = {"event", "symbol", "action"}
    for i, line in enumerate(
        _JOURNAL_PATH.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError) as exc:
            raise AssertionError(
                f"Journal line {i} is not valid JSON: {line!r}"
            ) from exc
        missing = required_keys - set(entry.keys())
        assert not missing, (
            f"Journal line {i} missing keys {missing}: {line!r}"
        )

    # Ledger is still a valid dict
    assert isinstance(ledger_after_c2, dict), "Cycle 2: ledger is not a JSON object"

    # Cycle 1 key survived into cycle 2
    assert key_a in ledger_after_c2_keys, (
        f"Cycle 2: key '{key_a}' from cycle 1 was lost"
    )

    # Cycle 2 key is present
    key_b = f"{_TRADE_B['symbol']}:{_TRADE_B['direction']}"
    assert key_b in ledger_after_c2_keys, (
        f"Cycle 2: key '{key_b}' missing from ledger"
    )

    # No duplicate keys (dict guarantees uniqueness; verify count matches)
    raw_text = _LEDGER_PATH.read_text(encoding="utf-8")
    reparsed = json.loads(raw_text)
    assert len(reparsed) == len(set(reparsed.keys())), (
        "Ledger contains duplicate keys after two cycles"
    )

    # No data loss: all keys present after cycle 1 are still present after cycle 2
    assert ledger_after_c1_keys.issubset(ledger_after_c2_keys), (
        "Cycle 2: ledger lost keys from cycle 1 — "
        f"missing: {ledger_after_c1_keys - ledger_after_c2_keys}"
    )
