
"""Restricted MCP write client for approved ticket submissions."""

import json
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class TicketWriteUncertainError(RuntimeError):
    """The write outcome could not be confirmed."""


async def create_approved_ticket(
    *,
    subject: str,
    description: str,
    category: str,
    priority: str,
    requester_email: str,
    department: str,
    attempted_steps: list[str],
    kb_refs: list[str],
    idempotency_key: str,
    affected_users: int = 1,
) -> dict:
    """Call the MCP create_ticket tool.

    IMPORTANT:
    This function does not verify user approval itself.
    Only the trusted submission coordinator may call it.
    """

    if not isinstance(idempotency_key, str) or not idempotency_key.strip():
        raise ValueError("Idempotency key is required")

    arguments = {
        "subject": subject,
        "description": description,
        "category": category,
        "priority": priority,
        "requester_email": requester_email,
        "department": department,
        "attempted_steps": attempted_steps,
        "kb_refs": kb_refs,
        "idempotency_key": idempotency_key,
        "affected_users": affected_users,
    }

    server = StdioServerParameters(
    command=sys.executable,
    args=["-m", "services.helpdesk_mcp"],
    env=os.environ.copy(),
)

    try:
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "create_ticket",
                    arguments=arguments,
                )

                if result.isError:
                    raise TicketWriteUncertainError(
                        "MCP create_ticket returned a protocol error."
                    )

                if result.structuredContent is not None:
                    data = result.structuredContent
                else:
                    text_blocks = [
                        item.text
                        for item in result.content
                        if hasattr(item, "text")
                    ]

                    if not text_blocks:
                        raise TicketWriteUncertainError(
                            "MCP returned no usable response."
                        )

                    data = json.loads(text_blocks[0])

                if not isinstance(data, dict):
                    raise TicketWriteUncertainError(
                        "Unexpected MCP response format."
                    )

                return data

    except TicketWriteUncertainError:
        raise
    except Exception as exc:
        raise TicketWriteUncertainError(
            "Ticket creation outcome could not be confirmed."
        ) from exc
