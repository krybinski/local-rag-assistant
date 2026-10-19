import httpx

from .config import settings

# A single shared HTTP client. The timeout is set to a high value because the initial model
# invocation (loading it into memory) can take several tens of seconds.
_client = httpx.Client(base_url=settings.ollama_url, timeout=300.0)

def embed(texts: list[str]) -> list[list[float]]:
    """Returns a vector (embedding) for each text in the list"""
    response = _client.post(
        "/api/embed",
        json={"model": settings.embed_model, "input": texts},
    )
    response.raise_for_status()
    return response.json()["embeddings"]

def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """A single turn of conversation with the model.
    Returns the assistant's message (keys: content and, optionally, tool_calls)."""
    payload: dict = {
        "model": settings.llm_model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1} # low temperature = more repeatable responses
    }
    if tools:
        payload["tools"] = tools
    response = _client.post("/api/chat", json=payload)
    response.raise_for_status()
    return response.json()["message"]
