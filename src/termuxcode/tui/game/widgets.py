"""Widgets de gamificación - XPBar, AchievementPopup, LevelUpBanner"""
from __future__ import annotations
from textual.widgets import Static, Label
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.message import Message
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .stats import Achievement


class XPBar(Static):
    """Barra de XP compacta - 1 línea"""

    xp_progress: reactive[float] = reactive(0.0)
    level: reactive[int] = reactive(1)
    xp: reactive[int] = reactive(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bar_width = 8

    def watch_xp_progress(self, progress: float) -> None:
        self._render_bar()

    def watch_level(self, level: int) -> None:
        self._render_bar()

    def watch_xp(self, xp: int) -> None:
        self._render_bar()

    def _render_bar(self) -> None:
        """Renderizar barra de progreso ASCII con colores cálidos"""
        filled = "█"
        empty = "░"

        filled_count = int(self._bar_width * self.xp_progress)
        empty_count = self._bar_width - filled_count

        # Barra sin corchetes para evitar problemas de markup
        bar_filled = filled * filled_count
        bar_empty = empty * empty_count
        # Usar │ y │ como delimitadores en lugar de [ ]
        self.update(f"[bold cyan]L{self.level}[/bold cyan] │[bold yellow]{bar_filled}[/bold yellow][dim]{bar_empty}[/dim]│ [bold gold1]{self.xp}[/bold gold1]XP")

    def update_stats(self, level: int, xp: int, progress: float) -> None:
        """Actualizar todas las estadísticas"""
        self.level = level
        self.xp = xp
        self.xp_progress = progress


class AchievementPopup(Static):
    """Popup de logro desbloqueado - temporal"""

    DEFAULT_CSS = """
    AchievementPopup {
        display: none;
        height: 2;
        width: 100%;
        background: $primary 20%;
        color: $text;
        padding: 0 1;
        border-top: solid $primary;
        dock: bottom;
    }

    AchievementPopup.visible {
        display: block;
    }
    """

    class Dismissed(Message):
        """Mensaje cuando el popup se cierra"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dismiss_timer = None
        self._achievement = None

    def show_achievement(self, achievement: "Achievement") -> None:
        """Mostrar un logro"""
        self._achievement = achievement
        icon = achievement.icon
        name = achievement.name[:20]
        xp = achievement.xp

        self.update(f"[{icon}] {name}\n  +{xp} XP")
        self.add_class("visible")

        if self._dismiss_timer:
            self._dismiss_timer.stop()
        self._dismiss_timer = self.set_timer(2.5, self._dismiss)

    def _dismiss(self) -> None:
        """Cerrar popup"""
        self.remove_class("visible")
        self.post_message(self.Dismissed())


class LevelUpBanner(Static):
    """Banner de subida de nivel - efímero"""

    DEFAULT_CSS = """
    LevelUpBanner {
        display: none;
        height: 1;
        width: 100%;
        background: $success 30%;
        color: $success;
        text-style: bold;
        padding: 0 1;
        content-align: center middle;
        dock: top;
    }

    LevelUpBanner.visible {
        display: block;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dismiss_timer = None

    def show_level_up(self, level: int) -> None:
        """Mostrar subida de nivel"""
        self.update(f"LEVEL UP! -> Nivel {level}")
        self.add_class("visible")

        if self._dismiss_timer:
            self._dismiss_timer.stop()
        self._dismiss_timer = self.set_timer(2.0, self._dismiss)

    def _dismiss(self) -> None:
        """Ocultar banner"""
        self.remove_class("visible")


class GameStatsDisplay(Horizontal):
    """Display compacto de estadísticas"""

    DEFAULT_CSS = """
    GameStatsDisplay {
        height: 1;
        width: auto;
        padding: 0 1;
    }

    GameStatsDisplay .level-badge {
        color: $primary;
        text-style: bold;
        min-width: 3;
    }

    GameStatsDisplay .xp-display {
        color: $text-muted;
        min-width: 6;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._level_label = Label("L1", classes="level-badge")
        self._xp_label = Label("0XP", classes="xp-display")

    def compose(self):
        yield self._level_label
        yield self._xp_label

    def update_stats(self, level: int, xp: int) -> None:
        self._level_label.update(f"L{level}")
        self._xp_label.update(f"{xp}XP")
