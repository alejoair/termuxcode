"""Trigger para validación de fases"""
from __future__ import annotations

from ..structured_response import PHASE_VALIDATION_SCHEMA
from .base import SimpleAgentTrigger

PHASE_VALIDATION_TRIGGER = SimpleAgentTrigger(
    name="phase_validation",
    system_prompt="""Eres un auditor de calidad de código y procesos de desarrollo de software.
Tu tarea es validar cambios de fase y proporcionar feedback constructivo.

Analiza cuidadosamente el contexto y proporciona:
1. Evaluación de si la fase anterior se completó correctamente
2. Justificación sobre si es apropiado el cambio de fase
3. Sugerencias para mejorar el proceso
4. Riesgos identificados
5. Una recomendación clara sobre cómo proceder""",
    prompt_template="{validation_prompt}",
    output_schema=PHASE_VALIDATION_SCHEMA,
)
