
"""Build policy-controlled ticket drafts for ResolveAI."""

from ticket_draft import TicketDraft
from ticket_policy import determine_priority, determine_category


def build_ticket_draft(
    *,
    employee: dict,
    subject: str,
    description: str,
    topic: str,
    affected_users: int,
    completely_blocked: bool,
    workaround_available: bool,
    request_type: str,
    security_incident: bool,
    attempted_steps: list[str],
    kb_references: list[str],
    reported_service: str = "",
    reported_error_code: str = "",
    troubleshooting_confirmed_none: bool = False,
) -> TicketDraft:
    """Create a draft using verified employee directory data."""

    if not isinstance(employee, dict):
        raise ValueError("Verified employee context is required")

    required = {
        "email",
        "department",
        "vip",
        "contractor",
        "account_status",
    }

    if not required.issubset(employee):
        raise ValueError("Incomplete employee context")

    if employee["account_status"] != "active":
        raise ValueError("Inactive employee account")

    if (
        type(employee["vip"]) is not bool
        or type(employee["contractor"]) is not bool
    ):
        raise ValueError("Invalid employee flags")

    department = employee["department"]

    if not isinstance(department, str) or not department.strip():
        raise ValueError("Invalid employee department")

    if (
        not isinstance(employee["email"], str)
        or not employee["email"].strip()
    ):
        raise ValueError("Invalid employee email")

    if (
        employee["contractor"]
        and topic == "vpn"
        and request_type == "request"
    ):
        raise ValueError(
            "Contractor VPN access requests are not permitted (KB-016)"
        )

    priority_result = determine_priority(
        affected_users=affected_users,
        completely_blocked=completely_blocked,
        workaround_available=workaround_available,
        request_type=request_type,
        is_vip=employee["vip"],
        security_incident=security_incident,
        department=department,
        is_vpn_issue=(topic == "vpn"),
    )

    category_result = determine_category(
        topic=topic,
        department=department,
    )

    draft = TicketDraft(
        subject=subject,
        description=description,
        employee_email=employee["email"],
        department=department,
        category=category_result["category"],
        priority=priority_result["priority"],
        attempted_steps=attempted_steps,
        kb_references=kb_references,
        policy_reasons=(
            priority_result["reasons"]
            + [category_result["reason"]]
        ),
        topic=topic,
        request_type=request_type,
        reported_service=reported_service,
        reported_error_code=reported_error_code,
        affected_users=affected_users,
        completely_blocked=completely_blocked,
        workaround_available=workaround_available,
        security_incident=security_incident,
        troubleshooting_confirmed_none=troubleshooting_confirmed_none,
    )

    draft.validate()
    return draft
