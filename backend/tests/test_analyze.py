from fastapi.testclient import TestClient

from app.main import app
from app.schemas.ingestion import IngestionResult
from app.services.conversation_service import clear_session


def test_analyze_returns_result_and_reuses_session_history(monkeypatch):
    session_id = "test-analyze-session"
    clear_session(session_id)
    observed_histories = []

    def fake_analyze_message(message):
        return IngestionResult(
            intent="order_tracking",
            risk_profile="medium",
            priority="low",
            requires_action=True,
            summary=message,
        )

    def fake_generate_response(result, history=None, current_message=None):
        observed_histories.append(history)
        return f"Response to: {current_message}"

    monkeypatch.setattr("app.main.analyze_message", fake_analyze_message)
    monkeypatch.setattr("app.main.generate_response", fake_generate_response)
    monkeypatch.setattr("app.main.database_enabled", lambda: False)

    with TestClient(app) as client:
        first = client.post(
            "/api/analyze",
            json={"session_id": session_id, "message": "Where is my order?"},
        )
        second = client.post(
            "/api/analyze",
            json={"session_id": session_id, "message": "And when will it arrive?"},
        )

    assert first.status_code == 200
    assert first.json()["session_id"] == session_id
    assert first.json()["response_markdown"] == "Response to: Where is my order?"
    assert first.json()["token_metadata"]["estimated_input_tokens"] > 0
    assert second.status_code == 200
    assert observed_histories[0] == []
    assert [message["role"] for message in observed_histories[1]] == [
        "user",
        "assistant",
    ]

    clear_session(session_id)
