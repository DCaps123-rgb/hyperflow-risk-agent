from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app.config import get_settings
from app.schemas import (
    ExplainRequest,
    ExplainResponse,
    HealthResponse,
    ReplaySummary,
    RiskDecision,
    TradeIntent,
    VersionResponse,
)
from risk_agent.engine import RiskEngine
from risk_agent.explainability import explain_decision
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


@app.post("/explain_decision", response_model=ExplainResponse)
def explain_decision_endpoint(request: ExplainRequest) -> ExplainResponse:
    """Return a plain-English narrative explanation for a risk decision.

    Accepts the output of ``/evaluate_trade`` (or any dict with the same
    shape) and returns an enriched, human-readable breakdown.  This endpoint
    is entirely deterministic — it makes no external API calls and never
    modifies the supplied risk score, action, or rule results.
    """
    payload = request.model_dump()
    result = explain_decision(payload)
    return ExplainResponse(**result)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    html_path = Path(__file__).parent / "dashboard.html"
    return FileResponse(str(html_path), media_type="text/html")


@app.get("/api/dashboard")
def api_dashboard() -> JSONResponse:
    """Compute all dashboard data from real logs + engine state."""
    log_path = Path(settings.log_path)
    records: list[dict] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    # ── Risk score history (last 25 entries, for sparkline) ───────────────────
    score_history = [round(r["decision"]["risk_score"], 4) for r in records[-25:]]

    # ── Latest decision ───────────────────────────────────────────────────────
    latest = records[-1] if records else None
    latest_decision = latest["decision"] if latest else None
    latest_request = latest["request"] if latest else None
    latest_ts = latest["timestamp"] if latest else None

    # ── Aggregate counts ──────────────────────────────────────────────────────
    total = len(records)
    action_counts: Counter = Counter(r["decision"]["action"] for r in records)
    allow_count = action_counts.get("ALLOW", 0)
    scale_count = action_counts.get("SCALE_DOWN", 0)
    block_count = action_counts.get("BLOCK", 0)
    kill_count = action_counts.get("KILL_SWITCH", 0)

    # ── Average risk score ────────────────────────────────────────────────────
    avg_score = round(sum(r["decision"]["risk_score"] for r in records) / total, 4) if total else 0.0

    # ── Current / latest risk posture ─────────────────────────────────────────
    current_score = latest_decision["risk_score"] if latest_decision else None
    if current_score is None:
        posture = "NO DATA"
    elif current_score < 0.45:
        posture = "LOW RISK"
    elif current_score < 0.70:
        posture = "MEDIUM RISK"
    elif current_score < 0.90:
        posture = "HIGH RISK"
    else:
        posture = "CRITICAL"

    # ── Top risk drivers from failed rules ────────────────────────────────────
    failed_rule_counts: Counter = Counter()
    for r in records:
        for rr in r["decision"]["rule_results"]:
            if not rr["passed"]:
                failed_rule_counts[rr["name"]] += 1

    # Also count high-score decisions (score >= 0.70) as risk drivers
    high_score_count = sum(1 for r in records if r["decision"]["risk_score"] >= 0.70)
    block_driver_count = block_count + kill_count

    top_drivers = []
    for rule_name, count in failed_rule_counts.most_common(5):
        top_drivers.append({"name": rule_name.replace("_", " ").title(), "count": count})
    if high_score_count and "High Score Events" not in [d["name"] for d in top_drivers]:
        top_drivers.append({"name": "High Score Events (≥0.70)", "count": high_score_count})
    top_drivers = top_drivers[:5]

    # ── Live feed: last 10 records ────────────────────────────────────────────
    live_feed = []
    for r in reversed(records[-10:]):
        d = r["decision"]
        live_feed.append({
            "symbol": r["request"]["symbol"],
            "action": d["action"],
            "risk_score": d["risk_score"],
            "reason": d["reason"],
            "timestamp": r["timestamp"],
        })

    # ── Risk clusters: group by symbol + action ───────────────────────────────
    cluster_map: dict = defaultdict(lambda: {"count": 0, "max_score": 0.0, "actions": Counter()})
    for r in records:
        sym = r["request"]["symbol"]
        act = r["decision"]["action"]
        sc = r["decision"]["risk_score"]
        cluster_map[sym]["count"] += 1
        cluster_map[sym]["actions"][act] += 1
        cluster_map[sym]["max_score"] = max(cluster_map[sym]["max_score"], sc)

    clusters = []
    for sym, data in sorted(cluster_map.items(), key=lambda x: -x[1]["max_score"]):
        dominant_action = data["actions"].most_common(1)[0][0]
        if data["max_score"] >= 0.90:
            severity = "CRITICAL"
        elif data["max_score"] >= 0.70:
            severity = "HIGH"
        elif data["max_score"] >= 0.45:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        clusters.append({
            "symbol": sym,
            "event_count": data["count"],
            "severity": severity,
            "dominant_action": dominant_action,
            "max_score": round(data["max_score"], 4),
        })

    # ── AI Recommendations (evidence-based) ───────────────────────────────────
    recommendations = []

    stop_loss_fails = failed_rule_counts.get("stop_loss_required", 0)
    if stop_loss_fails > 0:
        recommendations.append({
            "icon": "shield-x",
            "title": f"Stop loss missing on {stop_loss_fails} trade(s) — enforce stop loss in strategy",
            "impact": "HIGH",
        })

    conf_fails = failed_rule_counts.get("minimum_confidence", 0)
    if conf_fails > 0:
        recommendations.append({
            "icon": "brain",
            "title": f"Confidence below threshold on {conf_fails} trade(s) — review signal quality",
            "impact": "HIGH",
        })

    spread_fails = failed_rule_counts.get("spread_limit", 0)
    if spread_fails > 0:
        recommendations.append({
            "icon": "trending-up",
            "title": f"Spread exceeded limit on {spread_fails} evaluation(s) — widen spread threshold or filter sessions",
            "impact": "MEDIUM",
        })

    if block_driver_count == 0 and total > 0:
        recommendations.append({
            "icon": "check-circle",
            "title": f"All {total} evaluations passed hard rules — risk profile is clean",
            "impact": "LOW",
        })

    if not recommendations:
        recommendations.append({
            "icon": "info",
            "title": "No evaluations in log yet — run /evaluate_trade to generate data",
            "impact": "INFO",
        })

    # ── Log file freshness ────────────────────────────────────────────────────
    log_fresh = False
    log_age_seconds = None
    log_entry_count = total
    if log_path.exists():
        log_mtime = log_path.stat().st_mtime
        log_age_seconds = int(time.time() - log_mtime)
        log_fresh = log_age_seconds < 3600  # fresh if modified in last hour

    # ── Health status cards ───────────────────────────────────────────────────
    api_healthy = True  # we're responding, so yes
    engine_healthy = True  # engine is instantiated at startup
    log_status = "fresh" if log_fresh else ("stale" if log_entry_count > 0 else "empty")
    model_status = "no_model"  # BaselineRiskModel.is_available() always False

    health_cards = {
        "api_server": {"status": "healthy", "detail": "Responding normally", "value": "Online"},
        "risk_engine": {"status": "healthy", "detail": "Deterministic engine active", "value": f"{total} evals"},
        "decision_logs": {
            "status": log_status,
            "detail": f"{log_entry_count} entries" + (f", {log_age_seconds}s ago" if log_age_seconds is not None else ""),
            "value": f"{log_entry_count} records",
        },
        "event_store": {
            "status": "healthy" if log_entry_count > 0 else "empty",
            "detail": f"JSONL event store at {settings.log_path}",
            "value": f"{log_entry_count} events",
        },
        "model_state": {
            "status": "unavailable",
            "detail": "No ML model connected. Deterministic scorer active.",
            "value": "No model",
        },
    }

    # ── Latest engine stage statuses ──────────────────────────────────────────
    architecture = {
        "ingestion": {
            "status": "active" if latest_request else "idle",
            "latest": f"{latest_request['symbol']} {latest_request['direction']}" if latest_request else "No data",
            "session": latest_request["session"] if latest_request else "—",
        },
        "control": {
            "status": "active" if latest_decision else "idle",
            "risk_score": latest_decision["risk_score"] if latest_decision else None,
            "passed_rules": sum(1 for rr in latest_decision["rule_results"] if rr["passed"]) if latest_decision else None,
            "failed_rules": sum(1 for rr in latest_decision["rule_results"] if not rr["passed"]) if latest_decision else None,
        },
        "execution": {
            "status": "active" if latest_decision else "idle",
            "action": latest_decision["action"] if latest_decision else "—",
            "lot_multiplier": latest_decision["lot_multiplier"] if latest_decision else None,
            "reason": latest_decision["reason"] if latest_decision else "—",
        },
        "health": {
            "api_alive": api_healthy,
            "log_fresh": log_fresh,
            "log_entries": log_entry_count,
        },
        "status": {
            "posture": posture,
            "current_score": current_score,
            "triggered_rules": [rr["name"] for rr in latest_decision["rule_results"] if not rr["passed"]] if latest_decision else [],
            "final_reason": latest_decision["reason"] if latest_decision else "No data",
        },
    }

    return JSONResponse({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_evaluations": total,
        "action_counts": {"ALLOW": allow_count, "SCALE_DOWN": scale_count, "BLOCK": block_count, "KILL_SWITCH": kill_count},
        "avg_risk_score": avg_score,
        "current_risk_score": current_score,
        "posture": posture,
        "score_history": score_history,
        "top_drivers": top_drivers,
        "live_feed": live_feed,
        "clusters": clusters,
        "recommendations": recommendations,
        "health": health_cards,
        "architecture": architecture,
        "latest_timestamp": latest_ts,
    })