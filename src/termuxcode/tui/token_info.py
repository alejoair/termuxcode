"""Widget compacto que muestra tokens acumulados desde el Blackboard."""
from textual.widgets import Static

from termuxcode.core.memory.blackboard import Blackboard


def _format_tokens(n: int) -> str:
    """Format token count: 1.2K, 15K, etc."""
    if n >= 1000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    return str(n)


class TokenInfo(Static):
    """Barra de una línea que muestra tokens de entrada/salida acumulados."""

    DEFAULT_CSS = """
    TokenInfo {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
        content-align: right middle;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bb = Blackboard("app")

    def on_mount(self) -> None:
        """Inicializar y escuchar cambios."""
        self._refresh_from_bb()
        # Escuchar cambios en cualquier sesión (wildcard)
        Blackboard.on("sessions.**", self._on_bb_change)
        Blackboard.on("session.active_id", self._on_bb_change)

    def on_unmount(self) -> None:
        """Limpiar listeners."""
        Blackboard.off("sessions.**", self._on_bb_change)
        Blackboard.off("session.active_id", self._on_bb_change)

    async def _on_bb_change(self, path: str, value, bb: Blackboard) -> None:
        """Callback del Blackboard: refresca el contenido cuando cambian los tokens."""
        # Usar la instancia del callback que tiene los datos actualizados
        self._refresh_from_bb(bb)

    def _refresh_from_bb(self, bb: Blackboard | None = None) -> None:
        """Lee el Blackboard y actualiza el texto para la sesión activa."""
        bb = bb or self._bb
        # Recargar del disco para asegurar datos actualizados
        bb._load_from_disk()

        # Obtener la sesión activa
        active_id = bb.get("session.active_id")
        if not active_id:
            self.update("")
            return

        # Leer tokens de la sesión activa
        tokens = bb.get(f"sessions.{active_id}.tokens")

        if not tokens:
            self.update("")
            return

        inp = tokens.get("input", 0)
        out = tokens.get("output", 0)

        if inp == 0 and out == 0:
            self.update("")
            return

        parts = [
            f"📥 {_format_tokens(inp)}",
            f"📤 {_format_tokens(out)}",
        ]

        cost = bb.get(f"sessions.{active_id}.cost")
        if cost:
            parts.append(f"${cost:.3f}")

        self.update("  ".join(parts))
