from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_api_health_endpoint_works() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_evaluate_endpoint_works() -> None:
    response = client.post(
        "/evaluate_trade",
        json={
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
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"] in {"ALLOW", "SCALE_DOWN"}
    assert "rule_results" in body