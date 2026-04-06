#!/usr/bin/env python3
"""Helpers para manipular símbolos LSP."""

from .config import SYMBOL_KINDS


def get_range(sym: dict) -> dict | None:
    """Extrae el range de un símbolo (location.range o range directo).

    pylsp retorna SymbolInformation[] con ``location.range``;
    otros servers (tsserver, gopls) pueden usar ``range`` directo.
    """
    loc = sym.get("location")
    if isinstance(loc, dict):
        rng = loc.get("range")
        if isinstance(rng, dict):
            return rng
    rng = sym.get("range")
    if isinstance(rng, dict):
        return rng
    return None


def get_sym_line(sym: dict) -> int:
    """Extrae línea de inicio de un símbolo (0-based)."""
    rng = get_range(sym)
    if rng is None:
        return 0
    start = rng.get("start")
    if start is None:
        return 0
    return start.get("line", 0)


def get_sym_col(sym: dict, source: str = "") -> int:
    """Extrae columna del nombre del símbolo buscando en el source.

    pylsp retorna SymbolInformation[] con ``location.range`` que apunta
    al inicio de la línea (columna 0), no al nombre. Buscamos el nombre
    en el source para obtener la columna correcta para hover.

    Args:
        sym: Símbolo del LSP con 'name' y 'location.range'
        source: Contenido del archivo (opcional para backward compatibility)
    """
    rng = get_range(sym)
    if rng is None:
        return 0
    start = rng.get("start")
    if start is None:
        return 0
    line_idx = start.get("line", 0)
    name = sym.get("name", "")

    # Si tenemos source, buscar el nombre en la línea
    if source and name:
        lines = source.split("\n")
        if line_idx < len(lines):
            line_text = lines[line_idx]
            col = line_text.find(name)
            if col >= 0:
                return col

    # Fallback: usar columna del range (generalmente 0)
    return start.get("character", 0)


def extract_hover_content(hover: str) -> str | None:
    """Extrae contenido útil del hover, manejando formatos de diferentes LSPs.

    ty retorna bloques ```xml <type>...</type> ```
    pylsp retorna texto plano con la firma
    """
    if not hover:
        return None

    hover = hover.strip()

    # Si hay bloque de código, extraer contenido
    if hover.startswith("```"):
        lines = hover.split("\n")
        # Saltar primera línea (```xml o ```python)
        content_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block and line.strip():
                content_lines.append(line.strip())

        if content_lines:
            # Tomar primera línea significativa
            return content_lines[0]

    # Fallback: primera línea no vacía
    for line in hover.split("\n"):
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("```"):
            return cleaned

    return None


def diag_key(diag: dict) -> str | None:
    """Clave para comparar diagnósticos por mensaje (sin línea).

    Usa solo el mensaje para evitar falsos positivos cuando un edit
    agrega/remueve líneas y los diagnósticos preexistentes shift de línea.
    """
    msg = diag.get("message", "")
    return msg if msg else None


def format_symbol_bare(sym: dict) -> str:
    """Formatea un símbolo sin hover (fallback)."""
    kind_name = SYMBOL_KINDS.get(sym.get("kind", 0), "Unknown")
    line = get_sym_line(sym)
    return f"L{line}: [{kind_name}] {sym['name']}"
