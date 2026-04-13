"""Registry central de custom tools.

Para añadir un tool nuevo:
  1. Crear termuxcode/custom_tools/tools/mi_tool.py con @tool
  2. Importarlo aquí y añadirlo a TOOLS
"""

from termuxcode.custom_tools.tools.type_check import type_check
from termuxcode.custom_tools.tools.rename_symbol import rename_symbol
from termuxcode.custom_tools.tools.quick_fix import quick_fix
from termuxcode.custom_tools.tools.find_definition import find_definition

TOOLS = [
    type_check,
    rename_symbol,
    quick_fix,
    find_definition,
]
