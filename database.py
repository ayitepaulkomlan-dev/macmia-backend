"""
database.py — Gestion base de données utilisateurs SQLite (MACMIA)
"""
import sqlite3
import os
import uuid
import hashlib
import hmac
import base64
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise les tables users et sessions au démarrage."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT    PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            expires_at TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    """Hash PBKDF2-SHA256 (hashlib builtin — aucune dépendance externe)."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.b64encode(salt + key).decode()


def verify_password(password: str, stored_hash: str) -> bool:
    """Vérifie un mot de passe contre son hash stocké."""
    try:
        decoded = base64.b64decode(stored_hash.encode())
        salt = decoded[:32]
        stored_key = decoded[32:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return hmac.compare_digest(key, stored_key)
    except Exception:
        return False


def create_session(user_id: int, days: int = 30) -> str:
    """Crée un token UUID valide pendant 30 jours."""
    token = str(uuid.uuid4())
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at),
    )
    conn.commit()
    conn.close()
    return token


def get_user_by_token(token: str) -> dict | None:
    """Retourne l'utilisateur associé à un token valide, ou None."""
    conn = get_db()
    row = conn.execute(
        """SELECT u.id, u.username, u.email, s.expires_at
           FROM sessions s JOIN users u ON s.user_id = u.id
           WHERE s.token = ? AND s.expires_at > datetime('now')""",
        (token,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(token: str):
    """Supprime une session (déconnexion)."""
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
