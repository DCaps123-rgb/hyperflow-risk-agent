from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def run_replay(engine: Any, replay_path: str | Path) -> dict[str, Any]:
    path = Path(replay_path)
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    decisions = [engine.evaluate(record) for record in records]
    total = len(decisions)
    summary = {
        "total": total,
        "allowed": sum(1 for item in decisions if item["action"] == "ALLOW"),
        "scaled_down": sum(1 for item in decisions if item["action"] == "SCALE_DOWN"),
        "blocked": sum(1 for item in decisions if item["action"] == "BLOCK"),
        "kill_switch": sum(1 for item in decisions if item["action"] == "KILL_SWITCH"),
        "average_risk_score": round(
            sum(item["risk_score"] for item in decisions) / total,
            4,
        ) if total else 0.0,
    }
    return summary