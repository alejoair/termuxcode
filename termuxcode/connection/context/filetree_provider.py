"""Context provider: File tree del proyecto."""

from __future__ import annotations

from pathlib import Path

from termuxcode.connection.context import register_context_provider


_EXCLUDE_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv",
    "dist", "build", ".pytest_cache", ".mypy_cache",
    "target", ".cargo", "bin", "obj",
    "site-packages", "dist-packages", "lib-dynload",
    "Lib", "Include", "Scripts", "tcl", "tk",
}


def _looks_like_python_install(path: Path) -> bool:
    """True si el directorio parece una instalación de Python (PythonXYZ, pythonX.Y)."""
    name = path.name
    lower = name.lower()
    if lower.startswith("python") and len(name) > 6:
        suffix = name[6:]
        return suffix[:1].isdigit() or suffix[:1] in ("3", "2")
    return False


@register_context_provider("filetree", priority=10)
def generate_filetree_context(cwd: str) -> str:
    max_depth = 3
    exclude_files = {".DS_Store", "Thumbs.db", "*.pyc"}

    def build_tree(path: Path, prefix: str = "", depth: int = 0) -> list[str]:
        if depth > max_depth:
            return []
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return []

        lines = []
        for i, entry in enumerate(entries):
            if entry.name.startswith('.') and entry.name not in {'.github', '.gitignore', '.env.example'}:
                continue

            if entry.is_dir():
                if entry.name in _EXCLUDE_DIRS or _looks_like_python_install(entry):
                    continue
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}/")
                child_prefix = prefix + ("    " if is_last else "│   ")
                lines.extend(build_tree(entry, child_prefix, depth + 1))
            else:
                if any(entry.name.endswith(ext.removeprefix('*')) for ext in exclude_files if '*' in ext):
                    continue
                if entry.name in exclude_files:
                    continue
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{entry.name}")

        return lines

    root = Path(cwd)
    if not root.exists():
        return f"### File Tree\n\n⚠️ Error: Directorio no encontrado: {cwd}"

    tree_lines = [root.name + "/"]
    tree_lines.extend(build_tree(root))
    tree_str = "\n".join(tree_lines)

    return f"""### File Tree

```
{tree_str}
```"""


def _iter_project_files(cwd: str, pattern: str):
    """rglob excluyendo site-packages e instalaciones de Python."""
    root = Path(cwd)
    for p in root.rglob(pattern):
        parts = p.relative_to(root).parts
        if any(
            part in _EXCLUDE_DIRS or _looks_like_python_install(Path(part))
            for part in parts
        ):
            continue
        yield p


@register_context_provider("stats", priority=20)
def generate_stats_context(cwd: str) -> str:
    try:
        py_files = list(_iter_project_files(cwd, "*.py"))
        js_files = list(_iter_project_files(cwd, "*.js")) + list(_iter_project_files(cwd, "*.ts"))
        total_files = len(py_files) + len(js_files)

        return f"""### Project Stats

- **Python files**: {len(py_files)}
- **JS/TS files**: {len(js_files)}
- **Total tracked files**: {total_files}"""
    except Exception:
        return "### Project Stats\n\n⚠️ No se pudieron calcular las estadísticas"
