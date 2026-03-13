# TermuxCode

Una interfaz TUI (Terminal User Interface) interactiva para chatear con Claude Code en Termux.

## Requisitos

**Claude Code debe estar instalado primero.** En Termux:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Una vez que Claude Code esté funcionando, instala TermuxCode:

```bash
pip install termuxcode
```

## Uso

```bash
termuxcode
```

Opciones:
- `--dev`: Modo desarrollo con devtools y debug
- `--cwd <directorio>`: Especificar directorio de trabajo

## Por qué TermuxCode

- **Multi-sesión con tabs** - Maneja múltiples conversaciones en paralelo con `Ctrl+N` y `Ctrl+W`
- **Historial persistente** - Cada sesión guarda su historial automáticamente
- **Interfaz moderna** - TUI responsive con soporte markdown y syntax highlighting
- **Diseñado para móvil** - Optimizado para pantallas de Termux en Android
- **Cero configuración** - Funciona out of the box con Claude Code

## Atajos de teclado

| Atajo | Acción |
|-------|--------|
| `Ctrl+N` | Nueva sesión |
| `Ctrl+W` | Cerrar sesión actual |

## Desarrollo

```bash
# Clonar y instalar en modo desarrollo
git clone https://github.com/tu-usuario/termuxcode.git
cd termuxcode
pip install -e ".[dev]"

# Ejecutar la TUI
textual run src/termuxcode/tui.py

# Tests
pytest

# Formato y lint
ruff format .
ruff check .
```

## Licencia

MIT
