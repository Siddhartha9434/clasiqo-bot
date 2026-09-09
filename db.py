"""
SQLite storage for detected news items.
"""
import sqlite3
import json
from datetime import datetime, timezone
from contextlib import contextmanager

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    original_url TEXT NOT NULL UNIQUE,
    headline TEXT NOT NULL,
    summary TEXT,
    published_at TEXT,
    fetched_at TEXT NOT NULL,
    embedding BLOB,
    cluster_id INTEGER,
    category TEXT,
    importance INTEGER,
    is_rumour INTEGER DEFAULT 0,
    caption TEXT,
    image_path TEXT,
    status TEXT DEFAULT 'new',  -- new, clustered, analyzed, captioned, imaged, queued, posted, ignored, skipped_duplicate
    instagram_post_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    representative_item_id INTEGER,
    created_at TEXT NOT NULL,
    posted INTEGER DEFAULT 0
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def item_exists(url: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM news_items WHERE original_url = ?", (url,)
        ).fetchone()
        return row is not None


def insert_item(source, url, headline, summary, published_at, embedding=None):
    now = datetime.now(timezone.utc).isoformat()
    emb_blob = json.dumps(embedding.tolist()) if embedding is not None else None
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO news_items
               (source, original_url, headline, summary, published_at, fetched_at,
                embedding, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)""",
            (source, url, headline, summary, published_at, now, emb_blob, now),
        )
        return cur.lastrowid


def get_recent_items(hours=48):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM news_items
               WHERE fetched_at >= datetime('now', ?)
               ORDER BY fetched_at DESC""",
            (f'-{hours} hours',),
        ).fetchall()
        return [dict(r) for r in rows]


def get_items_by_status(status):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM news_items WHERE status = ? ORDER BY fetched_at ASC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_item(item_id, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [item_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE news_items SET {cols} WHERE id = ?", values)


def mark_duplicate(item_id, cluster_id):
    update_item(item_id, status="skipped_duplicate", cluster_id=cluster_id)


def create_cluster(representative_item_id):
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clusters (representative_item_id, created_at) VALUES (?, ?)",
            (representative_item_id, now),
        )
        return cur.lastrowid


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
