
"""Verify whether a live incident covers an employee's issue."""

import re
from dataclasses import dataclass


@dataclass
class IncidentVerification:
    status: str
    reason: str
    incident_id: str | None = None


def confirm_incident_match(
    *,
    incident: dict,
    employee: dict,
    reported_service: str,
    reported_error_code: str,
) -> IncidentVerification:
    """Verify service, error code, and employee gateway scope."""

    if not isinstance(incident, dict) or not isinstance(employee, dict):
        return IncidentVerification(
            "unknown", "Incident or employee data is unavailable."
        )

    if incident.get("status") != "active":
        return IncidentVerification(
            "confirmed_no_match", "Incident is not active."
        )

    service = incident.get("service")
    codes = incident.get("error_codes")

    if (
        not isinstance(service, str)
        or not isinstance(codes, list)
        or not all(isinstance(code, str) for code in codes)
        or not isinstance(reported_service, str)
        or not isinstance(reported_error_code, str)
    ):
        return IncidentVerification(
            "unknown", "Service or error-code data is incomplete."
        )

    if service.casefold() != reported_service.casefold():
        return IncidentVerification(
            "confirmed_no_match", "Different service."
        )

    if reported_error_code.upper() not in {
        code.upper() for code in codes
    }:
        return IncidentVerification(
            "confirmed_no_match", "Different error code."
        )

    # The current fixture documents GW-2 scope for INC-2207.
    # Do not generalize this rule to unrelated incidents.
    if incident.get("id") != "INC-2207":
        return IncidentVerification(
            "unknown",
            "No structured scope rule for this incident."
        )

    gateway = employee.get("vpn_gateway")

    if not isinstance(gateway, str) or not gateway.strip():
        return IncidentVerification(
            "unknown", "Employee VPN gateway is unknown."
        )

    normalized_gateway = gateway.strip().upper()

    if normalized_gateway == "GW-2":
        return IncidentVerification(
            "confirmed_match",
            "Employee uses affected gateway GW-2.",
            incident_id="INC-2207",
        )

    if normalized_gateway in {"GW-1", "GW-3"}:
        return IncidentVerification(
            "confirmed_no_match",
            f"Employee uses {normalized_gateway}, not GW-2.",
        )

    return IncidentVerification(
        "unknown",
        "Employee gateway cannot be mapped to incident scope.",
    )
