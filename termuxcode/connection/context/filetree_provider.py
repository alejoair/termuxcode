"""Context provider: File tree del proyecto."""

from __future__ import annotations

from pathlib import Path

from termuxcode.connection.context import register_context_provider


@register_context_provider("filetree", priority=10)
def generate_filetree_context(cwd: str) -> str:
    """Genera un árbol de archivos del proyecto.

    Args:
        cwd: Directorio raíz del proyecto

    Returns:
        String con el árbol de archivos en formato markdown
    """
    max_depth = 3
    exclude_dirs = {
        "node_modules", ".git", "__pycache__", "venv", ".venv",
        "dist", "build", ".pytest_cache", ".mypy_cache",
        "target", ".cargo", "bin", "obj"
    }
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
                if entry.name in exclude_dirs:
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


@register_context_provider("stats", priority=20)
def generate_stats_context(cwd: str) -> str:
    """Genera estadísticas del proyecto.

    Args:
        cwd: Directorio raíz del proyecto

    Returns:
        String con estadísticas en formato markdown
    """
    try:
        py_files = list(Path(cwd).rglob("*.py"))
        js_files = list(Path(cwd).rglob("*.js")) + list(Path(cwd).rglob("*.ts"))
        total_files = len(py_files) + len(js_files)

        return f"""### Project Stats

- **Python files**: {len(py_files)}
- **JS/TS files**: {len(js_files)}
- **Total tracked files**: {total_files}"""
    except Exception:
        return "### Project Stats\n\n⚠️ No se pudieron calcular las estadísticas"
