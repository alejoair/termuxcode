#!/usr/bin/env python3
"""MCP server externo para type_check — workaround al bug del SDK in-process."""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio
import os
import shutil
from typing import Any

app = Server("termuxcode-external")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Lista las tools disponibles."""
    return [
        Tool(
            name="type_check",
            description="Check a Python file for type errors using ty.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Python file to check"
                    }
                },
                "required": ["file_path"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Ejecuta la tool."""
    if name != "type_check":
        raise ValueError(f"Unknown tool: {name}")

    file_path = arguments.get("file_path", "").strip()

    if not file_path:
        return [TextContent(type="text", text="Error: file_path is required")]

    if not os.path.isfile(file_path):
        return [TextContent(type="text", text=f"Error: file not found: {file_path}")]

    if not file_path.endswith(".py"):
        return [TextContent(type="text", text=f"Error: ty only supports .py files")]

    if not shutil.which("ty"):
        return [TextContent(type="text", text="Error: ty is not installed")]

    try:
        proc = await asyncio.create_subprocess_exec(
            "ty", "check", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
    except asyncio.TimeoutError:
        return [TextContent(type="text", text="Error: ty check timed out")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error running ty: {e}")]

    output = (stdout.decode(errors="replace").strip() or
              stderr.decode(errors="replace").strip())

    if not output:
        return [TextContent(type="text", text=f"No type errors found in {file_path}")]

    return [TextContent(type="text", text=output)]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
