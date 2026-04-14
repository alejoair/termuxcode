/**
 * CodeMirror 6 extensions for LSP integration.
 * Provides diagnostics, completion, hover, and document sync.
 */

import { EditorView } from "codemirror";
import { setDiagnostics } from "@codemirror/lint";

// ── Position helpers ──────────────────────────────────────

export function offsetToPos(doc, offset) {
    const line = doc.lineAt(offset);
    return { line: line.number - 1, character: offset - line.from };
}

export function posToOffset(doc, pos) {
    const line = doc.line(pos.line + 1);
    return Math.min(line.from + pos.character, line.to);
}

// ── Diagnostics extension ─────────────────────────────────

export function lspDiagnostics(client, documentUri) {
    const severityMap = { 1: "error", 2: "warning", 3: "info", 4: "info" };
    client.onNotification("textDocument/publishDiagnostics", (params) => {
        console.log("[LSP] publishDiagnostics:", params.uri, params.diagnostics.length, "diagnostics");
        if (params.uri !== documentUri) {
            console.log("[LSP] URI mismatch, expected:", documentUri);
            return;
        }
        const view = client._view;
        if (!view) { console.log("[LSP] No view yet"); return; }
        const diags = params.diagnostics
            .map((d) => ({
                from: posToOffset(view.state.doc, d.range.start),
                to: posToOffset(view.state.doc, d.range.end),
                severity: severityMap[d.severity] || "error",
                message: d.message,
            }))
            .filter((d) => d.from != null && d.to != null);
        console.log("[LSP] Applying diagnostics:", diags);
        view.dispatch(setDiagnostics(view.state, diags));
    });
    return EditorView.updateListener.of((update) => {
        client._view = update.view;
    });
}

// ── Completion extension ──────────────────────────────────

export function lspCompletion(client, documentUri) {
    const kindMap = {
        3: "function", 6: "variable", 7: "class", 9: "module",
        10: "property", 12: "method", 14: "enum", 19: "keyword",
        21: "constant", 22: "type", 23: "interface",
    };
    return (context) => {
        if (!client.ready || !client.capabilities?.completionProvider) return null;
        const pos = context.pos;
        const lspPos = offsetToPos(context.state.doc, pos);
        let triggerKind = 1; // Invoked
        let triggerChar;
        if (!context.explicit && client.capabilities.completionProvider.triggerCharacters) {
            const line = context.state.doc.lineAt(pos);
            const prev = line.text[pos - line.from - 1];
            if (client.capabilities.completionProvider.triggerCharacters.includes(prev)) {
                triggerKind = 2; // TriggerCharacter
                triggerChar = prev;
            }
        }
        if (!context.explicit && triggerKind === 1 && !context.matchBefore(/\w+$/)) return null;

        return client.request("textDocument/completion", {
            textDocument: { uri: documentUri },
            position: lspPos,
            context: { triggerKind, triggerCharacter: triggerChar },
        }).then((result) => {
            if (!result) return null;
            const items = Array.isArray(result) ? result : result.items;
            const token = context.matchBefore(/\w*/);
            const from = token ? token.from : pos;
            const word = token ? token.text.toLowerCase() : "";
            const filtered = word
                ? items.filter((i) => (i.filterText ?? i.label).toLowerCase().includes(word))
                : items;
            return {
                from,
                options: filtered.map((item) => ({
                    label: item.label,
                    detail: item.detail,
                    type: kindMap[item.kind] || "variable",
                    apply: item.textEdit?.newText ?? item.label,
                    info: async () => {
                        let doc = item.documentation;
                        if (!doc && client.capabilities?.completionProvider?.resolveProvider) {
                            const resolved = await client.request("completionItem/resolve", item);
                            doc = resolved.documentation;
                        }
                        if (!doc) return null;
                        const text = typeof doc === "string" ? doc : doc.value;
                        const dom = document.createElement("div");
                        dom.textContent = text;
                        return dom;
                    },
                })),
                filter: false,
            };
        }).catch(() => null);
    };
}

// ── Hover extension ───────────────────────────────────────

export function lspHover(client, documentUri) {
    return async (view, pos, side) => {
        if (!client.ready || !client.capabilities?.hoverProvider) return null;
        const lspPos = offsetToPos(view.state.doc, pos);
        let result;
        try {
            result = await client.request("textDocument/hover", {
                textDocument: { uri: documentUri },
                position: lspPos,
            });
        } catch { return null; }
        if (!result) return null;

        let html = "";
        const contents = result.contents;
        if (typeof contents === "string") {
            html = `<pre><code>${escapeHtml(contents)}</code></pre>`;
        } else if (Array.isArray(contents)) {
            html = contents.map((c) => typeof c === "string"
                ? `<pre><code>${escapeHtml(c)}</code></pre>`
                : `<pre><code>${escapeHtml(c.value)}</code></pre>`
            ).join("<hr>");
        } else if (contents?.kind === "markdown") {
            html = `<div>${renderMarkdownSimple(contents.value)}</div>`;
        } else if (contents?.value) {
            html = `<pre><code>${escapeHtml(contents.value)}</code></pre>`;
        }
        if (!html) return null;

        const from = result.range ? posToOffset(view.state.doc, result.range.start) : pos;
        const to = result.range ? posToOffset(view.state.doc, result.range.end) : pos;
        if (from == null) return null;

        const dom = document.createElement("div");
        dom.className = "cm-lsp-hover";
        dom.innerHTML = html;

        return { pos: from, end: to, create: () => ({ dom }), above: true };
    };
}

// ── Document sync extension ───────────────────────────────

export function lspSync(client, documentUri) {
    return EditorView.updateListener.of((update) => {
        if (!update.docChanged || !client.ready) return;
        client.sendChange(documentUri, update.state.doc.toString());
    });
}

// ── Helpers ───────────────────────────────────────────────

function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderMarkdownSimple(md) {
    return md
        .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/\n/g, "<br>");
}
