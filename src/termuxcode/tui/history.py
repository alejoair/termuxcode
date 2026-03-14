"""Módulo para manejo de historial de conversación en JSONL"""
import json
import uuid
from pathlib import Path
from typing import Optional

from .filters import FilterConfig, preprocess_history, estimate_prompt_size


class MessageHistory:
    """Gestiona el historial de mensajes en formato JSONL"""

    def __init__(self, filename: str = "messages.jsonl", max_messages: int = 100,
                 session_id: str = None, cwd: str = None,
                 filter_config: FilterConfig = None):
        self.max_messages = max_messages
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.base_dir = self._get_history_dir()
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.filename = filename.replace(".jsonl", f"_{self.session_id}.jsonl")
        self._history_file = self.base_dir / self.filename
        # Configuración de filtros para preprocesamiento
        self.filter_config = filter_config or FilterConfig()

    def _get_history_dir(self) -> Path:
        """Retorna el directorio donde se guarda el historial"""
        sessions_dir = self.cwd / ".sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir

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

    def append(self, role: str, content: str) -> list[dict]:
        """Agrega un mensaje al historial y lo guarda"""
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
                (truncar tool_result, etc.)

        Returns:
            Prompt reconstruido listo para enviar al LLM
        """
        # Aplicar filtros si están habilitados
        if apply_filters and self.filter_config:
            history = preprocess_history(history, self.filter_config)

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

    def estimate_size(self, history: list[dict] = None) -> dict:
        """Estima el tamaño del prompt reconstruido.

        Args:
            history: Historial a estimar. Si es None, carga desde archivo.

        Returns:
            Dict con estadísticas: character_count, line_count, message_breakdown,
            tool_result_total_size
        """
        if history is None:
            history = self.load()

        return estimate_prompt_size(history)

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

    def build_prompt_with_feedback(
        self,
        history: list[dict],
        new_message: str,
        apply_filters: bool = True,
        agent_feedback: dict = None
    ) -> str:
        """Construir prompt incluyendo feedback personalizado para el agente.

        Args:
            history: Historial de mensajes
            new_message: Nuevo mensaje del usuario
            apply_filters: Si True, aplica los filtros configurados
            agent_feedback: Dict con feedback para el agente (reflexiones, objetivos, etc.)

        Returns:
            Prompt completo con feedback incluido
        """
        from .structured_response import format_agent_feedback

        # Construir prompt base
        prompt = self.build_prompt(history, new_message, apply_filters=apply_filters)

        # Agregar feedback si existe
        if agent_feedback:
            feedback = format_agent_feedback(
                last_reflection=agent_feedback.get("last_reflection", ""),
                personal_goal=agent_feedback.get("personal_goal", ""),
                goal_achieved=agent_feedback.get("goal_achieved", False),
                goal_streak=agent_feedback.get("goal_streak", 0),
                long_term_goal=agent_feedback.get("long_term_goal", ""),
                long_term_progress=agent_feedback.get("long_term_progress", 0),
                recent_achievements=agent_feedback.get("recent_achievements", [])
            )
            prompt += "\n" + feedback

        return prompt
