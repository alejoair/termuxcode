"""Inicializador de datos en Fifo y Blackboard desde diversas fuentes."""
import json
from pathlib import Path
from typing import Any

from .blackboard import Blackboard
from .fifo import Fifo

# Directorio por defecto para persistencia
_DEFAULT_MEMORY_DIR = ".claude/memory"


class Initializer:
    """Inicializa datos en Fifo y Blackboard desde diversas fuentes.

    Esta clase facilita la carga inicial de datos cuando se inicia la aplicación,
    permitiendo leer archivos de configuración, documentación, etc. y guardarlos
    en estructuras de memoria persistentes.
    """

    def __init__(self, memory_dir: str = None, cwd: str = None):
        """Inicializa el Initializer.

        Args:
            memory_dir: Directorio para persistencia (default: .claude/memory/).
            cwd: Directorio de trabajo (default: Path.cwd()).
        """
        if cwd is None:
            cwd = str(Path.cwd())
        self.cwd = Path(cwd)
        self.memory_dir = memory_dir or str(self.cwd / _DEFAULT_MEMORY_DIR)

    def load_claude_md(self, blackboard_name: str = "app", path: str = None) -> None:
        """Lee CLAUDE.md y lo guarda en el blackboard.

        Args:
            blackboard_name: Nombre del blackboard (default: "app").
            path: Ruta al CLAUDE.md (default: cwd/CLAUDE.md).
        """
        if path is None:
            path = self.cwd / "CLAUDE.md"
        else:
            path = Path(path)

        if path.exists():
            content = path.read_text(encoding="utf-8")
            bb = Blackboard(blackboard_name, memory_dir=self.memory_dir)
            bb.set_sync("docs.claude_md", content)
        else:
            raise FileNotFoundError(f"CLAUDE.md no encontrado en {path}")

    def load_config_json(self, blackboard_name: str = "app", path: str = None,
                         blackboard_path: str = "config") -> None:
        """Lee un archivo JSON de configuración y lo guarda en el blackboard.

        Args:
            blackboard_name: Nombre del blackboard.
            path: Ruta al JSON (default: cwd/config.json).
            blackboard_path: Ruta donde guardar en el blackboard (default: "config").
        """
        if path is None:
            path = self.cwd / "config.json"
        else:
            path = Path(path)

        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            bb = Blackboard(blackboard_name, memory_dir=self.memory_dir)
            bb.set_sync(blackboard_path, config)
        else:
            raise FileNotFoundError(f"Config no encontrado en {path}")

    def initialize_fifo(self, fifo_name: str, items: list[Any]) -> None:
        """Inicializa una Fifo con una secuencia de items.

        Args:
            fifo_name: Nombre de la Fifo.
            items: Lista de items a agregar (se añaden en orden).
        """
        fifo = Fifo(fifo_name, memory_dir=self.memory_dir)
        # Solo agregar si la Fifo está vacía
        if fifo.is_empty():
            for item in items:
                fifo.push(item)

    def initialize_fifo_from_file(self, fifo_name: str, path: str,
                                   format: str = "json") -> None:
        """Inicializa una Fifo desde un archivo.

        Args:
            fifo_name: Nombre de la Fifo.
            path: Ruta al archivo.
            format: Formato del archivo ("json" o "txt").
        """
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado en {path}")

        items = []
        if format == "json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]
        elif format == "txt":
            with open(path, "r", encoding="utf-8") as f:
                items = [line.strip() for line in f if line.strip()]
        else:
            raise ValueError(f"Formato no soportado: {format}")

        self.initialize_fifo(fifo_name, items)

    def initialize_tags(self, tags_file: str = None) -> dict[str, bool]:
        """Inicializa Fifo de tags desde archivo JSON.

        Args:
            tags_file: Ruta al archivo JSON con definiciones de tags.
                      Por defecto: cwd/memory/tags.json

        Returns:
            Dict con resultados: {"tags": True, ...}
        """
        if tags_file is None:
            tags_file = self.cwd / "memory" / "tags.json"
        else:
            tags_file = Path(tags_file)

        results = {}

        if tags_file.exists():
            with open(tags_file, "r", encoding="utf-8") as f:
                tags = json.load(f)
            # Guardar cada tag como JSON string en la Fifo
            # Primero limpiar si ya existe
            fifo = Fifo("tags", memory_dir=self.memory_dir)
            fifo.clear()
            # Cargar cada tag como JSON string
            for tag in tags:
                fifo.push(json.dumps(tag))
            results["tags"] = True
        else:
            results["tags"] = False

        return results

    def initialize_all(self) -> dict[str, bool]:
        """Inicializa todas las fuentes por defecto.

        Returns:
            Dict con resultados: {"claude_md": True, "config": True, ...}
        """
        results = {}

        try:
            self.load_claude_md()
            results["claude_md"] = True
        except FileNotFoundError:
            results["claude_md"] = False

        try:
            self.load_config_json()
            results["config"] = True
        except FileNotFoundError:
            results["config"] = False

        return results
