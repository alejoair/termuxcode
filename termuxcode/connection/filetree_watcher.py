#!/usr/bin/env python3
"""Generación del filetree como JSON para el frontend."""

from __future__ import annotations

from pathlib import Path

from termuxcode.ws_config import logger

EXCLUDE_DIRS = frozenset({
    "node_modules", ".git", "__pycache__", "venv", ".venv",
    "dist", "build", ".pytest_cache", ".mypy_cache",
    "target", ".cargo", "bin", "obj",
})

EXCLUDE_FILES = frozenset({".DS_Store", "Thumbs.db"})

EXCLUDE_EXTENSIONS = frozenset({".pyc"})

ALLOWED_HIDDEN = frozenset({".github", ".gitignore", ".env.example"})


def generate_filetree_json(cwd: str, max_depth: int = 4) -> list[dict]:
    """Genera el filetree como lista de nodos JSON.

    Returns:
        Lista de nodos: [{name, path, type: "dir"|"file", children?: [...]}]
        Los dirs tienen ``children``, los files no.
        Ordenados: dirs primero, luego files, ambos alfabético case-insensitive.
    """
    root = Path(cwd)
    if not root.exists():
        return []

    try:
        return _build_node(root, "", max_depth)
    except Exception as e:
        logger.warning(f"Error generando filetree: {e}")
        return []


def _build_node(path: Path, parent_rel: str, max_depth: int, depth: int = 0) -> list[dict]:
    """Construye la lista de nodos hijos de un directorio."""
    if depth >= max_depth:
        return []

    try:
        entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except (PermissionError, OSError):
        return []

    nodes = []
    for entry in entries:
        # Filtro hidden
        if entry.name.startswith('.') and entry.name not in ALLOWED_HIDDEN:
            continue

        rel = f"{parent_rel}/{entry.name}" if parent_rel else entry.name

        if entry.is_dir():
            if entry.name in EXCLUDE_DIRS:
                continue
            children = _build_node(entry, rel, max_depth, depth + 1)
            nodes.append({
                "name": entry.name,
                "path": rel,
                "type": "dir",
                "children": children,
            })
        else:
            if entry.name in EXCLUDE_FILES:
                continue
            if entry.suffix in EXCLUDE_EXTENSIONS:
                continue
            nodes.append({
                "name": entry.name,
                "path": rel,
                "type": "file",
            })

    return nodes
