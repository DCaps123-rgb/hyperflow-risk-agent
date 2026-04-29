from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import Settings
from risk_agent.engine import RiskEngine

# Same repo-relative artifact paths used by all execution tests.
# Do NOT use tmp_path — the CI invariant step checks these exact locations.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_JOURNAL_PATH = _REPO_ROOT / "lifecycle_journal.jsonl"
_LEDGER_PATH = _REPO_ROOT / "logs" / "idempotency_ledger.json"

# Single fixed trade — used for BOTH runs.
# Symbol is "DEMO_ID" to avoid key collisions with the "DEMO", "DEMO_A", "DEMO_B"
# entries written by the other execution test files.
_FIXED_TRADE: dict = {
    "symbol": "DEMO_ID",
    "direction": "BUY",
    "confidence": 0.68,
    "entry_price": 150.0,
    "stop_loss": 147.0,
    "take_profit": 156.0,
    "lot_size": 0.01,
    "account_equity": 10000.0,
    "daily_loss": 0.0,
    "open_positions": 0,
    "volatility": 0.10,
    "spread": 5.0,
    "session": "LONDON",
}


def _derive_intent_id(trade: dict) -> str:
    """Return a deterministic SHA-256 fingerprint of the trade payload.

    Serialises the dict with sorted keys and no extraneous whitespace so that
    two identical dicts always produce the same hexdigest, regardless of
    insertion order or Python version.  Any change to any field — including
    numeric precision — produces a different fingerprint.
    """
    canonical = json.dumps(trade, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_ledger() -> dict:
    """Return the current ledger dict, or {} if absent / corrupt."""
    if not _LEDGER_PATH.exists():
        return {}
    try:
        return json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def _run_and_emit(trade: dict) -> tuple[str, dict]:
    """Evaluate *trade*, append a journal line, and merge the intent_id into the ledger.

    The intent_id is used directly as the ledger key so that idempotency is
    expressed at the storage level: two runs with the same input produce the
    same key and the second run simply overwrites the existing entry — the
    ledger key set does not grow.

    Returns (intent_id, decision).
    """
    intent_id = _derive_intent_id(trade)

    config = Settings()
    engine = RiskEngine(config)
    decision = engine.evaluate(trade)

    # Append one JSONL line — the intent_id is embedded for auditability.
    with _JOURNAL_PATH.open("a", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "event": "evaluation_cycle",
                    "symbol": trade["symbol"],
                    "action": decision["action"],
                    "risk_score": decision["risk_score"],
                    "intent_id": intent_id,
                }
            )
            + "\n"
        )

    # Read-modify-write ledger; intent_id is the key.
    # A second run with the same input overwrites the same key — no new entry.
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger = _load_ledger()
    ledger[intent_id] = decision["action"]
    _LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    return intent_id, decision


def test_execution_identity_and_idempotency() -> None:
    """Running the same input twice must produce:

    1. The same intent_id both times (identity determinism — no hash drift).
    2. The same action and risk_score both times (evaluation determinism).
    3. Exactly one ledger entry for that intent after both runs (no key
       explosion — the second run must overwrite, not add).
    4. The intent_id key present and stable in the ledger after both runs.
    5. A valid, non-empty ledger JSON object with no pre-existing data lost.
    6. Journal entries for this trade all carry the same intent_id (no
       multiple distinct identities for a single logical trade).

    Failure modes detected:
    - Non-deterministic intent IDs (UUID/time-based derivation).
    - Evaluation drift (stateful or non-pure engine path).
    - Ledger key explosion (append-only semantics where overwrite is required).
    - Identity absence (intent not recorded in ledger at all).
    - Silent data loss (pre-existing ledger keys removed on write).
    """
    ledger_before = _load_ledger()

    # ── Run 1 ──────────────────────────────────────────────────────────────
    intent_id_run1, decision_run1 = _run_and_emit(_FIXED_TRADE)
    ledger_after_run1 = _load_ledger()

    # ── Run 2 — exact same input ────────────────────────────────────────────
    intent_id_run2, decision_run2 = _run_and_emit(_FIXED_TRADE)
    ledger_after_run2 = _load_ledger()

    # ── 1. Identity determinism ─────────────────────────────────────────────
    assert intent_id_run1 == intent_id_run2, (
        f"Intent ID is non-deterministic across identical inputs: "
        f"run1={intent_id_run1!r}, run2={intent_id_run2!r}"
    )

    # ── 2. Evaluation determinism ───────────────────────────────────────────
    assert decision_run1["action"] == decision_run2["action"], (
        f"Action drifted between identical runs: "
        f"run1={decision_run1['action']!r}, run2={decision_run2['action']!r}"
    )
    assert decision_run1["risk_score"] == decision_run2["risk_score"], (
        f"Risk score drifted: "
        f"run1={decision_run1['risk_score']}, run2={decision_run2['risk_score']}"
    )

    # ── 3. Ledger idempotency: no new key on second run ─────────────────────
    keys_before = set(ledger_before.keys())
    keys_after_run1 = set(ledger_after_run1.keys())
    keys_after_run2 = set(ledger_after_run2.keys())

    # Run 1 must have introduced the intent_id key.
    assert intent_id_run1 in keys_after_run1, (
        f"Ledger missing intent_id key after run 1: {intent_id_run1!r}"
    )

    # Run 2 must NOT have introduced any new ledger keys.
    # Same input → same intent_id → existing key overwritten, key set unchanged.
    new_keys_after_run2 = keys_after_run2 - keys_after_run1
    assert len(new_keys_after_run2) == 0, (
        f"Run 2 created new ledger keys despite identical input: {new_keys_after_run2}"
    )

    # The intent_id key must still be present after run 2 (no accidental removal).
    assert intent_id_run1 in keys_after_run2, (
        f"Ledger lost intent_id key after run 2: {intent_id_run1!r}"
    )

    # The stored value is stable across both runs.
    assert ledger_after_run1[intent_id_run1] == ledger_after_run2[intent_id_run2], (
        "Ledger value for intent changed between run 1 and run 2 despite "
        "identical inputs — suggests non-deterministic evaluation"
    )

    # ── 4. Ledger integrity ─────────────────────────────────────────────────
    raw = _LEDGER_PATH.read_text(encoding="utf-8")
    reparsed = json.loads(raw)
    assert isinstance(reparsed, dict), "Ledger is not a JSON object"
    assert len(reparsed) > 0, "Ledger is empty after two evaluation runs"

    # No pre-existing keys lost.
    assert keys_before.issubset(set(reparsed.keys())), (
        f"Pre-existing ledger keys were lost: {keys_before - set(reparsed.keys())}"
    )

    # ── 5. Journal: all entries for this trade carry the same intent_id ─────
    journal_entries_this_trade: list[dict] = []
    for line in _JOURNAL_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if entry.get("symbol") == _FIXED_TRADE["symbol"] and "intent_id" in entry:
            journal_entries_this_trade.append(entry)

    # Both runs must have written entries for DEMO_ID.
    assert len(journal_entries_this_trade) >= 2, (
        f"Expected at least 2 journal entries for DEMO_ID, "
        f"found {len(journal_entries_this_trade)}"
    )

    # All entries for this trade must carry the same intent_id.
    distinct_ids_in_journal = {e["intent_id"] for e in journal_entries_this_trade}
    assert len(distinct_ids_in_journal) == 1, (
        f"Journal contains multiple distinct intent IDs for the same trade: "
        f"{distinct_ids_in_journal}"
    )
    assert intent_id_run1 in distinct_ids_in_journal, (
        "Journal intent_id does not match the derived identity"
    )
