# Schemas

Este módulo contiene todos los esquemas JSON utilizados en la aplicación.

## Estructura

```
schemas/
├── __init__.py              # Módulo de Python con helpers y exports
├── structured_response.json # Schema para respuestas estructuradas del SDK
└── README.md                # Este archivo
```

## Uso

### Importar un schema específico

```python
from termuxcode.tui.schemas import STRUCTURED_RESPONSE_SCHEMA

# Usar con el SDK de Claude
options = ClaudeAgentOptions(
    output_format={
        "type": "json_schema",
        "schema": STRUCTURED_RESPONSE_SCHEMA
    }
)
```

### Cargar cualquier schema dinámicamente

```python
from termuxcode.tui.schemas import load_schema

# Cargar cualquier schema por nombre
schema = load_schema("structured_response")
```

## Agregar nuevos schemas

1. Crear un archivo `.json` en esta carpeta:
   ```bash
   touch schemas/tu_nuevo_schema.json
   ```

2. Escribir el esquema JSON válido:
   ```json
   {
       "type": "object",
       "properties": {
           "campo1": {"type": "string"},
           "campo2": {"type": "number"}
       },
       "required": ["campo1", "campo2"]
   }
   ```

3. (Opcional) Exportarlo en `__init__.py` para facilitar el import:
   ```python
   # En __init__.py
   TU_SCHEMA = _load_tu_schema()

   __all__ = [
       "STRUCTURED_RESPONSE_SCHEMA",
       "TU_SCHEMA",
       "load_schema",
   ]
   ```

## Schemas disponibles

| Archivo | Nombre de export | Descripción |
|---------|------------------|-------------|
| `structured_response.json` | `STRUCTURED_RESPONSE_SCHEMA` | Schema para respuestas estructuradas del SDK de Claude |
