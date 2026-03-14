"""Mixin para sistema de gamificación"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import ClaudeChat
    from ..structured_response import StructuredResponse


class GamificationMixin:
    """Mixin que maneja la gamificación para ClaudeChat"""

    def _update_xp_bar(self: "ClaudeChat") -> None:
        """Actualizar barra de XP con estadísticas actuales"""
        stats = self.stats_manager.stats
        self.xp_bar.update_stats(
            level=stats.level,
            xp=stats.xp,
            progress=stats.xp_progress
        )

    def _show_achievement(self: "ClaudeChat", achievement) -> None:
        """Mostrar popup de logro desbloqueado"""
        try:
            from ..game import AchievementPopup
            popup = self.query_one(AchievementPopup)
            popup.show_achievement(achievement)
            # Añadir mensaje al chat
            self.chat_log.write(
                f"[bold yellow]![/bold yellow] [dim]{achievement.name} desbloqueado![/dim]"
            )
        except Exception:
            pass

    def _show_level_up(self: "ClaudeChat", level: int) -> None:
        """Mostrar banner de subida de nivel"""
        try:
            from ..game import LevelUpBanner
            banner = self.query_one(LevelUpBanner)
            banner.show_level_up(level)
            self.chat_log.write(
                f"[bold green]*[/bold green] [bold]LEVEL UP! Nivel {level}[/bold]"
            )
        except Exception:
            pass

    def _on_message_sent(self: "ClaudeChat") -> None:
        """Callback cuando usuario envía mensaje"""
        # Añadir XP y verificar logros
        unlocked = self.stats_manager.add_message()
        self._update_xp_bar()

        # Verificar subida de nivel
        old_level = self.stats_manager.stats.level
        self.stats_manager.stats.add_xp(5)  # XP por enviar mensaje
        if self.stats_manager.stats.level > old_level:
            self._show_level_up(self.stats_manager.stats.level)

        # Mostrar logros desbloqueados
        for ach in unlocked:
            self._show_achievement(ach)

        self._update_xp_bar()

    def _on_response_received(self: "ClaudeChat") -> None:
        """Callback cuando se recibe respuesta del agente"""
        self.stats_manager.add_response()
        self._update_xp_bar()

    def _on_tool_used(self: "ClaudeChat") -> None:
        """Callback cuando se usa una herramienta"""
        unlocked = self.stats_manager.add_tool_use()
        for ach in unlocked:
            self._show_achievement(ach)
        self._update_xp_bar()

    def _on_structured_response(self: "ClaudeChat", structured: StructuredResponse) -> None:
        """Callback cuando se recibe una respuesta estructurada"""
        from ..structured_response import format_phase_badge, format_advances_badge, format_suggestion_box, format_classification_badge
        from ..game import get_all_metadata_achievements

        # Obtener metadata
        metadata = structured.metadata

        # Guardar última sugerencia para ejecutar con Tab
        if metadata.next_suggested_immediate_action:
            self._last_suggestion = metadata.next_suggested_immediate_action

        # Mostrar badges en el chat
        badges = []

        # Badge de clasificación del prompt del usuario
        if metadata.user_prompt_classification:
            class_badge = format_classification_badge(metadata.user_prompt_classification)
            if class_badge:
                badges.append(class_badge)

        phase_badge = format_phase_badge(metadata.task_phase)
        if phase_badge:
            badges.append(phase_badge)
        adv_badge = format_advances_badge(metadata.advances_current_task)
        if adv_badge:
            badges.append(adv_badge)
        if not metadata.is_useful_to_record_in_history:
            badges.append("[dim]ℹ️ NO GUARDADO[/dim]")

        if badges:
            self.chat_log.write(" ".join(badges))

        # Mostrar el objetivo entendido del usuario si está disponible
        if metadata.user_prompt_objective:
            self.chat_log.write(f"[dim italic]Objetivo entendido: {metadata.user_prompt_objective}[/dim italic]")

        # Mostrar sugerencia si existe
        if metadata.next_suggested_immediate_action:
            self.chat_log.write(format_suggestion_box(metadata.next_suggested_immediate_action))

        # Notificar al ExtendedStatsManager si está disponible
        if hasattr(self, 'extended_stats_manager'):
            xp_gained, achievements = self.extended_stats_manager.process_structured_response(
                advances_task=metadata.advances_current_task,
                phase=metadata.task_phase,
                saved_to_history=metadata.is_useful_to_record_in_history,
                has_suggestion=bool(metadata.next_suggested_immediate_action),
                confidence=metadata.confidence,
                requires_refresh=metadata.requires_context_refresh
            )

            # Procesar reflexión y objetivos personales del agente
            if metadata.self_reflection or metadata.personal_goal or metadata.long_term_goal:
                ref_xp, ref_achievements = self.extended_stats_manager.process_reflection_and_goal(
                    reflection=metadata.self_reflection,
                    personal_goal=metadata.personal_goal,
                    long_term_goal=metadata.long_term_goal,
                    long_term_progress=metadata.long_term_goal_progress
                )
                xp_gained += ref_xp
                achievements.extend(ref_achievements)

            # Mostrar XP ganada
            if xp_gained > 0:
                self.chat_log.write(f"[dim]+{xp_gained} XP por respuesta estructurada[/dim]")

            # Mostrar logros desbloqueados
            for ach in achievements:
                self._show_achievement(ach)

            self._update_xp_bar()

    def _on_suggestion_followed(self: "ClaudeChat") -> None:
        """Callback cuando usuario sigue una sugerencia"""
        if hasattr(self, 'extended_stats_manager'):
            xp_gained, achievements = self.extended_stats_manager.follow_suggestion()

            self.chat_log.write(f"[dim]+{xp_gained} XP por seguir sugerencia[/dim]")

            for ach in achievements:
                self._show_achievement(ach)

            self._update_xp_bar()

