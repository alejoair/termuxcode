# Bug Report: claude-agent-sdk create_sdk_mcp_server validation error

## Issue Tracking
- **Repository**: https://github.com/anthropics/claude-agent-sdk-python/issues
- **Status**: 🔍 Not reported yet - needs verification if this is a regression or new bug
- **Related**: Pydantic fix in v0.1.13 (different issue)

## Summary

Custom tools created with `@tool` decorator and wrapped with `create_sdk_mcp_server` fail with Pydantic validation errors. The MCP server internally converts the tool's return value incorrectly using `list(dict.items())`, producing tuples instead of the expected content blocks.

## Environment

- **Python**: 3.12
- **OS**: Windows (MSYS_NT-10.0-26100)
- **claude-agent-sdk**: 0.1.58 (latest)
- **mcp**: (dependency of claude-agent-sdk)

## Steps to Reproduce

```python
import asyncio
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server, query, ClaudeAgentOptions

@tool(
    "test_tool",
    "A simple test tool that echoes back the input",
    {"message": str},
)
async def test_tool(args: dict[str, Any]) -> dict[str, Any]:
    msg = args.get("message", "")
    return {"content": [{"type": "text", "text": f"Echo: {msg}"}]}

async def main():
    server = create_sdk_mcp_server(name="test", version="1.0.0", tools=[test_tool])
    options = ClaudeAgentOptions(
        mcp_servers={"test": server},
        allowed_tools=["mcp__test__test_tool"],
    )

    async for message in query("Call test_tool with message 'hello'", options=options):
        if hasattr(message, 'result'):
            print(f"Result: {message.result}")

asyncio.run(main())
```

## Expected Behavior

Tool should execute successfully and return:
```
Result: Echo: hello
```

## Actual Behavior

Tool execution fails with Pydantic validation error:

```
20 validation errors for CallToolResult
content.0.TextContent
  Input should be a valid dictionary or instance of TextContent
  [type=model_type, input_value=('meta', None), input_type=tuple]
content.1.TextContent
  Input should be a valid dictionary or instance of TextContent
  [type=model_type, input_value=('content', [TextContent(...)]), input_type=tuple]
content.2.TextContent
  Input should be a valid dictionary or instance of TextContent
  [type=model_type, input_value=('structuredContent', None), input_type=tuple]
content.3.TextContent
  Input should be a valid dictionary or instance of TextContent
  [type=model_type, input_value=('isError', False), input_type=tuple]
```

## Root Cause

The MCP server internally calls `list(dict.items())` on the tool's return value:

```python
# Tool returns:
{"content": [{"type": "text", "text": "Echo: hello"}]}

# MCP server converts to:
[('meta', None), ('content', [...]), ('structuredContent', None), ('isError', False)]
```

This produces a list of tuples instead of the expected list of content blocks:
```python
[{"type": "text", "text": "..."}]
```

## Investigation Notes

1. **Tool handler is called correctly**: Logs show the handler executes with correct args
2. **Return value format matches documentation**: Using exact format from official docs
3. **Error occurs in MCP bridge**: Between tool handler return and Pydantic validation
4. **Workarounds tested**:
   - Returning `list[dict]` directly → Error: `'list' object has no attribute 'get'`
   - Returning `str` → Error: `'str' object has no attribute 'get'`
   - Adding `isError` field → Same validation error

## Minimal Test Script

See `test_tool.py`:
```bash
python test_tool.py
```

Output shows:
```
[TOOL] test_tool llamado con: hello world
[TOOL] Retornando: {'content': [{'type': 'text', 'text': 'Echo: hello world'}]}
# Then Pydantic validation error in UserMessage
```

## Workaround

Use external MCP server (stdio/process) instead of in-process `create_sdk_mcp_server`:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

app = Server("my-server")

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    return [TextContent(type="text", text="Result")]

# Run with stdio_server()
```

Configure in ClaudeAgentOptions:
```python
mcp_servers={
    "my-server": McpServerConfig(
        command="python",
        args=["server.py"],
    )
}
```

## Impact

- **Breaking**: All examples from official documentation fail
- **Severity**: High - Cannot use in-process MCP servers at all
- **Scope**: Affects all `@tool` decorators with `create_sdk_mcp_server`

## Related Documentation

Official docs show this pattern (which fails):
https://code.claude.com/docs/llms.txt
Search for: "Give Claude custom tools"

Example from docs:
```python
@tool("get_temperature", "Get temperature", {"lat": float, "lon": float})
async def get_temperature(args):
    return {"content": [{"type": "text", "text": f"Temp: {temp}"}]}

weather_server = create_sdk_mcp_server(name="weather", version="1.0.0", tools=[get_temperature])
```

This exact pattern fails with the validation error described above.

## Search Keywords for GitHub Issues

- `create_sdk_mcp_server validation error`
- `CallToolResult Pydantic validation`
- `in-process MCP server tuple`
- `content.0.TextContent input_value tuple`
- `mcp__ server tools isError`

## Files to Attach

- `test_tool.py` - Minimal reproduction script
- Full error traceback with Pydantic validation details
- Python version and pip package list
