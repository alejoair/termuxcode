# Recomendación: Tools LSP para mejorar Claude Code

**Fecha:** 2026-04-13

## Features de ty que NO usas → ¿Vale la pena como tools?

### TOP PRIORIDAD: Las que más ayudarían a Claude

| Feature | Método | Tool propuesta | Valor para Claude |
|---------|--------|----------------|-------------------|
| **🥇 Rename** | `textDocument/rename` | `rename_symbol` | Refactorizaciones seguras en todo el codebase |
| **🥈 Quick Fix** | `textDocument/codeAction` | `quick_fix` | Auto-corregir errores, add imports |
| **🥉 Go to Definition** | `textDocument/definition` | `find_definition` | Entender código de terceros, stdlib |

---

## 1. 🔥 `rename_symbol` (TOP PRIORITY)

### Qué hace
Renombra una clase, función o variable en **todo el codebase** de forma segura (usa LSP para encontrar todas las referencias).

### Por qué ayuda a Claude
- **Problema actual:** Cuando Claude quiere renombrar algo, usa Edit tool pero puede:
  - Perder referencias en otros archivos
  - Romper código si hay colisión de nombres
  - No saber todos los lugares donde se usa
- **Solución:** LSP ya tiene el grafo de referencias completo, el rename es atómico y seguro

### Ejemplo de uso
```python
# Claude quiere renombrar "process_data" → "process_items"

# SIN tool (riesgoso):
Edit(old_string="def process_data(", new_string="def process_items(")
# Puede perder usos en otros archivos

# CON tool (seguro):
rename_symbol(
    file_path="src/analyzer.py",
    line=42,
    col=12,
    new_name="process_items"
)
# Renombra en todos los archivos del proyecto
```

### Implementación
```python
@tool(
    "rename_symbol",
    "Rename a class, function, or variable across the entire codebase safely. Use this when you need to refactor names - the LSP will find ALL references and rename them atomically.",
    {"file_path": str, "line": int, "col": int, "new_name": str}
)
async def rename_symbol(args: dict[str, Any]) -> dict[str, Any]:
    """Renombra un símbolo en todo el codebase usando LSP."""
    file_path = normalize_path(args["file_path"])
    line = args["line"]
    col = args["col"]
    new_name = args["new_name"]

    if not _lsp_manager:
        return {"content": [{"type": "text", "text": "Error: LSP not available"}]}

    client = _lsp_manager.get_client(file_path)
    if not client:
        return {"content": [{"type": "text", "text": "Error: No LSP for this file"}]}

    # textDocument/prepareRename - verifica si se puede renombrar
    prepare_result = await client.prepare_rename(file_path, line, col)
    if not prepare_result:
        return {"content": [{"type": "text", "text": "Error: Cannot rename this symbol"}]}

    # textDocument/rename - ejecuta el rename
    edits = await client.rename(file_path, line, col, new_name)

    if not edits:
        return {"content": [{"type": "text", "text": "No changes made"}]}

    # edits es: {"file_path": [TextEdit, ...], ...}
    lines = [f"Renamed symbol to '{new_name}':"]
    for path, text_edits in edits.items():
        lines.append(f"  {path}: {len(text_edits)} edit(s)")

    return {"content": [{"type": "text", "text": "\n".join(lines)}]}
```

### Notas
- Necesitas agregar `prepare_rename()` y `rename()` a `LanguageFeatures`
- ty soporta `textDocument/prepareRename` + `textDocument/rename`

---

## 2. 🔥 `quick_fix` (HIGH VALUE)

### Qué hace
Aplica correcciones automáticas del LSP:
- Auto-importar símbolos faltantes
- Corregir errores comunes
- Implementar stubs de métodos faltantes

### Por qué ayuda a Claude
- **Problema actual:** Claude escribe código que necesita imports que olvida agregar
- **Solución:** El LSP detecta esto y puede aplicar el fix automáticamente

### Ejemplo de uso
```python
# Claude escribe código sin import
result = List[str]()  # ❌ Missing import

# LSP detecta y quick_fix agrega:
from typing import List
result = List[str]  # ✅
```

### Implementación
```python
@tool(
    "quick_fix",
    "Apply automatic fixes from the LSP: add missing imports, implement stubs, or fix common errors. Use this when code has diagnostics that suggest quick fixes.",
    {"file_path": str, "line": int, "col": int}
)
async def quick_fix(args: dict[str, Any]) -> dict[str, Any]:
    """Aplica quick fixes del LSP."""
    file_path = normalize_path(args["file_path"])
    line = args.get("line")
    col = args.get("col")

    if not _lsp_manager:
        return {"content": [{"type": "text", "text": "Error: LSP not available"}]}

    client = _lsp_manager.get_client(file_path)
    if not client:
        return {"content": [{"type": "text", "text": "Error: No LSP for this file"}]}

    # textDocument/codeAction - obtener fixes disponibles
    fixes = await client.get_code_actions(file_path, line, col)

    if not fixes:
        return {"content": [{"type": "text", "text": "No quick fixes available"}]}

    # Aplicar el primer fix (usualmente el más relevante)
    fix = fixes[0]
    edit = fix.get("edit")

    if not edit:
        return {"content": [{"type": "text", "text": "Fix has no edits"}]}

    # Aplicar los edits
    # ... (lógica similar a rename)

    return {"content": [{"type": "text", "text": f"Applied fix: {fix.get('title', '')}"}]}
```

### Notas
- Necesitas agregar `get_code_actions()` a `LanguageFeatures`
- ty soporta `textDocument/codeAction`

---

## 3. 🔍 `find_definition` (MEDIUM VALUE)

### Qué hace
Encuentra dónde está definido un símbolo (puede ser en otro archivo del proyecto o en stdlib).

### Por qué ayuda a Claude
- **Uso:** Cuando Claude necesita entender cómo funciona una función de terceros
- **Limitación actual:** Solo puede leer el archivo actual, no "salta" a definiciones externas

### Ejemplo de uso
```python
# Claude ve código que llama a una función oscura
result = process_items(data)

# ¿Qué hace process_items?
find_definition(file_path="src/main.py", line=10, col=12)
# → Va a donde está definido y Claude puede leerlo
```

### Implementación
```python
@tool(
    "find_definition",
    "Find where a symbol is defined. Use this to understand how a function or class works - jumps to its definition even if it's in another file.",
    {"file_path": str, "line": int, "col": int}
)
async def find_definition(args: dict[str, Any]) -> dict[str, Any]:
    """Encuentra la definición de un símbolo usando LSP."""
    file_path = normalize_path(args["file_path"])
    line = args["line"]
    col = args["col"]

    if not _lsp_manager:
        return {"content": [{"type": "text", "text": "Error: LSP not available"}]}

    client = _lsp_manager.get_client(file_path)
    if not client:
        return {"content": [{"type": "text", "text": "Error: No LSP for this file"}]}

    # textDocument/definition
    locations = await client.get_definition(file_path, line, col)

    if not locations:
        return {"content": [{"type": "text", "text": "No definition found"}]}

    lines = [f"Definition found at:"]
    for loc in locations[:3]:  # Primeras 3 definiciones
        uri = loc.get("uri", "")
        path = uri_to_file_path(uri)
        rng = loc.get("range", {})
        l = rng.get("start", {}).get("line", "?")
        lines.append(f"  {path}:{l}")

    return {"content": [{"type": "text", "text": "\n".join(lines)}]}
```

### Notas
- Necesitas agregar `get_definition()` a `LanguageFeatures`
- ty soporta `textDocument/definition`

---

## LOW PRIORITY: Features que NO recomiendo

| Feature | Por qué NO vale la pena |
|---------|------------------------|
| `completion` | Claude ya sugiere código, no necesita autocompletado |
| `signatureHelp` | Claude ya conoce signatures, no es útil como tool |
| `documentHighlight` | Redundante con `get_references` (que ya usas) |
| `semanticTokens` | Es visual para el editor, no ayuda a Claude |
| `selectionRange` | Muy específico para UX del editor |

---

## Plan de Implementación

### Paso 1: Agregar métodos a `LanguageFeatures` (`features.py`)

```python
async def prepare_rename(
    self, file_path: str, line: int, col: int
) -> dict | None:
    """textDocument/prepareRename -> verifica si se puede renombrar."""
    if not self._supports("textDocument/prepareRename"):
        return None
    uri = file_path_to_uri(file_path)
    result = await self._transport.send_request(
        "textDocument/prepareRename",
        {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": col},
        },
    )
    return result

async def rename(
    self,
    file_path: str,
    line: int,
    col: int,
    new_name: str,
) -> dict[str, list[dict]] | None:
    """textDocument/rename -> edits de renombrado.

    Retorna: {file_uri: [TextEdit, ...], ...}
    """
    if not self._supports("textDocument/rename"):
        return None
    uri = file_path_to_uri(file_path)
    result = await self._transport.send_request(
        "textDocument/rename",
        {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": col},
            "newName": new_name,
        },
    )
    if not result or "changes" not in result:
        return None
    return result["changes"]

async def get_definition(
    self,
    file_path: str,
    line: int,
    col: int,
) -> list[dict]:
    """textDocument/definition -> lista de Location."""
    if not self._supports("textDocument/definition"):
        return []
    uri = file_path_to_uri(file_path)
    result = await self._transport.send_request(
        "textDocument/definition",
        {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": col},
        },
    )
    if isinstance(result, list):
        return result
    return []

async def get_code_actions(
    self,
    file_path: str,
    line: int | None = None,
    col: int | None = None,
) -> list[dict]:
    """textDocument/codeAction -> lista de CodeAction."""
    if not self._supports("textDocument/codeAction"):
        return []
    uri = file_path_to_uri(file_path)

    range_val = (
        {
            "start": {"line": line, "character": col},
            "end": {"line": line, "character": col},
        }
        if line is not None and col is not None
        else None
    )

    result = await self._transport.send_request(
        "textDocument/codeAction",
        {
            "textDocument": {"uri": uri},
            "range": range_val,
            "context": {"diagnostics": []},
        },
    )
    if isinstance(result, list):
        return result
    return []
```

### Paso 2: Agregar capability checks en `LSPClient`

```python
CAPABILITY_MAP = {
    # ... existing ...
    "textDocument/prepareRename": "renameProvider",
    "textDocument/rename": "renameProvider",
    "textDocument/definition": "definitionProvider",
    "textDocument/codeAction": "codeActionProvider",
}
```

### Paso 3: Crear las 3 tools

1. `termuxcode/custom_tools/tools/rename_symbol.py`
2. `termuxcode/custom_tools/tools/quick_fix.py`
3. `termuxcode/custom_tools/tools/find_definition.py`

### Paso 4: Registrar en `__init__.py`

```python
from termuxcode.custom_tools.tools.rename_symbol import rename_symbol
from termuxcode.custom_tools.tools.quick_fix import quick_fix
from termuxcode.custom_tools.tools.find_definition import find_definition

TOOLS = [
    # ... existing ...
    type_check,
    rename_symbol,
    quick_fix,
    find_definition,
]
```

---

## Impacto Esperado

| Tool | Problema que resuelve | Frecuencia de uso |
|------|---------------------|-------------------|
| `rename_symbol` | Refactorizaciones seguras | Alta (cada vez que Claude quiere mejorar nombres) |
| `quick_fix` | Imports faltantes, errores comunes | Muy alta (cada edición de código) |
| `find_definition` | Entender código externo | Media (cuando explora código nuevo) |

**Recomendación:** Empezar con `quick_fix` (mayor ROI) y luego `rename_symbol`.
