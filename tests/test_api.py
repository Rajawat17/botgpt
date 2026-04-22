"""
Unit tests for BOT GPT API.
Run with: pytest tests/ -v
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app

# ── In-memory SQLite for tests ────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test_botgpt.db"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


client = TestClient(app)

MOCK_USER_ID = "test-user-001"


# ── Test 1: Health check ──────────────────────────────────────────────────────
def test_health_check():
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "BOT GPT" in data["service"]


# ── Test 2: Create conversation ───────────────────────────────────────────────
@patch("app.services.conversation_service.call_llm", new_callable=AsyncMock)
def test_create_conversation(mock_llm):
    mock_llm.return_value = "Hello! How can I help you today?"

    response = client.post("/api/v1/conversations/", json={
        "user_id": MOCK_USER_ID,
        "first_message": "Hello BOT GPT!",
        "mode": "open",
    })

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["user_id"] == MOCK_USER_ID
    assert data["mode"] == "open"
    assert len(data["messages"]) == 2          # user + assistant
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["content"] == "Hello! How can I help you today?"

    # Store for use in later tests
    pytest.created_conv_id = data["id"]


# ── Test 3: List conversations ────────────────────────────────────────────────
def test_list_conversations():
    response = client.get(f"/api/v1/conversations/?user_id={MOCK_USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1
    assert data["page"] == 1


# ── Test 4: Get conversation detail ──────────────────────────────────────────
def test_get_conversation_detail():
    conv_id = pytest.created_conv_id
    response = client.get(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == conv_id
    assert "messages" in data


# ── Test 5: Add message to conversation ──────────────────────────────────────
@patch("app.services.conversation_service.call_llm", new_callable=AsyncMock)
def test_add_message(mock_llm):
    mock_llm.return_value = "Sure, I can help with that!"
    conv_id = pytest.created_conv_id

    response = client.post(f"/api/v1/conversations/{conv_id}/messages", json={
        "user_message": "Can you help me with Python?",
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 4          # 2 original + 2 new
    last = data["messages"][-1]
    assert last["role"] == "assistant"
    assert last["content"] == "Sure, I can help with that!"


# ── Test 6: Get non-existent conversation ─────────────────────────────────────
def test_get_missing_conversation():
    response = client.get("/api/v1/conversations/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"


# ── Test 7: Delete conversation ───────────────────────────────────────────────
def test_delete_conversation():
    conv_id = pytest.created_conv_id
    response = client.delete(f"/api/v1/conversations/{conv_id}")
    assert response.status_code == 204

    # Confirm it's gone
    get_resp = client.get(f"/api/v1/conversations/{conv_id}")
    assert get_resp.status_code == 404


# ── Test 8: LLM context window builder ───────────────────────────────────────
def test_build_context_window():
    from app.services.llm_service import build_context_window

    messages = [{"role": "user", "content": "A" * 100}, {"role": "assistant", "content": "B" * 100}]
    result = build_context_window(messages, max_tokens=100)
    # With a tight budget, should return fewer messages
    assert isinstance(result, list)
    for msg in result:
        assert "role" in msg and "content" in msg


# ── Test 9: Pagination parameters ────────────────────────────────────────────
@patch("app.services.conversation_service.call_llm", new_callable=AsyncMock)
def test_pagination(mock_llm):
    mock_llm.return_value = "OK"
    # Create two more conversations
    for i in range(2):
        client.post("/api/v1/conversations/", json={
            "user_id": MOCK_USER_ID,
            "first_message": f"Test message {i}",
        })

    response = client.get(f"/api/v1/conversations/?user_id={MOCK_USER_ID}&page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert data["page_size"] == 2
