"""Gestor de tareas en background para ejecución paralela de sesiones"""
from typing import Callable, Dict, Optional
import asyncio


class BackgroundTaskManager:
    """Gestiona tasks de asyncio por sesión sin cancelar al cambiar de sesión"""

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}

    def start_task(
        self,
        session_id: str,
        coro,
        on_complete: Callable[[str, Optional[Exception]], None] = None
    ) -> None:
        """Iniciar task para una sesión

        Args:
            session_id: ID de la sesión
            coro: Coroutine a ejecutar
            on_complete: Callback opcional que se llama cuando la task termina
                         (session_id, Exception | None)
        """
        # Cancelar task anterior si existe
        if session_id in self._tasks:
            self.cancel_task(session_id)

        async def wrapped():
            try:
                await coro
            except asyncio.CancelledError:
                # No llamamos on_complete para CancelledError, es esperado
                raise
            except Exception as e:
                if on_complete:
                    on_complete(session_id, e)
            else:
                if on_complete:
                    on_complete(session_id, None)

        task = asyncio.create_task(wrapped())
        self._tasks[session_id] = task

    def cancel_task(self, session_id: str) -> bool:
        """Cancelar task de una sesión explícitamente

        Args:
            session_id: ID de la sesión

        Returns:
            True si se canceló, False si no existía o ya había terminado
        """
        if session_id in self._tasks:
            task = self._tasks[session_id]
            if not task.done():
                task.cancel()
            # Remover del dict aunque ya haya terminado
            del self._tasks[session_id]
            return True
        return False

    def is_running(self, session_id: str) -> bool:
        """Verificar si una sesión tiene task activo

        Args:
            session_id: ID de la sesión

        Returns:
            True si hay un task activo para esa sesión
        """
        if session_id not in self._tasks:
            return False
        return not self._tasks[session_id].done()

    def get_running_sessions(self) -> list[str]:
        """Obtener todas las sesiones con tasks activos

        Returns:
            Lista de session_ids con tasks activos
        """
        return [
            sid for sid, task in self._tasks.items()
            if not task.done()
        ]

    def get_task(self, session_id: str) -> Optional[asyncio.Task]:
        """Obtener el task de una sesión (si existe)

        Args:
            session_id: ID de la sesión

        Returns:
            El Task o None si no existe
        """
        return self._tasks.get(session_id)

    def cancel_all(self) -> None:
        """Cancelar todos los tasks activos"""
        for session_id in list(self._tasks.keys()):
            self.cancel_task(session_id)

    def cleanup_finished(self) -> None:
        """Remover tasks que ya terminaron del dict"""
        finished = [
            sid for sid, task in self._tasks.items()
            if task.done()
        ]
        for sid in finished:
            del self._tasks[sid]
