CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    source      TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           SERIAL PRIMARY KEY,
    document_id  INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index  INTEGER NOT NULL,
    page         INTEGER NOT NULL DEFAULT 1,
    content      TEXT NOT NULL,
    embedding    vector(1024) NOT NULL  -- bge-m3 model dimension
);

-- Approximate nearest neighbor search index (cosine)
CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks (document_id);
