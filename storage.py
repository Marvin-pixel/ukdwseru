"""
storage.py - Penyimpanan data akun Anies (SQLite)

Hanya mengurus baca/tulis database. Validasi dan hashing password
ada di auth.py.
"""

import sqlite3
from datetime import datetime

DB_PATH = "anies_users.db"


def _get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    """Membuat tabel users jika belum ada."""
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                email         TEXT NOT NULL UNIQUE,
                password_hash BLOB NOT NULL,
                salt          BLOB NOT NULL,
                created_at    TEXT NOT NULL
            )
            """
        )


def create_user(username: str, email: str, password_hash: bytes, salt: bytes) -> bool:
    """Simpan akun baru. Mengembalikan False jika username/email sudah ada."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, salt, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, email, password_hash, salt, datetime.now().isoformat()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_user(identity: str):
    """Cari akun berdasarkan username atau email. Mengembalikan dict atau None."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, email, password_hash, salt FROM users "
            "WHERE username = ? OR email = ?",
            (identity.strip(), identity.strip().lower()),
        ).fetchone()

    if row is None:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "password_hash": row[3],
        "salt": row[4],
    }


def count_users() -> int:
    with _get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]