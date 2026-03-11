"""Módulo para manejo de historial de conversación en JSONL"""
import json
from pathlib import Path
from typing import Optional


class MessageHistory:
    """Gestiona el historial de mensajes en formato JSONL"""

    def __init__(self, filename: str = "messages.jsonl", max_messages: int = 100):
        self.filename = filename
        self.max_messages = max_messages
        self._history_file = self._get_history_dir() / filename

    def _get_history_dir(self) -> Path:
        """Retorna el directorio donde se guarda el historial"""
        claude_dir = Path.home() / ".claude" / "local_sessions"
        claude_dir.mkdir(parents=True, exist_ok=True)
        return claude_dir

    def load(self) -> list[dict]:
        """Carga el historial desde el archivo JSONL"""
        if not self._history_file.exists():
            return []
        with open(self._history_file, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]

    def save(self, messages: list[dict]) -> None:
        """Guarda el historial en el archivo JSONL (limitado a max_messages)"""
        # Mantener solo los últimos max_messages mensajes
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

    def build_prompt(self, history: list[dict], new_message: str) -> str:
        """Construye el prompt con el historial de conversación"""
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
