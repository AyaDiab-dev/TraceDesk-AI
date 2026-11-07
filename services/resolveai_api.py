"""TraceDesk AI API: agent, demo employee lookup, and controlled ticket workflow.

Employee selection by email is for a LOCAL, NON-PUBLIC demo only.
It does not authenticate the person who entered the email.
"""
import os
import re
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "agent"))

from graph import build_graph  # noqa: E402
from approval_store import ApprovalStore  # noqa: E402
from ticket_submitter import TicketSubmitter  # noqa: E402
from session_store import SessionStore  # noqa: E402
from conversation_repository import ConversationRepository  # noqa: E402
from kb_loader import load_knowledge_base  # noqa: E402
from ticket_context import extract_ticket_context  # noqa: E402
from voice_intent import classify_wake_intent  # noqa: E402
from mcp_client import lookup_employee, search_tickets, get_ticket  # noqa: E402

app = FastAPI(title="TraceDesk AI API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def normalize_demo_email(email: str) -> str:
    """Normalize a Nakhla demo address (not proof of account ownership)."""
    value = email.strip().casefold()
    if not value or not re.fullmatch(r"[a-z0-9][a-z0-9._+-]*@nakhla\.example", value):
        raise HTTPException(status_code=422, detail="Enter a valid Nakhla work email.")
    return value


def mcp_failure(result: dict, message: str) -> None:
    """Translate MCP error envelopes to HTTP errors without leaking internals."""
    error = result.get("error") or {}
    code = error.get("code") if isinstance(error, dict) else None
    if code in {"employee_not_found", "ticket_not_found"}:
        raise HTTPException(status_code=404, detail="Record not found.")
    raise HTTPException(status_code=502, detail=message)


@app.get("/api/demo/employee")
async def identify_demo_employee(email: str = Query(..., min_length=3)):
    """Select a directory employee for a local demo; not authentication."""
    normalized = normalize_demo_email(email)
    try:
        result = await lookup_employee(normalized)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Employee directory is unavailable.") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Invalid directory response.")
    if result.get("ok") is not True:
        mcp_failure(result, "Unable to look up employee.")
    employee = result.get("employee")
    if not isinstance(employee, dict):
        raise HTTPException(status_code=502, detail="Invalid employee response.")
    return {"employee": employee, "mode": "local_demo"}


@app.get("/api/my-tickets")
async def list_my_tickets(
    requester_email: str = Query(..., min_length=3),
    q: str | None = Query(default=None, max_length=200),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=50),
):
    """Read ticket archive for a selected demo employee (no real authentication)."""
    email = normalize_demo_email(requester_email)
    if status not in (None, "open", "resolved", "closed"):
        raise HTTPException(status_code=422, detail="Invalid ticket status.")
    try:
        result = await search_tickets(
            query=q, requester_email=email, status=status, limit=limit
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to retrieve tickets.") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Invalid tickets response.")
    if result.get("ok") is not True:
        mcp_failure(result, "Unable to retrieve tickets.")
    tickets = result.get("tickets")
    if not isinstance(tickets, list) or not all(isinstance(t, dict) for t in tickets):
        raise HTTPException(status_code=502, detail="Invalid tickets response.")
    # Defense-in-depth for demo filtering: never return records for another email.
    own_tickets = [
        ticket for ticket in tickets
        if str(ticket.get("requester_email", "")).strip().casefold() == email
    ]
    return {
        "tickets": own_tickets,
        "count": len(own_tickets),
        "total_matches": result.get("total_matches", len(own_tickets)),
    }


@app.get("/api/my-tickets/{ticket_id}")
async def read_my_ticket(
    ticket_id: str,
    requester_email: str = Query(..., min_length=3),
):
    """Read a ticket only if it matches the selected local demo employee."""
    email = normalize_demo_email(requester_email)
    try:
        result = await get_ticket(ticket_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Unable to retrieve ticket details.") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Invalid ticket response.")
    if result.get("ok") is not True:
        mcp_failure(result, "Unable to retrieve ticket details.")
    ticket = result.get("ticket")
    if not isinstance(ticket, dict):
        raise HTTPException(status_code=502, detail="Invalid ticket response.")
    if str(ticket.get("requester_email", "")).strip().casefold() != email:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    return ticket


graph = build_graph()
approval_store = ApprovalStore()
ticket_submitter = TicketSubmitter(approval_store)
session_store = SessionStore()
conversation_repository = ConversationRepository()

@app.get("/api/knowledge-base")
async def list_knowledge_documents():
    """List current, authoritative KB documents for the demo UI."""
    documents = load_knowledge_base()

    eligible = [
        doc for doc in documents
        if doc["metadata"]["status"] == "current"
        and doc["metadata"]["authoritative"] is True
    ]

    # Exclude documents superseded by another eligible document.
    superseded_ids = {
        old_id
        for doc in eligible
        for old_id in (
            [doc["metadata"].get("supersedes")]
            if isinstance(doc["metadata"].get("supersedes"), str)
            else (doc["metadata"].get("supersedes") or [])
        )
        if isinstance(old_id, str)
    }

    result = [
        {
            "id": doc["id"],
            "title": doc["metadata"]["title"],
            "version": doc["metadata"]["version"],
            "last_updated": doc["metadata"]["last_updated"],
            "owner": doc["metadata"]["owner"],
            "tags": doc["metadata"].get("tags", []),
            "content": doc["content"],
        }
        for doc in eligible
        if doc["id"] not in superseded_ids
    ]

    result.sort(key=lambda doc: doc["id"])

    return {
        "documents": result,
        "count": len(result),
    }

@app.get("/api/conversations")
async def list_conversations(
    employee_email: str = Query(..., min_length=3),
):
    """List saved conversations for a selected demo employee."""
    email = normalize_demo_email(employee_email)

    return {
        "conversations": conversation_repository.list_conversations(
            email,
            limit=50,
        )
    }


@app.get("/api/conversations/{session_id}")
async def get_saved_conversation(
    session_id: str,
    employee_email: str = Query(..., min_length=3),
):
    """Read a saved conversation belonging to a demo employee."""
    email = normalize_demo_email(employee_email)

    conversation = conversation_repository.get_conversation(
        session_id,
        email,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return {"conversation": conversation}
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

class VoiceWakeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)

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

@app.post("/api/voice/wake-intent")
def voice_wake_intent(request: VoiceWakeRequest):
    """Classify a transcript without invoking the agent or tools."""
    decision = classify_wake_intent(request.text)

    return {
        "intent": decision.intent.value,
        "should_wake": decision.should_wake,
        "reason": decision.reason,
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

    if session["employee_email"]:
        conversation_repository.add_message(
            request.session_id,
            session["employee_email"],
            "user",
            request.message,
        )

    # Keep a short window for LangGraph,
    # but preserve the full session for ticket extraction.
    full_history = [
        *session["messages"],
        {"role": "user", "content": request.message},
    ]

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
            if session["employee_email"]:
                conversation_repository.add_message(
                    request.session_id,
                    session["employee_email"],
                    "assistant",
                    reply,
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
    if session["employee_email"]:
        conversation_repository.add_message(
            request.session_id,
            session["employee_email"],
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
