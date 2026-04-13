# Capabilidades LSP de ty

**Versión:** 0.0.29 (438a78d68 2026-04-05)
**Repo:** https://github.com/astral-sh/ty/
**Descripción:** Type checker para Python escrito en Rust con servidor LSP integrado.

## Comando LSP

```bash
ty server  # Inicia el servidor LSP en stdin/stdout
```

## Features Soportados

### Core Features

| Capacidad | Método LSP | Descripción |
|-----------|------------|-------------|
| **Diagnostics** | `textDocument/diagnostic` | Reporta errores de tipo en tiempo real |
| | `workspace/diagnostic` | Diagnósticos a nivel de workspace |
| **Go to Definition** | `textDocument/definition` | Navega a definiciones, resuelve imports |
| **Go to Declaration** | `textDocument/declaration` | Navega a declaración (ej. stub files) |
| **Go to Type Definition** | `textDocument/typeDefinition` | Navega al tipo de un símbolo |
| **Find References** | `textDocument/references` | Encuentra todos los usos de un símbolo |
| **Document Symbols** | `textDocument/documentSymbol` | Outline del archivo actual |
| **Workspace Symbols** | `workspace/symbol` | Búsqueda de símbolos en todo el proyecto |
| **Completions** | `textDocument/completion` | Autocompletado con auto-import |

### Advanced Features

| Capacidad | Método LSP | Descripción |
|-----------|------------|-------------|
| **Rename** | `textDocument/prepareRename` | Prepara renombrado seguro |
| | `textDocument/rename` | Renombra símbolos en todo el codebase |
| **Quick Fixes** | `textDocument/codeAction` | Correciones automáticas |
| **Add Import** | `textDocument/codeAction` | Agrega imports faltantes |
| **Selection Range** | `textDocument/selectionRange` | Expande/contrae selección por sintaxis |
| **Hover** | `textDocument/hover` | Muestra tipo, docstring, signatures |
| **Inlay Hints** | `textDocument/inlayHint` | Type hints inline, nombres de parámetros |
| **Signature Help** | `textDocument/signatureHelp` | Muestra parámetros al llamar función |
| **Document Highlight** | `textDocument/documentHighlight` | Resalta ocurrencias del símbolo |
| **Semantic Tokens** | `textDocument/semanticTokens` | Syntax highlighting semántico |
| **Notebook Support** | `notebookDocument/*` | Soporte para Jupyter `.ipynb` |

## Features NO Soportados

- `callHierarchy/*`
- `textDocument/codeLens`
- `textDocument/documentColor`
- `textDocument/documentLink`
- `textDocument/foldingRange`
- `textDocument/implementation`
- `textDocument/onTypeFormatting`
- `textDocument/rangeFormatting`
- `typeHierarchy/*`
- `workspace/willRenameFiles`

**Nota:** Para formateo, ty recomienda usar **Ruff**.

## Referencias

- [Repo oficial](https://github.com/astral-sh/ty/)
- [Documentación en DeepWiki](https://deepwiki.com/search/what-lsp-capabilitiesfeatures_886337ab-cf55-4540-b8c2-3d80996ae4d5)
