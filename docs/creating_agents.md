# Guía: Cómo crear un agente de inicialización en termuxcode

## ¿Qué es esto y para qué sirve?

Los agentes de inicialización son procesos que se lanzan automáticamente al abrir la app y poblan la memoria de sesión con información del proyecto antes de que el usuario escriba su primer mensaje. Esto permite que el agente principal ya tenga contexto — qué lenguaje usa el proyecto, qué dependencias tiene, cómo se corre — sin tener que explorarlo en cada conversación.

Cada agente es **incremental**: al arrancar revisa el Blackboard y solo pide al subagente los campos que faltan. Si todo está completo, no se lanza. Esto ahorra tokens y tiempo en reinicios sucesivos.

---

## Conceptos del proyecto que necesitás conocer

**Blackboard** (`core/memory/blackboard.py`): almacenamiento key-value persistido en disco como JSON. Funciona como una base de datos simple con rutas anidadas separadas por puntos: `bb.set("project.runtime.language", "python")`. El archivo físico vive en `.claude/memory/app.json` dentro del directorio del proyecto. Métodos útiles: `bb.get(path, default)`, `bb.exists(path)`.

**Storage** (`core/memory/storage.py`): capa base de persistencia. Define `MEMORY_DIR = Path.cwd() / ".claude" / "memory"`, que es el único lugar donde se define la ruta de memoria. `Blackboard` y `Fifo` la usan automáticamente sin que nadie tenga que pasarla como argumento.

**Fifo** (`core/memory/fifo.py`): cola persistida en disco como CSV. Útil para listas ordenadas de items.

**BackgroundTaskManager** (`core/background_manager.py`): wrapper sobre `asyncio.create_task` que permite correr corutinas en paralelo sin bloquear la UI. Cada task se asocia a una clave string. Para tasks globales (no vinculadas a una sesión de chat) se usa cualquier clave descriptiva como `"project_init"`.

**ClaudeAgentOptions** (del SDK `claude-agent-sdk`): configuración que se pasa a `query()` para lanzar un subagente. Define qué tools puede usar, qué modelo, en qué directorio opera, y el formato de salida estructurada.

**StructuredOutput** (tool del SDK): tool especial que el agente usa para devolver el resultado final en formato JSON. Siempre tiene que estar incluida en `tools`, o el agente no puede terminar correctamente.

**agent_utils** (`core/agents/agent_utils.py`): funciones compartidas para ejecución parcial. Contiene `get_missing_fields()` y `build_partial_schema()`. Todos los agentes las usan para detectar qué falta en el Blackboard y generar un schema recortado.

---

## Proceso para crear un agente nuevo

### 1. Crear el schema

Crear `core/schemas/nombre_agent_schema.py` con el output estructurado que el agente debe devolver.

**Regla crítica: mantener el schema plano.** Sin clases anidadas dentro de otras clases. Los modelos anidados generan `$defs` en el JSON schema que el tool `StructuredOutput` no puede resolver, haciendo que el agente falle silenciosamente en un loop.

**Si necesitás un dict como valor**, usá `str` con JSON serializado en vez de `dict[str, str]`, porque los tipos genéricos de dict también generan `$defs`. El agente parsea el JSON string de vuelta a dict en `_persist`.

```python
# ✅ Correcto: schema plano, dicts como JSON strings
class MiAgentResponse(BaseModel):
    campo_uno: str | None = Field(default=None, description="...")
    campo_dos: list[str] = Field(default_factory=list, description="...")
    campo_dict: str = Field(default="", description="JSON string mapping X to Y.")

# ❌ Incorrecto: modelos anidados generan $defs
class SubModelo(BaseModel):
    x: str

class MiAgentResponse(BaseModel):
    sub: SubModelo  # esto rompe StructuredOutput

# ❌ Incorrecto: dict genérico también genera $defs
class MiAgentResponse(BaseModel):
    roles: dict[str, str]  # genera $defs, rompe StructuredOutput
```

### 2. Definir el FIELD_MAP

Cada agente necesita un diccionario que mapee rutas del Blackboard a nombres de campos del schema. Esto es lo que `agent_utils` usa para saber qué falta y qué pedir.

```python
FIELD_MAP = {
    "project.mi_seccion.campo_uno": "campo_uno",
    "project.mi_seccion.campo_dos": "campo_dos",
    "project.mi_seccion.campo_dict": "campo_dict",
}
```

La clave izquierda es la ruta exacta en el Blackboard. La derecha es el nombre del campo en el Pydantic model. Deben coincidir exactamente con los nombres del schema.

### 3. Crear el agente con ejecución parcial

Crear `core/agents/nombre_agent.py`. El agente revisa el Blackboard al inicio de `run()`, y si no falta nada, retorna sin lanzar el subagente.

```python
from termuxcode.core.agents.agent_utils import get_missing_fields, build_partial_schema

class MiAgent:
    def __init__(self, cwd: str = None):
        self.cwd = cwd or os.getcwd()

    async def run(self) -> None:
        bb = Blackboard("app")
        missing = get_missing_fields(FIELD_MAP, bb)

        if not missing:
            logger.info("all fields present, skipping agent")
            return

        schema = build_partial_schema(MiAgentResponse, missing)
        field_names = list(missing.values())
        prompt = (
            _BASE_PROMPT
            + f"\nOnly fill these fields: {', '.join(field_names)}. "
            + "Leave no field empty."
        )

        options = ClaudeAgentOptions(
            permission_mode="bypassPermissions",
            cwd=self.cwd,
            model="opus",
            setting_sources=["project", "user"],
            tools=["Read", "LS", "Bash", "StructuredOutput"],
            output_format={
                "type": "json_schema",
                "schema": schema,  # schema parcial, solo campos faltantes
            },
        )

        async for message in query(prompt=prompt, options=options):
            if message.__class__.__name__ == "ResultMessage":
                structured = getattr(message, "structured_output", None)
                if structured:
                    self._persist(structured, missing)
```

**Importante: no usar `break` dentro del `async for` de `query()`.** El `ResultMessage` es siempre el último mensaje del generador. Hacer `break` fuerza el cierre del generador y provoca un error de `anyio` (`Attempted to exit cancel scope in a different task`). Dejar que el loop termine solo.

    def _persist(self, structured: dict, missing: dict[str, str]) -> None:
        bb = Blackboard("app")
        for bb_path, schema_field in missing.items():
            value = structured.get(schema_field)
            if value is not None:
                bb.set(bb_path, value)
```

**Puntos clave:**
- `get_missing_fields(FIELD_MAP, bb)` retorna solo las entradas del map cuyo valor en el BB es `None`, `""` o `[]`.
- `build_partial_schema(Model, missing)` genera un JSON schema con solo los campos faltantes. Retorna `None` si no falta nada.
- El prompt se parchea con `"\nOnly fill these fields: ..."` para que el subagente no pierda tokens en campos que ya existen.
- `_persist` recibe `missing` (no el model completo) y solo escribe esos campos al BB.

**Si el schema tiene campos JSON string (dicts serializados):**

```python
_JSON_STRING_FIELDS = {"campo_dict"}

def _persist(self, structured: dict, missing: dict[str, str]) -> None:
    bb = Blackboard("app")
    for bb_path, schema_field in missing.items():
        value = structured.get(schema_field)
        if value is None:
            continue
        if schema_field in _JSON_STRING_FIELDS and isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
        bb.set(bb_path, value)
```

### 4. Inyectar contexto de agentes previos (opcional)

Si el agente se beneficia de datos que otro agente ya escribió al Blackboard, puede leerlos e inyectarlos en el prompt. Esto se hace dentro de `run()`, después de calcular `missing`.

```python
        # Inject context from a previous agent
        context_keys = {
            "project.runtime.language": "Language",
            "project.structure.source_dir": "Source directory",
        }
        context_lines = []
        for bb_path, label in context_keys.items():
            val = bb.get(bb_path)
            if val is not None:
                context_lines.append(f"- {label}: {val}")

        context_block = ""
        if context_lines:
            context_block = (
                "\n\nAlready known about this project:\n"
                + "\n".join(context_lines)
                + "\nUse this to guide your exploration.\n"
            )

        prompt = _BASE_PROMPT + context_block + f"\nOnly fill these fields: ..."
```

Si el agente previo aún no corrió, los campos estarán vacíos y `context_block` queda como string vacío — no rompe nada. Para garantizar que el contexto esté disponible, los agentes se encadenan en secuencia (ver paso 7).

### 5. Agregar logs

Usar `logging` estándar. Los logs aparecen en `textual console` cuando la app corre con `--dev` (correr `textual console` en otra terminal primero).

```python
logger = logging.getLogger(__name__)

logger.debug(f"tool_use: {block.name}")   # visible con -v en textual console
logger.info("persisted to blackboard")    # visible siempre
```

### 6. Lanzarlo al inicio

Los agentes se ejecutan en secuencia dentro de un solo background task en `tui/app.py`, dentro de `_initialize_memory()`. Esto garantiza que cada agente tenga acceso al contexto que escribió el anterior.

```python
async def _run_init_agents():
    env = EnvironmentAgent(cwd=self.cwd)
    await env.run()
    arch = ArchitectureAgent(cwd=self.cwd)
    await arch.run()
    # Agregar nuevos agentes aquí en el orden deseado

self.background_manager.start_task("project_init", _run_init_agents())
```

Cada agente decide internamente si ejecutarse o no. Si no le faltan campos, hace `return` y el siguiente arranca inmediato. El caller no necesita chequear nada.

**Orden importa:** si un agente necesita contexto de otro, debe ir después en la secuencia. Por ejemplo, ArchitectureAgent usa `language` y `source_dir` del EnvironmentAgent, así que va segundo.

---

## Referencia: agent_utils

Archivo: `core/agents/agent_utils.py`

**`get_missing_fields(field_map, bb) -> dict[str, str]`**
Recibe un `FIELD_MAP` y una instancia de `Blackboard`. Retorna el subconjunto de entradas cuyo valor en el BB es `None`, `""` o `[]`. Si retorna vacío, no hay nada que hacer.

**`build_partial_schema(full_model, missing_fields) -> dict | None`**
Recibe el Pydantic model completo y el dict de campos faltantes. Genera un JSON schema que solo incluye las `properties` de los campos faltantes. Retorna `None` si `missing_fields` está vacío.

---

## Directorio de agentes y claves del Blackboard

Todas las claves del Blackboard, qué agente las escribe, su tipo y un ejemplo de valor están en `docs/agent_registry.json`. Ese archivo es la fuente de verdad para saber qué campos existen y a qué agente pertenecen.
