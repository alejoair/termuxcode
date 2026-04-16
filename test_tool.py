#!/usr/bin/env python3
"""Test script minimal para custom tool MCP."""

import asyncio
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server, query, ClaudeAgentOptions, ResultMessage


@tool(
    "test_tool",
    "A simple test tool that echoes back the input",
    {"message": str},
)
async def test_tool(args: dict[str, Any]) -> str:
    """Tool de prueba que retorna el mensaje recibido."""
    msg = args.get("message", "")
    print(f"[TOOL] test_tool llamado con: {msg}")
    result = f"Echo: {msg}"
    print(f"[TOOL] Retornando string: {result}")
    return result


async def main():
    print("=== Creando MCP server ===")
    test_server = create_sdk_mcp_server(
        name="test",
        version="1.0.0",
        tools=[test_tool],
    )
    print(f"Server: {test_server}")
    print(f"Server type: {type(test_server)}")
    print(f"Server keys: {list(test_server.keys()) if isinstance(test_server, dict) else 'N/A'}")

    print("\n=== Creando ClaudeAgentOptions ===")
    options = ClaudeAgentOptions(
        mcp_servers={"test": test_server},
        allowed_tools=["mcp__test__test_tool"],
    )
    print(f"Options creado")

    print("\n=== Iniciando query ===")
    prompt = "Call the test_tool with message 'hello world'"
    print(f"Prompt: {prompt}")

    try:
        async for message in query(prompt=prompt, options=options):
            print(f"\n[Mensaje] Tipo: {type(message).__name__}")
            print(f"[Mensaje] Atributos: {dir(message)}")

            if hasattr(message, '__dict__'):
                print(f"[Mensaje] Dict: {message.__dict__}")

            if isinstance(message, ResultMessage):
                print(f"\n[RESULT] Subtype: {message.subtype}")
                print(f"[RESULT] Result: {message.result}")
                print(f"[RESULT] Is error: {message.is_error}")
                print(f"[RESULT] Num turns: {message.num_turns}")

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
