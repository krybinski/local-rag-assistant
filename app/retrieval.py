import sys

from .config import settings
from .db import get_conn, to_pgvector
from .ollama_client import embed

SEARCH_SQL = """
             SELECT c.content,
                    c.page,
                    d.source,
                    1 - (c.embedding <=> %s::vector) AS score
             FROM chunks c
                      JOIN documents d ON d.id = c.document_id
             ORDER BY c.embedding <=> %s::vector
                 LIMIT %s \
             """


def search(query: str, k: int | None = None) -> list[dict]:
    """Return the k most similar segments (in descending order by score).

    `<=>` this is the cosine distance in pgvector (0 = identical directions),
    therefore, we calculate similarity as 1 - the distance.
    """
    k = k or settings.top_k
    [query_vector] = embed([query])
    vector = to_pgvector(query_vector)

    with get_conn() as conn:
        rows = conn.execute(SEARCH_SQL, (vector, vector, k)).fetchall()

    return [
        {"content": content, "page": page, "source": source, "score": float(score)}
        for content, page, source, score in rows
    ]


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What do the documents contain?"
    for hit in search(question):
        print(f"{hit['score']:.3f}  {hit['source']} (str. {hit['page']})")
        print("   ", hit["content"][:200].replace("\n", " "), "...\n")
