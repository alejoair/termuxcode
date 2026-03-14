"""Módulo de memoria con persistencia en disco.

Proporciona tres clases para gestión de datos:
- Storage: Persistencia genérica en disco (JSON/CSV) - interna
- Fifo: Cola FIFO con persistencia en CSV
- Blackboard: Almacenamiento key-value tipo Firebase con persistencia en JSON
"""
import csv
import json
import os
from pathlib import Path
from typing import Any

# Directorio por defecto para persistencia
_DEFAULT_MEMORY_DIR = ".memory"


class Storage:
    """Clase base para persistencia genérica en disco (uso interno).

    Proporciona métodos genéricos para guardar y cargar datos en
    formato JSON o CSV.
    """

    def __init__(self, base_path: str):
        """Inicializa el storage con un directorio base.

        Args:
            base_path: Directorio base para guardar archivos.
        """
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def save(self, file_name: str, data: Any, format: str = "json") -> None:
        """Guarda datos a disco.

        Args:
            file_name: Nombre del archivo a guardar.
            data: Datos a guardar.
            format: Formato del archivo ("json" o "csv").
        """
        path = os.path.join(self.base_path, file_name)

        if format == "json":
            self._write_json(path, data)
        elif format == "csv":
            self._write_csv(path, data)
        else:
            raise ValueError(f"Formato no soportado: {format}")

    def load(self, file_name: str, format: str = "json") -> Any:
        """Carga datos desde disco.

        Args:
            file_name: Nombre del archivo a cargar.
            format: Formato del archivo ("json" o "csv").

        Returns:
            Datos cargados o None si el archivo no existe.
        """
        path = os.path.join(self.base_path, file_name)

        if not os.path.exists(path):
            return None

        if format == "json":
            return self._read_json(path)
        elif format == "csv":
            return self._read_csv(path)
        else:
            raise ValueError(f"Formato no soportado: {format}")

    def delete(self, file_name: str) -> bool:
        """Elimina un archivo del storage.

        Args:
            file_name: Nombre del archivo a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        path = os.path.join(self.base_path, file_name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def exists(self, file_name: str) -> bool:
        """Verifica si existe un archivo.

        Args:
            file_name: Nombre del archivo a verificar.

        Returns:
            True si el archivo existe.
        """
        path = os.path.join(self.base_path, file_name)
        return os.path.exists(path)

    # Helpers privados

    def _write_json(self, path: str, data: Any) -> None:
        """Escribe datos en formato JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_json(self, path: str) -> Any:
        """Lee datos en formato JSON."""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_csv(self, path: str, rows: list[list[Any]]) -> None:
        """Escribe datos en formato CSV."""
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)

    def _read_csv(self, path: str) -> list[list[str]]:
        """Lee datos en formato CSV."""
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.reader(f))


class Fifo:
    """Cola FIFO con persistencia en CSV.

    Primero en entrar, primero en salir. Los datos se guardan
    automáticamente en disco en formato CSV.
    """

    def __init__(self, name: str, memory_dir: str = None):
        """Inicializa una cola FIFO.

        Args:
            name: Nombre de la cola (usado para el archivo).
            memory_dir: Directorio para persistencia (default: .memory/).
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


class Blackboard:
    """Almacenamiento key-value tipo Firebase con persistencia en JSON.

    Permite guardar y recuperar datos usando rutas anidadas
    separadas por puntos (ej: "usuario.nombre").
    """

    def __init__(self, name: str, memory_dir: str = None):
        """Inicializa un blackboard.

        Args:
            name: Nombre del blackboard (usado para el archivo).
            memory_dir: Directorio para persistencia (default: .memory/).
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
