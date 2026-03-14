"""Módulo para manejo de historial de conversación en JSONL"""
import json
import uuid
from pathlib import Path
from typing import Literal, Optional

from .filters import FilterManager, estimate_prompt_size
from .feedback_filter import FeedbackFilter, FeedbackFilterConfig, format_filtered_feedback


class MessageHistory:
    """Gestiona el historial de mensajes en formato JSONL"""

    def __init__(self, filename: str = "messages.jsonl", max_messages: int = 100,
                 session_id: str = None, cwd: str = None,
                 # Configuración de filtros (directa, sin FilterConfig)
                 filter_by_useful: Literal[None, False, True] = True,
                 max_tool_result_length: int | None = 500,
                 max_assistant_length: int | None = None,
                 truncate_strategy: Literal["cut", "ellipsis", "summary"] = "ellipsis",
                 # Configuración de feedback
                 feedback_filter_config: FeedbackFilterConfig = None):
        self.max_messages = max_messages
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.base_dir = self._get_history_dir()
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.filename = filename.replace(".jsonl", f"_{self.session_id}.jsonl")
        self._history_file = self.base_dir / self.filename

        # Configuración de filtros para preprocesamiento
        self.filter_by_useful = filter_by_useful
        self.max_tool_result_length = max_tool_result_length
        self.max_assistant_length = max_assistant_length
        self.truncate_strategy = truncate_strategy

        # Filtro de feedback del agente
        self.feedback_filter = FeedbackFilter(feedback_filter_config or FeedbackFilterConfig())

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
            history = [json.loads(line) for line in f if line.strip()]

        # Migrar mensajes antiguos agregando is_useful
        migrated = False
        for msg in history:
            if "is_useful" not in msg:
                msg["is_useful"] = True
                migrated = True

        # Si hubo migración, guardar el archivo actualizado
        if migrated:
            self.save(history)

        return history

    def save(self, messages: list[dict]) -> None:
        """Guarda el historial en el archivo JSONL (limitado a max_messages)"""
        messages_to_save = messages[-self.max_messages:]
        with open(self._history_file, 'w', encoding='utf-8') as f:
            for msg in messages_to_save:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')

    def append_single(self, role: str, content: str | dict, is_useful: bool = True) -> None:
        """Guarda un solo mensaje al historial sin cargar todo el archivo.

        Args:
            role: Rol del mensaje ('user', 'assistant', 'tool_use', 'tool_result')
            content: Contenido del mensaje (string para user/assistant/result, dict para tool_use)
            is_useful: Si el mensaje es útil para incluir en el prompt (default True)
        """
        msg = {"role": role, "content": content, "is_useful": is_useful}

        # Agregar al archivo directamente
        with open(self._history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(msg, ensure_ascii=False) + '\n')

        # Aplicar rolling window si es necesario
        history = self.load()
        if len(history) > self.max_messages:
            self.save(history)

    def append(self, role: str, content: str, is_useful: bool = True) -> list[dict]:
        """Agrega un mensaje al historial y lo guarda.

        Args:
            role: Rol del mensaje
            content: Contenido del mensaje
            is_useful: Si el mensaje es útil para incluir en el prompt (default True)
        """
        history = self.load()
        history.append({"role": role, "content": content, "is_useful": is_useful})
        self.save(history)
        return history

    def append_batch(self, messages: list[dict], is_useful: bool = True) -> list[dict]:
        """Agrega múltiples mensajes al historial y lo guarda.

        Cada mensaje debe tener 'role' y 'content'.
        Roles soportados: 'user', 'assistant', 'tool_use', 'tool_result'.
        Para 'tool_use': content es dict con 'name' e 'input'.
        Para 'tool_result': content es string con el resultado.

        Args:
            messages: Lista de mensajes a agregar
            is_useful: Si los mensajes son útiles para incluir en el prompt (default True)
        """
        history = self.load()
        # Agregar is_useful a cada mensaje si no tiene el campo
        for msg in messages:
            if "is_useful" not in msg:
                msg["is_useful"] = is_useful
        history.extend(messages)
        self.save(history)
        return history

    def build_prompt(self, history: list[dict], new_message: str, apply_filters: bool = True) -> str:
        """Construye el prompt con el historial de conversación.

        Args:
            history: Historial de mensajes
            new_message: Nuevo mensaje del usuario
            apply_filters: Si True, aplica los filtros configurados antes de reconstruir
                (truncar tool_result, filtrar mensajes no útiles, etc.)

        Returns:
            Prompt reconstruido listo para enviar al LLM
        """
        # Aplicar filtros usando FilterManager
        if apply_filters:
            manager = FilterManager(
                filter_by_useful=self.filter_by_useful,
                max_tool_result_length=self.max_tool_result_length,
                max_assistant_length=self.max_assistant_length,
                truncate_strategy=self.truncate_strategy,
            )
            history = manager.apply(history)

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
        # Construir prompt base
        prompt = self.build_prompt(history, new_message, apply_filters=apply_filters)

        # Agregar feedback filtrado si existe
        if agent_feedback:
            # Aplicar filtros al feedback (últimas 3 reflexiones, 1 logro, etc.)
            filtered_feedback = self.feedback_filter.filter_feedback(
                raw_feedback=agent_feedback
            )

            # Formatear el feedback filtrado
            feedback_text = format_filtered_feedback(filtered_feedback)
            prompt += "\n" + feedback_text

        return prompt
