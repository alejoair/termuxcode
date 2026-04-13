# Análisis: Uso de features LSP de ty en termuxcode

**Fecha:** 2026-04-13
**Versión ty:** 0.0.29

## Métodos LSP de ty que tu código SÍ usa

| Método LSP | Archivo | Función | Uso |
|------------|---------|---------|-----|
| `textDocument/documentSymbol` | `features.py` | `get_symbols()` | Extrae símbolos del archivo (classes, functions) |
| `textDocument/hover` | `features.py` | `get_hover()` | Obtiene tipos y signatures de símbolos |
| `textDocument/references` | `features.py` | `get_references()` | Encuentra usos de símbolos en el codebase |
| `textDocument/typeDefinition` | `features.py` | `get_type_definition()` | Encuentra definiciones de tipos |
| `textDocument/inlayHint` | `features.py` | `get_inlay_hints()` | Tipos inferidos inline |
| `textDocument/diagnostic` | `diagnostics.py` | `handle_notification()` | Recibe errores de tipo en tiempo real |

## Métodos LSP que tu código PERO ty NO soporta

| Método LSP | Archivo | Función | Estado |
|------------|---------|---------|--------|
| `textDocument/typeHierarchy` | `features.py` | `get_type_hierarchy()` | ❌ **No soportado por ty** - Retorna vacío |
| `textDocument/formatting` | `features.py` | `format_file()` | ❌ **No soportado por ty** - Retorna None |

## Cómo se usa cada feature en tu código

### 1. `textDocument/documentSymbol` ✅
- **Usado en:** `LspAnalyzer.analyze_file()` → `format_signatures()`, `format_methods()`
- **Propósito:** Obtener outline del archivo (classes, functions, variables)
- **Código:** `formatters.py:27-48`, `formatters.py:65-90`

### 2. `textDocument/hover` ✅
- **Usado en:** `LspAnalyzer.analyze_file()` → `format_signatures()`, `format_methods()`
- **Propósito:** Obtener tipos completos y signatures de funciones
- **Código:** `formatters.py:51-62`, `formatters.py:93-102`

### 3. `textDocument/references` ✅
- **Usado en:** `LspAnalyzer.analyze_file()` → `format_references()`
- **Propósito:** Encontrar dónde se usan clases y funciones
- **Código:** `formatters.py:105-143`

### 4. `textDocument/typeDefinition` ✅
- **Usado en:** `LspAnalyzer.analyze_file()` → `format_type_definitions()`
- **Propósito:** Encontrar dónde está definido el tipo de un símbolo
- **Código:** `formatters.py:219-250`

### 5. `textDocument/inlayHint` ✅
- **Usado en:** `LspAnalyzer.analyze_file()` → `format_inlay_hints()`
- **Propósito:** Mostrar tipos inferidos de variables sin anotación
- **Código:** `formatters.py:184-216`

### 6. `textDocument/diagnostic` ✅
- **Usado en:** `LspAnalyzer.validate_file()` + hooks PreToolUse/PostToolUse
- **Propósito:** Validar código antes de editar y mostrar errores después
- **Código:** `lsp_analyzer/analyzer.py:137-171`, `hooks.py:58-140`

### 7. `textDocument/typeHierarchy` ❌ NO SOPORTADO
- **Usado en:** `LspAnalyzer.analyze_file()` → `format_type_hierarchy()`
- **Problema:** ty no implementa este método
- **Impacto:** La sección "Type Hierarchy" del análisis siempre retorna vacío
- **Código:** `formatters.py:146-181`

### 8. `textDocument/formatting` ❌ NO SOPORTADO
- **Usado en:** `LSPClient.format_file()`
- **Problema:** ty no implementa formatting (recomienda usar Ruff)
- **Impacto:** Si llamas a `format_file()` con ty, retorna None
- **Código:** `features.py:171-189`

## Flujos donde se usan estos features

### Flujo 1: `analyze_file()` - PostToolUse Read Hook
```
analyze_file()
 ├─> get_symbols() [documentSymbol] ✅
 ├─> format_signatures() → get_hover() [hover] ✅
 ├─> format_methods() → get_hover() [hover] ✅
 ├─> format_references() → get_references() [references] ✅
 ├─> format_type_hierarchy() → get_type_hierarchy() [typeHierarchy] ❌
 ├─> format_inlay_hints() → get_inlay_hints() [inlayHint] ✅
 └─> format_type_definitions() → get_type_definition() [typeDefinition] ✅
```

### Flujo 2: `validate_file()` - PreToolUse Write|Edit Hooks
```
validate_file()
 └─> open_and_wait() / update_and_wait()
     └─> Espera publishDiagnostics [diagnostic push] ✅
```

### Flujo 3: `get_pre_edit_diagnostics()` - PreToolUse baseline
```
get_pre_edit_diagnostics()
 └─> get_cached_diagnostics() [diagnostic cache] ✅
```

## Recomendaciones

### 1. Remover `typeHierarchy` del análisis
El método `textDocument/typeHierarchy` no está soportado por ty. Puedes:
- Remover la llamada a `format_type_hierarchy()` de `analyze_file()`
- O hacer el call condicional: `if client.supports("textDocument/typeHierarchy"):`

### 2. Remover `format_file()` o delegar a Ruff
El método `textDocument/formatting` no está soportado por ty. Puedes:
- Remover `format_file()` de `LanguageFeatures` si no se usa
- O delegar a Ruff LSP server para formateo

### 3. Features de ty que NO estás usando

ty soporta estos features que tu código no usa actualmente:
- `textDocument/definition` - Go to definition
- `textDocument/declaration` - Go to declaration
- `textDocument/completion` - Code completions
- `textDocument/prepareRename` / `textDocument/rename` - Rename symbol
- `textDocument/selectionRange` - Selection range expansion
- `textDocument/signatureHelp` - Signature help (parameters popup)
- `textDocument/documentHighlight` - Highlight occurrences
- `textDocument/semanticTokens` - Semantic highlighting
- `textDocument/codeAction` - Quick fixes, add import
- `workspace/diagnostic` - Workspace-wide diagnostics
- `workspace/symbol` - Search symbols across workspace
- `notebookDocument/*` - Jupyter notebook support

## Resumen

**Features usados:** 6 de 13 (46%)
**Features no soportados por ty:** 2 (`typeHierarchy`, `formating`)
**Features de ty sin usar:** 7

Tu código aprovecha bien las capacidades de análisis de ty, pero hay 2 features que no funcionan por falta de soporte en ty.
