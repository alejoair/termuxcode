"""Módulo para comunicarse con el agente Claude con sistema de rolling window"""
import os
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from claude_agent_sdk import query, ClaudeAgentOptions

if TYPE_CHECKING:
    from .chat import ChatLog


@dataclass
class RollingWindowConfig:
    """Configuración para el rolling window de mensajes"""
    max_visible: int = 50    # Máximo de mensajes visibles en UI
    max_session: int = 200   # Máximo de mensajes guardados en archivo de sesión
    max_turns: int = 50      # Máximo de turnos a Claude (contexto)

    def __post_init__(self):
        if self.max_visible <= 0:
            raise ValueError("max_visible debe ser mayor a 0")
        if self.max_session < self.max_visible:
            raise ValueError("max_session debe ser >= max_visible")
        if self.max_turns <= 0:
            raise ValueError("max_turns debe ser mayor a 0")


class MessageType(str, Enum):
    """Tipo de mensaje"""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    RESULT = "result"
    ERROR = "error"


@dataclass
class StoredMessage:
    """Mensaje almacenado en archivo de sesión"""
    type: MessageType
    content: str
    tool_name: Optional[str] = None
    tool_input: Optional[str] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StoredMessage':
        return cls(
            type=MessageType(data["type"]),
            content=data["content"],
            tool_name=data.get("tool_name"),
            tool_input=data.get("tool_input"),
            timestamp=data.get("timestamp"),
        )


class SessionManager:
    """Gestiona persistencia local de sesiones"""

    def __init__(self, cwd: str, session_name: str = "termuxcode_tui"):
        self.cwd = Path(cwd)
        self.session_name = session_name
        self._session_file = self._get_session_dir() / f"{session_name}.json"

    def _get_session_dir(self) -> Path:
        claude_dir = Path.home() / ".claude" / "local_sessions"
        claude_dir.mkdir(parents=True, exist_ok=True)
        return claude_dir

    def save_messages(self, messages: list[StoredMessage]) -> None:
        data = {
            "cwd": str(self.cwd),
            "session_name": self.session_name,
            "messages": [msg.to_dict() for msg in messages],
        }
        with open(self._session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_messages(self) -> list[StoredMessage]:
        if not self._session_file.exists():
            return []
        with open(self._session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [StoredMessage.from_dict(msg) for msg in data.get("messages", [])]


class AgentClient:
    """Cliente para comunicarse con Claude Agent SDK con rolling window"""

    def __init__(
        self,
        chat_log: 'ChatLog',
        cwd: str = None,
        config: RollingWindowConfig = None
    ):
        self.chat_log = chat_log
        self.cwd = cwd or os.getcwd()
        self.config = config or RollingWindowConfig()
        self.session_id: Optional[str] = None
        self.is_connected = False
        self._session_manager = SessionManager(self.cwd, "termuxcode_tui")
        self._all_messages: list[StoredMessage] = []

    async def load_history_only(self) -> None:
        """Cargar mensajes del archivo de sesión sin mostrar en UI"""
        self._all_messages = self._session_manager.load_messages()

    async def rebuild_ui(self) -> None:
        """Reconstruir UI con los últimos max_visible mensajes"""
        visible_messages = self._get_visible_messages()
        for msg in visible_messages:
            self._write_message_to_chat(msg)

    async def connect(self, session_id: str = None) -> None:
        """Marcar el agente como conectado"""
        self.session_id = session_id
        self.is_connected = True

    async def disconnect(self) -> None:
        """Marcar el agente como desconectado"""
        self.is_connected = False
        self._save_history()

    def _get_visible_messages(self) -> list[StoredMessage]:
        """Retornar los últimos max_visible mensajes"""
        return self._all_messages[-self.config.max_visible:]

    def _get_session_messages(self) -> list[StoredMessage]:
        """Retornar los últimos max_session mensajes para guardar"""
        return self._all_messages[-self.config.max_session:]

    def _save_history(self) -> None:
        """Guardar mensajes limitando a max_session"""
        messages_to_save = self._get_session_messages()
        self._session_manager.save_messages(messages_to_save)

    def _add_message(self, msg: StoredMessage) -> None:
        """Agregar mensaje al historial y guardar"""
        if msg.timestamp is None:
            msg.timestamp = datetime.now().isoformat()
        self._all_messages.append(msg)
        # Guardar en cada mensaje para evitar pérdida de datos
        self._save_history()

    def _write_message_to_chat(self, msg: StoredMessage) -> None:
        """Escribe un mensaje almacenado al ChatLog"""
        if msg.type == MessageType.USER:
            self.chat_log.write_user(msg.content)
        elif msg.type == MessageType.ASSISTANT:
            self.chat_log.write_assistant(msg.content)
        elif msg.type == MessageType.TOOL:
            self.chat_log.write_tool(msg.tool_name or "unknown", msg.tool_input)
        elif msg.type == MessageType.RESULT:
            self.chat_log.write_result(msg.content)
        elif msg.type == MessageType.ERROR:
            self.chat_log.write_error(msg.content)

    async def query(self, prompt: str) -> None:
        """Ejecutar query del agente usando query() del SDK"""
        try:
            # Agregar mensaje del usuario al historial
            user_msg = StoredMessage(
                type=MessageType.USER,
                content=prompt,
                timestamp=datetime.now().isoformat(),
            )
            self._add_message(user_msg)

            # Mostrar mensaje del usuario
            self._write_message_to_chat(user_msg)

            # Usar query() del SDK con continue_conversation=True para mantener historial
            options = ClaudeAgentOptions(
                permission_mode="bypassPermissions",
                cwd=self.cwd,
                include_partial_messages=False,
                cli_path="/data/data/com.termux/files/home/.claude/local/claude",
                max_budget_usd=0.10,
                continue_conversation=True,
                max_turns=self.config.max_turns,
            )

            old_claudecode = os.environ.pop('CLAUDECODE', None)

            try:
                async for message in query(prompt=prompt, options=options):
                    await self._process_message(message)
            finally:
                if old_claudecode:
                    os.environ['CLAUDECODE'] = old_claudecode

        except Exception as e:
            error_msg = StoredMessage(
                type=MessageType.ERROR,
                content=f"{type(e).__name__}: {str(e)}",
                timestamp=datetime.now().isoformat(),
            )
            self._add_message(error_msg)
            self._write_message_to_chat(error_msg)

    async def _process_message(self, message) -> None:
        """Procesar mensaje del agente"""
        msg_type = message.__class__.__name__

        if msg_type == "ResultMessage":
            # ResultMessage indica fin de respuesta - no se guarda
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
                    # Guardar y mostrar texto del asistente
                    msg = StoredMessage(
                        type=MessageType.ASSISTANT,
                        content=block.text,
                        timestamp=datetime.now().isoformat(),
                    )
                    self._add_message(msg)
                    self._write_message_to_chat(msg)

                elif block_type == "ToolUseBlock":
                    tool_input = str(block.input) if hasattr(block, 'input') else None
                    msg = StoredMessage(
                        type=MessageType.TOOL,
                        content=block.name,
                        tool_name=block.name,
                        tool_input=tool_input,
                        timestamp=datetime.now().isoformat(),
                    )
                    self._add_message(msg)
                    self._write_message_to_chat(msg)

    async def _process_user(self, message) -> None:
        """Procesar UserMessage (tool results)"""
        if hasattr(message, 'content') and isinstance(message.content, list):
            for block in message.content:
                if block.__class__.__name__ == "ToolResultBlock":
                    content_str = str(block.content)
                    msg = StoredMessage(
                        type=MessageType.RESULT,
                        content=content_str,
                        timestamp=datetime.now().isoformat(),
                    )
                    self._add_message(msg)
                    self._write_message_to_chat(msg)

    async def get_session_list(self, limit: int = 10) -> list:
        """Obtener lista de sesiones disponibles"""
        from claude_agent_sdk._internal.sessions import list_sessions
        return list_sessions(directory=self.cwd, limit=limit)
