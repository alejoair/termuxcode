"""Clase base para filtros de mensajes."""


class MessageFilter:
    """Clase base para filtros de mensajes del historial.

    Cada filtro debe implementar el método `apply()` que recibe
    una lista de mensajes y retorna los mensajes filtrados/transformados.
    """

    def apply(self, messages: list[dict]) -> list[dict]:
        """Aplica este filtro a los mensajes.

        Args:
            messages: Lista de mensajes a filtrar

        Returns:
            Lista de mensajes filtrados/transformados
        """
        raise NotImplementedError
