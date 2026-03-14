"""Base para triggers de SimpleAgent"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class SimpleAgentTrigger:
    """Configuración para un caso de uso específico de SimpleAgent

    Cada trigger define:
    - name: Identificador del trigger
    - system_prompt: Instrucciones del sistema para el LLM
    - prompt_template: Template del prompt (usa str.format())
    - output_schema: JSON schema para structured output (opcional)
    """
    name: str
    system_prompt: str
    prompt_template: str
    output_schema: dict | None = None

    def build_prompt(self, **kwargs: Any) -> str:
        """Construir prompt con variables

        Args:
            **kwargs: Variables para el template

        Returns:
            Prompt con las variables interpoladas

        Raises:
            KeyError: Si falta una variable en el template
        """
        return self.prompt_template.format(**kwargs)
