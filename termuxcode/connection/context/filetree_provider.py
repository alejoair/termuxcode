"""Context provider: File tree del proyecto (gitignore-aware)."""

from __future__ import annotations

from pathlib import Path

import pathspec

from termuxcode.connection.context import register_context_provider


def _load_spec(root: Path) -> pathspec.PathSpec:
    """Carga y combina todos los .gitignore desde root hacia abajo (primer nivel)."""
    patterns: list[str] = []
    for gitignore in root.rglob(".gitignore"):
        try:
            patterns.extend(gitignore.read_text(errors="ignore").splitlines())
        except OSError:
            pass
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def _is_ignored(path: Path, root: Path, spec: pathspec.PathSpec) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    rel_str = str(rel).replace("\\", "/")
    if path.is_dir():
        rel_str += "/"
    return spec.match_file(rel_str)


@register_context_provider("filetree", priority=10)
def generate_filetree_context(cwd: str) -> str:
    root = Path(cwd)
    if not root.exists():
        return f"### File Tree\n\n⚠️ Error: Directorio no encontrado: {cwd}"

    spec = _load_spec(root)
    max_depth = 3

    def build_tree(path: Path, prefix: str = "", depth: int = 0) -> list[str]:
        if depth > max_depth:
            return []
        try:
            entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return []

        visible = [
            e for e in entries
            if not _is_ignored(e, root, spec)
            and not (e.name.startswith(".") and e.name not in {".github", ".gitignore", ".env.example"})
        ]

        lines = []
        for i, entry in enumerate(visible):
            is_last = i == len(visible) - 1
            connector = "└── " if is_last else "├── "
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                child_prefix = prefix + ("    " if is_last else "│   ")
                lines.extend(build_tree(entry, child_prefix, depth + 1))
            else:
                lines.append(f"{prefix}{connector}{entry.name}")

        return lines

    tree_lines = [root.name + "/"]
    tree_lines.extend(build_tree(root))
    tree_str = "\n".join(tree_lines)

    return f"""### File Tree

```
{tree_str}
```"""


@register_context_provider("stats", priority=20)
def generate_stats_context(cwd: str) -> str:
    try:
        root = Path(cwd)
        spec = _load_spec(root)

        py_files = [
            p for p in root.rglob("*.py")
            if not _is_ignored(p, root, spec)
        ]
        js_files = [
            p for p in root.rglob("*.js") + root.rglob("*.ts")
            if not _is_ignored(p, root, spec)
        ]
        total_files = len(py_files) + len(js_files)

        return f"""### Project Stats

- **Python files**: {len(py_files)}
- **JS/TS files**: {len(js_files)}
- **Total tracked files**: {total_files}"""
    except Exception:
        return "### Project Stats\n\n⚠️ No se pudieron calcular las estadísticas"
