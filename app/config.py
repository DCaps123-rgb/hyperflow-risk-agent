from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from risk_agent.constants import APP_NAME, APP_VERSION


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="HFRA_")

    app_name: str = APP_NAME
    version: str = APP_VERSION
    max_daily_loss_pct: float = Field(default=0.05)
    max_open_positions: int = Field(default=3)
    max_lot_size: float = Field(default=0.25)
    min_confidence: float = Field(default=0.55)
    max_spread: float = Field(default=25.0)
    log_path: Path = Field(default=Path("logs/decisions.jsonl"))
    replay_path: Path = Field(default=Path("data/replay_examples.jsonl"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()