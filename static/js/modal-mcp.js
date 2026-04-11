// ===== Modal MCP Servers =====

import { state, mcpServers } from './state.js';
import { saveTabs } from './storage.js';
import { escapeHtml, createOverlay, showModal } from './modal-utils.js';
import { disconnectTab, connectTab } from './connection.js';

// ── Helpers ────────────────────────────────────────────────────────────────

function sendToActiveTab(msg) {
    const tab = state.tabs.get(state.activeTabId);
    if (tab && tab.ws && tab.ws.readyState === WebSocket.OPEN) {
        tab.ws.send(JSON.stringify(msg));
    }
}

function getDisabledServers(tab) {
    return new Set(tab.settings.disabledMcpServers || []);
}

function setDisabledServers(tab, disabledSet) {
    tab.settings.disabledMcpServers = [...disabledSet];
    saveTabs();
}

// ── Renderizado del contenido del modal ────────────────────────────────────

export function renderMcpModalContent(overlay, servers, tabId) {
    const tab = state.tabs.get(tabId || state.activeTabId);
    if (!tab) return;

    const disabledServers = getDisabledServers(tab);
    const body = overlay.querySelector('.mcp-body');
    if (!body) return;

    if (!servers || servers.length === 0) {
        body.innerHTML = `
            <div class="mcp-empty">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
                    <rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>
                </svg>
                <p>No hay MCP servers configurados</p>
                <span>Configura servidores MCP en <code>~/.claude/claude_desktop_config.json</code></span>
            </div>
        `;
        return;
    }

    body.innerHTML = servers.map(server => {
        const isDisabled = disabledServers.has(server.name);
        const statusClass = server.status === 'connected' ? 'connected'
            : server.status === 'disconnected' ? 'disconnected' : 'unknown';
        const statusLabel = server.status === 'connected' ? 'conectado'
            : server.status === 'disconnected' ? 'desconectado' : server.status || 'desconocido';
        const toolCount = (server.tools || []).length;
        const toolsHtml = toolCount > 0
            ? (server.tools || []).map(t =>
                `<li class="mcp-tool-item" title="${escapeHtml(t.desc || '')}">${escapeHtml(t.name)}</li>`
              ).join('')
            : '<li class="mcp-tool-item mcp-tool-empty">Sin tools</li>';

        return `
            <div class="mcp-server-card ${isDisabled ? 'mcp-server-card--disabled' : ''}" data-server="${escapeHtml(server.name)}">
                <div class="mcp-server-header">
                    <div class="mcp-server-info">
                        <span class="mcp-status-chip mcp-status-chip--${statusClass}">
                            <span class="mcp-status-dot"></span>${escapeHtml(statusLabel)}
                        </span>
                        <span class="mcp-server-name">${escapeHtml(server.name)}</span>
                    </div>
                    <label class="mcp-toggle" title="${isDisabled ? 'Activar servidor' : 'Desactivar servidor'}">
                        <input type="checkbox" class="mcp-toggle-input" data-server="${escapeHtml(server.name)}" ${isDisabled ? '' : 'checked'}>
                        <span class="mcp-toggle-track"></span>
                    </label>
                </div>
                ${server.error ? `<div class="mcp-server-error">${escapeHtml(server.error)}</div>` : ''}
                <details class="mcp-tools-details">
                    <summary class="mcp-tools-summary">${toolCount} tool${toolCount !== 1 ? 's' : ''}</summary>
                    <ul class="mcp-tools-list">${toolsHtml}</ul>
                </details>
            </div>
        `;
    }).join('');

    // Bind toggle events
    body.querySelectorAll('.mcp-toggle-input').forEach(input => {
        input.addEventListener('change', () => {
            const serverName = input.dataset.server;
            const currentTab = state.tabs.get(state.activeTabId);
            if (!currentTab) return;

            const enabled = input.checked;
            const disabled = getDisabledServers(currentTab);
            if (enabled) {
                disabled.delete(serverName);
            } else {
                disabled.add(serverName);
            }
            setDisabledServers(currentTab, disabled);

            // Actualizar apariencia de la card
            const card = input.closest('.mcp-server-card');
            if (card) card.classList.toggle('mcp-server-card--disabled', !enabled);

            // Actualizar tab.settings.tools: añadir/quitar tools del server toggleado
            const server = mcpServers.find(s => s.name === serverName);
            if (server && server.tools) {
                const serverToolNames = server.tools.map(t => t.name);
                if (enabled) {
                    // Añadir tools del server habilitado (si no están ya)
                    for (const name of serverToolNames) {
                        if (!currentTab.settings.tools.includes(name)) {
                            currentTab.settings.tools.push(name);
                        }
                    }
                } else {
                    // Quitar tools del server deshabilitado
                    currentTab.settings.tools = currentTab.settings.tools.filter(
                        n => !serverToolNames.includes(n)
                    );
                }
                saveTabs();
            }

            // Mostrar hint de reconexión
            const hint = overlay.querySelector('.mcp-reconnect-hint');
            if (hint) hint.style.display = 'block';
        });
    });
}

// ── Modal principal ────────────────────────────────────────────────────────

export function openMCPModal() {
    if (document.getElementById('mcpModal')) return;

    const tab = state.tabs.get(state.activeTabId);
    if (!tab) return;

    const overlay = createOverlay('mcpModal');
    overlay.innerHTML = `
        <div class="question-modal mcp-modal">
            <div class="question-header">
                <span class="question-chip">MCP Servers</span>
                <div class="mcp-header-actions">
                    <button class="mcp-btn-refresh" id="mcpRefreshBtn" title="Actualizar estado">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <path d="M23 4v6h-6M1 20v-6h6"/>
                            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                        </svg>
                        Refresh
                    </button>
                    <button class="mcp-btn-close" id="mcpCloseBtn" title="Cerrar">✕</button>
                </div>
            </div>
            <div class="mcp-body"></div>
            <div class="mcp-reconnect-hint" style="display:none">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
                </svg>
                Cambios aplicados al reconectar
            </div>
            <div class="mcp-footer">
                <button class="mcp-btn-reconnect" id="mcpReconnectBtn">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M23 4v6h-6M1 20v-6h6"/>
                        <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                    </svg>
                    Reconectar sesión
                </button>
            </div>
        </div>
    `;

    showModal(overlay);

    // Poblar contenido inicial con estado actual
    renderMcpModalContent(overlay, mcpServers, state.activeTabId);

    // Solicitar estado actualizado al backend
    sendToActiveTab({ type: 'request_mcp_status' });

    // Botón refresh
    overlay.querySelector('#mcpRefreshBtn').addEventListener('click', () => {
        const btn = overlay.querySelector('#mcpRefreshBtn');
        btn.style.opacity = '0.5';
        btn.style.pointerEvents = 'none';
        sendToActiveTab({ type: 'request_mcp_status' });
        setTimeout(() => {
            btn.style.opacity = '';
            btn.style.pointerEvents = '';
        }, 1500);
    });

    // Botón reconectar
    overlay.querySelector('#mcpReconnectBtn').addEventListener('click', () => {
        overlay.remove();
        const tabId = state.activeTabId;
        if (tabId) {
            disconnectTab(tabId);
            connectTab(tabId);
        }
    });

    // Botón cerrar
    overlay.querySelector('#mcpCloseBtn').addEventListener('click', () => overlay.remove());

    // Cerrar al click fuera del modal
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });
}
