"""Cola FIFO con persistencia en disco."""
from typing import Any

from .storage import Storage


class Fifo:
    """Cola FIFO con persistencia en CSV."""

    def __init__(self, name: str):
        """Inicializa una cola FIFO.

        Args:
            name: Nombre de la cola (determina el nombre del archivo CSV).
        """
        self.name = name
        self.storage = Storage()
        self.file_path = f"{name}.csv"
        self.queue: list[Any] = []
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Carga la cola desde disco."""
        data = self.storage.load(self.file_path, format="csv")
        self.queue = data if data else []

    def _persist(self) -> None:
        """Guarda la cola en disco."""
        rows = [[str(item)] for item in self.queue]
        self.storage.save(self.file_path, rows, format="csv")

    def push(self, data: Any) -> None:
        """Agrega un elemento al final de la cola."""
        self.queue.append(data)
        self._persist()

    def pop(self) -> Any | None:
        """Elimina y retorna el primer elemento de la cola."""
        if not self.queue:
            return None
        data = self.queue.pop(0)
        self._persist()
        return data

    def peek(self) -> Any | None:
        """Retorna el primer elemento sin eliminarlo."""
        return self.queue[0] if self.queue else None

    def size(self) -> int:
        """Retorna la cantidad de elementos en la cola."""
        return len(self.queue)

    def is_empty(self) -> bool:
        """Verifica si la cola está vacía."""
        return len(self.queue) == 0

    def clear(self) -> None:
        """Elimina todos los elementos de la cola."""
        self.queue = []
        self._persist()

    def to_list(self) -> list:
        """Retorna una copia de la cola como lista."""
        return list(self.queue)
