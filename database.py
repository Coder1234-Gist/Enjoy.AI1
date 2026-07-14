"""
Lightweight SQLite persistence layer.

Operations here are fast (single small table, indexed by primary key), so
we use plain synchronous sqlite3 rather than pulling in aiosqlite — this
keeps the project dependency-light. If you scale to many thousands of
users, swap this for aiosqlite or a real database without changing the
call sites much.
"""
import sqlite3
from contextlib import contextmanager
from config import DB_PATH


@contextmanager
def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id         INTEGER PRIMARY KEY,
                username        TEXT,
                first_name      TEXT,
                subscribed      INTEGER NOT NULL DEFAULT 0,
                last_category   TEXT,
                last_genre      TEXT,
                joined_at       TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def upsert_user(user_id: int, username: str | None, first_name: str | None):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        """, (user_id, username, first_name))


def set_subscription(user_id: int, subscribed: bool):
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET subscribed = ? WHERE user_id = ?",
            (1 if subscribed else 0, user_id),
        )


def is_subscribed(user_id: int) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT subscribed FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        return bool(row and row["subscribed"])


def get_subscribed_user_ids() -> list[int]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE subscribed = 1"
        ).fetchall()
        return [r["user_id"] for r in rows]


def save_last_filters(user_id: int, category: str, genre: str):
    with _conn() as conn:
        conn.execute(
            "UPDATE users SET last_category = ?, last_genre = ? WHERE user_id = ?",
            (category, genre, user_id),
        )


def get_last_filters(user_id: int) -> tuple[str | None, str | None]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT last_category, last_genre FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None, None
        return row["last_category"], row["last_genre"]
