
"""Safety and eligibility guard for ResolveAI ticket creation."""

from dataclasses import dataclass
from incident_verifier import confirm_incident_match

@dataclass
class GuardDecision:
    allowed: bool
    reason: str
    policy_ref: str
    incident_id: str | None = None


def check_ticket_eligibility(
    *,
    employee: dict,
    topic: str,
    request_type: str,
    service_status_verified: bool,
    matching_incident: dict | None = None,
) -> GuardDecision:
    """Decide whether a ticket may proceed to the draft stage."""

    if not isinstance(employee, dict):
        return GuardDecision(
            False, "Employee context is missing.", "KB-016"
        )

    if employee.get("account_status") != "active":
        return GuardDecision(
            False, "Employee account is not active.", "KB-016"
        )

    if (
        type(employee.get("vip")) is not bool
        or type(employee.get("contractor")) is not bool
        or not isinstance(employee.get("department"), str)
        or not employee["department"].strip()
        or not isinstance(employee.get("email"), str)
        or not employee["email"].strip()
    ):
        return GuardDecision(
            False, "Employee directory data is incomplete.", "KB-016"
        )

    if topic == "vpn" and request_type == "request":
        if employee["contractor"]:
            return GuardDecision(
                False,
                "Contractors are not eligible for VPN access.",
                "KB-016",
            )

    if not service_status_verified:
        return GuardDecision(
            False,
            "Live service status could not be verified.",
            "KB-015",
        )

    if matching_incident is not None:
        return GuardDecision(
            False,
            "An active incident already covers this issue. "
            "Follow the documented workaround and subscribe "
            "to the status page.",
            "KB-015",
            incident_id=matching_incident.get("incident_id"),
        )

    return GuardDecision(
        True,
        "No blocking policy condition was detected.",
        "KB-015, KB-016",
    )

def verify_and_guard_ticket(
    *,
    employee: dict,
    topic: str,
    request_type: str,
    reported_service: str,
    reported_error_code: str,
    service_status_verified: bool,
    active_incidents: list[dict],
) -> GuardDecision:
    """Verify live incidents before allowing a ticket draft."""

    if not service_status_verified:
        return check_ticket_eligibility(
            employee=employee,
            topic=topic,
            request_type=request_type,
            service_status_verified=False,
        )

    if not isinstance(active_incidents, list):
        return GuardDecision(
            False,
            "Incident data is incomplete.",
            "KB-015",
        )

    unknown_incident = False

    for incident in active_incidents:
        verification = confirm_incident_match(
            incident=incident,
            employee=employee,
            reported_service=reported_service,
            reported_error_code=reported_error_code,
        )

        if verification.status == "confirmed_match":
            return check_ticket_eligibility(
                employee=employee,
                topic=topic,
                request_type=request_type,
                service_status_verified=True,
                matching_incident={
                    "incident_id": verification.incident_id
                },
            )

        if verification.status == "unknown":
            unknown_incident = True

    if unknown_incident:
        return GuardDecision(
            False,
            "Incident scope could not be verified. "
            "Manual verification is required.",
            "KB-015",
        )

    return check_ticket_eligibility(
        employee=employee,
        topic=topic,
        request_type=request_type,
        service_status_verified=True,
    )
