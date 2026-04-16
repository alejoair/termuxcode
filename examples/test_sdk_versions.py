#!/usr/bin/env python3
"""
Test: reproducir bug de serialización CallToolResult con diferentes versiones del SDK.

BUG: Al usar ClaudeSDKClient con un MCP server in-process, la respuesta del tool
se corrompe al cruzar del SDK Python al CLI de Claude (subproceso Node.js).

El flujo es:
1. Python: tool handler retorna {"content": [{"type": "text", "text": "..."}]}
2. SDK Python: create_sdk_mcp_server convierte dicts a objetos Pydantic (TextContent, etc.)
3. SDK Python (query.py:_handle_sdk_mcp_request): lee result.root.content, convierte a dicts limpios
4. SDK Python: envía JSON por transporte al CLI: {"mcp_response": {"content": [{"type": "text", "text": "..."}]}}
5. CLI (Node.js): recibe el JSON, intenta construir CallToolResult con Pydantic
6. CLI (Node.js): PASA dict.items() (tuplas) en vez del dict → ("meta", None) → error de validación

El error exacto:
    20 validation errors for CallToolResult
    content.0.TextContent
      Input should be a valid dictionary or instance of TextContent
      [type=model_type, input_value=('meta', None), input_type=tuple]

El input_value=('meta', None) es una tupla resultante de dict.items().
Pydantic no puede validar una tupla como TextContent.

NOTA: query() funciona correctamente. Solo ClaudeSDKClient falla.
La diferencia es que query() maneja el transporte internamente de forma diferente
a ClaudeSDKClient (que mantiene una conexión bidireccional persistente).

USO:
    python examples/test_sdk_versions.py [version1] [version2] ...

    # Probar versión actual
    python examples/test_sdk_versions.py

    # Probar versiones específicas (instala cada una antes)
    pip install claude-agent-sdk==0.1.50
    python examples/test_sdk_versions.py 0.1.50
    pip install claude-agent-sdk==0.1.55
    python examples/test_sdk_versions.py 0.1.55
"""

import asyncio
import sys
from typing import Any

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    ResultMessage,
    UserMessage,
    tool,
    create_sdk_mcp_server,
    __version__,
)


@tool(
    "echo",
    "Returns the input message as-is",
    {"message": str},
)
async def echo(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [
            {"type": "text", "text": f"Echo: {args.get('message', '')}"}
        ]
    }


server = create_sdk_mcp_server(name="test", version="1.0.0", tools=[echo])


async def run_test() -> bool:
    """Retorna True si el tool funciona sin errores de validación."""
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        mcp_servers={"test": server},
        allowed_tools=["mcp__test__echo"],
    )

    client = ClaudeSDKClient(options)
    await client.connect()

    try:
        await client.query("Call the echo tool with message 'hello'")

        async for msg in client.receive_response():
            if isinstance(msg, UserMessage):
                for block in msg.content:
                    text = str(block)
                    if "validation error" in text.lower() or "CallToolResult" in text:
                        print(f"  FAIL: {text[:200]}")
                        return False
                    if "Echo: hello" in text:
                        print(f"  OK: tool result received correctly")
                        return True
            elif isinstance(msg, ResultMessage):
                result = msg.result or ""
                if "Echo: hello" in result:
                    print(f"  OK: {result[:200]}")
                    return True
                if "validation error" in result.lower() or "internal error" in result.lower():
                    print(f"  FAIL: {result[:200]}")
                    return False

        print("  UNKNOWN: no result received")
        return False
    finally:
        await client.disconnect()


async def main():
    print(f"SDK version: {__version__}")
    print(f"Testing in-process MCP tool with ClaudeSDKClient...\n")

    success = await run_test()
    print(f"\nResult: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
