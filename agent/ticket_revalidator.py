
"""Live revalidation before ticket submission."""

from dataclasses import dataclass

from mcp_client import get_service_status, lookup_employee
from ticket_guard import verify_and_guard_ticket


@dataclass
class RevalidationResult:
    allowed: bool
    reason: str
    policy_ref: str
    employee: dict | None = None


async def revalidate_ticket(
    *,
    employee_email: str,
    topic: str,
    request_type: str,
    reported_service: str,
    reported_error_code: str,
) -> RevalidationResult:
    """Fail closed unless current employee and incident checks pass."""

    try:
        # Fetch live data through MCP.
        employee_result = await lookup_employee(employee_email)
        status_result = await get_service_status()

        # Validate MCP response envelopes.
        if not isinstance(employee_result, dict):
            raise ValueError("Invalid employee response")

        if not isinstance(status_result, dict):
            raise ValueError("Invalid service status response")

        if employee_result.get("ok") is not True:
            raise ValueError("Employee lookup failed")

        if status_result.get("ok") is not True:
            raise ValueError("Service status lookup failed")

        # Extract actual data from MCP response envelopes.
        employee = employee_result.get("employee")
        status_data = status_result.get("status")

        if not isinstance(employee, dict):
            raise ValueError("Invalid employee data")

        if not isinstance(status_data, dict):
            raise ValueError("Invalid service status data")

        # Verify that the returned employee matches the requested email.
        returned_email = employee.get("email")

        if not isinstance(returned_email, str):
            raise ValueError("Employee email is missing or invalid")

        if (
            returned_email.strip().casefold()
            != employee_email.strip().casefold()
        ):
            raise ValueError("Employee identity mismatch")

        # Only active employees may proceed.
        if employee.get("account_status") != "active":
            return RevalidationResult(
                allowed=False,
                reason="Employee account is not active.",
                policy_ref="Employee directory",
            )

        # Extract current incidents from the nested status object.
        incidents = status_data.get("incidents")

        if not isinstance(incidents, list):
            raise ValueError("Incident list is unavailable")

        # Do not silently ignore malformed incident records.
        if not all(isinstance(incident, dict) for incident in incidents):
            raise ValueError("Invalid incident data")

        active_incidents = [
            incident
            for incident in incidents
            if incident.get("status") == "active"
        ]

        # Recheck ticket eligibility against current employee
        # and incident information.
        decision = verify_and_guard_ticket(
            employee=employee,
            topic=topic,
            request_type=request_type,
            reported_service=reported_service,
            reported_error_code=reported_error_code,
            service_status_verified=True,
            active_incidents=active_incidents,
        )

        return RevalidationResult(
            allowed=decision.allowed,
            reason=decision.reason,
            policy_ref=decision.policy_ref,
            employee=employee if decision.allowed else None,
        )

    except Exception as exc:
        # Fail closed on MCP errors, malformed responses,
        # or unexpected verification failures.
        return RevalidationResult(
            allowed=False,
            reason=f"Live verification failed: {type(exc).__name__}",
            policy_ref="Fail-closed safety rule",
        )
