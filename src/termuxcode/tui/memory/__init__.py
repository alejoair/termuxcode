"""Módulo de memoria con persistencia en disco.

Este módulo proporciona clases para gestión de datos con persistencia:

- Fifo: Cola FIFO con persistencia en CSV
- Blackboard: Almacenamiento key-value tipo Firebase con persistencia en JSON
- Storage: Persistencia genérica (uso interno)

Las clases Fifo y Blackboard crean su propio Storage internamente.

Ejemplo de uso:
    from termuxcode.tui.memory import Fifo, Blackboard

    # Usar Fifo (crea Storage internamente en .memory/)
    fifo = Fifo("messages")
    fifo.push("mensaje 1")
    fifo.push("mensaje 2")
    msg = fifo.pop()  # "mensaje 1"

    # Usar Blackboard (crea Storage internamente en .memory/)
    bb = Blackboard("session_data")
    bb.set("usuario.nombre", "Juan")
    bb.set("usuario.edad", 30)
    nombre = bb.get("usuario.nombre")  # "Juan"
"""

from .memory import Blackboard, Fifo, Storage

__all__ = ["Fifo", "Blackboard", "Storage"]
