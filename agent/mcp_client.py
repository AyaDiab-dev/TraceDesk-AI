
"""Read-only MCP client for ResolveAI."""

import asyncio
import json
import sys
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


READ_ONLY_TOOLS = {
    "get_service_status",
    "lookup_employee",
    "search_tickets",
    "get_ticket",
}


async def call_read_tool(
    tool_name: str,
    arguments: dict | None = None,
) -> dict:
    """Call an explicitly allowed read-only MCP tool."""

    if tool_name not in READ_ONLY_TOOLS:
        raise ValueError(
            f"Tool '{tool_name}' is not allowed "
            "through the read-only MCP client."
        )

    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "services.helpdesk_mcp"],
        env=os.environ.copy(),
)

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments=arguments or {},
            )

            if result.isError:
                raise RuntimeError(
                    f"MCP tool '{tool_name}' failed."
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
                    raise RuntimeError(
                        "MCP returned no usable response."
                    )

                data = json.loads(text_blocks[0])

            if not isinstance(data, dict):
                raise RuntimeError(
                    "Unexpected MCP response format."
                )

            return data


async def get_service_status() -> dict:
    """Read the current IT service status."""
    return await call_read_tool("get_service_status")


async def lookup_employee(email: str) -> dict:
    """Look up an employee by work email."""
    return await call_read_tool(
        "lookup_employee",
        {"email": email},
    )


async def search_tickets(
    query: str | None = None,
    requester_email: str | None = None,
    status: str | None = None,
    limit: int = 5,
) -> dict:
    """Search existing Helpdesk tickets."""
    return await call_read_tool(
        "search_tickets",
        {
            "query": query,
            "requester_email": requester_email,
            "status": status,
            "limit": limit,
        },
    )


async def get_ticket(ticket_id: str) -> dict:
    """Read an existing Helpdesk ticket."""
    return await call_read_tool(
        "get_ticket",
        {"ticket_id": ticket_id},
    )


if __name__ == "__main__":
    async def main():
        result = await get_service_status()

        print(
            "SERVICE STATUS OK:",
            result.get("ok"),
        )

        if result.get("ok"):
            print(
                "ACTIVE INCIDENTS:",
                result["status"].get(
                    "active_incidents", []
                ),
            )

    asyncio.run(main())
