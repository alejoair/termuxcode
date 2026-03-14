"""Triggers para SimpleAgent

Este módulo contiene configuraciones predefinidas para diferentes casos de uso
del SimpleAgent, permitiendo mantener SimpleAgent genérico y reutilizable.
"""
from .base import SimpleAgentTrigger
from .phase_validation import PHASE_VALIDATION_TRIGGER

__all__ = ["SimpleAgentTrigger", "PHASE_VALIDATION_TRIGGER"]
