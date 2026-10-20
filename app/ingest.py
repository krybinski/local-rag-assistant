import logging
import sys

from pathlib import Path

from pypdf import PdfReader

from .chunking import chunk_text
from .config import settings
from .db import get_conn, to_pgvector
from .ollama_client import embed

log = logging.getLogger(__name__)

BATCH_SIZE = 16
SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}

def load_pages(path: Path) -> list[tuple[int, str]]:
    """Returns a list (page_number, text). Markdown/Txt files treat as single page."""
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        pages = [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    else:
        pages = [(1, path.read_text(encoding="utf-8", errors="ignore"))]

    # PostgreSQL does not accept the NUL character in text, but some PDF files contain it.
    return [(page, text.replace("\x00", "")) for page, text in pages]

def build_chunks(path: Path) -> list[tuple[int, str]]:
    """Returns a list (page_number, text_segment) for the whole file."""
    items: list[tuple[int, str]] = []

    for page, text in load_pages(path):
        for piece in chunk_text(text, settings.chunk_size, settings.chunk_overlap):
            items.append((page, piece))

    return items

def ingest_file(path: Path) -> int:
    """Index a single file. Returns a number of saved segments.

    First, we count all the embeddings; only then we open a transaction.
    This ensures that if an error occurs halfway through the process, the database isn’t left
    partially modified, and reloading the same file replaces the old version (idempotence).
    """
    items = build_chunks(path)
    if not items:
        log.warning("No text in the file %s (perhaps it is a scan without OCR)", path.name)
        return 0

    vectors: list[list[float]] = []
    for i in range(0, len(items), BATCH_SIZE):
        batch = [text for _, text in items[i : i + BATCH_SIZE]]
        vectors.extend(embed(batch))
        log.info("%s: %d/%d segments", path.name, min(i + BATCH_SIZE, len(items)), len(items))

    rows_data = [
        (idx, page, text, to_pgvector(vector))
        for idx, ((page, text), vector) in enumerate(zip(items, vectors))
    ]

    with get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE source = %s", (path.name,))
        doc_id = conn.execute(
            "INSERT INTO documents (source) VALUES (%s) RETURNING id", (path.name,)
        ).fetchone()[0]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, chunk_index, page, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s::vector)",
                [(doc_id, idx, page, text, vec) for idx, page, text, vec in rows_data],
            )

    return len(items)

def ingest_directory(directory: Path) -> dict[str, int]:
    """It indexes all supported files in the directory (recursively)."""
    result: dict[str, int] = {}

    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            result[path.name] = ingest_file(path)

    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    target = Path(sys.argv[1] if len(sys.argv) > 1 else settings.data_dir)
    print(ingest_directory(target))
