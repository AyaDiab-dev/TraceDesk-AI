
"""Secure coordination of approved Helpdesk ticket submissions."""

from dataclasses import dataclass

from approval_store import ApprovalStore
from mcp_write_client import (
    TicketWriteUncertainError,
    create_approved_ticket,
)
from ticket_revalidator import revalidate_ticket
from ticket_builder import build_ticket_draft


@dataclass
class SubmissionResult:
    status: str
    reason: str
    ticket_id: str | None = None


class TicketSubmitter:
    def __init__(self, approval_store: ApprovalStore):
        self.approval_store = approval_store

    async def submit(
        self,
        *,
        draft_id: str,
        authenticated_email: str,
    ) -> SubmissionResult:
        """Submit a stored, approved draft using trusted identity."""

        draft = self.approval_store.begin_submission(
            draft_id,
            authenticated_email,
        )

        if draft is None:
            return SubmissionResult(
                status="blocked",
                reason="Draft is missing, expired, unapproved, or already used.",
            )

        # Keep the draft consumed after any submission attempt.
        # This avoids unsafe automatic retries after uncertain writes.
        consumed = True

        try:
            required = (
                "subject",
                "description",
                "employee_email",
                "department",
                "category",
                "priority",
                "attempted_steps",
                "kb_references",
                "topic",
                "request_type",
                "reported_service",
                "reported_error_code",
                "affected_users",
                "completely_blocked",
                "workaround_available",
                "security_incident",
            )

            if any(field not in draft for field in required):
                return SubmissionResult(
                    status="blocked",
                    reason="Approved draft is incomplete.",
                )

            draft_email = draft["employee_email"]

            if (
                not isinstance(draft_email, str)
                or not isinstance(authenticated_email, str)
                or draft_email.strip().casefold()
                != authenticated_email.strip().casefold()
            ):
                return SubmissionResult(
                    status="blocked",
                    reason="Requester identity mismatch.",
                )

            # Revalidate using context from the stored draft only.
            verification = await revalidate_ticket(
                employee_email=draft_email,
                topic=draft["topic"],
                request_type=draft["request_type"],
                reported_service=draft["reported_service"],
                reported_error_code=draft["reported_error_code"],
            )

            if not verification.allowed:
                return SubmissionResult(
                    status="blocked",
                    reason=verification.reason,
                )

            employee = verification.employee

            if not isinstance(employee, dict):
                return SubmissionResult(
                    status="blocked",
                    reason="Verified employee context is unavailable.",
                )

            # Recalculate policy-controlled fields using live data.
            updated = build_ticket_draft(
                employee=employee,
                subject=draft["subject"],
                description=draft["description"],
                topic=draft["topic"],
                request_type=draft["request_type"],
                reported_service=draft["reported_service"],
                reported_error_code=draft["reported_error_code"],
                affected_users=draft["affected_users"],
                completely_blocked=draft["completely_blocked"],
                workaround_available=draft["workaround_available"],
                security_incident=draft["security_incident"],
                attempted_steps=draft["attempted_steps"],
                kb_references=draft["kb_references"],
            )

            # The user approved the original priority/category.
            # Any change requires a fresh draft and approval.
            if (
                updated.category != draft["category"]
                or updated.priority != draft["priority"]
                or updated.department != draft["department"]
            ):
                return SubmissionResult(
                    status="blocked",
                    reason=(
                        "Ticket policy values changed. "
                        "A new draft and approval are required."
                    ),
                )

            response = await create_approved_ticket(
                subject=updated.subject,
                description=updated.description,
                category=updated.category,
                priority=updated.priority,
                requester_email=updated.employee_email,
                department=updated.department,
                attempted_steps=updated.attempted_steps,
                kb_refs=updated.kb_references,
                affected_users=draft["affected_users"],
                idempotency_key=draft_id,
            )

            if response.get("ok") is not True:
                return SubmissionResult(
                    status="failed",
                    reason="Helpdesk rejected ticket creation.",
                )

            ticket = response.get("ticket")

            if not isinstance(ticket, dict):
                return SubmissionResult(
                    status="uncertain",
                    reason="Helpdesk response did not confirm a ticket.",
                )

            ticket_id = ticket.get("ticket_id")

            if not isinstance(ticket_id, str) or not ticket_id:
                return SubmissionResult(
                    status="uncertain",
                    reason="Helpdesk returned no valid ticket ID.",
                )

            return SubmissionResult(
                status="created",
                reason="Ticket created successfully.",
                ticket_id=ticket_id,
            )

        except TicketWriteUncertainError:
            return SubmissionResult(
                status="uncertain",
                reason=(
                    "Ticket creation outcome is unknown. "
                    "Do not submit a new draft until verified."
                ),
            )

        except Exception:
            return SubmissionResult(
                status="blocked",
                reason="Submission failed a safety check.",
            )

        finally:
            self.approval_store.finish_submission(
                draft_id,
                consumed=consumed,
            )
