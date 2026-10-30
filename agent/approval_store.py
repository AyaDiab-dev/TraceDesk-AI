
"""Server-side ticket draft and approval storage."""

import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import uuid4

from draft_integrity import draft_fingerprint


@dataclass
class StoredDraft:
    draft_id: str
    draft: dict
    fingerprint: str
    employee_email: str
    expires_at: datetime
    approved: bool = False
    consumed: bool = False
    submitting: bool = False


class ApprovalStore:
    def __init__(self):
        self._drafts = {}
        self._lock = Lock()

    def save_draft(
        self,
        draft: dict,
        employee_email: str,
    ) -> str:
        if not isinstance(draft, dict) or not draft:
            raise ValueError("Valid draft required")

        if not isinstance(employee_email, str) or not employee_email.strip():
            raise ValueError("Employee email required")

        draft_copy = copy.deepcopy(draft)

        record = StoredDraft(
            draft_id=str(uuid4()),
            draft=draft_copy,
            fingerprint=draft_fingerprint(draft_copy),
            employee_email=employee_email.strip().casefold(),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=15),
        )

        with self._lock:
            self._drafts[record.draft_id] = record

        return record.draft_id

    def approve(
        self,
        draft_id: str,
        authenticated_email: str,
    ) -> bool:
        with self._lock:
            record = self._drafts.get(draft_id)

            if not self._valid_record(
                record, authenticated_email
            ):
                return False

            if record.approved or record.submitting:
                return False

            record.approved = True
            return True

    def reject(
        self,
        draft_id: str,
        authenticated_email: str,
    ) -> bool:
        """Permanently reject a pending draft without submitting it."""
        with self._lock:
            record = self._drafts.get(draft_id)

            if not self._valid_record(
                record, authenticated_email
            ):
                return False

            if record.approved or record.submitting:
                return False

            record.consumed = True
            return True

    def get_approved(
        self,
        draft_id: str,
        authenticated_email: str,
    ) -> dict | None:
        with self._lock:
            record = self._drafts.get(draft_id)

            if not self._valid_record(
                record, authenticated_email
            ):
                return None

            if not record.approved or record.submitting:
                return None

            return copy.deepcopy(record.draft)


    def get_pending(
        self,
        draft_id: str,
        authenticated_email: str,
    ) -> dict | None:
        """Read an unapproved draft for user review."""

        with self._lock:
            record = self._drafts.get(draft_id)

            if not self._valid_record(
                record, authenticated_email
            ):
                return None

            if record.approved or record.consumed or record.submitting:
                return None

            return copy.deepcopy(record.draft)


    def begin_submission(
        self,
        draft_id: str,
        authenticated_email: str,
    ) -> dict | None:
        """Atomically reserve an approved draft for submission."""

        with self._lock:
            record = self._drafts.get(draft_id)

            if not self._valid_record(
                record, authenticated_email
            ):
                return None

            if not record.approved or record.submitting:
                return None

            record.submitting = True
            return copy.deepcopy(record.draft)

    def finish_submission(
        self,
        draft_id: str,
        *,
        consumed: bool,
    ) -> bool:
        with self._lock:
            record = self._drafts.get(draft_id)

            if record is None or not record.submitting:
                return False

            record.submitting = False

            if consumed:
                record.consumed = True

            return True

    def mark_consumed(self, draft_id: str) -> bool:
        with self._lock:
            record = self._drafts.get(draft_id)

            if (
                record is None
                or record.consumed
                or record.submitting
                or not record.approved
            ):
                return False

            record.consumed = True
            return True

    @staticmethod
    def _valid_record(
        record: StoredDraft | None,
        authenticated_email: str,
    ) -> bool:
        if record is None or record.consumed:
            return False

        if record.submitting:
            return False

        if datetime.now(timezone.utc) >= record.expires_at:
            return False

        if not isinstance(authenticated_email, str):
            return False

        if (
            record.employee_email
            != authenticated_email.strip().casefold()
        ):
            return False

        if (
            draft_fingerprint(record.draft)
            != record.fingerprint
        ):
            return False

        return True
