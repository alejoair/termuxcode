"""Módulo para manejo de historial de conversación en JSONL"""
import json
from pathlib import Path
from typing import Literal

from termuxcode.core.history_manager.filters import ExponentialTruncateFilter


class MessageHistory:
    """Gestiona el historial de mensajes en formato JSONL"""

    def __init__(self, filepath: Path | str = None, max_messages: int = 100,
                 # Configuración de filtros
                 base_length: int = 2000,
                 decay: float = 0.08,
                 min_length: int = 200,
                 max_decay_distance: int = 10,
                 truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
                 # Deprecated: mantener por compatibilidad
                 filename: str = None, session_id: str = None, cwd: str = None):
        self.max_messages = max_messages

        # Determinar ruta del archivo
        if filepath is not None:
            self._history_file = Path(filepath)
        elif cwd is not None and session_id is not None:
            # Ruta legacy: cwd/.claude/sessions/messages_{session_id}.jsonl
            base_dir = Path(cwd) / ".claude" / "sessions"
            base_dir.mkdir(parents=True, exist_ok=True)
            name = filename or "messages.jsonl"
            name = name.replace(".jsonl", f"_{session_id}.jsonl")
            self._history_file = base_dir / name
        else:
            raise ValueError("Se requiere filepath o (cwd + session_id)")

        # Configuración de filtros para preprocesamiento
        self.base_length = base_length
        self.decay = decay
        self.min_length = min_length
        self.max_decay_distance = max_decay_distance
        self.truncate_strategy = truncate_strategy

    def load(self) -> list[dict]:
        """Carga el historial desde el archivo JSONL"""
        if not self._history_file.exists():
            return []
        with open(self._history_file, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]

    def save(self, messages: list[dict]) -> None:
        """Guarda el historial en el archivo JSONL (limitado a max_messages)"""
        messages_to_save = messages[-self.max_messages:]
        with open(self._history_file, 'w', encoding='utf-8') as f:
            for msg in messages_to_save:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')

    def append_single(self, role: str, content: str | dict) -> None:
        """Guarda un solo mensaje al historial sin cargar todo el archivo.

        Args:
            role: Rol del mensaje ('user', 'assistant', 'tool_use', 'tool_result')
            content: Contenido del mensaje (string para user/assistant/result, dict para tool_use)
        """
        msg = {"role": role, "content": content}

        # Agregar al archivo directamente
        with open(self._history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(msg, ensure_ascii=False) + '\n')

        # Aplicar rolling window si es necesario
        history = self.load()
        if len(history) > self.max_messages:
            self.save(history)

    def append(self, role: str, content: str) -> list[dict]:
        """Agrega un mensaje al historial y lo guarda.

        Args:
            role: Rol del mensaje
            content: Contenido del mensaje
        """
        history = self.load()
        history.append({"role": role, "content": content})
        self.save(history)
        return history

    def append_batch(self, messages: list[dict]) -> list[dict]:
        """Agrega múltiples mensajes al historial y lo guarda.

        Cada mensaje debe tener 'role' y 'content'.
        Roles soportados: 'user', 'assistant', 'tool_use', 'tool_result'.
        Para 'tool_use': content es dict con 'name' e 'input'.
        Para 'tool_result': content es string con el resultado.

        Args:
            messages: Lista de mensajes a agregar
        """
        history = self.load()
        history.extend(messages)
        self.save(history)
        return history

    def build_prompt(self, history: list[dict], new_message: str, apply_filters: bool = True) -> str:
        """Construye el prompt con el historial de conversación.

        Args:
            history: Historial de mensajes
            new_message: Nuevo mensaje del usuario
            apply_filters: Si True, aplica los filtros configurados antes de reconstruir

        Returns:
            Prompt reconstruido listo para enviar al LLM
        """
        # Aplicar truncado directamente
        if apply_filters:
            truncate_filter = ExponentialTruncateFilter(
                base_length=self.base_length,
                decay=self.decay,
                min_length=self.min_length,
                max_decay_distance=self.max_decay_distance,
                truncate_strategy=self.truncate_strategy,
            )
            history = truncate_filter.apply(history)

        prompt = ""
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
            elif role == "tool_use":
                tool_name = content.get("name", "unknown") if isinstance(content, dict) else "unknown"
                tool_input = content.get("input", "") if isinstance(content, dict) else str(content)
                prompt += f"Assistant: [Used tool: {tool_name}, input: {tool_input}]\n\n"
            elif role == "tool_result":
                prompt += f"[Tool result: {content}]\n\n"
        prompt += f"User: {new_message}\n\nAssistant:"
        return prompt

    def clear(self) -> None:
        """Limpia el historial"""
        if self._history_file.exists():
            self._history_file.unlink()

    def count(self) -> int:
        """Retorna la cantidad de mensajes en el historial"""
        return len(self.load())

    @property
    def filepath(self) -> Path:
        """Retorna la ruta del archivo de historial"""
        return self._history_file
