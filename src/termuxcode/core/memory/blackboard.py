"""Almacenamiento key-value tipo Firebase con persistencia en disco y eventos."""
from __future__ import annotations

import fnmatch
import logging
from typing import Any, Callable, Awaitable

from .storage import Storage

logger = logging.getLogger(__name__)

# Type for event callbacks: receives (path, value, blackboard_instance)
EventCallback = Callable[[str, Any, "Blackboard"], Awaitable[None]]


class Blackboard:
    """Almacenamiento key-value con rutas anidadas separadas por puntos.

    Soporta listeners que se disparan cuando un path cambia de valor.
    Los listeners se registran a nivel de clase con Blackboard.on().
    """

    # Class-level listener registry: { pattern: [callback, ...] }
    _listeners: dict[str, list[EventCallback]] = {}

    def __init__(self, name: str):
        """Inicializa un blackboard.

        Args:
            name: Nombre del blackboard (determina el nombre del archivo JSON).
        """
        self.name = name
        self.storage = Storage()
        self.file_path = f"{name}.json"
        self.data: dict = {}
        self._load_from_disk()

    # ── Event system ──────────────────────────────────────────────

    @classmethod
    def on(cls, pattern: str, callback: EventCallback) -> None:
        """Registra un listener para un patrón de path.

        Patrones soportados:
        - Exacto: "project.architecture.modules"
        - Wildcard: "project.architecture.*"
        - Deep wildcard: "project.**"

        Args:
            pattern: Patrón de path a escuchar.
            callback: Función async que recibe (path, value, blackboard).
        """
        if pattern not in cls._listeners:
            cls._listeners[pattern] = []
        cls._listeners[pattern].append(callback)
        logger.debug(f"listener registered: {pattern}")

    @classmethod
    def off(cls, pattern: str, callback: EventCallback | None = None) -> None:
        """Remueve un listener o todos los listeners de un patrón.

        Args:
            pattern: Patrón de path.
            callback: Callback específico a remover. Si es None, remueve todos.
        """
        if pattern not in cls._listeners:
            return
        if callback is None:
            del cls._listeners[pattern]
        else:
            cls._listeners[pattern] = [
                cb for cb in cls._listeners[pattern] if cb is not callback
            ]
            if not cls._listeners[pattern]:
                del cls._listeners[pattern]

    @classmethod
    def clear_listeners(cls) -> None:
        """Remueve todos los listeners registrados."""
        cls._listeners.clear()

    @classmethod
    def _match(cls, pattern: str, path: str) -> bool:
        """Verifica si un path matchea un patrón.

        - "project.architecture.modules" matchea exacto.
        - "project.architecture.*" matchea un nivel.
        - "project.**" matchea cualquier profundidad.
        """
        # Convert dot-separated paths to slash-separated for fnmatch
        # ** needs special handling: replace with a greedy glob
        p = pattern.replace(".", "/")
        t = path.replace(".", "/")
        # "**" should match any depth
        p = p.replace("**", "DOUBLESTAR")
        p = p.replace("DOUBLESTAR", "**")
        # fnmatch doesn't support **, so we handle it manually
        if "**" in p:
            prefix = p.split("**")[0].rstrip("/")
            return t.startswith(prefix) or t == prefix.rstrip("/")
        return fnmatch.fnmatch(t, p)

    async def _dispatch(self, path: str, value: Any) -> None:
        """Dispara todos los listeners que matchean el path."""
        for pattern, callbacks in self._listeners.items():
            if self._match(pattern, path):
                for cb in callbacks:
                    try:
                        await cb(path, value, self)
                    except Exception as e:
                        logger.error(f"listener error on {pattern}: {e}")

    # ── Core operations ───────────────────────────────────────────

    def _load_from_disk(self) -> None:
        """Carga los datos desde disco."""
        loaded = self.storage.load(self.file_path, format="json")
        self.data = loaded if loaded and isinstance(loaded, dict) else {}

    def _persist(self) -> None:
        """Guarda los datos en disco."""
        self.storage.save(self.file_path, self.data, format="json")

    async def set(self, path: str, value: Any) -> None:
        """Guarda un valor en una ruta anidada y dispara eventos.

        Args:
            path: Ruta anidada separada por puntos (ej: "usuario.nombre").
            value: Valor a guardar.
        """
        self.set_sync(path, value)
        await self._dispatch(path, value)

    def set_sync(self, path: str, value: Any) -> None:
        """Guarda un valor sin disparar eventos. Usar desde código sincrónico."""
        keys = path.split(".")
        current = self.data

        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

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

    async def update(self, new_data: dict) -> None:
        """Actualiza los datos con merge recursivo y dispara eventos.

        Args:
            new_data: Datos para mezclar con los existentes.
        """
        self.data = self._deep_merge(self.data, new_data)
        self._persist()
        # Dispatch events for all leaf paths in the update
        for path, value in self._flatten(new_data).items():
            await self._dispatch(path, value)

    async def delete(self, path: str) -> bool:
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
            await self._dispatch(path, None)
            return True
        return False

    async def clear(self) -> None:
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
        sentinel = object()
        return self.get(path, sentinel) is not sentinel

    def keys(self) -> list:
        """Retorna todas las claves de nivel superior.

        Returns:
            Lista de claves.
        """
        return list(self.data.keys())

    # ── Helpers ────────────────────────────────────────────────────

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Merge recursivo de diccionarios."""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _flatten(data: dict, prefix: str = "") -> dict[str, Any]:
        """Aplana un dict anidado a paths separados por puntos.

        Args:
            data: Diccionario a aplanar.
            prefix: Prefijo para las claves.

        Returns:
            Dict con paths planos como claves.
        """
        result = {}
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(Blackboard._flatten(value, path))
            else:
                result[path] = value
        return result
