# Claude Agent SDK - Reference Guide

## Función Principal: `query()`

```python
async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None,
    transport: Transport | None = None
) -> AsyncIterator[UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent]
```

### Tipos de Mensajes Devueltos:

#### 1. **UserMessage**
```python
class UserMessage:
    content: str | list[TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock]
    uuid: str | None
    parent_tool_use_id: str | None
    tool_use_result: dict[str, Any] | None
```

#### 2. **AssistantMessage**
```python
class AssistantMessage:
    content: list[TextBlock | ThinkingBlock | ToolUseBlock | ToolResultBlock]
    model: str
    parent_tool_use_id: str | None
    error: Literal['authentication_failed', 'billing_error', 'rate_limit', 'invalid_request', 'server_error', 'unknown'] | None
```

#### 3. **SystemMessage**
```python
class SystemMessage:
    subtype: str
    data: dict[str, Any]
```

#### 4. **ResultMessage**
```python
class ResultMessage:
    subtype: str
    duration_ms: int
    duration_api_ms: int
    is_error: bool
    num_turns: int
    session_id: str
    stop_reason: str | None
    total_cost_usd: float | None
    usage: dict[str, Any] | None
    result: str | None
    structured_output: Any
```

#### 5. **StreamEvent**
```python
class StreamEvent:
    uuid: str
    session_id: str
    event: dict[str, Any]
    parent_tool_use_id: str | None
```

## Bloques de Contenido

### **TextBlock**
```python
class TextBlock:
    text: str
```

### **ToolUseBlock**
```python
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
```

### **ToolResultBlock**
```python
class ToolResultBlock:
    tool_use_id: str
    content: str | list[dict[str, Any]] | None
    is_error: bool | None
```

### **ThinkingBlock**
```python
class ThinkingBlock:
    thinking: str
    signature: str
```

## Funciones de Sesión

### **get_session_messages()**
```python
def get_session_messages(
    session_id: str,
    directory: str | None = None,
    limit: int | None = None,
    offset: int = 0
) -> list[SessionMessage]
```

**Devuelve:**
```python
class SessionMessage:
    type: Literal['user', 'assistant']
    uuid: str
    session_id: str
    message: Any
    parent_tool_use_id: None
```

### **list_sessions()**
```python
def list_sessions(
    directory: str | None = None,
    limit: int | None = None,
    include_worktrees: bool = True
) -> list[SDKSessionInfo]
```

## Eventos de Tarea

### **TaskStartedMessage**
```python
class TaskStartedMessage:
    task_id: str
    description: str
    uuid: str
    session_id: str
    tool_use_id: str | None
    task_type: str | None
```

### **TaskProgressMessage**
```python
class TaskProgressMessage:
    task_id: str
    description: str
    usage: TaskUsage
    uuid: str
    session_id: str
    tool_use_id: str | None
    last_tool_name: str | None
```

### **TaskNotificationMessage**
```python
class TaskNotificationMessage:
    task_id: str
    status: Literal['completed', 'failed', 'stopped']
    output_file: str
    summary: str
    uuid: str
    session_id: str
    tool_use_id: str | None
    usage: TaskUsage | None
```

### **TaskUsage**
```python
class TaskUsage:
    total_tokens: int
    tool_uses: int
    duration_ms: int
```

## Configuración: ClaudeAgentOptions

```python
class ClaudeAgentOptions:
    # Herramientas y modelo
    tools: list[str] | ToolsPreset | None
    allowed_tools: list[str]
    disallowed_tools: list[str]
    model: str | None
    fallback_model: str | None

    # Prompt y contexto
    system_prompt: str | SystemPromptPreset | None
    cwd: str | pathlib.Path | None
    env: dict[str, str]

    # MCP servidores
    mcp_servers: dict[str, McpServerConfig] | str | pathlib.Path

    # Permisos
    permission_mode: Literal['default', 'acceptEdits', 'plan', 'bypassPermissions'] | None
    permission_prompt_tool_name: str | None

    # Hooks
    hooks: dict[HookType, list[HookMatcher]] | None

    # Límites
    max_turns: int | None
    max_budget_usd: float | None
    max_thinking_tokens: int | None
    max_buffer_size: int | None

    # Thinking y effort
    thinking: ThinkingConfigAdaptive | ThinkingConfigEnabled | ThinkingConfigDisabled | None
    effort: Literal['low', 'medium', 'high', 'max'] | None

    # Agentes
    agents: dict[str, AgentDefinition] | None

    # Sandbox
    sandbox: SandboxSettings | None

    # Output
    output_format: dict[str, Any] | None
    enable_file_checkpointing: bool

    # Otros
    continue_conversation: bool
    resume: str | None
    betas: list[Literal['context-1m-2025-08-07']]
    debug_stderr: Any
    stderr: Callable[[str], None] | None
    can_use_tool: Callable | None
    user: str | None
    include_partial_messages: bool
    fork_session: bool
    add_dirs: list[str | pathlib.Path]
    extra_args: dict[str, str | None]
```

## Ejemplo de Uso

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-6",
        tools=["bash"],
        permission_mode="default",
        cwd="/path/to/project"
    )

    async for message in query(prompt="Hola, ¿cómo estás?", options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"Assistant: {block.text}")
        elif isinstance(message, ResultMessage):
            print(f"Task completed. Cost: ${message.total_cost_usd}")

asyncio.run(main())
```
