# Title: `create_sdk_mcp_server` tools fail with Pydantic validation error - content converted to tuples

## Issue Description

Custom tools created with `@tool` decorator and wrapped with `create_sdk_mcp_server` fail with Pydantic validation errors. The tool handler executes correctly and returns the expected format, but the MCP server internally converts the return value using `list(dict.items())`, producing tuples instead of content blocks.

## Environment

- **claude-agent-sdk version**: 0.1.58
- **Python version**: 3.12
- **OS**: Windows 10 (MSYS_NT-10.0-26100)
- **Installation**: pip install claude-agent-sdk

## Minimal Reproduction

```python
import asyncio
from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server, query, ClaudeAgentOptions

@tool(
    "test_tool",
    "A simple test tool",
    {"message": str},
)
async def test_tool(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"Echo: {args['message']}"}]}

async def main():
    server = create_sdk_mcp_server(name="test", version="1.0.0", tools=[test_tool])
    options = ClaudeAgentOptions(
        mcp_servers={"test": server},
        allowed_tools=["mcp__test__test_tool"],
    )

    async for msg in query("Call test_tool with 'hello'", options=options):
        print(f"Msg: {type(msg).__name__}")

asyncio.run(main())
```

**Expected**: Tool returns "Echo: hello"
**Actual**: Pydantic validation error

## Error Details

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

## Root Cause Analysis

**Tool handler returns**:
```python
{"content": [{"type": "text", "text": "..."}]}
```

**MCP server converts to**:
```python
[('meta', None), ('content', [...]), ('structuredContent', None), ('isError', False)]
```

This is `list(dict.items())` with extra fields (`meta`, `structuredContent`) added internally.

**Evidence**:
- Tool handler logs show correct return value
- Error occurs in UserMessage (after MCP processing)
- Pydantic receives tuples instead of dicts

## Additional Context

1. **Documentation example fails**: The pattern from official docs produces this error
2. **Not a v0.1.13 regression**: Different issue than the Pydantic fix in v0.1.13
3. **Version**: Current v0.1.58 (latest as of 2026-04-14)
4. **Impact**: All in-process MCP servers are broken

## Workaround

Use external MCP server (stdio/process) instead of in-process:

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent

app = Server("my-server")

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    return [TextContent(type="text", text="Result")]

# ClaudeAgentOptions:
mcp_servers={"my-server": McpServerConfig(command="python", args=["server.py"])}
```

## Attachments

- `test_tool.py` - Complete minimal reproduction script
- Full error logs with stack traces
- Tested on claude-agent-sdk v0.1.58

## Keywords for Search

create_sdk_mcp_server, CallToolResult, Pydantic, validation error, MCP, in-process server, tuple, content

---

**To report**: Visit https://github.com/anthropics/claude-agent-sdk-python/issues/new
