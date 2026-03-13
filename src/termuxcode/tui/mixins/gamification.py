"""Mixin para sistema de gamificación"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..app import ClaudeChat


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
