// ===== Estado global y configuracion =====

export const WS_URL = 'ws://localhost:8769';
export const STORAGE_KEY = 'ccm_tabs';

export const DEFAULT_SETTINGS = {
    permission_mode: 'acceptEdits',
    model: 'sonnet',
    system_prompt: '',
    append_system_prompt: '',
    max_turns: '',
    allowed_tools: '',
    disallowed_tools: '',
    rolling_window: 100,
    tools: ['TaskOutput', 'Bash', 'Glob', 'Grep', 'Read', 'Edit', 'Write', 'TodoWrite', 'EnterPlanMode', 'ExitPlanMode', 'TaskStop'],
};

// Lista de todas las tools disponibles
export const AVAILABLE_TOOLS = [
    { name: 'Agent', desc: 'Lanza agentes especializados' },
    { name: 'TaskOutput', desc: 'Obtiene resultado de tareas en segundo plano' },
    { name: 'Bash', desc: 'Ejecuta comandos de terminal' },
    { name: 'Glob', desc: 'Busca archivos por patrón' },
    { name: 'Grep', desc: 'Busca contenido en archivos' },
    { name: 'Read', desc: 'Lee archivos' },
    { name: 'Edit', desc: 'Edita archivos' },
    { name: 'Write', desc: 'Crea/escribe archivos' },
    { name: 'NotebookEdit', desc: 'Edita celdas de Jupyter notebooks' },
    { name: 'TodoWrite', desc: 'Lista de tareas' },
    { name: 'WebSearch', desc: 'Búsqueda web' },
    { name: 'AskUserQuestion', desc: 'Pregunta al usuario' },
    { name: 'EnterPlanMode', desc: 'Entra en modo planificación' },
    { name: 'ExitPlanMode', desc: 'Sale del modo planificación' },
    { name: 'EnterWorktree', desc: 'Crea git worktree aislado' },
    { name: 'TaskStop', desc: 'Detiene tarea en segundo plano' },
    { name: 'Skill', desc: 'Ejecuta skills especializados' },
    { name: 'ListMcpResourcesTool', desc: 'Lista recursos MCP' },
    { name: 'ReadMcpResourceTool', desc: 'Lee recurso MCP' },
    { name: 'mcp__4_5v_mcp__analyze_image', desc: 'Analiza imágenes con IA' },
    { name: 'mcp__deepwiki__ask_question', desc: 'Pregunta sobre repos GitHub' },
    { name: 'mcp__deepwiki__read_wiki_contents', desc: 'Documentación de repos' },
    { name: 'mcp__deepwiki__read_wiki_structure', desc: 'Estructura de docs' },
    { name: 'mcp__web-reader__webReader', desc: 'Convierte URLs a markdown' },
    { name: 'mcp__web-search-prime__web_search_prime', desc: 'Búsqueda web con resúmenes' },
    { name: 'mcp__web_reader__webReader', desc: 'Convierte URLs (alt)' },
];

export const state = {
    tabs: new Map(),
    activeTabId: null,
    tabCounter: 0,
};

// Referencias DOM
export const dom = {
    messages: document.getElementById('messages'),
    input: document.getElementById('prompt'),
    statusDot: document.getElementById('globalStatusDot'),
    statusText: document.getElementById('globalStatusText'),
};
