"""Isolated SQLite text memory; basic lexical retrieval, no embeddings."""
import sqlite3
from pathlib import Path

class KnowledgeStore:
    def __init__(self, path: str):
        self.path = str(Path(path))
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS documents (project TEXT NOT NULL, doc_id TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(project, doc_id))")

    def put(self, project: str, doc_id: str, body: str) -> None:
        if not all(isinstance(x, str) and x.strip() for x in (project, doc_id, body)):
            raise ValueError("Nonempty project, doc_id and body required")
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO documents VALUES (?, ?, ?)", (project, doc_id, body))

    def search(self, project: str, term: str, limit: int = 10) -> list[tuple[str, str]]:
        if not project or not term or not 1 <= limit <= 100:
            raise ValueError("Invalid search parameters")
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT doc_id, body FROM documents WHERE project = ? AND instr(lower(body), lower(?)) > 0 ORDER BY doc_id LIMIT ?", (project, term, limit)).fetchall()
