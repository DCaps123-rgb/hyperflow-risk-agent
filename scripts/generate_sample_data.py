from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sample_signals = [
        {"symbol": "BTCUSD", "direction": "BUY", "confidence": 0.67, "session": "LONDON"},
        {"symbol": "ETHUSD", "direction": "SELL", "confidence": 0.58, "session": "NEW_YORK"},
        {"symbol": "XAUUSD", "direction": "BUY", "confidence": 0.43, "session": "OFF_HOURS"},
    ]
    (DATA_DIR / "sample_signals.json").write_text(json.dumps(sample_signals, indent=2), encoding="utf-8")

    rows = [
        {
            "symbol": "BTCUSD",
            "direction": "BUY",
            "confidence": 0.67,
            "entry_price": 78000.0,
            "stop_loss": 77500.0,
            "take_profit": 79000.0,
            "lot_size": 0.05,
            "account_equity": 10000.0,
            "daily_loss": 0.0,
            "open_positions": 1,
            "volatility": 0.32,
            "spread": 12.5,
            "session": "LONDON",
        },
        {
            "symbol": "ETHUSD",
            "direction": "SELL",
            "confidence": 0.61,
            "entry_price": 4100.0,
            "stop_loss": 4180.0,
            "take_profit": 3980.0,
            "lot_size": 0.08,
            "account_equity": 12000.0,
            "daily_loss": 180.0,
            "open_positions": 2,
            "volatility": 0.28,
            "spread": 14.0,
            "session": "NEW_YORK",
        },
    ]
    with (DATA_DIR / "sample_trades.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with (DATA_DIR / "replay_examples.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()