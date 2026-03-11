"""Módulo para comunicarse con el agente Claude con historial en JSONL"""
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from claude_agent_sdk import query, ClaudeAgentOptions

if TYPE_CHECKING:
    from .chat import ChatLog


class AgentClient:
    """Cliente para comunicarse con Claude Agent SDK con historial en JSONL"""

    def __init__(
        self,
        chat_log: 'ChatLog',
        cwd: str = None,
        max_history: int = 100,
    ):
        self.chat_log = chat_log
        self.cwd = cwd or os.getcwd()
        self.max_history = max_history
        self._history_file = Path.home() / ".claude" / "local_sessions" / "messages.jsonl"
        self._history_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_history(self) -> list[dict]:
        """Cargar historial desde JSONL"""
        if not self._history_file.exists():
            return []
        with open(self._history_file, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]

    def _save_history(self, messages: list[dict]) -> None:
        """Guardar historial en JSONL (limitado a max_history)"""
        # Mantener solo los últimos max_history mensajes
        messages_to_save = messages[-self.max_history:]
        with open(self._history_file, 'w', encoding='utf-8') as f:
            for msg in messages_to_save:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')

    def _build_prompt(self, history: list[dict], new_message: str) -> str:
        """Construir el prompt con el historial de conversación"""
        prompt = ""
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        prompt += f"User: {new_message}\n\nAssistant:"
        return prompt

    async def query(self, prompt: str) -> None:
        """Ejecutar query del agente con historial en JSONL"""
        # Cargar historial existente
        history = self._load_history()

        # Mostrar mensaje del usuario en la UI
        self.chat_log.write_user(prompt)

        # Guardar mensaje del usuario en historial
        history.append({"role": "user", "content": prompt})

        # Construir prompt con historial
        full_prompt = self._build_prompt(history[:-1], prompt)

        # Usar query() del SDK
        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            include_partial_messages=False,
            cli_path="/data/data/com.termux/files/home/.claude/local/claude",
            max_budget_usd=0.10,
        )

        old_claudecode = os.environ.pop('CLAUDECODE', None)
        assistant_response = ""

        try:
            async for message in query(prompt=full_prompt, options=options):
                await self._process_message(message)
                # Acumular la respuesta del asistente
                if hasattr(message, 'content') and isinstance(message.content, list):
                    for block in message.content:
                        if block.__class__.__name__ == "TextBlock":
                            assistant_response += block.text
        finally:
            if old_claudecode:
                os.environ['CLAUDECODE'] = old_claudecode

        # Guardar respuesta del asistente en historial
        if assistant_response:
            history.append({"role": "assistant", "content": assistant_response})
            self._save_history(history)

    async def _process_message(self, message) -> None:
        """Procesar mensaje del agente"""
        msg_type = message.__class__.__name__

        if msg_type == "ResultMessage":
            return
        elif msg_type == "AssistantMessage":
            await self._process_assistant(message)
        elif msg_type == "UserMessage":
            await self._process_user(message)

    async def _process_assistant(self, message) -> None:
        """Procesar AssistantMessage"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                block_type = block.__class__.__name__

                if block_type == "TextBlock":
                    self.chat_log.write_assistant(block.text)

                elif block_type == "ToolUseBlock":
                    tool_input = str(block.input) if hasattr(block, 'input') else None
                    self.chat_log.write_tool(block.name, tool_input)

    async def _process_user(self, message) -> None:
        """Procesar UserMessage (tool results)"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                if block.__class__.__name__ == "ToolResultBlock":
                    self.chat_log.write_result(str(block.content))
