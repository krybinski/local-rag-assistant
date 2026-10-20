from fastapi.testclient import TestClient

from app.db import to_pgvector
from app.main import app

client = TestClient(app)

def test_ask_rejects_too_short_question():
    response = client.post("/ask", json={"question": "a"})
    assert response.status_code == 422

def test_ask_uses_rag_pipeline(monkeypatch):
    monkeypatch.setattr(
        "app.main.answer_question", lambda q: {"answer": "ok", "sources": []}
    )
    response = client.post("/ask", json={"question": "What is a RAG?"})
    assert response.status_code == 200
    assert response.json()["answer"] == "ok"

def test_ask_uses_agent_when_requested(monkeypatch):
    monkeypatch.setattr(
        "app.main.run_agent", lambda q: {"answer": "agent", "sources": [], "steps": 1}
    )
    response = client.post("/ask", json={"question": "What is a RAG?", "use_agent": True})
    assert response.json()["answer"] == "agent"

def test_to_pgvector_format():
    assert to_pgvector([0.5, 1.0]) == "[0.50000000,1.00000000]"
