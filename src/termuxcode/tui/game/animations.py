"""Animaciones de gamificación - efectos visuales en terminal"""
from __future__ import annotations
from textual.app import App
from textual.reactive import reactive
from textual.widgets import Static
from textual.message import Message
import asyncio
from typing import Generator


def bounce_frames(chars: str, width: int = 5) -> Generator[str, None, None]:
    """Generar frames de animación de rebote"""
    positions = list(range(width)) + list(range(width - 2, 0, -1))
    for pos in positions:
        spaces = " " * pos
        yield f"[{spaces}{chars[0]}{' ' * (width - pos - 1)}]"


def pulse_frames(char: str = "*", intensity: int = 3) -> Generator[str, None, None]:
    """Generar frames de pulso (brillo variable)"""
    brightness = ["dim", "", "bold", "", "dim"]
    for b in brightness * intensity:
        if b:
            yield f"[{b}]{char}[/{b}]"
        else:
            yield char


def progress_fill(width: int = 10, char: str = "=") -> Generator[str, None, None]:
    """Generar frames de llenado progresivo"""
    for i in range(width + 1):
        filled = char * i
        empty = "-" * (width - i)
        yield f"[{filled}{empty}]"


class AnimatedDots(Static):
    """Animación de puntos pensantes"""

    DEFAULT_CSS = """
    AnimatedDots {
        height: 1;
        width: auto;
        color: $primary;
    }
    """

    frame: reactive[int] = reactive(0)
    is_animating: reactive[bool] = reactive(False)

    DOT_PATTERNS = [
        ".  ",
        ".. ",
        "...",
        " ..",
        "  .",
    ]

    def __init__(self, prefix: str = "Thinking", **kwargs):
        super().__init__(**kwargs)
        self._prefix = prefix
        self._task = None

    def start(self) -> None:
        """Iniciar animación"""
        self.is_animating = True
        self._task = asyncio.create_task(self._animate())

    def stop(self) -> None:
        """Detener animación"""
        self.is_animating = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _animate(self) -> None:
        """Loop de animación"""
        try:
            while self.is_animating:
                for pattern in self.DOT_PATTERNS:
                    if not self.is_animating:
                        break
                    self.update(f"{self._prefix}{pattern}")
                    await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            pass


class FlashEffect(Static):
    """Efecto de flash temporal"""

    DEFAULT_CSS = """
    FlashEffect {
        height: 1;
        width: 100%;
        background: $primary;
        color: $background;
        text-style: bold;
        content-align: center middle;
        display: none;
    }

    FlashEffect.visible {
        display: block;
    }
    """

    visible: reactive[bool] = reactive(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dismiss_timer = None

    def flash(self, message: str, duration: float = 0.5, color: str = "primary") -> None:
        """Mostrar efecto flash"""
        self.update(message)
        self.visible = True

        if self._dismiss_timer:
            self._dismiss_timer.stop()
        self._dismiss_timer = self.set_timer(duration, self._hide)

    def _hide(self) -> None:
        """Ocultar efecto"""
        self.visible = False


class SparkleText:
    """Efecto de brillo en texto (sin unicode)"""

    # Caracteres ASCII para efecto
    CHARS = ["*", "+", "#", "@", "!"]

    @classmethod
    def sparkle(cls, text: str, frame: int = 0) -> str:
        """Aplicar efecto de brillo"""
        char = cls.CHARS[frame % len(cls.CHARS)]
        return f"{char} {text} {char}"

    @classmethod
    def celebrate(cls, text: str) -> str:
        """Formato de celebración"""
        return f"[bold]>== {text} ==<[/bold]"


class TypewriterEffect:
    """Efecto de máquina de escribir"""

    @staticmethod
    async def type_text(
        widget: Static,
        text: str,
        speed: float = 0.02,
        prefix: str = ""
    ) -> None:
        """Escribir texto caracter por caracter"""
        current = prefix
        for char in text:
            current += char
            widget.update(current)
            await asyncio.sleep(speed)


class AnimationManager:
    """Gestor de animaciones centralizado"""

    def __init__(self, app: "App"):
        self._app = app
        self._active_animations: list[asyncio.Task] = []

    def show_achievement(self, name: str, xp: int, icon: str = "*") -> None:
        """Mostrar animación de logro"""
        # Buscar o crear AchievementPopup
        try:
            popup = self._app.query_one("AchievementPopup")
            if popup:
                from .stats import Achievement
                ach = Achievement(id="", name=name, xp=xp, icon=icon, unlocked=True)
                popup.show_achievement(ach)
        except Exception:
            pass

    def show_level_up(self, level: int) -> None:
        """Mostrar animación de subida de nivel"""
        try:
            banner = self._app.query_one("LevelUpBanner")
            if banner:
                banner.show_level_up(level)
        except Exception:
            pass

    def flash_message(self, message: str, duration: float = 0.5) -> None:
        """Mostrar mensaje flash temporal"""
        try:
            flash = self._app.query_one("FlashEffect")
            if flash:
                flash.flash(message, duration)
        except Exception:
            pass

    def cancel_all(self) -> None:
        """Cancelar todas las animaciones activas"""
        for task in self._active_animations:
            if not task.done():
                task.cancel()
        self._active_animations.clear()
