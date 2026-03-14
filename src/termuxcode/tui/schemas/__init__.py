"""Schemas JSON usados en la aplicación.

Este módulo contiene todos los esquemas JSON utilizados para
definir la estructura de datos que espera la aplicación.

Ejemplo de uso:
    from termuxcode.tui.schemas import STRUCTURED_RESPONSE_SCHEMA

    options = ClaudeAgentOptions(
        output_format={
            "type": "json_schema",
            "schema": STRUCTURED_RESPONSE_SCHEMA
        }
    )
"""

from pathlib import Path
import json

# Ruta base del módulo
_BASE_PATH = Path(__file__).parent


def load_schema(name: str) -> dict:
    """
    Cargar un esquema JSON por nombre.

    Args:
        name: Nombre del archivo sin extensión (ej: "structured_response")

    Returns:
        dict: El esquema JSON cargado

    Raises:
        FileNotFoundError: Si el archivo no existe
        json.JSONDecodeError: Si el archivo no es un JSON válido
    """
    schema_path = _BASE_PATH / f"{name}.json"
    with schema_path.open("r", encoding="utf-8") as f:
        return json.load(f)


# Schemas importables directamente
def _load_structured_response() -> dict:
    """Cargar el esquema de respuesta estructurada."""
    return load_schema("structured_response")


# Exportar schemas
STRUCTURED_RESPONSE_SCHEMA = _load_structured_response()

__all__ = [
    "STRUCTURED_RESPONSE_SCHEMA",
    "load_schema",
]
