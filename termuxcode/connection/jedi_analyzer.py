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
        - Signatures: firmas completas con tipos via Name.get_signatures()
        - Methods: métodos de clases con firmas completas
        - Import defs: imports del proyecto resueltos via goto()
        - References: usos cross-file de cada símbolo via get_references()
        - Imports: lista plana de imports
        - Variables: tipos inferidos de variables top-level

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

            top_names = script.get_names()
            all_names = script.get_names(all_scopes=True)

            # ── 1. Signatures (reemplaza "Symbols" + "Class details") ──
            # Name.get_signatures() funciona sobre definiciones (no call sites)
            if top_names:
                lines.append("Signatures:")
                for name in top_names:
                    try:
                        if name.type in ("function", "class"):
                            sigs = name.get_signatures()
                            if sigs:
                                lines.append(f"  L{name.line}: {sigs[0].to_string()}")
                            else:
                                lines.append(f"  L{name.line}: {name.description}")
                        else:
                            lines.append(f"  L{name.line}: [{name.type}] {name.description}")
                    except Exception:
                        lines.append(f"  L{name.line}: [{name.type}] {name.description}")

            # Métodos de clases (con firmas completas)
            class_methods = {}
            for name in all_names:
                if name.type == "function":
                    try:
                        parent_name = name.parent() if hasattr(name, 'parent') else None
                        if parent_name and parent_name.type == "class":
                            cls_name = parent_name.name
                            if cls_name not in class_methods:
                                class_methods[cls_name] = []
                            try:
                                sigs = name.get_signatures()
                                sig_str = sigs[0].to_string() if sigs else name.description
                            except Exception:
                                sig_str = name.description
                            class_methods[cls_name].append(
                                (name.line, sig_str)
                            )
                    except Exception:
                        continue

            if class_methods:
                lines.append("Methods:")
                for cls, methods in class_methods.items():
                    for line_no, sig in methods:
                        lines.append(f"    L{line_no}: {sig}")

            # ── 2. Import defs (goto → firmas de imports del proyecto) ──
            import_names = [
                n for n in all_names if n.type == "module" or
                (n.description and n.description.startswith("import "))
            ]

            # Detectar imports tipo "from x import Y" donde Y es class/function
            # Jedi los clasifica como su tipo real, no como "module"
            project_dir = os.path.dirname(os.path.abspath(file_path))
            for name in top_names:
                if name.type in ("class", "function") and name not in import_names:
                    try:
                        defs = script.goto(
                            line=name.line, column=name.column,
                            follow_imports=True
                        )
                        if not defs:
                            continue
                        d = defs[0]
                        mod_path = str(d.module_path) if d.module_path else ""
                        # Si goto resuelve a otro archivo del proyecto, es import
                        if (mod_path and "site-packages" not in mod_path
                                and (os.sep + "Lib" + os.sep) not in mod_path
                                and mod_path != file_path
                                and mod_path.startswith(project_dir)):
                            import_names.append(name)
                    except Exception:
                        continue

            # Resolver imports del proyecto con goto(follow_imports=True)
            import_def_lines = []
            resolved_count = 0
            for imp_name in import_names:
                if resolved_count >= 5:
                    break
                try:
                    defs = script.goto(
                        line=imp_name.line, column=imp_name.column,
                        follow_imports=True
                    )
                    if not defs:
                        continue
                    d = defs[0]
                    mod_path = str(d.module_path) if d.module_path else ""
                    # Solo imports del proyecto (no site-packages ni stdlib)
                    if not mod_path or "site-packages" in mod_path or (
                        os.sep + "Lib" + os.sep) in mod_path:
                        continue
                    if d.type == "class":
                        import_def_lines.append(
                            f"  {d.name} -> class {d.name} "
                            f"({os.path.basename(mod_path)} L{d.line})"
                        )
                        # Leer la clase importada y extraer firmas de métodos
                        try:
                            imp_source = Path(mod_path).read_text(
                                encoding="utf-8", errors="replace"
                            )
                            imp_script = jedi.Script(imp_source, path=mod_path)
                            imp_names = imp_script.get_names(all_scopes=True)
                            for mn in imp_names:
                                if mn.type != "function":
                                    continue
                                mn_parent = mn.parent() if hasattr(mn, 'parent') else None
                                if not mn_parent or mn_parent.name != d.name:
                                    continue
                                try:
                                    msigs = mn.get_signatures()
                                    msig = msigs[0].to_string() if msigs else mn.description
                                except Exception:
                                    msig = mn.description
                                import_def_lines.append(f"    {msig}")
                        except Exception:
                            pass
                        resolved_count += 1
                    elif d.type == "function":
                        try:
                            fsigs = d.get_signatures() if hasattr(d, 'get_signatures') else []
                            fsig = fsigs[0].to_string() if fsigs else d.description
                        except Exception:
                            fsig = d.description
                        import_def_lines.append(
                            f"  {d.name} -> {fsig} "
                            f"({os.path.basename(mod_path)} L{d.line})"
                        )
                        resolved_count += 1
                except Exception:
                    continue

            if import_def_lines:
                lines.append("Import defs:")
                lines.extend(import_def_lines)

            # ── 3. References (referencias cross-file de símbolos) ──
            ref_lines = []
            symbols_with_refs = 0
            for name in top_names:
                if name.type not in ("function", "class"):
                    continue
                if symbols_with_refs >= 10:
                    break
                try:
                    refs = script.get_references(
                        line=name.line, column=name.column
                    )
                except Exception:
                    continue
                usages = [r for r in refs if not r.is_definition()]
                if not usages:
                    continue
                ref_lines.append(
                    f"  {name.name} -> {len(usages)} "
                    f"usage{'s' if len(usages) > 1 else ''}:"
                )
                for r in usages[:8]:
                    ref_file = os.path.basename(str(r.module_path)) if r.module_path else "?"
                    ref_lines.append(
                        f"    {ref_file} L{r.line}: {r.description.strip()}"
                    )
                if len(usages) > 8:
                    ref_lines.append(f"    ... +{len(usages) - 8} more")
                symbols_with_refs += 1

            if ref_lines:
                lines.append("References:")
                lines.extend(ref_lines)

            # ── 4. Imports (lista plana) ──
            if import_names:
                imports = sorted(set(
                    n.description for n in import_names if n.description
                ))
                lines.append(f"Imports: {', '.join(imports)}")

            # ── 5. Variables con tipos inferidos ──
            statements = [
                n for n in top_names if n.type == "statement"
            ]
            if statements:
                lines.append("Variables:")
                for stmt in statements:
                    try:
                        inferred = script.infer(line=stmt.line, column=stmt.column)
                        if inferred:
                            types = ", ".join(
                                i.description for i in inferred[:3]
                            )
                            lines.append(
                                f"  L{stmt.line}: {stmt.name} -> {types}"
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
