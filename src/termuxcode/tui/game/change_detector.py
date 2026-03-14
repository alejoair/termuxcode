"""Sistema genérico de detección de cambios para validación"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum
from datetime import datetime


class ChangeType(Enum):
    """Tipos de cambios detectados"""
    VALUE_CHANGED = "value_changed"  # Cambio en un valor simple
    FIELD_CHANGED = "field_changed"  # Cambio en un campo específico
    STRUCTURE_CHANGED = "structure_changed"  # Cambio en la estructura de datos
    FILE_CHANGED = "file_changed"  # Cambio en un archivo
    PHASE_CHANGED = "phase_changed"  # Cambio de fase (caso especial)
    CONFIDENCE_CHANGED = "confidence_changed"  # Cambio significativo en confianza
    GOAL_CHANGED = "goal_changed"  # Cambio en objetivo personal


class ValidationSeverity(Enum):
    """Severidad de validación requerida"""
    NONE = "none"  # Sin validación
    LOW = "low"  # Validación simple
    MEDIUM = "medium"  # Validación con LLM
    HIGH = "high"  # Validación completa con auditoría


@dataclass
class ChangeRule:
    """Regla para detectar cambios"""
    field_path: str  # Ruta del campo (ej: "current_phase", "personal_goal", "config.mode")
    change_type: ChangeType
    severity: ValidationSeverity = ValidationSeverity.MEDIUM
    validator_prompt_template: str | None = None
    validate_on_equal: bool = False  # Si True, valida también cuando el valor es igual
    threshold: float | None = None  # Umbral para cambios numéricos


@dataclass
class DetectedChange:
    """Cambio detectado"""
    field_path: str
    old_value: Any
    new_value: Any
    change_type: ChangeType
    severity: ValidationSeverity
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Resultado de validación"""
    change: DetectedChange
    passed: bool
    message: str
    recommendations: list[str] = field(default_factory=list)
    validated_by: str | None = None  # Qué sistema validó (LLM, rule, etc.)
    validation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ChangeDetector:
    """Detector de cambios genérico con sistema de validación"""

    def __init__(self, config_file: str | None = None):
        """
        Inicializar detector de cambios

        Args:
            config_file: Ruta a archivo de configuración de reglas (opcional)
        """
        self.rules: dict[str, ChangeRule] = {}
        self.previous_values: dict[str, Any] = {}
        self.change_history: list[DetectedChange] = []
        self.max_history = 100

        if config_file:
            self.load_rules_from_file(config_file)
        else:
            self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Cargar reglas por defecto para ExtendedGameStats"""
        default_rules = [
            ChangeRule(
                field_path="current_phase",
                change_type=ChangeType.PHASE_CHANGED,
                severity=ValidationSeverity.MEDIUM,
                validator_prompt_template="""Valida el cambio de fase {old_value} → {new_value}.
Responde:
1. ¿Se completó correctamente la fase {old_value}?
2. ¿Es apropiado pasar a {new_value}?
3. ¿Qué se debe mejorar?"""
            ),
            ChangeRule(
                field_path="current_confidence",
                change_type=ChangeType.CONFIDENCE_CHANGED,
                severity=ValidationSeverity.LOW,
                threshold=0.15,  # Solo valida si el cambio es > 15%
                validator_prompt_template="""La confianza cambió de {old_value} a {new_value}.
¿Es este cambio esperado y razonable en el contexto actual?"""
            ),
            ChangeRule(
                field_path="personal_goal",
                change_type=ChangeType.GOAL_CHANGED,
                severity=ValidationSeverity.LOW,
                validator_prompt_template="""El objetivo personal cambió de "{old_value}" a "{new_value}".
¿El nuevo objetivo es más específico y accionable que el anterior?"""
            ),
            ChangeRule(
                field_path="long_term_goal",
                change_type=ChangeType.GOAL_CHANGED,
                severity=ValidationSeverity.LOW,
                validator_prompt_template="""El objetivo a largo plazo cambió de "{old_value}" a "{new_value}".
¿Es el nuevo objetivo ambicioso y medible?"""
            ),
        ]

        for rule in default_rules:
            self.rules[rule.field_path] = rule

    def add_rule(self, rule: ChangeRule) -> None:
        """Agregar una regla de detección"""
        self.rules[rule.field_path] = rule

    def load_rules_from_file(self, filepath: str) -> None:
        """Cargar reglas desde archivo JSON"""
        import json
        with open(filepath, "r") as f:
            data = json.load(f)

        for rule_data in data.get("rules", []):
            rule = ChangeRule(
                field_path=rule_data["field_path"],
                change_type=ChangeType(rule_data["change_type"]),
                severity=ValidationSeverity(rule_data.get("severity", "medium")),
                validator_prompt_template=rule_data.get("validator_prompt_template"),
                validate_on_equal=rule_data.get("validate_on_equal", False),
                threshold=rule_data.get("threshold")
            )
            self.rules[rule.field_path] = rule

    def save_rules_to_file(self, filepath: str) -> None:
        """Guardar reglas en archivo JSON"""
        import json
        data = {
            "rules": [
                {
                    "field_path": rule.field_path,
                    "change_type": rule.change_type.value,
                    "severity": rule.severity.value,
                    "validator_prompt_template": rule.validator_prompt_template,
                    "validate_on_equal": rule.validate_on_equal,
                    "threshold": rule.threshold
                }
                for rule in self.rules.values()
            ]
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def detect_changes(self, current_values: dict[str, Any]) -> list[DetectedChange]:
        """
        Detectar cambios en los valores

        Args:
            current_values: Valores actuales a comparar

        Returns:
            Lista de cambios detectados
        """
        changes = []

        for field_path, rule in self.rules.items():
            old_value = self.previous_values.get(field_path)
            new_value = current_values.get(field_path)

            if new_value is None:
                continue

            # Verificar si hay cambio
            changed = old_value != new_value

            # Verificar umbral para valores numéricos
            if changed and rule.threshold is not None:
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    percent_change = abs((new_value - old_value) / old_value) if old_value != 0 else 1.0
                    changed = percent_change >= rule.threshold

            # Validar también cuando no hay cambio (si se configura)
            if rule.validate_on_equal and not changed:
                pass  # Se procesa aunque no haya cambio

            # Crear detected change
            if changed or rule.validate_on_equal:
                change = DetectedChange(
                    field_path=field_path,
                    old_value=old_value,
                    new_value=new_value,
                    change_type=rule.change_type,
                    severity=rule.severity,
                    context={
                        "threshold_exceeded": rule.threshold is not None
                    }
                )
                changes.append(change)

        # Actualizar valores previos
        self.previous_values = current_values.copy()

        # Guardar en historial
        self.change_history.extend(changes)
        if len(self.change_history) > self.max_history:
            self.change_history = self.change_history[-self.max_history:]

        return changes

    def get_recent_changes(self, limit: int = 10) -> list[DetectedChange]:
        """Obtener cambios recientes"""
        return self.change_history[-limit:]

    def get_changes_by_field(self, field_path: str) -> list[DetectedChange]:
        """Obtener cambios de un campo específico"""
        return [c for c in self.change_history if c.field_path == field_path]

    def get_changes_by_type(self, change_type: ChangeType) -> list[DetectedChange]:
        """Obtener cambios por tipo"""
        return [c for c in self.change_history if c.change_type == change_type]


class ChangeValidator:
    """Validador de cambios usando reglas o LLM"""

    def __init__(self, llm_query_func: Callable | None = None):
        """
        Inicializar validador

        Args:
            llm_query_func: Función para consultar LLM (opcional)
        """
        self.llm_query_func = llm_query_func
        self.validation_history: list[ValidationResult] = []
        self.max_history = 50

    async def validate_change(
        self,
        change: DetectedChange,
        rule: ChangeRule,
        context: dict | None = None
    ) -> ValidationResult:
        """
        Validar un cambio detectado

        Args:
            change: Cambio detectado
            rule: Regla que disparó el cambio
            context: Contexto adicional para validación

        Returns:
            Resultado de validación
        """
        # Si no requiere validación, aprobar automáticamente
        if change.severity == ValidationSeverity.NONE:
            return ValidationResult(
                change=change,
                passed=True,
                message="Cambio no requiere validación",
                validated_by="auto"
            )

        # Validación LOW: reglas simples
        if change.severity == ValidationSeverity.LOW:
            return self._validate_with_rules(change, rule)

        # Validación MEDIUM/HIGH: LLM
        if change.severity in [ValidationSeverity.MEDIUM, ValidationSeverity.HIGH]:
            if self.llm_query_func:
                return await self._validate_with_llm(change, rule, context)
            else:
                # Fallback a reglas si no hay LLM
                return self._validate_with_rules(change, rule)

        # Default: aprobar
        return ValidationResult(
            change=change,
            passed=True,
            message="Validación no implementada para este tipo",
            validated_by="default"
        )

    def _validate_with_rules(self, change: DetectedChange, rule: ChangeRule) -> ValidationResult:
        """Validar usando reglas simples"""
        passed = True
        message = "Cambio validado con reglas"
        recommendations = []

        # Regla específica para confianza
        if change.change_type == ChangeType.CONFIDENCE_CHANGED:
            if isinstance(change.new_value, float) and change.new_value < 0.7:
                passed = False
                recommendations.append("La confianza está baja (< 0.7). Revisa la calidad de las respuestas.")
            elif isinstance(change.new_value, float) and change.new_value > 0.95:
                message = "Confianza alta - excelente trabajo"

        # Regla para objetivos
        if change.change_type == ChangeType.GOAL_CHANGED:
            if isinstance(change.new_value, str) and len(change.new_value) < 10:
                recommendations.append("El objetivo es muy corto. Sé más específico.")

        return ValidationResult(
            change=change,
            passed=passed,
            message=message,
            recommendations=recommendations,
            validated_by="rules"
        )

    async def _validate_with_llm(
        self,
        change: DetectedChange,
        rule: ChangeRule,
        context: dict | None = None
    ) -> ValidationResult:
        """Validar usando LLM"""
        if not rule.validator_prompt_template:
            return ValidationResult(
                change=change,
                passed=True,
                message="No hay template de validación",
                validated_by="fallback"
            )

        # Construir prompt
        prompt = rule.validator_prompt_template.format(
            old_value=change.old_value,
            new_value=change.new_value,
            field_path=change.field_path,
            **(context or {})
        )

        try:
            # Llamar al LLM
            response = await self.llm_query_func(prompt)

            # Analizar respuesta (simple parse)
            # En una implementación más robusta, podríamos usar structured output
            passed = "✓" in response.lower() or "✅" in response.lower() or "sí" in response.lower()

            return ValidationResult(
                change=change,
                passed=passed,
                message=response,
                validated_by="llm"
            )
        except Exception as e:
            return ValidationResult(
                change=change,
                passed=True,  # Fallback: aprobar si hay error
                message=f"Error en validación LLM: {e}",
                recommendations=["La validación falló, pero se permite el cambio"],
                validated_by="error_fallback"
            )

    def get_recent_validations(self, limit: int = 10) -> list[ValidationResult]:
        """Obtener validaciones recientes"""
        return self.validation_history[-limit:]


class ChangeManager:
    """Manager para orquestar detección y validación de cambios"""

    def __init__(self, config_file: str | None = None, llm_query_func: Callable | None = None):
        """
        Inicializar manager

        Args:
            config_file: Ruta a archivo de configuración de reglas
            llm_query_func: Función para consultar LLM
        """
        self.detector = ChangeDetector(config_file)
        self.validator = ChangeValidator(llm_query_func)
        self.on_change_callback: Callable | None = None

    async def process_changes(
        self,
        current_values: dict[str, Any],
        context: dict | None = None
    ) -> tuple[list[DetectedChange], list[ValidationResult]]:
        """
        Procesar cambios: detectar y validar

        Args:
            current_values: Valores actuales
            context: Contexto adicional para validación

        Returns:
            (cambios detectados, resultados de validación)
        """
        # Detectar cambios
        changes = self.detector.detect_changes(current_values)

        # Validar cada cambio
        validations = []
        for change in changes:
            rule = self.detector.rules.get(change.field_path)
            if rule:
                result = await self.validator.validate_change(change, rule, context)
                validations.append(result)
                self.validator.validation_history.append(result)

                # Callback si se configuró
                if self.on_change_callback:
                    self.on_change_callback(change, result)

        return changes, validations

    def set_change_callback(self, callback: Callable) -> None:
        """Establecer callback para cuando hay cambios"""
        self.on_change_callback = callback
