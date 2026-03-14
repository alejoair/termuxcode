"""Widgets de UI para mostrar metadata de respuestas"""
from __future__ import annotations
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..structured_response import StructuredResponse
    from .extended_stats import ExtendedGameStats


class PhaseBadge(Static):
    """Badge de fase de tarea"""

    phase: reactive[str] = reactive("otro")

    DEFAULT_CSS = """
    PhaseBadge {
        height: auto;
        width: auto;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }
    """

    PHASE_COLORS = {
        "planificacion": "blue",
        "implementacion": "yellow",
        "testing": "green",
        "debugging": "red",
        "analisis": "purple",
        "otro": "gray"
    }

    PHASE_ICONS = {
        "planificacion": "🔵",
        "implementacion": "🟡",
        "testing": "🟢",
        "debugging": "🔴",
        "analisis": "🟣",
        "otro": "⚪"
    }

    def watch_phase(self, phase: str) -> None:
        icon = self.PHASE_ICONS.get(phase, "⚪")
        color = self.PHASE_COLORS.get(phase, "gray")
        self.update(f"[{color}]{icon} {phase.upper()}[/{color}]")

    def set_phase(self, phase: str) -> None:
        self.phase = phase


class AdvancesBadge(Static):
    """Badge de 'avanza tarea'"""

    advances: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    AdvancesBadge {
        height: auto;
        width: auto;
        padding: 0 1;
        text-align: center;
        text-style: bold;
    }
    """

    def watch_advances(self, advances: bool) -> None:
        if advances:
            self.update("[green]✓ AVANZA TAREA[/green]")
        else:
            self.update("")

    def set_advances(self, advances: bool) -> None:
        self.advances = advances


class SuggestionBox(Static):
    """Caja de sugerencia ejecutable"""

    DEFAULT_CSS = """
    SuggestionBox {
        height: auto;
        width: 100%;
        padding: 1;
        border: solid violet;
        border-substyle: none none dashed none;
        text-style: italic;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._suggestion = ""

    def set_suggestion(self, suggestion: str) -> None:
        self._suggestion = suggestion
        if suggestion:
            self.update(f"""
─── SUGERENCIA ──────────────────────────────────────────────
🎯 {suggestion}
────────────────────────────────────────────────────────────
[Press Tab to execute this suggestion]
            """)
        else:
            self.update("")


class ProductivityIndicator(Static):
    """Indicador de productividad"""

    advances_ratio: reactive[float] = reactive(0.0)
    current_streak: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    ProductivityIndicator {
        height: auto;
        width: auto;
        padding: 0 1;
    }
    """

    def watch_advances_ratio(self, ratio: float) -> None:
        self._update()

    def watch_current_streak(self, streak: int) -> None:
        self._update()

    def _update(self) -> None:
        ratio = self.advances_ratio
        streak = self.current_streak

        if ratio >= 0.8:
            emoji = "⚡"
        elif ratio >= 0.6:
            emoji = "👍"
        elif ratio >= 0.4:
            emoji = "👌"
        else:
            emoji = "📉"

        streak_emoji = "🔥" if streak >= 3 else ""

        self.update(f"[dim]{emoji} Productividad: {ratio*100:.0f}%{streak_emoji}[/dim]")

    def update_stats(self, advances_ratio: float, current_streak: int) -> None:
        self.advances_ratio = advances_ratio
        self.current_streak = current_streak


class PhaseDistribution(Static):
    """Distribución de mensajes por fase"""

    DEFAULT_CSS = """
    PhaseDistribution {
        height: auto;
        width: 100%;
        padding: 1;
        border: solid gray;
        border-substyle: none none dashed none;
    }
    """

    PHASE_COLORS = {
        "planificacion": "[blue]",
        "implementacion": "[yellow]",
        "testing": "[green]",
        "debugging": "[red]",
        "analisis": "[purple]",
        "otro": "[dim]"
    }

    PHASE_ICONS = {
        "planificacion": "🔵",
        "implementacion": "🟡",
        "testing": "🟢",
        "debugging": "🔴",
        "analisis": "🟣",
        "otro": "⚪"
    }

    def update_distribution(self, phases: dict[str, int]) -> None:
        if not phases:
            self.update("[dim]Sin datos de fases[/dim]")
            return

        total = sum(phases.values())
        if total == 0:
            self.update("[dim]Sin mensajes[/dim]")
            return

        lines = ["[bold]📊 Distribución por Fase[/bold]", ""]

        # Ordenar por cantidad descendente
        sorted_phases = sorted(phases.items(), key=lambda x: x[1], reverse=True)

        for phase, count in sorted_phases:
            if count == 0:
                continue
            percentage = (count / total) * 100
            color = self.PHASE_COLORS.get(phase, "[dim]")
            icon = self.PHASE_ICONS.get(phase, "⚪")

            # Barra de progreso
            bar_length = int(percentage / 10)
            bar = "█" * bar_length + "░" * (10 - bar_length)

            lines.append(f"{color}{icon} {phase.capitalize():<12} {bar}[/{color}] {percentage:.0f}%")

        self.update("\n".join(lines))


class SuggestionTracker(Static):
    """Rastreador de sugerencias"""

    suggestions_made: reactive[int] = reactive(0)
    suggestions_followed: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    SuggestionTracker {
        height: auto;
        width: auto;
        padding: 0 1;
    }
    """

    def watch_suggestions_made(self, made: int) -> None:
        self._update()

    def watch_suggestions_followed(self, followed: int) -> None:
        self._update()

    def _update(self) -> None:
        made = self.suggestions_made
        followed = self.suggestions_followed

        if made == 0:
            self.update("[dim]🎯 Sin sugerencias[/dim]")
            return

        ratio = followed / made
        self.update(f"[dim]🎯 {followed}/{made} sugerencias seguidas ({ratio*100:.0f}%)[/dim]")

    def update_stats(self, made: int, followed: int) -> None:
        self.suggestions_made = made
        self.suggestions_followed = followed


class MetadataPanel(Vertical):
    """Panel completo de metadata y estadísticas"""

    DEFAULT_CSS = """
    MetadataPanel {
        height: auto;
        width: 100%;
        padding: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._structured_response = None
        self._stats = None

    def compose(self):
        yield ProductivityIndicator(id="prod-indicator")
        yield SuggestionTracker(id="suggestion-tracker")

    def set_structured_response(self, response: StructuredResponse) -> None:
        self._structured_response = response
        # Actualizar badges
        # (Esto se haría desde fuera con query_one)

    def set_stats(self, stats: ExtendedGameStats) -> None:
        self._stats = stats

        try:
            prod_indicator = self.query_one("#prod-indicator", ProductivityIndicator)
            prod_indicator.update_stats(
                advances_ratio=stats.advances_task_ratio,
                current_streak=stats.current_streak
            )
        except Exception:
            pass

        try:
            suggestion_tracker = self.query_one("#suggestion-tracker", SuggestionTracker)
            suggestion_tracker.update_stats(
                made=stats.suggestions_made,
                followed=stats.suggestions_followed
            )
        except Exception:
            pass


class MessageMetadata(Static):
    """Widget de metadata para un mensaje individual"""

    DEFAULT_CSS = """
    MessageMetadata {
        height: auto;
        width: 100%;
        padding: 0 1;
        text-style: italic;
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._structured_response = None

    def set_structured_response(self, response: StructuredResponse) -> None:
        self._structured_response = response

        if not response or not response.metadata:
            self.update("")
            return

        metadata = response.metadata

        badges = []

        # Badge de fase
        from ..structured_response import format_phase_badge
        phase_badge = format_phase_badge(metadata.task_phase)
        if phase_badge:
            badges.append(phase_badge)

        # Badge de avanza tarea
        from ..structured_response import format_advances_badge
        adv_badge = format_advances_badge(metadata.advances_current_task)
        if adv_badge:
            badges.append(adv_badge)

        # Badge de no guardado
        if not metadata.is_useful_to_record_in_history:
            badges.append("[dim]ℹ️ NO GUARDADO[/dim]")

        if badges:
            self.update(" ".join(badges))
        else:
            self.update("")
