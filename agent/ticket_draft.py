
"""Validated ticket drafts for TraceDesk AI."""

from dataclasses import dataclass, field


ALLOWED_CATEGORIES = {
    "network_access",
    "identity_access",
    "hardware",
    "software",
    "email_collab",
    "security",
    "onboarding",
    "other",
}

ALLOWED_PRIORITIES = {"P1", "P2", "P3", "P4"}


@dataclass
class TicketDraft:
    subject: str
    description: str
    employee_email: str
    department: str
    category: str
    priority: str
    attempted_steps: list[str]

    kb_references: list[str] = field(default_factory=list)
    policy_reasons: list[str] = field(default_factory=list)

    # Context used for eligibility and incident verification.
    topic: str = ""
    request_type: str = ""
    reported_service: str = ""
    reported_error_code: str = ""

    # Inputs used to calculate policy-controlled priority.
    affected_users: int = 1
    completely_blocked: bool = False
    workaround_available: bool = False
    security_incident: bool = False

    # True only when the employee explicitly confirms
    # that no troubleshooting steps were attempted.
    troubleshooting_confirmed_none: bool = False

    def validate(self) -> None:
        """Reject incomplete, unsupported, or invalid drafts."""

        # 1. Validate required text fields.
        required_text = {
            "subject": self.subject,
            "description": self.description,
            "employee_email": self.employee_email,
            "department": self.department,
            "topic": self.topic,
            "request_type": self.request_type,
            "reported_service": self.reported_service,
        }

        for name, value in required_text.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")

        # 2. Validate category and priority.
        if self.category not in ALLOWED_CATEGORIES:
            raise ValueError("Invalid ticket category")

        if self.priority not in ALLOWED_PRIORITIES:
            raise ValueError("Invalid ticket priority")

        # 3. Validate troubleshooting steps.
        if (
            not isinstance(self.attempted_steps, list)
            or any(
                not isinstance(step, str) or not step.strip()
                for step in self.attempted_steps
            )
        ):
            raise ValueError("Invalid attempted_steps")

        # 4. Validate explicit no-troubleshooting confirmation.
        if type(self.troubleshooting_confirmed_none) is not bool:
            raise ValueError(
                "Invalid troubleshooting confirmation"
            )

        # Missing information is different from explicitly
        # confirming that no steps were attempted.
        if (
            not self.attempted_steps
            and not self.troubleshooting_confirmed_none
        ):
            raise ValueError(
                "Troubleshooting information has not been confirmed"
            )

        # Prevent contradictory troubleshooting information.
        if (
            self.attempted_steps
            and self.troubleshooting_confirmed_none
        ):
            raise ValueError(
                "Conflicting troubleshooting information"
            )

        # 5. Validate knowledge and policy references.
        for name, values in {
            "kb_references": self.kb_references,
            "policy_reasons": self.policy_reasons,
        }.items():
            if (
                not isinstance(values, list)
                or any(
                    not isinstance(value, str) or not value.strip()
                    for value in values
                )
            ):
                raise ValueError(f"Invalid {name}")

        # 6. Validate affected users.
        if (
            type(self.affected_users) is not int
            or self.affected_users < 1
        ):
            raise ValueError("Invalid affected_users")

        # 7. Validate incident and priority inputs.
        for name in (
            "completely_blocked",
            "workaround_available",
            "security_incident",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"Invalid {name}")
