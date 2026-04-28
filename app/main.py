from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI

from app.config import get_settings
from app.schemas import HealthResponse, ReplaySummary, RiskDecision, TradeIntent, VersionResponse
from risk_agent.engine import RiskEngine
from risk_agent.replay import run_replay

settings = get_settings()
engine = RiskEngine(settings)
app = FastAPI(title=settings.app_name, version=settings.version)


def _append_log(request_payload: dict, decision: dict) -> None:
    log_path = Path(settings.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": request_payload,
        "decision": decision,
        "version": settings.version,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(name=settings.app_name, version=settings.version)


@app.post("/evaluate_trade", response_model=RiskDecision)
def evaluate_trade(trade_intent: TradeIntent) -> RiskDecision:
    payload = trade_intent.model_dump()
    decision = engine.evaluate(payload)
    _append_log(payload, decision)
    return RiskDecision(**decision)


@app.post("/replay", response_model=ReplaySummary)
def replay() -> ReplaySummary:
    summary = run_replay(engine, settings.replay_path)
    return ReplaySummary(**summary)