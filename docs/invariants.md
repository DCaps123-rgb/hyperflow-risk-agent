# Enforced Invariants

This file records verified runtime invariants and architectural boundaries for the
HyperFlow Risk Agent.  Each entry is backed by a passing CI test at the tagged
commit shown.  Update this file whenever a new invariant is confirmed or an
existing one changes.

---

## Layer Map

| # | Layer | Enforced by | Tag |
|---|-------|-------------|-----|
| 1 | Setup reproducibility | `pyproject.toml`, `requirements.txt`, CI matrix | `baseline-ci-readme-setup` |
| 2 | Cross-platform CI | `.github/workflows/ci.yml` (windows-latest + ubuntu-latest) | `baseline-ci-matrix-invariants` |
| 3 | Artifact generation | `tests/test_execution_invariants.py` | `baseline-ci-active-invariants` |
| 4 | Semantic invariant validation | CI PowerShell step validates journal + ledger on every run | `baseline-ci-semantic-invariants` |
| 5 | State evolution | `tests/test_execution_state_consistency.py` — two sequential cycles, no key loss | `baseline-ci-state-consistency` |
| 6 | Identity / idempotency | `tests/test_execution_identity_idempotency.py` — SHA-256 intent ID, no ledger key explosion | `baseline-ci-identity-idempotency` |
| 7 | Gate correctness | `tests/test_gate_correctness.py` — all 6 block paths, 2 scale paths, 3 score branches, kill-switch, priority | `baseline-ci-gate-correctness` |

---

## Action-Resolution Priority

`_resolve_action` in `risk_agent/engine.py` applies gates in this strict order.
A higher-priority gate short-circuits all lower ones.

```
1. Any block rule failed  →  BLOCK
2. Any scale rule failed  →  SCALE_DOWN
3. risk_score < 0.45      →  ALLOW
4. risk_score < 0.70      →  SCALE_DOWN
5. risk_score < 0.90      →  BLOCK
6. risk_score >= 0.90     →  KILL_SWITCH
```

---

## Block Rules (severity = "block")

Each rule below produces `ACTION_BLOCK` when it fails, regardless of the risk score.

| Rule | Condition | Config key |
|------|-----------|------------|
| `max_daily_loss` | `daily_loss / account_equity > max_daily_loss_pct` | `HFRA_MAX_DAILY_LOSS_PCT` (default 0.05) |
| `max_open_positions` | `open_positions > max_open_positions` | `HFRA_MAX_OPEN_POSITIONS` (default 3) |
| `max_lot_size` (hard) | `lot_size > max_lot_size × 1.5` | `HFRA_MAX_LOT_SIZE` (default 0.25) |
| `minimum_confidence` | `confidence < min_confidence` | `HFRA_MIN_CONFIDENCE` (default 0.55) |
| `spread_limit` | `spread > max_spread` | `HFRA_MAX_SPREAD` (default 25.0) |
| `stop_loss_required` | `stop_loss = 0` or `stop_loss == entry_price` | — |
| `session_filter` | session not in `SESSION_RISK_MODIFIERS` | — |

---

## Scale Rules (severity = "scale")

Each rule below produces `ACTION_SCALE_DOWN` when it fails **and no block rule has
already fired**.

| Rule | Condition |
|------|-----------|
| `max_lot_size` (soft) | `max_lot_size < lot_size ≤ max_lot_size × 1.5` |
| `session_filter` | `session == "OFF_HOURS"` |

---

## Kill-Switch Boundary (CRITICAL)

> **Under default Settings, KILL_SWITCH via the score path is unreachable.**

With default thresholds the maximum achievable risk score while keeping every gate
in a passing state is approximately **0.75** — well inside the BLOCK zone
(`0.70 ≤ score < 0.90`) and below the `0.90` kill-switch threshold.

This is because the default gates are tight enough that no single trade can
simultaneously satisfy all rules **and** accumulate the extreme penalty values
required to push the score past 0.90.

### Implications

- Default protection is **rule-driven**: kill-level outcomes are produced by hard
  block rules firing before the score path is reached.
- The score-path KILL_SWITCH (`risk_score >= 0.90`) is currently only reachable
  when Settings are explicitly relaxed (e.g. `min_confidence=0.0`,
  `max_daily_loss_pct=1.0`, etc.) — as in the `test_gate_kill_switch` test which
  uses `_PERMISSIVE` config.
- **Do not assume** that raising score weights alone will make KILL_SWITCH
  reachable under normal operation.  The gate tightness is the binding constraint,
  not the score formula.
- If future tuning intends to make score-path KILL_SWITCH reachable under default
  settings, the gate thresholds must be loosened deliberately and the change must
  be reflected in a new test and a new tag.

### How to verify

```bash
python -m pytest tests/test_gate_correctness.py::test_gate_kill_switch -v
python -m pytest tests/test_gate_correctness.py::test_gate_score_block -v
```

`test_gate_score_block` demonstrates the ceiling: a trade with every input pressed
to the edge of each gate's pass threshold produces a score of ~0.749, which is
`BLOCK`, not `KILL_SWITCH`.

---

## Artifact Schema

Two runtime artifacts are required by the CI semantic-invariant step.

### `lifecycle_journal.jsonl` (repo root)

One JSONL line per evaluation cycle.  Every line must be valid JSON and must
contain at least:

```json
{ "event": "...", "symbol": "...", "action": "..." }
```

Tests that emit an `intent_id` field also include it, but it is not required by
the CI check.

### `logs/idempotency_ledger.json` (repo-relative)

A JSON object with at least one key.  Tests use two key formats:

| Format | Written by |
|--------|-----------|
| `"SYMBOL:DIRECTION"` | `test_execution_invariants.py`, `test_execution_state_consistency.py` |
| SHA-256 hex string (`intent_id`) | `test_execution_identity_idempotency.py`, `test_gate_correctness.py` |

Both formats coexist in the same file.  The CI step checks only that the file is
non-empty valid JSON — it does not inspect key format or value types.

Both artifact files are listed in `.gitignore` and are produced at test runtime.

---

## Invariant Stability Guarantee

A test that was green at its tag commit must remain green on every subsequent
commit.  If a change causes a previously-tagged invariant to fail, the change is
breaking and must either be reverted or accompanied by an explicit invariant
revision and a new tag.
