#!/usr/bin/env python3
"""Utilidades para conversión de paths y URIs LSP."""

import os
import urllib.parse
from pathlib import PurePosixPath, PureWindowsPath

# Mapeo de extensiones a Language IDs del protocolo LSP
LANGUAGE_IDS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascriptreact",
    ".ts": "typescript",
    ".tsx": "typescriptreact",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".lua": "lua",
}


def is_windows() -> bool:
    """Retorna True si el sistema operativo es Windows."""
    return os.name == "nt"


def file_path_to_uri(path: str) -> str:
    """Convierte una ruta de archivo a URI file://."""
    if is_windows():
        # Windows: file:///C:/path/to/file
        return "file:///" + str(PureWindowsPath(path)).replace("\\", "/")
    return "file://" + str(PurePosixPath(path))


def uri_to_file_path(uri: str) -> str:
    """Convierte una URI file:// a ruta de archivo."""
    parsed = urllib.parse.urlparse(uri)
    path = urllib.parse.unquote(parsed.path)
    if is_windows():
        # file:///C:/path → C:/path
        if path.startswith("/"):
            path = path[1:]
    return path


def extension_to_language_id(file_path: str) -> str:
    """Retorna el Language ID LSP para una extensión dada."""
    _, ext = os.path.splitext(file_path)
    return LANGUAGE_IDS.get(ext, "")
