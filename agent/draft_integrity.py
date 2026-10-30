
"""Deterministic ticket draft integrity checks."""

import hashlib
import json


def draft_fingerprint(draft: dict) -> str:
    """Compute a stable fingerprint of the complete draft."""

    if not isinstance(draft, dict) or not draft:
        raise ValueError("A non-empty ticket draft is required.")

    serialized = json.dumps(
        draft,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def verify_draft_integrity(
    draft: dict,
    approved_fingerprint: str,
) -> bool:
    """Reject a draft that differs from the approved version."""

    if not isinstance(approved_fingerprint, str):
        return False

    try:
        current_fingerprint = draft_fingerprint(draft)
    except (TypeError, ValueError):
        return False

    return current_fingerprint == approved_fingerprint
