/**
 * LSP JSON-RPC WebSocket Client.
 * Bridges CodeMirror to a Language Server via WebSocket.
 */

export class LspClient {
    constructor(url) {
        this.ws = new WebSocket(url);
        this._id = 0;
        this._pending = new Map();
        this._notifHandlers = new Map();
        this.ready = false;
        this.capabilities = null;
        this._view = null;

        this.ws.onmessage = (e) => this._onMessage(JSON.parse(e.data));
        this.ws.onclose = () => { this.ready = false; };
        this.ws.onerror = () => { this.ready = false; };
    }

    _onMessage(msg) {
        // Response
        if (msg.id != null && this._pending.has(msg.id)) {
            const { resolve, reject, timer } = this._pending.get(msg.id);
            clearTimeout(timer);
            this._pending.delete(msg.id);
            if (msg.error) reject(new Error(msg.error.message));
            else resolve(msg.result);
            return;
        }
        // Notification
        if (msg.method) {
            const h = this._notifHandlers.get(msg.method);
            if (h) h(msg.params);
            // Server-to-client request: respond with null
            if (msg.id) {
                this.ws.send(JSON.stringify({ jsonrpc: "2.0", id: msg.id, result: null }));
            }
        }
    }

    request(method, params, timeout = 10000) {
        return new Promise((resolve, reject) => {
            const id = this._id++;
            const timer = setTimeout(() => {
                this._pending.delete(id);
                reject(new Error(`${method} timed out`));
            }, timeout);
            this._pending.set(id, { resolve, reject, timer });
            this.ws.send(JSON.stringify({ jsonrpc: "2.0", id, method, params }));
        });
    }

    notify(method, params) {
        this.ws.send(JSON.stringify({ jsonrpc: "2.0", method, params }));
    }

    onNotification(method, handler) {
        this._notifHandlers.set(method, handler);
    }

    close() { this.ws.close(); }

    async initialize(rootUri, languageId, documentUri, documentText) {
        const { capabilities } = await this.request("initialize", {
            capabilities: {
                textDocument: {
                    synchronization: { dynamicRegistration: false, willSave: false, didSave: false },
                    completion: {
                        completionItem: { snippetSupport: false, documentationFormat: ["markdown", "plaintext"], resolveSupport: { properties: ["detail", "documentation"] } },
                        contextSupport: true,
                    },
                    hover: { contentFormat: ["markdown", "plaintext"] },
                    publishDiagnostics: { relatedInformation: false },
                },
            },
            processId: null,
            rootUri,
            workspaceFolders: null,
        }, 30000);
        this.capabilities = capabilities;
        this.notify("initialized", {});
        this.ready = true;

        // Open document
        this.notify("textDocument/didOpen", {
            textDocument: { uri: documentUri, languageId, text: documentText, version: 0 },
        });
        this._version = 0;
    }

    sendChange(documentUri, text) {
        this._version++;
        this.notify("textDocument/didChange", {
            textDocument: { uri: documentUri, version: this._version },
            contentChanges: [{ text }],
        });
    }
}
