import psycopg

from .config import settings

def get_conn() -> psycopg.Connection:
    """New connection to the database. Usage: `with get_conn() as conn:`
    commits the transaction upon success, rolls it back if an exception occurs,
    and closes the connection."""
    return psycopg.connect(settings.database_url)

def to_pgvector(vector: list[float]) -> str:
    """Converts a list of numbers into a format understood by pgvector, e.g., '[0.1,0.2].
    In a query, we use it along with a cast: %s::vector."""
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"
