#!/usr/bin/env python3
"""Motor de análisis semántico Python usando Jedi + ast + pyflakes."""

import ast
import os
from pathlib import Path

from termuxcode.ws_config import logger


class JediAnalyzer:
    """Analiza código Python con Jedi para extraer información semántica.

    Provee tres funciones principales:
    - analyze_file(): contexto semántico completo (símbolos, tipos, imports)
    - validate_syntax(): validación sintáctica rápida con ast.parse()
    - check_file(): análisis lógico con pyflakes (si está instalado)
    """

    @staticmethod
    def is_python_file(file_path: str) -> bool:
        """Determina si un archivo es Python por su extensión."""
        if not file_path:
            return False
        return file_path.endswith(".py")

    @staticmethod
    def validate_syntax(code: str) -> tuple[bool, str]:
        """Valida sintaxis con ast.parse() (instantáneo, sin dependencias).

        Args:
            code: Código Python a validar.

        Returns:
            Tupla (ok, error_msg). Si ok=True, error_msg está vacío.
        """
        try:
            ast.parse(code)
            return (True, "")
        except SyntaxError as e:
            line = e.lineno or "?"
            col = e.offset or "?"
            msg = e.msg or "invalid syntax"
            return (False, f"SyntaxError at line {line}, col {col}: {msg}")

    @staticmethod
    def analyze_file(file_path: str) -> str:
        """Retorna contexto semántico completo de un archivo Python.

        Usa Jedi para extraer:
        - Símbolos top-level (funciones, clases, variables)
        - Métodos y atributos de clases
        - Imports
        - Tipos inferidos de variables

        Args:
            file_path: Ruta absoluta al archivo .py

        Returns:
            String formateado con el contexto, o vacío si no se puede analizar.
        """
        if not os.path.isfile(file_path):
            logger.debug(f"JediAnalyzer: archivo no existe: {file_path}")
            return ""

        try:
            source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"JediAnalyzer: error leyendo {file_path}: {e}")
            return ""

        # Validar sintaxis primero
        ok, error = JediAnalyzer.validate_syntax(source)
        if not ok:
            return f"[LSP: {os.path.basename(file_path)} has syntax errors - {error}]"

        try:
            import jedi
        except ImportError:
            # Jedi no disponible, fallback a ast
            return JediAnalyzer._analyze_with_ast(source, file_path)

        try:
            script = jedi.Script(source, path=file_path)
            lines = []

            basename = os.path.basename(file_path)
            lines.append(f"[LSP Context for {basename}]")

            # 1. Símbolos top-level
            top_names = script.get_names()
            if top_names:
                lines.append("Symbols:")
                for name in top_names:
                    type_label = name.type
                    desc = name.description
                    lines.append(f"  L{name.line}: [{type_label}] {desc}")

            # 2. Símbolos con scopes (incluye métodos de clases)
            all_names = script.get_names(all_scopes=True)
            class_methods = {}
            for name in all_names:
                if name.type == "function" and name.line != name.module_path:
                    # Agrupar métodos por cercanía a su clase padre
                    parent_name = name.parent() if hasattr(name, 'parent') else None
                    if parent_name and parent_name.type == "class":
                        cls_name = parent_name.name
                        if cls_name not in class_methods:
                            class_methods[cls_name] = []
                        class_methods[cls_name].append(
                            f"    L{name.line}: {name.description}"
                        )

            if class_methods:
                if "Symbols:" not in lines[-1] if lines else True:
                    lines.append("Class details:")
                for cls, methods in class_methods.items():
                    for m in methods:
                        lines.append(m)

            # 3. Imports
            import_names = [
                n for n in all_names if n.type == "module" or
                (n.description and n.description.startswith("import "))
            ]
            if import_names:
                imports = sorted(set(
                    n.description for n in import_names if n.description
                ))
                lines.append(f"Imports: {', '.join(imports)}")

            # 4. Variables con tipos inferidos (solo top-level)
            statements = [
                n for n in top_names if n.type == "statement"
            ]
            if statements:
                lines.append("Variables:")
                for stmt in statements:
                    # Intentar inferir tipo
                    try:
                        inferred = script.infer(line=stmt.line, column=stmt.column)
                        if inferred:
                            types = ", ".join(
                                i.description for i in inferred[:3]
                            )
                            lines.append(
                                f"  L{stmt.line}: {stmt.name} → {types}"
                            )
                        else:
                            lines.append(f"  L{stmt.line}: {stmt.name}")
                    except Exception:
                        lines.append(f"  L{stmt.line}: {stmt.name}")

            if len(lines) <= 1:
                return ""  # Archivo vacío o sin símbolos

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"JediAnalyzer: error con Jedi en {file_path}: {e}")
            return JediAnalyzer._analyze_with_ast(source, file_path)

    @staticmethod
    def _analyze_with_ast(source: str, file_path: str) -> str:
        """Fallback: análisis básico con ast cuando Jedi no está disponible."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return ""

        lines = []
        basename = os.path.basename(file_path)
        lines.append(f"[AST Context for {basename}]")

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                args = ", ".join(
                    a.arg for a in node.args.args if a.arg != "self"
                )
                returns = ""
                if node.returns:
                    returns = f" -> {ast.dump(node.returns)}"
                prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
                lines.append(f"  L{node.lineno}: {prefix}def {node.name}({args}){returns}")

            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(
                    ast.dump(b) for b in node.bases
                )
                lines.append(f"  L{node.lineno}: class {node.name}({bases})")
                # Métodos de la clase
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        args = ", ".join(
                            a.arg for a in item.args.args if a.arg != "self"
                        )
                        prefix = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                        lines.append(f"    L{item.lineno}: {prefix}def {item.name}({args})")

        # Imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(a.name for a in node.names)
                imports.append(f"{module}.{names}" if module else names)

        if imports:
            lines.append(f"Imports: {', '.join(imports[:20])}")

        if len(lines) <= 1:
            return ""

        return "\n".join(lines)

    @staticmethod
    def check_file(file_path: str) -> list[dict]:
        """Valida un archivo con pyflakes (si está instalado).

        Args:
            file_path: Ruta absoluta al archivo .py

        Returns:
            Lista de dicts: [{"line": int, "col": int, "msg": str, "severity": str}]
        """
        if not os.path.isfile(file_path):
            return []

        issues = []

        # pyflakes (opcional)
        try:
            import pyflakes.api
            import pyflakes.messages
            import io
            import contextlib

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                warning_count = pyflakes.api.check(
                    Path(file_path).read_text(encoding="utf-8", errors="replace"),
                    file_path
                )

            # pyflakes imprime warnings a stdout
            for line in output.getvalue().strip().split("\n"):
                if ":" in line and line.strip():
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        try:
                            issues.append({
                                "line": int(parts[1].strip()),
                                "col": 0,
                                "msg": parts[2].strip(),
                                "severity": "warning"
                            })
                        except ValueError:
                            pass
        except ImportError:
            logger.debug("pyflakes no instalado, saltando check_file")
        except Exception as e:
            logger.warning(f"JediAnalyzer: error con pyflakes en {file_path}: {e}")

        return issues
