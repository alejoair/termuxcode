"""Módulo de memoria con persistencia en disco.

Este módulo proporciona clases para gestión de datos con persistencia:

- Fifo: Cola FIFO con persistencia en CSV
- Blackboard: Almacenamiento key-value tipo Firebase con persistencia en JSON
- Initializer: Inicializa datos desde archivos (CLAUDE.md, config.json, etc.)
- Storage: Persistencia genérica (uso interno)

Las clases Fifo y Blackboard crean su propio Storage internamente.

Ejemplo de uso:
    from termuxcode.core.memory import Fifo, Blackboard, Initializer

    # Inicializar al inicio de la app
    init = Initializer()
    init.initialize_all()  # Carga CLAUDE.md y config.json

    # Usar Fifo (crea Storage internamente en .memory/)
    fifo = Fifo("messages")
    fifo.push("mensaje 1")
    msg = fifo.pop()  # "mensaje 1"

    # Usar Blackboard (crea Storage internamente en .memory/)
    bb = Blackboard("app")
    claude_md = bb.get("docs.claude_md")  # CLAUDE.md cargado
    config = bb.get("config")  # config.json cargado
"""

from termuxcode.core.memory.memory import Blackboard, Fifo, Initializer, Storage

__all__ = ["Fifo", "Blackboard", "Initializer", "Storage"]
