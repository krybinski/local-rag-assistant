# Local RAG Assistant

A fully local Retrieval-Augmented Generation (RAG) service: it answers questions about your own documents (PDF, Markdown, plain text) and cites the sources. Embeddings and the language model run on your machine through [Ollama](https://ollama.com), so no document ever leaves it.

## Features

- **Ingestion** of `.pdf`, `.md` and `.txt` files: text extraction, chunking with overlap, embedding, storage in PostgreSQL.
- **Semantic search** with pgvector (cosine distance, HNSW index).
- **Grounded answers**: the model only sees retrieved fragments, is told to answer from them alone, and returns the sources (file, page, similarity score).
- **Hallucination guard**: if the best match scores below `MIN_SCORE`, the model is not called and the service answers that the information was not found.
- **Agent mode** (`use_agent: true`): the model decides when and how to search through tool calling, with a hard step limit.
- **Containerised**: PostgreSQL and the API run with Docker Compose.

## Architecture

```
            ingest                                   query
 files ──► load ──► chunk ──► embed ──► pgvector     question ──► embed ──► top-k search
 (pdf/md/txt)      (800/120)  (bge-m3)  (HNSW)                                  │
                                                                                ▼
                                             answer + sources ◄── LLM ◄── prompt with numbered fragments
                                                                  (qwen2.5:7b)
```

| Component | Technology |
|---|---|
| API | FastAPI, Pydantic |
| Vector store | PostgreSQL 16 + pgvector (`vector(1024)`, HNSW, cosine) |
| Embeddings | Ollama, `bge-m3` (1024 dimensions) |
| LLM | Ollama, `qwen2.5:7b` (supports tool calling) |
| DB driver / HTTP client | psycopg 3, httpx |
| Tests | pytest |
| Packaging | Docker, Docker Compose |

### Project layout

```
app/
  config.py         settings (environment variables / .env)
  db.py             database connection, vector formatting
  ollama_client.py  embed() and chat() calls to the Ollama REST API
  chunking.py       text splitting with overlap
  ingest.py         load files, chunk, embed, store
  retrieval.py      vector search
  generation.py     prompt building and answer generation
  agent.py          tool-calling agent loop
  main.py           FastAPI endpoints
docker/init.sql     schema (runs only on an empty database volume)
tests/              unit and API tests
```

## Prerequisites

- Docker and Docker Compose
- [Ollama](https://ollama.com) installed and running on the host
- Python 3.12 (only for running outside Docker and tests)
- About 8 GB of free RAM for the 7B model

Pull the models once:

```bash
ollama pull bge-m3
ollama pull qwen2.5:7b
```

## Quick start

```bash
# 1. Configure
cp .env.example .env

# 2. Put some documents in ./data (pdf, md, txt)

# 3. Start the database
docker compose up -d db

# 4. Install dependencies and run the API locally
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 5. Index the documents and ask a question
curl -X POST http://localhost:8000/ingest
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What does the documentation say about deployment?"}'
```

## Running with Docker

This runs the database and the API in containers. **Ollama runs on the host, not in Docker**, so the models can use your GPU or Apple Silicon. The `api` container reaches Ollama through `host.docker.internal` and the database through the service name `db`.

Common steps on every system:

```bash
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
mkdir data                      # put your .pdf / .md / .txt files here
ollama pull bge-m3
ollama pull qwen2.5:7b
docker compose up -d --build
```

Then check that everything works:

```bash
docker compose ps                         # db should be "healthy", api "running"
curl http://localhost:8000/health         # {"status":"ok"}
curl -X POST http://localhost:8000/ingest
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question": "What is this project about?"}'
```

On Windows PowerShell use `curl.exe` instead of `curl`, and send JSON with:

```powershell
Invoke-RestMethod -Method Post -Uri http://localhost:8000/ask `
  -ContentType "application/json" `
  -Body '{"question": "What is this project about?"}'
```

### Windows 10/11

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) with the **WSL 2 backend** (the default). Virtualization must be enabled in BIOS/UEFI.
2. Install [Ollama for Windows](https://ollama.com/download/windows) and keep it running (tray icon).
3. Run the common steps above in PowerShell, from the project folder.

No extra Ollama configuration is needed: Docker Desktop forwards `host.docker.internal` to the host.

### macOS (Intel and Apple Silicon)

1. Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) and start it.
2. Install [Ollama for macOS](https://ollama.com/download/mac) and keep it running (menu bar icon). Run Ollama natively, not in Docker: only the native build can use Apple's GPU.
3. Run the common steps above in Terminal.

No extra Ollama configuration is needed. The `pgvector/pgvector` image supports both `amd64` and `arm64`.

### Linux

1. Install Docker Engine and the Compose plugin ([installation guide](https://docs.docker.com/engine/install/)). To run `docker` without `sudo`: `sudo usermod -aG docker $USER`, then log out and back in.
2. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`.
3. **Make Ollama reachable from containers.** On Linux, `host.docker.internal` points to the Docker bridge address of the host (this is what `extra_hosts: host.docker.internal:host-gateway` in `docker-compose.yml` does), but Ollama listens only on `127.0.0.1` by default, so the container cannot connect. Make it listen on all interfaces:

   ```bash
   sudo systemctl edit ollama
   ```

   Add the following, save, then restart:

   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

   Binding to `0.0.0.0` exposes Ollama to your network. On an untrusted network, restrict port 11434 with a firewall (for example `ufw`) to the Docker bridge (`172.17.0.0/16`) only.
4. Run the common steps above in a terminal.

### Useful commands

```bash
docker compose logs -f api        # follow API logs
docker compose logs db            # database logs
docker compose restart api        # restart after changing .env
docker compose down               # stop (data is kept in the pgdata volume)
docker compose down -v            # stop and DELETE the database volume (full reset)
docker compose up -d --build      # rebuild after changing code or requirements.txt
```

### Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `port is already allocated` on 5432 | A local PostgreSQL uses the port. Stop it, or change the mapping to `"5433:5432"` (and `DATABASE_URL` in `.env` if you run the API outside Docker). |
| `role "rag" does not exist` | You are connecting to another PostgreSQL (see above), or the volume was created earlier with different settings. Reset with `docker compose down -v`, then `up -d`. |
| `/health` returns 503 | The `db` container is not healthy yet or crashed. Check `docker compose ps` and `docker compose logs db`. |
| `/ingest` or `/ask` returns 502 | The API cannot reach Ollama. Verify Ollama is running (`ollama list`). On Linux, make sure `OLLAMA_HOST=0.0.0.0:11434` is set (step 3). |
| Empty `embeddings` from Ollama | The request payload is wrong (the key must be `input`), or the model is not pulled. Test directly: `curl http://localhost:11434/api/embed -d '{"model":"bge-m3","input":["test"]}'`. |
| `/ingest` says the data directory is missing | The `./data` folder does not exist or is not mounted. Create it and run `docker compose up -d` again. |
| First request takes a long time | Ollama is loading the model into memory. Later requests are faster. |
| Changes in `.env` have no effect | Values under `environment:` in `docker-compose.yml` override `.env` for the `api` container. Edit the compose file and run `docker compose up -d`. |

### Running the API locally instead

If you prefer to run only the database in Docker and the API on the host:

```bash
docker compose up -d db
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Configuration

Settings are read from environment variables, then from `.env`, then from the defaults in `app/config.py`. Names are case-insensitive.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://rag:rag@localhost:5432/rag` | PostgreSQL connection string |
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server address |
| `EMBED_MODEL` | `bge-m3` | Embedding model |
| `EMBED_DIM` | `1024` | Embedding size; must match `vector(1024)` in `docker/init.sql` |
| `LLM_MODEL` | `qwen2.5:7b` | Chat model |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `120` | Characters shared by neighbouring chunks |
| `TOP_K` | `4` | Fragments passed to the model |
| `MIN_SCORE` | `0.0` | Minimum similarity of the best hit; below it the model is not called |
| `DATA_DIR` | `data` | Directory scanned by `/ingest` |

If a local PostgreSQL already uses port 5432, change the mapping in `docker-compose.yml` to `"5433:5432"` and set `DATABASE_URL=postgresql://rag:rag@localhost:5433/rag` in `.env`.

## API

Interactive documentation is available at `http://localhost:8000/docs` once the API is running.

### `GET /health`

Checks that the application can reach the database.

- `200` `{"status": "ok"}`
- `503` database unavailable

### `POST /ingest`

Indexes all `.pdf`, `.md` and `.txt` files from `DATA_DIR`. The directory comes from server configuration, never from the request, so clients cannot point it at arbitrary paths. The first call can be slow while Ollama loads the model.

- `200` `{"ingested": {...}}`
- `404` data directory not found
- `502` Ollama unreachable

### `POST /ask`

Request body:

```json
{
  "question": "What does the documentation say about deployment?",
  "use_agent": false
}
```

| Field | Type | Notes |
|---|---|---|
| `question` | string | 3 to 1000 characters |
| `use_agent` | boolean | `false` (default): fixed retrieve-then-generate pipeline. `true`: the model decides when to search |

Response:

```json
{
  "answer": "...",
  "sources": [
    { "source": "handbook.pdf", "page": 12, "score": 0.742 }
  ]
}
```

- `422` invalid request (for example a question shorter than 3 characters)
- `502` Ollama unreachable

A Postman collection (`Local_RAG_Assistant.postman_collection.json`) with all endpoints is included for manual testing.

## Tests

```bash
pytest -q
```

Unit tests cover chunking; API tests run without a live database or model by replacing external calls with test doubles.

## Design decisions and limitations

- **pgvector instead of a dedicated vector database**: one system for relational data and vectors, simple operations, enough for this scale.
- **Prompt-injection hygiene**: retrieved text is marked as data, not instructions. This reduces the risk but does not eliminate it.
- **Language**: the system prompt and the fallback message are in English and the model is instructed to answer in English. Change `SYSTEM_PROMPT` and `NOT_FOUND` in `app/generation.py` for other languages.
- **Naive chunking**: fixed-size character windows ignore document structure.
- **Schema management**: `docker/init.sql` runs only on an empty volume. Use a migration tool (for example Alembic) for real schema changes. To reset locally: `docker compose down -v`, which deletes all data.
- **No authentication or per-user access control** on the API.
- **Ollama context window**: Ollama's default context may truncate long prompts; set `num_ctx` explicitly if you raise `TOP_K` or `CHUNK_SIZE`.
