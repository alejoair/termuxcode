# Ejemplos de uso del módulo de filtros

El módulo `filters.py` proporciona preprocesamiento para controlar el tamaño
del historial que se reconstruye en el prompt.

## Uso básico

```python
from termuxcode.tui import MessageHistory, FilterConfig

# Configuración con truncado de tool_result a 500 caracteres
config = FilterConfig(
    max_tool_result_length=500,
    truncate_strategy="ellipsis"
)

history = MessageHistory(
    session_id="abc123",
    filter_config=config
)

# Al construir el prompt, se aplicará el truncado automáticamente
prompt = history.build_prompt(history.load(), "Nuevo mensaje")
```

## Estrategias de truncado

```python
from termuxcode.tui import FilterConfig

# 1. "ellipsis" (default): Corta y agrega "..."
config = FilterConfig(
    max_tool_result_length=300,
    truncate_strategy="ellipsis"
)

# Resultado: "Este es un archivo muy largo que se trun..."
# Output en prompt: "[Tool result: Este es un archivo muy largo que se trun...]"

# 2. "cut": Corta directamente
config = FilterConfig(
    max_tool_result_length=300,
    truncate_strategy="cut"
)

# 3. "summary": Corta y agrega indicador
config = FilterConfig(
    max_tool_result_length=300,
    truncate_strategy="summary"
)

# Resultado: "Este es un archivo muy largo que se trun... [truncado de 5000 caracteres]"
```

## Estimar tamaño del prompt

```python
from termuxcode.tui import MessageHistory, FilterConfig

history = MessageHistory(session_id="abc123")

# Obtener estadísticas del tamaño
stats = history.estimate_size()
print(f"Tamaño: {stats['character_count']} caracteres")
print(f"Tool results: {stats['tool_result_total_size']} caracteres totales")
print(f"Breakdown: {stats['message_breakdown']}")
```

## Sugerir configuración automáticamente

```python
from termuxcode.tui import MessageHistory, FilterConfig, suggest_config

history = MessageHistory(session_id="abc123")

# Obtener estadísticas actuales
stats = history.estimate_size()

# Sugerir configuración para limitar a 50KB de prompt
suggested_config = suggest_config(stats, target_max_chars=50000)

print(f"Sugerido max_tool_result_length: {suggested_config.max_tool_result_length}")

# Aplicar la configuración sugerida
history.filter_config = suggested_config
```

## Usar el preprocesador directamente

```python
from termuxcode.tui import HistoryPreprocessor, FilterConfig

config = FilterConfig(
    max_tool_result_length=1000,
    max_assistant_length=2000,
    truncate_strategy="summary"
)

preprocessor = HistoryPreprocessor(config)

# Procesar un historial específico
filtered_history = preprocessor.process(raw_history)

# Estimar tamaño antes y después
before_stats = preprocessor.estimate_size(raw_history)
after_stats = preprocessor.estimate_size(filtered_history)

print(f"Antes: {before_stats['character_count']} chars")
print(f"Después: {after_stats['character_count']} chars")
```

## Configuración por defecto en app.py

Para configurar los filtros en la aplicación principal:

```python
# En app.py, al crear MessageHistory:
from termuxcode.tui import MessageHistory, FilterConfig

# Configuración por defecto para el proyecto
default_filter_config = FilterConfig(
    max_tool_result_length=500,  # Truncar tool_result a 500 caracteres
    max_assistant_length=None,       # No truncar assistant
    truncate_strategy="ellipsis"
)

history = MessageHistory(
    filename="messages.jsonl",
    max_messages=100,
    session_id=session_id,
    cwd=cwd,
    filter_config=default_filter_config
)
```

## Deshabilitar filtros temporalmente

```python
# Si en algún turno necesitas el historial completo:
prompt = history.build_prompt(
    history.load(),
    "Nuevo mensaje",
    apply_filters=False  # No aplicar truncado
)
```

## Estrategias según caso de uso

### Para conversaciones de desarrollo de software
```python
# Truncar tool_result agresivamente (archivos largos no son útiles)
config = FilterConfig(
    max_tool_result_length=300,
    truncate_strategy="ellipsis"
)
```

### Para conversaciones de análisis de datos
```python
# Truncar assistant y tool_result para mantener contexto
config = FilterConfig(
    max_tool_result_length=800,
    max_assistant_length=2000,
    truncate_strategy="summary"
)
```

### Para debugging (sin filtros)
```python
# Historial completo para inspeccionar
config = FilterConfig()  # Todos los valores None = sin filtros
```
