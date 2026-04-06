#!/usr/bin/env python3
"""Configuración de servidores LSP y constantes."""

# Configuración de servidores LSP por extensión
# Cada extensión puede tener múltiples servidores (lista de comandos)
# Se lanzan todos los que estén instalados; el primero es el "principal" (para analyze)
SERVERS: dict[str, list[list[str]]] = {
    ".py": [
        ["ty", "server"],  # Astral's type checker (hover, refs, types)
        ["ruff", "server"],  # Astral's linter (diagnósticos ultra rápidos)
    ],
    ".ts": [["typescript-language-server", "--stdio"]],
    ".js": [["typescript-language-server", "--stdio"]],
    ".tsx": [["typescript-language-server", "--stdio"]],
    ".jsx": [["typescript-language-server", "--stdio"]],
    ".go": [["gopls"]],
}

# SymbolKind del protocolo LSP
SYMBOL_KINDS: dict[int, str] = {
    1: "File",
    2: "Module",
    3: "Namespace",
    4: "Package",
    5: "Class",
    6: "Method",
    7: "Property",
    8: "Field",
    9: "Constructor",
    10: "Enum",
    11: "Interface",
    12: "Function",
    13: "Variable",
    14: "Constant",
    15: "String",
    16: "Number",
    17: "Boolean",
    18: "Array",
    19: "Object",
    20: "Key",
    21: "Null",
    22: "EnumMember",
    23: "Struct",
    24: "Event",
    25: "Operator",
    26: "TypeParameter",
}

# Kinds significativos para análisis (Class, Method, Constructor, Interface, Function, Struct)
MEANINGFUL_KINDS = {5, 6, 9, 11, 12, 23}

# Kinds para references (Class, Function, Struct)
REFERENCE_KINDS = {5, 12, 23}

# Kinds para type definitions (Class, Function)
TYPE_DEF_KINDS = {5, 12}

# Límites configurables
MAX_REFERENCES_PER_SYMBOL = 8
MAX_SYMBOLS_FOR_REFS = 10
MAX_CLASSES_FOR_HIERARCHY = 3
MAX_SUBTYPES = 5
MAX_INLAY_HINTS = 10
MAX_TYPE_DEFS_PER_SYMBOL = 2
MAX_SYMBOLS_FOR_TYPE_DEFS = 5
