
"""Extract supported ticket facts from helpdesk conversations."""

import re


ERROR_PATTERN = re.compile(
    r"\b(?:NX|NID|SWC|CRM)-\d+\b",
    re.IGNORECASE,
)

STEP_PATTERNS = {
    "NakhlaManage Sync": (
        r"\b(?:nakhlamanage\s+(?:sync|says)|"
        r"(?:performed?|did)\s+(?:a\s+)?(?:nakhlamanage\s+)?sync)\b"
    ),
    "Restarted laptop": (
        r"\b(?:"
        r"(?:restart(?:ed)?|reboot(?:ed)?)\s+"
        r"(?:(?:my|the)\s+)?(?:laptop|computer|device|macbook)"
        r"|"
        r"(?:i\s+)?(?:restart(?:ed)?|reboot(?:ed)?)\s+"
        r"(?:it|my laptop|the laptop)"
        r")\b"
),
    "Checked device compliance": (
        r"\b(?:check(?:ed)?\s+(?:device\s+)?compliance|"
        r"(?:device|laptop)\s+(?:is\s+)?compliant|"
        r"nakhlamanage\s+says\s+the\s+laptop)\b"
    ),
    "Updated dock firmware": (
        r"\b(?:updated?|installed?)\s*"
        r"(?:the\s+|my\s+)?dock\s+firmware\b"
    ),
    "Checked dock cables": (
        r"\b(?:checked?|reconnected?|reseated?|tried)\s+"
        r"(?:the\s+|my\s+)?(?:dock\s+)?cables?\b"
    ),
    "Restarted dock": (
        r"\b(?:restart(?:ed)?|reboot(?:ed)?|power.cycled?)\s+"
        r"(?:the\s+|my\s+)?dock\b"
    ),
    "Tested alternative cable": (
        r"\b(?:tried|tested|used|swapped(?:\s+to)?)\s+"
        r"(?:another|a different|an alternative|a spare)\s+"
        r"(?:dock\s+)?cable\b"
    ),
    "Attempted software installation": (
        r"\b(?:install|installing|installed)\s+"
        r"(?:nakhlacode\s+studio|[\w-]+\s+studio)\b"
    ),
}

SECURITY_PATTERN = re.compile(
    r"\b(?:phishing|stolen device|lost device|"
    r"password entered into a suspicious link|"
    r"account compromised)\b",
    re.IGNORECASE,
)


def extract_ticket_context(messages: list[dict]) -> dict:
    """Extract reported facts without inventing troubleshooting actions."""

    user_messages = [
        item["content"]
        for item in messages
        if isinstance(item, dict)
        and item.get("role") == "user"
        and isinstance(item.get("content"), str)
    ]

    conversation = "\n".join(user_messages)
    lower = conversation.lower()

    errors = ERROR_PATTERN.findall(conversation)
    error_code = errors[-1].upper() if errors else ""

    is_vpn = (
        "vpn" in lower
        or "nakhlaconnect" in lower
        or error_code.startswith("NX-")
    )

    is_software = (
        "software center" in lower
        or "nakhlacode studio" in lower
        or error_code.startswith("SWC-")
    )

    is_dock = bool(
        re.search(
            r"\b(?:dock\s*d3|nakhla\s*dock|docking\s+station)\b",
            lower,
        )
    )

    is_laptop = bool(
    re.search(
        r"\b(?:laptop|notebook|computer|macbook)\b",
        lower,
    )
)

    if is_dock:
        topic, service = "hardware", "Nakhla Dock D3"
    elif is_vpn:
        topic, service = "vpn", "NakhlaConnect"
    elif is_software:
        topic, service = "software", "Software Center"
    elif is_laptop:
        topic, service = "hardware", "Laptop"
    else:
        topic, service = "", ""

    attempted_steps = [
        label
        for label, pattern in STEP_PATTERNS.items()
        if re.search(pattern, conversation, re.IGNORECASE)
    ]


    troubleshooting_confirmed_none = bool(
        re.search(
            r"\b(?:"
            r"i\s+haven't\s+tried\s+anything"
            r"|i\s+have\s+not\s+tried\s+anything"
            r"|i\s+didn't\s+try\s+anything"
            r"|i\s+did\s+not\s+try\s+anything"
            r"|no\s+troubleshooting\s+(?:steps\s+)?(?:tried|done|performed)"
            r")\b",
            conversation,
            re.IGNORECASE,
        )
    )


    blocked = bool(
        re.search(
            r"\b(?:cannot work|can't work|unable to work|"
            r"completely blocked|can't do my work|"
            r"cannot do my work|unable to access anything)\b",
            lower,
        )
    )

    no_workaround = bool(
        re.search(
            r"\b(?:no workaround|without a workaround|"
            r"don't have a workaround|do not have a workaround|"
            r"nothing else works)\b",
            lower,
        )
    )

    has_workaround = bool(
        re.search(
            r"\b(?:workaround works|have a workaround|"
            r"can use an alternative)\b",
            lower,
        )
    )

    malfunction = bool(
    error_code
    or re.search(
        r"\b(?:"
        r"broken|not working|fails?|failing|"
        r"does not detect|doesn't detect|error|"
        r"unable to connect|cannot connect|can't connect|"
        r"connection failed|connection issue|"
        r"not connecting|doesn't connect|"
        r"crash(?:es|ed|ing)?|"
        r"overheat(?:s|ed|ing)?|"
        r"freez(?:e|es|ing)|frozen|"
        r"won't turn on|will not turn on|"
        r"doesn't turn on|does not turn on|"
        r"battery\s+(?:drains?|draining)|"
        r"battery\s+(?:dies?|dying)|"
        r"screen\s+flicker(?:s|ing)?"
        r")\b",
        lower,
    )
)

    if no_workaround:
        workaround_available = False
    elif has_workaround:
        workaround_available = True
    elif blocked and malfunction and attempted_steps:
        # An inference, not an explicit employee confirmation.
        workaround_available = False
    else:
        workaround_available = None

    # True means a security incident was reported.
    # False means no security incident was reported,
    # not that a security investigation ruled one out.
    security_incident = bool(
        SECURITY_PATTERN.search(conversation)
    )

    return {
        "topic": topic,
        "request_type": "incident" if malfunction else "",
        "reported_service": service,
        "reported_error_code": error_code,
        "affected_users": (
            1 if re.search(r"\b(?:my|i|me)\b", lower) else None
        ),
        "completely_blocked": True if blocked else None,
        "workaround_available": workaround_available,
        "attempted_steps": attempted_steps,
        "security_incident": security_incident,
        "troubleshooting_confirmed_none": troubleshooting_confirmed_none,
    }
