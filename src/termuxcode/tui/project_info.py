"""Widget compacto que muestra info del proyecto desde el Blackboard."""
from textual.widgets import Static

from termuxcode.core.memory.blackboard import Blackboard


class ProjectInfo(Static):
    """Barra de una línea que muestra lenguaje, versión, package manager y source dir."""

    DEFAULT_CSS = """
    ProjectInfo {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
        content-align: left middle;
    }
    """

    def on_mount(self) -> None:
        self._refresh_content()
        Blackboard.on("project.**", self._on_bb_change)

    async def _on_bb_change(self, path: str, value, bb: Blackboard) -> None:
        """Callback del Blackboard: refresca el contenido cuando cambia project.*"""
        self._refresh_content()

    def _refresh_content(self) -> None:
        """Lee el Blackboard y actualiza el texto."""
        bb = Blackboard("app")
        parts = []

        lang = bb.get("project.runtime.language")
        version = bb.get("project.runtime.version")
        if lang:
            text = lang
            if version and version != "null":
                text += f" {version}"
            parts.append(text)

        pkg = bb.get("project.runtime.package_manager")
        if pkg:
            parts.append(pkg)

        src = bb.get("project.structure.source_dir")
        if src:
            parts.append(src)

        entry = bb.get("project.structure.entry_point")
        if entry:
            parts.append(entry)

        if parts:
            self.update(" · ".join(parts))
        else:
            self.update("")
