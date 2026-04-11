// ===== Estado global y configuracion =====

export const WS_URL = 'ws://localhost:2025';
export const STORAGE_KEY = 'ccm_tabs';

export const DEFAULT_SETTINGS = {
    permission_mode: 'acceptEdits',
    model: 'sonnet',
    system_prompt: '',
    append_system_prompt: '',
    max_turns: '',
    rolling_window: 100,
    // Lista explícita de tools disponibles para el agente (built-ins + MCP habilitadas).
    // Se actualiza automáticamente cuando llega tools_list del backend.
    tools: ['Agent', 'Bash', 'Glob', 'Grep', 'Read', 'Edit', 'Write', 'NotebookEdit',
            'TodoWrite', 'WebSearch', 'AskUserQuestion', 'EnterPlanMode', 'ExitPlanMode',
            'EnterWorktree', 'TaskOutput', 'TaskStop', 'Skill',
            'ListMcpResourcesTool', 'ReadMcpResourceTool'],
    disabledMcpServers: [],  // nombres de MCP servers desactivados para este tab
};

// Lista de tools disponibles — se actualiza dinámicamente desde el backend vía 'tools_list'.
// Fallback inicial con las built-ins conocidas hasta que llegue la lista real.
export const AVAILABLE_TOOLS = [
    { name: 'Agent', desc: 'Lanza agentes especializados', source: 'builtin' },
    { name: 'Bash', desc: 'Ejecuta comandos de terminal', source: 'builtin' },
    { name: 'Glob', desc: 'Busca archivos por patrón', source: 'builtin' },
    { name: 'Grep', desc: 'Busca contenido en archivos', source: 'builtin' },
    { name: 'Read', desc: 'Lee archivos', source: 'builtin' },
    { name: 'Edit', desc: 'Edita archivos', source: 'builtin' },
    { name: 'Write', desc: 'Crea/escribe archivos', source: 'builtin' },
    { name: 'NotebookEdit', desc: 'Edita celdas de Jupyter notebooks', source: 'builtin' },
    { name: 'TodoWrite', desc: 'Lista de tareas', source: 'builtin' },
    { name: 'WebSearch', desc: 'Búsqueda web', source: 'builtin' },
    { name: 'AskUserQuestion', desc: 'Pregunta al usuario', source: 'builtin' },
    { name: 'EnterPlanMode', desc: 'Entra en modo planificación', source: 'builtin' },
    { name: 'ExitPlanMode', desc: 'Sale del modo planificación', source: 'builtin' },
    { name: 'EnterWorktree', desc: 'Crea git worktree aislado', source: 'builtin' },
    { name: 'TaskOutput', desc: 'Obtiene resultado de tareas en segundo plano', source: 'builtin' },
    { name: 'TaskStop', desc: 'Detiene tarea en segundo plano', source: 'builtin' },
    { name: 'Skill', desc: 'Ejecuta skills especializados', source: 'builtin' },
    { name: 'ListMcpResourcesTool', desc: 'Lista recursos MCP', source: 'builtin' },
    { name: 'ReadMcpResourceTool', desc: 'Lee recurso MCP', source: 'builtin' },
];

// Muta el array in-place para preservar la referencia importada por otros módulos.
export function updateAvailableTools(tools) {
    AVAILABLE_TOOLS.length = 0;
    tools.forEach(t => AVAILABLE_TOOLS.push(t));
}

// Estado de MCP servers — se actualiza dinámicamente desde el backend vía 'mcp_status'.
export const mcpServers = [];  // [{name, status, tools: [{name, desc}], error}]

export function updateMcpServers(servers) {
    mcpServers.length = 0;
    servers.forEach(s => mcpServers.push(s));
}

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
