import logging
from pathlib import Path

import httpx
import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .agent import run_agent
from .config import settings
from .db import get_conn
from .generation import answer_question
from .ingest import ingest_directory

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Local RAG Assistant", version="0.1.0")

class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    use_agent: bool = False

@app.get("/health")
def health() -> dict:
    """Checks whether the database response."""
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database not available")
    return {"status": "ok"}

@app.post("/ask")
def ask(request: AskRequest) -> dict:
    """Asks for a question. With `use_agent: true` the model makes the decision about the search."""
    try:
        if request.use_agent:
            return run_agent(request.question)
        return answer_question(request.question)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Communication error with the Ollama server")

@app.post("/ingest")
def ingest() -> dict:
    """It indexes documents from the DATA_DIR directory (the path is specified in the configuration,
    not by the user, so it is not possible to specify any directory on the server)."""
    directory = Path(settings.data_dir)
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder with data does not exist: {directory}")
    try:
        return {"ingested": ingest_directory(directory)}
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Communication error with the Ollama server")
