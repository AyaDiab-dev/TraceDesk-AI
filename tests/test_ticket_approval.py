
"""Safety tests for TraceDesk AI ticket approval and submission."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

# Allow tests to import modules from the agent directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

from approval_store import ApprovalStore
from ticket_submitter import TicketSubmitter


# ---------------------------------------------------------
# Test 1: Unapproved drafts must not be submitted.
# ---------------------------------------------------------

def test_unapproved_draft_cannot_be_submitted():
    store = ApprovalStore()

    draft = {
        "subject": "Laptop keeps crashing",
        "category": "hardware",
        "priority": "P3",
    }
    email = "tariq.hamdan@nakhla.example"

    action_id = store.save_draft(draft, email)

    result = store.begin_submission(action_id, email)

    assert result is None


# ---------------------------------------------------------
# Test 2: Rejected drafts must not be submitted.
# ---------------------------------------------------------

def test_rejected_draft_cannot_be_submitted():
    store = ApprovalStore()

    draft = {
        "subject": "Laptop keeps crashing",
        "category": "hardware",
        "priority": "P3",
    }
    email = "tariq.hamdan@nakhla.example"

    action_id = store.save_draft(draft, email)

    rejected = store.reject(action_id, email)

    assert rejected is True

    result = store.begin_submission(action_id, email)

    assert result is None


# ---------------------------------------------------------
# Test 3: Approved drafts cannot be reused.
# ---------------------------------------------------------

def test_approved_draft_cannot_be_submitted_twice():
    store = ApprovalStore()

    draft = {
        "subject": "Laptop keeps crashing",
        "category": "hardware",
        "priority": "P3",
    }
    email = "tariq.hamdan@nakhla.example"

    action_id = store.save_draft(draft, email)

    assert store.approve(action_id, email) is True

    # The first submission is allowed.
    first = store.begin_submission(action_id, email)
    assert first == draft

    # A second submission is blocked while the first is active.
    second = store.begin_submission(action_id, email)
    assert second is None

    # Complete and consume the first submission.
    assert store.finish_submission(
        action_id,
        consumed=True,
    ) is True

    # A consumed draft cannot be reused.
    third = store.begin_submission(action_id, email)
    assert third is None


# ---------------------------------------------------------
# Test 4: TicketSubmitter must not call MCP twice.
# ---------------------------------------------------------

def test_ticket_submitter_prevents_duplicate_mcp_calls():
    asyncio.run(
        _check_ticket_submitter_prevents_duplicate_mcp_calls()
    )


async def _check_ticket_submitter_prevents_duplicate_mcp_calls():
    store = ApprovalStore()
    email = "tariq.hamdan@nakhla.example"

    draft = {
        "subject": "Laptop keeps crashing",
        "description": "Laptop crashes after restart.",
        "employee_email": email,
        "department": "Engineering",
        "category": "hardware",
        "priority": "P3",
        "attempted_steps": ["Restarted laptop"],
        "kb_references": [],
        "topic": "hardware",
        "request_type": "incident",
        "reported_service": "Laptop",
        "reported_error_code": "",
        "affected_users": 1,
        "completely_blocked": None,
        "workaround_available": None,
        "security_incident": False,
    }

    draft_id = store.save_draft(draft, email)

    assert store.approve(draft_id, email) is True

    # Simulate successful employee verification.
    verification = SimpleNamespace(
        allowed=True,
        employee={
            "email": email,
            "department": "Engineering",
        },
    )

    # Simulate a policy-compliant ticket draft.
    updated = SimpleNamespace(
        subject=draft["subject"],
        description=draft["description"],
        employee_email=email,
        department=draft["department"],
        category=draft["category"],
        priority=draft["priority"],
        attempted_steps=draft["attempted_steps"],
        kb_references=draft["kb_references"],
    )

    # Mock all external operations.
    # No real Helpdesk ticket will be created.
    with (
        patch(
            "ticket_submitter.revalidate_ticket",
            new_callable=AsyncMock,
            return_value=verification,
        ),
        patch(
            "ticket_submitter.build_ticket_draft",
            return_value=updated,
        ),
        patch(
            "ticket_submitter.create_approved_ticket",
            new_callable=AsyncMock,
            return_value={
                "ok": True,
                "ticket": {
                    "ticket_id": "IT-TEST-001",
                },
            },
        ) as create_mock,
    ):
        submitter = TicketSubmitter(store)

        # First submission should succeed.
        first = await submitter.submit(
            draft_id=draft_id,
            authenticated_email=email,
        )

        # Reusing the same draft must be blocked.
        second = await submitter.submit(
            draft_id=draft_id,
            authenticated_email=email,
        )

    assert first.status == "created"
    assert first.ticket_id == "IT-TEST-001"

    assert second.status == "blocked"

    # The MCP write operation must run exactly once.
    create_mock.assert_awaited_once()
