
"""Deterministic ticket priority and category policy."""

PRIORITY_ORDER = {
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
}


def higher_priority(current: str, required: str) -> str:
    return min(
        (current, required),
        key=lambda p: PRIORITY_ORDER[p],
    )


def determine_priority(
    *,
    affected_users: int,
    completely_blocked: bool,
    workaround_available: bool,
    request_type: str,
    is_vip: bool,
    security_incident: bool,
    department: str,
    is_vpn_issue: bool,
) -> dict:
    """Apply KB-015 and KB-016 priority rules."""

    if type(affected_users) is not int or affected_users < 1:
        raise ValueError("affected_users must be a positive integer")

    if request_type not in {"incident", "request"}:
        raise ValueError("Invalid request_type")

    if type(completely_blocked) is not bool:
        raise ValueError("completely_blocked must be boolean")

    if type(workaround_available) is not bool:
        raise ValueError("workaround_available must be boolean")

    if type(security_incident) is not bool:
        raise ValueError("security_incident must be boolean")

    if type(is_vip) is not bool:
        raise ValueError("is_vip must be boolean")

    if not isinstance(department, str):
        raise ValueError("department must be a string")

    reasons = []

    if affected_users > 3:
        priority = "P1"
        reasons.append("More than three users affected (KB-015)")

    elif is_vip or department.casefold() == "executive office":
        priority = "P1"
        reasons.append("Executive/VIP escalation (KB-015, KB-016)")

    elif security_incident:
        priority = "P1"
        reasons.append("Reported security incident (KB-015)")

    elif request_type == "request":
        priority = "P4"
        reasons.append("Service request (KB-015)")

    elif completely_blocked and not workaround_available:
        priority = "P2"
        reasons.append("Work completely blocked (KB-015)")

    else:
        priority = "P3"
        reasons.append(
            "Incident without confirmed complete work blockage "
            "(provisional P3; review if impact changes)"
        )

    if department.casefold() == "finance" and is_vpn_issue:
        if priority != "P1":
            priority = "P2"

        reasons.append(
            "Finance VPN priority override (KB-016)"
        )

    return {
        "priority": priority,
        "reasons": reasons,
        "policy_refs": ["KB-015", "KB-016"],
    }


def determine_category(*, topic: str, department: str) -> dict:
    """Determine category and routing from KB-015 and KB-016."""

    categories = {
        "vpn": "network_access",
        "wifi": "network_access",
        "vdi": "network_access",
        "identity": "identity_access",
        "hardware": "hardware",
        "software": "software",
        "email": "email_collab",
        "security": "security",
        "onboarding": "onboarding",
        "other": "other",
    }

    if topic not in categories:
        raise ValueError(f"Unsupported ticket topic: {topic}")

    if department.casefold() == "finance" and topic == "vpn":
        return {
            "category": "security",
            "reason": "Finance VPN routed to Security Operations",
            "policy_ref": "KB-016",
        }

    return {
        "category": categories[topic],
        "reason": "General category mapping",
        "policy_ref": "KB-015",
    }
