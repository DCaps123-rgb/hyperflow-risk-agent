from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    placeholder = MODELS_DIR / "baseline_model_placeholder.txt"
    placeholder.write_text(
        "No trained model is required for the first version.\n"
        "Replace this artifact with a learned baseline when needed.\n",
        encoding="utf-8",
    )
    print(f"Created placeholder model artifact at {placeholder}")


if __name__ == "__main__":
    main()