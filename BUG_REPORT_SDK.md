# Bug: CallToolResult serialization error with in-process MCP tools (SDK 0.1.51+)

## Summary

When using `ClaudeSDKClient` with an in-process MCP server (via `create_sdk_mcp_server`), tool results fail with Pydantic validation errors starting from SDK version **0.1.51**. The last working version is **0.1.50**.

## Error

```
20 validation errors for CallToolResult
content.0.TextContent
  Input should be a valid dictionary or instance of TextContent
  [type=model_type, input_value=('meta', None), input_type=tuple]
```

The `input_value=('meta', None)` is a tuple from `dict.items()` — Pydantic cannot validate a tuple as TextContent.

## Root Cause (suspected)

The bug was introduced in the transition from **CLI 2.1.81 → 2.1.85** (bundled with SDK 0.1.50 → 0.1.51). Relevant changes in SDK 0.1.51:

- **#718**: Preserve dropped fields on AssistantMessage and ResultMessage for forward compatibility
- **#725**: Handle resource_link and embedded resource content types in SDK MCP tools
- **#717**: Propagate is_error flag from SDK MCP tool results
- **#736**: Convert TypedDict input_schema to proper JSON Schema in SDK MCP tools

The serialization path converts MCP tool result dicts to Pydantic objects, but somewhere in the pipeline `dict.items()` (tuples) is passed instead of the dict itself.

## Reproduction

```python
import asyncio
from typing import Any
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions, ResultMessage,
    UserMessage, tool, create_sdk_mcp_server,
)

@tool("echo", "Returns the input message as-is", {"message": str})
async def echo(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Echo: {args.get('message', '')}"}]}

server = create_sdk_mcp_server(name="test", version="1.0.0", tools=[echo])

async def test():
    options = ClaudeAgentOptions(
        permission_mode="bypassPermissions",
        mcp_servers={"test": server},
        allowed_tools=["mcp__test__echo"],
    )
    client = ClaudeSDKClient(options)
    await client.connect()
    await client.query("Call the echo tool with message 'hello'")
    async for msg in client.receive_response():
        print(msg)
    await client.disconnect()

asyncio.run(test())
```

## Bisection Results

| SDK Version | CLI Bundled | Result |
|-------------|-------------|--------|
| 0.1.50 | 2.1.81 | **PASS** |
| 0.1.51 | 2.1.85 | **FAIL** |
| 0.1.52 | 2.1.87 | FAIL |
| 0.1.53 | 2.1.88 | FAIL |
| 0.1.54 | — | FAIL |
| 0.1.55 | 2.1.91 | FAIL |
| 0.1.56 | 2.1.92 | FAIL |
| 0.1.57 | 2.1.96 | FAIL |
| 0.1.58 | 2.1.97 | FAIL |

## Environment

- Python 3.12
- Windows (MSYS_NT-10.0-26100)
- Reproduced on 2026-04-13

## Note

`query()` (the one-shot function) works correctly. Only `ClaudeSDKClient` (persistent bidirectional connection) fails. The difference is in how the transport layer handles MCP tool result serialization.
