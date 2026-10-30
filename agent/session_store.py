
"""Thread-safe, in-memory conversation storage for ResolveAI."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock


class SessionStore:
    def __init__(self, ttl_minutes: int = 60):
        self._sessions = {}
        self._lock = RLock()
        self._ttl = timedelta(minutes=ttl_minutes)

    def get_or_create(self, session_id: str, email: str | None = None) -> dict:
        if not session_id or not session_id.strip():
            raise ValueError("session_id is required")

        normalized_email = email.strip().casefold() if email else None
        now = datetime.now(timezone.utc)

        with self._lock:
            session = self._sessions.get(session_id)

            if session and now >= session["expires_at"]:
                del self._sessions[session_id]
                session = None

            if session is None:
                session = {
                    "session_id": session_id,
                    "employee_email": normalized_email,
                    "messages": [],
                    "issue_context": {},
                    "awaiting_ticket_details": False,
                    "pending_action_id": None,
                    "expires_at": now + self._ttl,
                }
                self._sessions[session_id] = session

            elif normalized_email:
                existing_email = session["employee_email"]
                if existing_email and existing_email != normalized_email:
                    raise ValueError("Session belongs to another employee")
                session["employee_email"] = normalized_email

            session["expires_at"] = now + self._ttl
            return deepcopy(session)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Invalid message role")

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or datetime.now(timezone.utc) >= session["expires_at"]:
                raise ValueError("Session missing or expired")

            session["messages"].append({
                "role": role,
                "content": content,
            })

    def update_context(self, session_id: str, updates: dict) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or datetime.now(timezone.utc) >= session["expires_at"]:
                raise ValueError("Session missing or expired")

            session["issue_context"].update(deepcopy(updates))

    def set_pending_action(self, session_id: str, action_id: str | None) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or datetime.now(timezone.utc) >= session["expires_at"]:
                raise ValueError("Session missing or expired")

            session["pending_action_id"] = action_id

    def set_awaiting_ticket_details(
        self,
        session_id: str,
        awaiting: bool,
    ) -> None:
        """Track whether a ticket request awaits clarification."""

        if type(awaiting) is not bool:
            raise ValueError("awaiting must be a boolean")

        with self._lock:
            session = self._sessions.get(session_id)

            if (
                session is None
                or datetime.now(timezone.utc)
                >= session["expires_at"]
            ):
                raise ValueError("Session missing or expired")

            session["awaiting_ticket_details"] = awaiting
