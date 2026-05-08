import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cache.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS processed (
            file_id TEXT PRIMARY KEY,
            file_name TEXT,
            people TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.commit()
    return conn


def is_processed(conn, file_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM processed WHERE file_id = ?", (file_id,)).fetchone()
    return row is not None


def mark_processed(conn, file_id: str, file_name: str, people: list[str]):
    conn.execute(
        "INSERT OR REPLACE INTO processed (file_id, file_name, people) VALUES (?, ?, ?)",
        (file_id, file_name, ",".join(people)),
    )
    conn.commit()
