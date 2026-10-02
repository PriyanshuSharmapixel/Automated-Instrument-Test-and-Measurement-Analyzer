"""Persist complete run snapshots atomically in SQLite."""

import json
from pathlib import Path
import sqlite3


class RunStore:
    def __init__(self, path="outputs/runs.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as con:
            con.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, title TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL)")

    def save(self, result):
        payload = json.dumps(result, allow_nan=False)
        with sqlite3.connect(self.path) as con:
            con.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?)",
                        (result["run_id"], result["created_at"], result["plan"]["title"], result["status"], payload))

    def list_runs(self, limit=100):
        with sqlite3.connect(self.path) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute("SELECT run_id, created_at, title, status FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))]

    def get(self, run_id):
        with sqlite3.connect(self.path) as con:
            row = con.execute("SELECT payload FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown run: {run_id}")
        return json.loads(row[0])
