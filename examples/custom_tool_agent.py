#!/usr/bin/env python3
"""Test: tool simple con ClaudeSDKClient para reproducir bug de serialización."""

import asyncio
from typing import Any

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    ToolUseBlock,
    tool,
    create_sdk_mcp_server,
)


@tool(
    "get_temperature",
    "Get the current temperature at a location",
    {"latitude": float, "longitude": float},
)
async def get_temperature(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": f"Temperature at ({args['latitude']}, {args['longitude']}): 72°F",
            }
        ]
    }


weather_server = create_sdk_mcp_server(
    name="weather",
    version="1.0.0",
    tools=[get_temperature],
)


async def main():
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        mcp_servers={"weather": weather_server},
        allowed_tools=["mcp__weather__get_temperature"],
    )

    client = ClaudeSDKClient(options)
    await client.connect()
    print("SDK conectado")

    try:
        await client.query("What is the temperature at latitude 40.7, longitude -74?")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        print(f"  [tool call] {block.name}({block.input})")
                    elif hasattr(block, "text"):
                        print(f"  [text] {block.text[:300]}")
            elif isinstance(msg, ResultMessage):
                print(f"\nRESULT: {msg.result[:300]}")
    finally:
        await client.disconnect()
        print("SDK desconectado")


if __name__ == "__main__":
    asyncio.run(main())
