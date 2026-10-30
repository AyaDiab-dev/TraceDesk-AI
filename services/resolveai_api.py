
"""ResolveAI API - LangGraph agent and controlled ticket workflow."""
import re
import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

from graph import build_graph  # noqa: E402
from approval_store import ApprovalStore  # noqa: E402
from ticket_submitter import TicketSubmitter  # noqa: E402
from session_store import SessionStore  # noqa: E402
from ticket_context import extract_ticket_context  # noqa: E402


app = FastAPI(title="ResolveAI API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

graph = build_graph()
approval_store = ApprovalStore()
ticket_submitter = TicketSubmitter(approval_store)
session_store = SessionStore()


def demo_identity() -> str:
    """Return the server-configured demo identity.

    This is a single-user demo mode, not real authentication.
    Do not expose this mode on a public deployment.
    """
    email = os.getenv(
        "RESOLVEAI_DEMO_EMAIL",
        "samir.nassar@nakhla.example",
    ).strip().casefold()

    if not email.endswith("@nakhla.example"):
        raise HTTPException(
            status_code=500,
            detail="Invalid server demo identity.",
        )

    return email


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class ChatUser(BaseModel):
    email: str | None = None


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=2000)
    user: ChatUser | None = None

class ApproveRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    action_id: str = Field(min_length=1)
    approved: bool

class DraftRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    topic: str = Field(min_length=1, max_length=100)
    request_type: str = Field(min_length=1, max_length=100)
    reported_service: str = Field(min_length=1, max_length=100)
    reported_error_code: str = Field(min_length=1, max_length=100)
    affected_users: int = Field(default=1, ge=1, le=10000)
    completely_blocked: bool
    workaround_available: bool
    security_incident: bool = False
    attempted_steps: list[str] = Field(min_length=1)
    kb_references: list[str] = Field(default_factory=list)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "resolveai",
    }


def prepare_ticket_fields(context: dict, messages: list[dict]) -> dict:
    """Prepare a ticket description from supported conversation facts."""

    topic = context.get("topic", "")
    service = context.get("reported_service", "")
    error_code = context.get("reported_error_code", "")

    user_messages = [
        message["content"]
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "user"
        and isinstance(message.get("content"), str)
    ]

    if not (topic and service):
        return {}

    issue_label = error_code if error_code else "reported issue"
    subject = f"{service} {issue_label} - Support required"

    description = (
        f"Reported service: {service}\n"
        f"Error code: {error_code or 'Not reported'}\n"
        "Employee report:\n"
        + "\n".join(user_messages[-3:])
    )

    known_kb = {
        "NX-112": ["KB-002"],
        "NX-781": ["KB-002"],
    }

    result = {
        "ticket_subject": subject,
        "ticket_description": description,
        "kb_references": known_kb.get(error_code, []),
    }

    # Security classification must come from verified evidence,
    # not from an unconditional default.
    if isinstance(context.get("security_incident"), bool):
        result["security_incident"] = context["security_incident"]

    return result


@app.post("/api/chat")

def official_chat(request: ChatRequest):
    """Chat with session memory and safe ticket clarification."""
    email = request.user.email if request.user else None

    try:
        session = session_store.get_or_create(
            request.session_id,
            email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    conversation_history = session["messages"][-6:]
    awaiting_details = session.get(
        "awaiting_ticket_details", False
    )

    session_store.add_message(
        request.session_id,
        "user",
        request.message,
    )

    full_history = conversation_history + [{
        "role": "user",
        "content": request.message,
    }]

    ticket_context = extract_ticket_context(full_history)
    ticket_fields = prepare_ticket_fields(
        ticket_context,
        full_history,
    )

    # Preserve ticket intent when the user answers a
    # previously requested clarification.
    graph_question = request.message

    if awaiting_details:
        if re.search(
            r"\b(cancel|never mind|nevermind|stop)\b",
            request.message,
            re.IGNORECASE,
        ):
            session_store.set_awaiting_ticket_details(
                request.session_id, False
            )

            reply = (
                "Understood. The ticket request was cancelled. "
                "No ticket was created."
            )
            session_store.add_message(
                request.session_id, "assistant", reply
            )

            return {
                "session_id": request.session_id,
                "reply": reply,
                "citations": [],
                "tool_calls": [],
                "pending_action": None,
                "result": None,
            }

        graph_question = (
            "Please create a support ticket for the "
            "previously reported issue. "
            "The employee's latest clarification is: "
            + request.message
        )

    result = graph.invoke({
        "question": graph_question,
        "employee_email": session.get("employee_email") or "",
        "conversation_history": conversation_history,
        **ticket_context,
        **ticket_fields,
    })

    reply = result.get("answer", "")
    pending_action = None
    draft = result.get("ticket_draft")

    missing_steps = (
        result.get("ticket_guard_allowed") is True
        and not isinstance(draft, dict)
        and "attempted_steps" in (
            result.get("ticket_draft_error") or ""
        )
    )

    if missing_steps:
        reply = (
            "Before I prepare your support ticket, "
            "have you tried any troubleshooting steps, "
            "such as restarting your laptop or checking "
            "the relevant device settings? "
            "Please tell me what you tried, or say "
            "that you haven't tried anything yet."
        )
        session_store.set_awaiting_ticket_details(
            request.session_id, True
        )

    elif isinstance(draft, dict) and (
        result.get("ticket_guard_allowed") is True
    ):
        employee_email = session.get("employee_email")

        if (
            employee_email
            and draft.get("employee_email", "").casefold()
            == employee_email.casefold()
        ):
            draft_id = approval_store.save_draft(
                draft, employee_email
            )
            session_store.set_pending_action(
                request.session_id, draft_id
            )
            session_store.set_awaiting_ticket_details(
                request.session_id, False
            )

            pending_action = {
                "action_id": draft_id,
                "type": "create_ticket",
                "summary": (
                    f"{draft['subject']} | "
                    f"{draft['category']} | "
                    f"{draft['priority']}"
                ),
            }

    else:
        # A policy block or verification failure must not
        # leave a ticket request awaiting clarification.
        session_store.set_awaiting_ticket_details(
            request.session_id, False
        )

    session_store.add_message(
        request.session_id,
        "assistant",
        reply,
    )

    evidence = result.get("evidence") or []
    citations = list(dict.fromkeys(
        item["document_id"]
        for item in evidence
        if isinstance(item, dict)
        and isinstance(item.get("document_id"), str)
    ))

    return {
        "session_id": request.session_id,
        "reply": reply,
        "citations": citations,
        "tool_calls": result.get("tool_calls") or [],
        "pending_action": pending_action,
        "result": None,
    }

@app.post("/api/approve")
async def official_approve(request: ApproveRequest):
    """Approve or reject a pending ticket action."""

    try:
        session = session_store.get_or_create(
            request.session_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    email = session.get("employee_email")

    if not email:
        raise HTTPException(
            status_code=403,
            detail="Verified session identity required.",
        )

    if session.get("pending_action_id") != request.action_id:
        raise HTTPException(
            status_code=409,
            detail="Action does not match pending session action.",
        )

    # --------------------------------------------------
    # REJECTION: Cancel without creating a ticket
    # --------------------------------------------------
    if not request.approved:
        rejected = approval_store.reject(
            request.action_id,
            email,
        )

        if not rejected:
            raise HTTPException(
                status_code=409,
                detail="Action cannot be rejected.",
            )

        session_store.set_pending_action(
            request.session_id,
            None,
        )

        return {
            "session_id": request.session_id,
            "reply": (
                "Ticket request cancelled. "
                "No ticket was created."
            ),
            "citations": [],
            "tool_calls": [],
            "pending_action": None,
            "result": None,
        }

    # --------------------------------------------------
    # APPROVAL: Approve the pending action
    # --------------------------------------------------
    approved = approval_store.approve(
        request.action_id,
        email,
    )

    if not approved:
        raise HTTPException(
            status_code=409,
            detail="Action cannot be approved.",
        )

    # --------------------------------------------------
    # SUBMISSION: Create ticket through the submitter
    # --------------------------------------------------
    submission = await ticket_submitter.submit(
        draft_id=request.action_id,
        authenticated_email=email,
    )

    session_store.set_pending_action(
        request.session_id,
        None,
    )

    # --------------------------------------------------
    # RESULT: Confirm only when a ticket ID exists
    # --------------------------------------------------
    if submission.ticket_id:
        reply = (
            "Ticket created successfully: "
            f"{submission.ticket_id}"
        )
    else:
        reply = (
            "Ticket creation could not be confirmed. "
            f"Reason: {submission.reason}. "
            "No ticket ID was returned."
        )

    return {
        "session_id": request.session_id,
        "reply": reply,
        "citations": [],
        "tool_calls": (
            ["create_ticket"]
            if submission.ticket_id
            else []
        ),
        "pending_action": None,
        "result": (
            {"ticket_id": submission.ticket_id}
            if submission.ticket_id
            else None
        ),
    }

@app.post("/agent/ask")
def ask_agent(request: AskRequest):
    result = graph.invoke({
        "question": request.question,
    })

    return {
        "intent": result.get("intent"),
        "answer": result.get("answer", ""),
        "evidence": result.get("evidence", []),
        "matching_incidents": result.get(
            "matching_incidents", []
        ),
        "service_status_error": result.get(
            "service_status_error"
        ),
        "trust_trace": {
            "ticket_guard_allowed": result.get(
                "ticket_guard_allowed"
            ),
            "ticket_guard_reason": result.get(
                "ticket_guard_reason"
            ),
            "ticket_guard_policy_ref": result.get(
                "ticket_guard_policy_ref"
            ),
            "ticket_guard_incident_id": result.get(
                "ticket_guard_incident_id"
            ),
        },
    }


@app.post("/tickets/draft")
def create_draft(request: DraftRequest):
    email = demo_identity()

    # The server controls the employee identity.
    # The graph performs employee lookup, guard checks,
    # and policy-based draft construction.
    state = {
        "question": request.question,
        "employee_email": email,
        "ticket_subject": request.subject,
        "ticket_description": request.description,
        "topic": request.topic,
        "request_type": request.request_type,
        "reported_service": request.reported_service,
        "reported_error_code": request.reported_error_code,
        "affected_users": request.affected_users,
        "completely_blocked": request.completely_blocked,
        "workaround_available": request.workaround_available,
        "security_incident": request.security_incident,
        "attempted_steps": request.attempted_steps,
        "kb_references": request.kb_references,
    }

    result = graph.invoke(state)

    if result.get("ticket_guard_allowed") is not True:
        raise HTTPException(
            status_code=403,
            detail=result.get(
                "ticket_guard_reason",
                "Ticket request was not authorized.",
            ),
        )

    draft = result.get("ticket_draft")

    if not isinstance(draft, dict):
        raise HTTPException(
            status_code=422,
            detail=result.get(
                "ticket_draft_error",
                "Ticket draft could not be created.",
            ),
        )

    if draft.get("employee_email", "").casefold() != email:
        raise HTTPException(
            status_code=403,
            detail="Draft requester mismatch.",
        )

    draft_id = approval_store.save_draft(
        draft,
        email,
    )

    return {
        "draft_id": draft_id,
        "status": "awaiting_user_approval",
        "draft": draft,
        "answer": result.get("answer", ""),
        "trust_trace": {
            "ticket_guard_allowed": True,
            "ticket_guard_reason": result.get(
                "ticket_guard_reason"
            ),
            "ticket_guard_policy_ref": result.get(
                "ticket_guard_policy_ref"
            ),
            "ticket_guard_incident_id": result.get(
                "ticket_guard_incident_id"
            ),
            "approval_status": "awaiting_user_approval",
        },
    }


@app.get("/tickets/draft/{draft_id}")
def get_draft(draft_id: str):
    email = demo_identity()

    draft = approval_store.get_pending(
        draft_id,
        email,
    )

    if draft is None:
        raise HTTPException(
            status_code=404,
            detail="Draft not found or unavailable.",
        )

    return {
        "draft_id": draft_id,
        "draft": draft,
    }


@app.post("/tickets/{draft_id}/approve")
def approve_draft(draft_id: str):
    email = demo_identity()

    approved = approval_store.approve(
        draft_id,
        email,
    )

    if not approved:
        raise HTTPException(
            status_code=409,
            detail="Draft cannot be approved.",
        )

    return {
        "draft_id": draft_id,
        "status": "approved",
    }


@app.post("/tickets/{draft_id}/submit")
async def submit_draft(draft_id: str):
    email = demo_identity()

    result = await ticket_submitter.submit(
        draft_id=draft_id,
        authenticated_email=email,
    )

    return {
        "status": result.status,
        "reason": result.reason,
        "ticket_id": result.ticket_id,
    }
