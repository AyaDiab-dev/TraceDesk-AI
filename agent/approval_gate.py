"""ResolveAI - Explicit approval gate for ticket drafts."""

from dataclasses import dataclass


@dataclass
class ApprovalDecision:
    approved: bool
    reason: str
    ready_for_submission: bool


def check_ticket_approval(
    *,
    ticket_draft: dict | None,
    user_approved: bool,
    authenticated: bool = False,
) -> ApprovalDecision:
    """Require a valid draft, explicit approval and authentication."""

    if not isinstance(ticket_draft, dict) or not ticket_draft:
        return ApprovalDecision(
            approved=False,
            reason="A valid ticket draft is required.",
            ready_for_submission=False,
        )

    if user_approved is not True:
        return ApprovalDecision(
            approved=False,
            reason="Explicit user approval is required.",
            ready_for_submission=False,
        )

    if authenticated is not True:
        return ApprovalDecision(
            approved=False,
            reason="Authenticated user identity is required.",
            ready_for_submission=False,
        )

    return ApprovalDecision(
        approved=True,
        reason="Approval and authentication checks passed. Revalidation is required before submission.",
        ready_for_submission=True,
    )