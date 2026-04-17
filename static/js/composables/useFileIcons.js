// SVG icons for file tree — same style as ActionToolbar:
// viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none"

const FOLDER_CLOSED = '<path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>';
const FOLDER_OPEN = '<path stroke-linecap="round" stroke-linejoin="round" d="M5 19h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/><path stroke-linecap="round" stroke-linejoin="round" d="M3 13h4l2-3h12"/>';

// Base file shape (page with folded corner)
const FILE_BASE = '<path stroke-linecap="round" stroke-linejoin="round" d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline stroke-linecap="round" stroke-linejoin="round" points="14 2 14 8 20 8"/>';

const ICONS = {
    // Folders
    folder: FOLDER_CLOSED,
    folderOpen: FOLDER_OPEN,

    // Generic file
    file: FILE_BASE,

    // Python — file + snake-like "Py"
    py: FILE_BASE + '<text x="8" y="18" font-size="7" font-family="monospace" font-weight="bold" fill="currentColor" stroke="none">Py</text>',

    // JavaScript — file + "JS"
    js: FILE_BASE + '<text x="7.5" y="18" font-size="7" font-family="monospace" font-weight="bold" fill="currentColor" stroke="none">JS</text>',

    // TypeScript — file + "TS"
    ts: FILE_BASE + '<text x="7.5" y="18" font-size="7" font-family="monospace" font-weight="bold" fill="currentColor" stroke="none">TS</text>',

    // JSON — file + curly braces
    json: FILE_BASE + '<path stroke-linecap="round" stroke-linejoin="round" d="M8 13v-1a1.5 1.5 0 000-3V8M16 13v-1a1.5 1.5 0 010-3V8"/>',

    // HTML — file + angle brackets
    html: FILE_BASE + '<polyline stroke-linecap="round" stroke-linejoin="round" points="8 13 10.5 15 13 13"/><polyline stroke-linecap="round" stroke-linejoin="round" points="11 11 13.5 13 11 15.5"/>',

    // CSS — file + braces
    css: FILE_BASE + '<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6M9 10h6M9 14h4"/>',

    // Vue — file + V shape
    vue: FILE_BASE + '<polyline stroke-linecap="round" stroke-linejoin="round" points="8 13 10.5 17 16 11" fill="none"/>',

    // Markdown — file + heading #
    md: FILE_BASE + '<path stroke-linecap="round" stroke-linejoin="round" d="M7 14h1M11 14h1M7 11v6M11 11v6M14 12h3M14 15h3"/>',

    // YAML — file + indented lines
    yml: FILE_BASE + '<path stroke-linecap="round" stroke-linejoin="round" d="M8 11h3M8 14h6M8 17h4"/>',
    yaml: null, // alias, resolved at runtime

    // Shell — file + prompt $_
    sh: FILE_BASE + '<path stroke-linecap="round" stroke-linejoin="round" d="M8 13l2 1.5L8 16"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 16h4"/>',
    bash: null, // alias

    // Text — file + text lines
    txt: FILE_BASE + '<path stroke-linecap="round" stroke-linejoin="round" d="M8 11h8M8 14h5M8 17h6"/>',

    // Env/gitignore — file + lock
    env: FILE_BASE + '<rect x="9" y="12" width="6" height="5" rx="1"/><path d="M10 12V10.5a2 2 0 014 0V12"/>',
    gitignore: null, // alias

    // Config (generic)
    cfg: FILE_BASE + '<circle cx="12" cy="12" r="1.5"/><path d="M12 8v1M12 15v1M8.5 9.5l.87.5M14.63 14l.87.5M8.5 14.5l.87-.5M14.63 10l.87-.5"/>',
    toml: null,
    ini: null,

    // Image files
    svg: FILE_BASE + '<rect x="8" y="11" width="8" height="6" rx="1"/><circle cx="10.5" cy="13.5" r="1"/><path d="M8 17l2.5-2.5L12 16l2-3 2 3"/>',

    // Lock file
    lock: FILE_BASE + '<rect x="9" y="12" width="6" height="5" rx="1"/><path d="M10 12V10.5a2 2 0 014 0V12"/>',
};

// Resolve aliases
ICONS.yaml = ICONS.yml;
ICONS.bash = ICONS.sh;
ICONS.gitignore = ICONS.env;
ICONS.toml = ICONS.cfg;
ICONS.ini = ICONS.cfg;

/**
 * Returns the SVG inner content for a file icon by extension.
 * @param {string} ext - File extension (without dot, e.g. "py", "js")
 * @returns {string} SVG inner HTML for use inside <svg viewBox="0 0 24 24">
 */
export function getFileIcon(ext) {
    return ICONS[ext] || ICONS.file;
}

/**
 * Returns the SVG inner content for a folder icon.
 * @param {boolean} open - Whether the folder is open
 * @returns {string} SVG inner HTML
 */
export function getFolderIcon(open = false) {
    return open ? ICONS.folderOpen : ICONS.folder;
}

/**
 * Returns a full <svg> element string for a file/folder icon.
 * @param {string} ext - Extension or 'folder'/'folder-open'
 * @param {string} size - Width/height class (default 'w-4 h-4')
 * @returns {string} Full <svg> HTML string
 */
export function getFileIconSvg(ext, size = 'w-4 h-4') {
    const content = ext === 'folder' ? getFolderIcon(false)
        : ext === 'folder-open' ? getFolderIcon(true)
        : getFileIcon(ext);
    return `<svg class="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${content}</svg>`;
}
