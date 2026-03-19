"""Cola FIFO con persistencia en disco."""
from pathlib import Path
from typing import Any

from .storage import Storage

# Directorio por defecto para persistencia
_DEFAULT_MEMORY_DIR = ".claude/memory"


class Fifo:
    """Cola FIFO con persistencia en CSV.

    Primero en entrar, primero en salir. Los datos se guardan
    automáticamente en disco en formato CSV.
    """

    def __init__(self, name: str, memory_dir: str = None):
        """Inicializa una cola FIFO.

        Args:
            name: Nombre de la cola (usado para el archivo).
            memory_dir: Directorio para persistencia (default: .claude/memory/).
        """
        self.name = name
        if memory_dir is None:
            cwd = Path.cwd()
            memory_dir = str(cwd / _DEFAULT_MEMORY_DIR)
        self.storage = Storage(memory_dir)
        self.file_path = f"{name}.csv"
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Carga la cola desde disco."""
        data = self.storage.load(self.file_path, format="csv")
        self.queue = data if data else []

    def _persist(self) -> None:
        """Guarda la cola en disco."""
        # Convertir todos los elementos a string para CSV
        rows = [[str(item)] for item in self.queue]
        self.storage.save(self.file_path, rows, format="csv")

    def push(self, data: Any) -> None:
        """Agrega un elemento al final de la cola.

        Args:
            data: Dato a agregar.
        """
        self.queue.append(data)
        self._persist()

    def pop(self) -> Any | None:
        """Elimina y retorna el primer elemento de la cola.

        Returns:
            El primer elemento o None si la cola está vacía.
        """
        if not self.queue:
            return None
        data = self.queue.pop(0)
        self._persist()
        return data

    def peek(self) -> Any | None:
        """Retorna el primer elemento sin eliminarlo.

        Returns:
            El primer elemento o None si la cola está vacía.
        """
        if not self.queue:
            return None
        return self.queue[0]

    def size(self) -> int:
        """Retorna la cantidad de elementos en la cola.

        Returns:
            Número de elementos.
        """
        return len(self.queue)

    def is_empty(self) -> bool:
        """Verifica si la cola está vacía.

        Returns:
            True si la cola no tiene elementos.
        """
        return len(self.queue) == 0

    def clear(self) -> None:
        """Elimina todos los elementos de la cola."""
        self.queue = []
        self._persist()

    def to_list(self) -> list:
        """Retorna una copia de la cola como lista.

        Returns:
            Lista con los elementos de la cola.
        """
        return list(self.queue)
