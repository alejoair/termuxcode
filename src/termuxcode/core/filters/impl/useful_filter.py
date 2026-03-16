"""Filtro que elimina mensajes marcados como no útiles."""

from typing import Literal
from ..base import MessageFilter


class UsefulFilter(MessageFilter):
    """Filtra mensajes basándose en el campo 'is_useful'.

    Args:
        filter_by_useful: Controla el comportamiento:
            - None: respeta el valor de cada mensaje (incluso si es False)
            - False: incluye todos los mensajes ignorando is_useful
            - True: filtra los mensajes con is_useful=False
    """

    def __init__(self, filter_by_useful: Literal[None, False, True] = True):
        self.filter_by_useful = filter_by_useful

    def apply(self, messages: list[dict]) -> list[dict]:
        """Filtra mensajes por is_useful.

        Args:
            messages: Lista de mensajes a filtrar

        Returns:
            Lista de mensajes filtrados
        """
        # Si filter_by_useful es None, respeta el valor de cada mensaje
        if self.filter_by_useful is None:
            return messages

        # Si filter_by_useful es False, incluye todos los mensajes
        if self.filter_by_useful is False:
            return messages

        # Si filter_by_useful es True, filtra los no útiles
        return [msg for msg in messages if msg.get("is_useful", True)]
