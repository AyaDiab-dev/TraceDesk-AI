
"""Persistent conversation history for TraceDesk AI."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock


DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "conversations.sqlite3"
)


class ConversationRepository:
    """Store and retrieve employee conversation history using SQLite."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        """Create database tables if they do not already exist."""
        with self._lock, self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    employee_email TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL
                        CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id)
                        REFERENCES conversations(session_id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_conversations_employee
                ON conversations(employee_email, updated_at);
            """)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_email(email):
        if not isinstance(email, str) or not email.strip():
            raise ValueError("Employee email is required")

        return email.strip().casefold()

    def add_message(self, session_id, employee_email, role, content):
        """Save a message and associate it with an employee conversation."""
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("Session ID is required")

        if role not in ("user", "assistant"):
            raise ValueError("Invalid message role")

        if not isinstance(content, str):
            raise ValueError("Message content must be a string")

        email = self._normalize_email(employee_email)
        now = self._now()

        with self._lock, self._connect() as connection:
            existing = connection.execute(
                """
                SELECT employee_email
                FROM conversations
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()

            if existing and existing["employee_email"] != email:
                raise ValueError(
                    "Conversation belongs to another employee"
                )

            if existing is None:
                title = (
                    content.strip()[:80] or "Support conversation"
                    if role == "user"
                    else "Support conversation"
                )

                connection.execute(
                    """
                    INSERT INTO conversations
                    (
                        session_id,
                        employee_email,
                        title,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (session_id, email, title, now, now),
                )

            connection.execute(
                """
                INSERT INTO conversation_messages
                (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, role, content, now),
            )

            connection.execute(
                """
                UPDATE conversations
                SET updated_at = ?
                WHERE session_id = ?
                """,
                (now, session_id),
            )

    def list_conversations(self, employee_email, limit=50):
        """Return saved conversations belonging to one employee."""
        email = self._normalize_email(employee_email)

        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")

        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    session_id,
                    title,
                    created_at,
                    updated_at
                FROM conversations
                WHERE employee_email = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (email, limit),
            ).fetchall()

        return [dict(row) for row in rows]

    def get_conversation(self, session_id, employee_email):
        """Return a conversation and its messages for the owning employee."""
        email = self._normalize_email(employee_email)

        with self._lock, self._connect() as connection:
            conversation = connection.execute(
                """
                SELECT
                    session_id,
                    title,
                    created_at,
                    updated_at
                FROM conversations
                WHERE session_id = ?
                  AND employee_email = ?
                """,
                (session_id, email),
            ).fetchone()

            if conversation is None:
                return None

            messages = connection.execute(
                """
                SELECT role, content, created_at
                FROM conversation_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

        return {
            **dict(conversation),
            "messages": [dict(row) for row in messages],
        }
