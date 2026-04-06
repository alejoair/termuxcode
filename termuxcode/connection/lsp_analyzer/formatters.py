#!/usr/bin/env python3
"""Formateadores de output para análisis LSP."""

import os

from termuxcode.connection.lsp import LSPClient, uri_to_file_path

from .config import (
    MAX_CLASSES_FOR_HIERARCHY,
    MAX_INLAY_HINTS,
    MAX_REFERENCES_PER_SYMBOL,
    MAX_SUBTYPES,
    MAX_SYMBOLS_FOR_REFS,
    MAX_SYMBOLS_FOR_TYPE_DEFS,
    MAX_TYPE_DEFS_PER_SYMBOL,
    MEANINGFUL_KINDS,
    REFERENCE_KINDS,
    TYPE_DEF_KINDS,
)
from .symbols import (
    extract_hover_content,
    get_sym_col,
    get_sym_line,
)


async def format_signatures(
    client: LSPClient, file_path: str, symbols: list[dict], source: str
) -> list[str]:
    """Formatea símbolos top-level con sus signatures (hover)."""
    top_syms = [
        s
        for s in symbols
        if ("location" in s or "range" in s) and s.get("kind") in MEANINGFUL_KINDS
    ]

    sig_lines = []
    for sym in top_syms:
        try:
            sig = await _format_symbol_with_hover(client, file_path, sym, source)
            if sig:
                sig_lines.append(sig)
        except Exception:
            from .symbols import format_symbol_bare

            sig_lines.append(format_symbol_bare(sym))

    return sig_lines


async def _format_symbol_with_hover(
    client: LSPClient, file_path: str, sym: dict, source: str
) -> str | None:
    """Formatea un símbolo con su hover (tipo/signature completa)."""
    line = get_sym_line(sym)
    col = get_sym_col(sym, source)
    hover = await client.get_hover(file_path, line, col)
    if hover:
        hover_text = extract_hover_content(hover)
        if hover_text:
            return f"L{line}: {hover_text}"
    return None


async def format_methods(
    client: LSPClient, file_path: str, symbols: list[dict], source: str
) -> list[str]:
    """Formatea métodos dentro de clases con sus signatures."""
    top_syms = [
        s
        for s in symbols
        if ("location" in s or "range" in s) and s.get("kind") in MEANINGFUL_KINDS
    ]
    classes = {s["name"] for s in top_syms if s.get("kind") == 5}  # Class

    method_lines = []
    for sym in top_syms:
        kind = sym.get("kind", 0)
        container = sym.get("containerName")
        if kind in (6, 9, 12) and container in classes:  # Method/Constructor/Function
            try:
                hover = await _safe_hover(client, file_path, sym, source)
                if hover:
                    method_lines.append(f"    L{get_sym_line(sym)}: {hover}")
                else:
                    method_lines.append(f"    L{get_sym_line(sym)}: {sym['name']}()")
            except Exception:
                method_lines.append(f"    L{get_sym_line(sym)}: {sym['name']}()")

    return method_lines


async def _safe_hover(
    client: LSPClient, file_path: str, sym: dict, source: str
) -> str | None:
    """Hover seguro que no lanza excepciones."""
    try:
        return await client.get_hover(
            file_path, get_sym_line(sym), get_sym_col(sym, source)
        )
    except Exception:
        return None


async def format_references(
    client: LSPClient, file_path: str, symbols: list[dict], source: str
) -> list[str]:
    """Formatea referencias cross-file de clases y funciones."""
    top_syms = [
        s
        for s in symbols
        if ("location" in s or "range" in s) and s.get("kind") in MEANINGFUL_KINDS
    ]

    ref_lines = []
    symbols_checked = 0
    for sym in top_syms:
        kind = sym.get("kind", 0)
        if kind not in REFERENCE_KINDS:
            continue
        if symbols_checked >= MAX_SYMBOLS_FOR_REFS:
            break
        try:
            refs = await client.get_references(
                file_path, get_sym_line(sym), get_sym_col(sym, source)
            )
            if not refs:
                continue
            name = sym["name"]
            ref_lines.append(f"  {name} -> {len(refs)} usage(s):")
            for r in refs[:MAX_REFERENCES_PER_SYMBOL]:
                r_uri = r.get("uri", "")
                r_path = uri_to_file_path(r_uri)
                r_file = os.path.basename(r_path)
                r_line = r.get("range", {}).get("start", {}).get("line", "?")
                ref_lines.append(f"    {r_file} L{r_line}")
            if len(refs) > MAX_REFERENCES_PER_SYMBOL:
                ref_lines.append(f"    ... +{len(refs) - MAX_REFERENCES_PER_SYMBOL} more")
            symbols_checked += 1
        except Exception:
            continue

    return ref_lines


async def format_type_hierarchy(
    client: LSPClient, file_path: str, symbols: list[dict], source: str
) -> list[str]:
    """Formatea subtipos de clases."""
    top_syms = [
        s
        for s in symbols
        if ("location" in s or "range" in s) and s.get("kind") in MEANINGFUL_KINDS
    ]
    class_syms = [s for s in top_syms if s.get("kind") == 5]  # Class

    hierarchy_lines = []
    for sym in class_syms[:MAX_CLASSES_FOR_HIERARCHY]:
        try:
            hierarchy = await client.get_type_hierarchy(
                file_path,
                get_sym_line(sym),
                get_sym_col(sym, source),
            )
            if hierarchy and hierarchy.get("subtypes"):
                subs = hierarchy["subtypes"]
                if subs:
                    name = sym["name"]
                    hierarchy_lines.append(f"  {name} subtypes:")
                    for sub in subs[:MAX_SUBTYPES]:
                        sub_name = sub.get("name", "?")
                        sub_uri = sub.get("uri", "")
                        sub_path = uri_to_file_path(sub_uri)
                        sub_file = os.path.basename(sub_path)
                        hierarchy_lines.append(f"    {sub_name} ({sub_file})")
                    if len(subs) > MAX_SUBTYPES:
                        hierarchy_lines.append(f"    ... +{len(subs) - MAX_SUBTYPES} more")
        except Exception:
            continue

    return hierarchy_lines


async def format_inlay_hints(client: LSPClient, file_path: str) -> list[str]:
    """Formatea tipos inferidos de variables/parámetros."""
    try:
        hints = await client.get_inlay_hints(file_path)
        if not hints:
            return []

        hint_lines = []
        for hint in hints[:MAX_INLAY_HINTS]:
            pos = hint.get("position", {})
            line_num = pos.get("line", "?")
            label = hint.get("label", "")
            kind = hint.get("kind", 0)
            # kind 1 = Type, kind 2 = Parameter
            hint_type = "type" if kind == 1 else "param"
            # ty retorna label como lista de objetos con 'value'
            if isinstance(label, list):
                parts = []
                for item in label:
                    if isinstance(item, dict):
                        parts.append(item.get("value", ""))
                    elif isinstance(item, str):
                        parts.append(item)
                label = "".join(parts)
            # Limpiar: sacar ": " inicial si es type hint
            if hint_type == "type" and label.startswith(": "):
                label = label[2:]
            if label:
                hint_lines.append(f"  L{line_num}: {hint_type} → {label}")

        return hint_lines
    except Exception:
        return []


async def format_type_definitions(
    client: LSPClient, file_path: str, symbols: list[dict], source: str
) -> list[str]:
    """Formatea definiciones de tipos de símbolos."""
    top_syms = [
        s
        for s in symbols
        if ("location" in s or "range" in s) and s.get("kind") in MEANINGFUL_KINDS
    ]

    typedef_lines = []
    for sym in top_syms[:MAX_SYMBOLS_FOR_TYPE_DEFS]:
        kind = sym.get("kind", 0)
        if kind not in TYPE_DEF_KINDS:
            continue
        try:
            type_defs = await client.get_type_definition(
                file_path, get_sym_line(sym), get_sym_col(sym, source)
            )
            if type_defs:
                name = sym["name"]
                for td in type_defs[:MAX_TYPE_DEFS_PER_SYMBOL]:
                    td_uri = td.get("uri", "")
                    if td_uri.startswith("file://"):
                        td_path = uri_to_file_path(td_uri)
                        td_file = os.path.basename(td_path)
                        td_line = td.get("range", {}).get("start", {}).get("line", "?")
                        typedef_lines.append(f"  {name} type from: {td_file} L{td_line}")
        except Exception:
            continue

    return typedef_lines
