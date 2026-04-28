from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from risk_agent.engine import RiskEngine
from risk_agent.replay import run_replay


def main() -> None:
    settings = get_settings()
    engine = RiskEngine(settings)
    summary = run_replay(engine, settings.replay_path)
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()