"""Sistema de notificaciones para tareas que terminan en background"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class NotificationType(Enum):
    """Tipo de notificación"""
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"


@dataclass
class Notification:
    """Notificación individual"""
    session_id: str
    session_name: str
    message: str
    notification_type: NotificationType
    timestamp: datetime
    read: bool = False


class NotificationQueue:
    """Cola de notificaciones para tareas que terminaron en background"""

    def __init__(self, max_notifications: int = 100):
        self._notifications: List[Notification] = []
        self._max_notifications = max_notifications

    def add(
        self,
        session_id: str,
        session_name: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO
    ) -> None:
        """Agregar una nueva notificación

        Args:
            session_id: ID de la sesión
            session_name: Nombre de la sesión
            message: Mensaje de la notificación
            notification_type: Tipo de notificación
        """
        notif = Notification(
            session_id=session_id,
            session_name=session_name,
            message=message,
            notification_type=notification_type,
            timestamp=datetime.now(),
        )
        self._notifications.append(notif)

        # Mantener límite de notificaciones
        if len(self._notifications) > self._max_notifications:
            # Remover las más antiguas
            self._notifications = self._notifications[-self._max_notifications:]

    def get_for_session(self, session_id: str) -> List[Notification]:
        """Obtener notificaciones no leídas de una sesión

        Args:
            session_id: ID de la sesión

        Returns:
            Lista de notificaciones no leídas para esa sesión
        """
        return [n for n in self._notifications if n.session_id == session_id and not n.read]

    def get_unread(self) -> List[Notification]:
        """Obtener todas las notificaciones no leídas

        Returns:
            Lista de todas las notificaciones no leídas
        """
        return [n for n in self._notifications if not n.read]

    def get_unread_count(self, session_id: str) -> int:
        """Obtener cantidad de notificaciones no leídas de una sesión

        Args:
            session_id: ID de la sesión

        Returns:
            Cantidad de notificaciones no leídas
        """
        return sum(1 for n in self._notifications if n.session_id == session_id and not n.read)

    def mark_as_read(self, session_id: str) -> None:
        """Marcar todas las notificaciones de una sesión como leídas

        Args:
            session_id: ID de la sesión
        """
        for notif in self._notifications:
            if notif.session_id == session_id:
                notif.read = True

    def mark_all_as_read(self) -> None:
        """Marcar todas las notificaciones como leídas"""
        for notif in self._notifications:
            notif.read = True

    def clear(self) -> None:
        """Limpiar todas las notificaciones"""
        self._notifications.clear()

    def clear_session(self, session_id: str) -> None:
        """Limpiar notificaciones de una sesión específica

        Args:
            session_id: ID de la sesión
        """
        self._notifications = [n for n in self._notifications if n.session_id != session_id]

    def get_all(self) -> List[Notification]:
        """Obtener todas las notificaciones (incluyendo leídas)

        Returns:
            Lista completa de notificaciones
        """
        return self._notifications.copy()
