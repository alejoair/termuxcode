"""Almacenamiento key-value tipo Firebase con persistencia en disco."""
from pathlib import Path
from typing import Any

from .storage import Storage

# Directorio por defecto para persistencia
_DEFAULT_MEMORY_DIR = ".claude/memory"


class Blackboard:
    """Almacenamiento key-value tipo Firebase con persistencia en JSON.

    Permite guardar y recuperar datos usando rutas anidadas
    separadas por puntos (ej: "usuario.nombre").
    """

    def __init__(self, name: str, memory_dir: str = None):
        """Inicializa un blackboard.

        Args:
            name: Nombre del blackboard (usado para el archivo).
            memory_dir: Directorio para persistencia (default: .claude/memory/).
        """
        self.name = name
        if memory_dir is None:
            cwd = Path.cwd()
            memory_dir = str(cwd / _DEFAULT_MEMORY_DIR)
        self.storage = Storage(memory_dir)
        self.file_path = f"{name}.json"
        self.data: dict = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Carga los datos desde disco."""
        loaded = self.storage.load(self.file_path, format="json")
        self.data = loaded if loaded and isinstance(loaded, dict) else {}

    def _persist(self) -> None:
        """Guarda los datos en disco."""
        self.storage.save(self.file_path, self.data, format="json")

    def set(self, path: str, value: Any) -> None:
        """Guarda un valor en una ruta anidada.

        Args:
            path: Ruta anidada separada por puntos (ej: "usuario.nombre").
            value: Valor a guardar.
        """
        keys = path.split(".")
        current = self.data

        # Navegar hasta el penúltimo nivel
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        # Asignar valor
        current[keys[-1]] = value
        self._persist()

    def get(self, path: str, default: Any = None) -> Any:
        """Retorna un valor de una ruta anidada.

        Args:
            path: Ruta anidada separada por puntos.
            default: Valor por defecto si no existe.

        Returns:
            El valor almacenado o el default.
        """
        keys = path.split(".")
        current = self.data

        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]

        return current

    def get_all(self) -> dict:
        """Retorna una copia de todos los datos.

        Returns:
            Diccionario con todos los datos del blackboard.
        """
        return self.data.copy()

    def update(self, new_data: dict) -> None:
        """Actualiza los datos con merge recursivo.

        Args:
            new_data: Datos para mezclar con los existentes.
        """
        self.data = self._deep_merge(self.data, new_data)
        self._persist()

    def delete(self, path: str) -> bool:
        """Elimina una ruta específica.

        Args:
            path: Ruta anidada separada por puntos.

        Returns:
            True si se eliminó, False si no existía.
        """
        keys = path.split(".")
        current = self.data

        # Navegar hasta el padre del último nivel
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                return False
            current = current[key]

        if keys[-1] in current:
            del current[keys[-1]]
            self._persist()
            return True
        return False

    def clear(self) -> None:
        """Elimina todos los datos del blackboard."""
        self.data = {}
        self._persist()

    def exists(self, path: str) -> bool:
        """Verifica si existe una ruta.

        Args:
            path: Ruta anidada separada por puntos.

        Returns:
            True si la ruta existe.
        """
        # Usamos un objeto único como default que no puede estar en los datos
        sentinel = object()
        return self.get(path, sentinel) is not sentinel

    def keys(self) -> list:
        """Retorna todas las claves de nivel superior.

        Returns:
            Lista de claves.
        """
        return list(self.data.keys())

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Merge recursivo de diccionarios.

        Args:
            base: Diccionario base.
            update: Diccionario a mezclar.

        Returns:
            Diccionario combinado.
        """
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
