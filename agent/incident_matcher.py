
"""Match employee error codes to active Helpdesk incidents."""

import re


def extract_error_codes(text: str) -> set[str]:
    """Extract supported Nakhla error codes from text."""
    return set(
        re.findall(r"\bNX-\d{3}\b", text.upper())
    )


def match_active_incidents(
    question: str,
    service_status: dict,
) -> list[dict]:
    """Return active incidents with matching error codes."""
    question_codes = extract_error_codes(question)

    if not question_codes:
        return []

    matches = []

    for incident in service_status.get("incidents", []):
        if incident.get("status") != "active":
            continue

        incident_codes = {
            code.upper()
            for code in incident.get("error_codes", [])
        }

        matched_codes = question_codes & incident_codes

        if matched_codes:
            matches.append({
                "incident_id": incident["id"],
                "service": incident.get("service"),
                "title": incident.get("title"),
                "matched_error_codes": sorted(matched_codes),
                "affected": incident.get("affected"),
                "workaround": incident.get("workaround"),
                "instructions": incident.get("instructions"),
            })

    return matches
