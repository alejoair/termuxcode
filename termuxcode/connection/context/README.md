# Context Providers System

Sistema modular para inyectar información actualizada en `CLAUDE.md` antes de cada query del SDK.

## Arquitectura

```
termuxcode/connection/
├── claude_md_manager.py       # Orquesta todo y actualiza CLAUDE.md
└── context/
    ├── __init__.py            # Registry de providers
    ├── filetree_provider.py   # File tree + estadísticas
    ├── git_provider.py        # Git info + git status
    └── example_custom_provider.py  # Ejemplo para crear nuevos
```

## Flujo

1. Usuario envía mensaje → `message_processor.py`
2. Antes de llamar al SDK → `update_claude_md(cwd, session_id)`
3. `claude_md_manager.py` ejecuta todos los providers registrados
4. Genera sección `## Project Context (Auto-generated)` en CLAUDE.md
5. SDK lee CLAUDE.md con la info actualizada

## Providers Actuales

| Provider | Prioridad | Requiere Git | Descripción |
|----------|-----------|--------------|-------------|
| `generate_system_context` | 5 | No | Información del sistema (OS, usuario, fecha, Python, shell) |
| `generate_extended_system_context` | 6 | No | Variables de entorno (PATH, LANG, TERM) |
| `generate_filetree_context` | 10 | No | Árbol de archivos (profundidad 3) |
| `generate_stats_context` | 20 | No | Estadísticas (Python/JS files) |
| `generate_git_context` | 30 | Sí | Branch + últimos 3 commits |
| `generate_git_status_context` | 31 | Sí | Archivos modificados (git status) |

## Cómo Agregar un Nuevo Provider

### Paso 1: Crear el archivo

`termuxcode/connection/context/mi_provider.py`:

```python
from termuxcode.connection.context import register_context_provider

@register_context_provider("mi_provider", priority=50)
def generate_mi_context(cwd: str) -> str:
    """Genera información personalizada."""

    # Tu lógica aquí
    return """### Mi Contexto

- Dato 1: ...
- Dato 2: ...
"""
```

### Paso 2: Registrar en manager

`termuxcode/connection/claude_md_manager.py`:

```python
# Agregar al inicio con los otros imports
from termuxcode.connection.context import mi_provider  # noqa: F401
```

### Paso 3: ¡Listo!

El provider se ejecutará automáticamente antes de cada query.

## Decorador `@register_context_provider`

```python
@register_context_provider(
    name="nombre",           # Para logs/debugging
    priority=100,            # Menor = se ejecuta primero
    requires_git=False,      # True si necesita repo git
)
def mi_funcion(cwd: str) -> str:
    return "### Mi Sección\n\nContenido"
```

## Prioridades

| Valor | Uso típico |
|-------|------------|
| 1-10 | Información crítica (debe ir primero) |
| 10-30 | Estructura del proyecto (filetree, stats) |
| 30-50 | Info de git/SCM |
| 50-100 | Contexto secundario o custom |
| 100+ | Información opcional |

## Excluir Providers sin Git

Si el proyecto no tiene git, los providers con `requires_git=True` se saltan automáticamente.

## Debugging

Para ver qué providers están registrados:

```python
from termuxcode.connection.claude_md_manager import list_active_providers

providers = list_active_providers()
for p in providers:
    print(f"{p['name']} (priority={p['priority']}, git={p['requires_git']})")
```

## Output en CLAUDE.md

```markdown
## Project Context (Auto-generated)

> **Nota**: Esta sección se genera automáticamente antes de cada query.
> No la edites manualmente ya que se sobrescribirá.
>
> Providers activos: generate_filetree_context, generate_stats_context, generate_git_context

### File Tree

```
termuxcode/
├── ...
```

### Project Stats

- **Python files**: 42
- **JS/TS files**: 15
- **Total tracked files**: 57

### Git Info

- **Branch**: `main`
  - 9fe6877 feat: migración Vue 3 completa
  - 2c7d8f1 feat: MCP per-tab state
  - 7dd1b03 feat: wake lock + reconexión

---
```
