// ===== WsLspClient: Adapter LspClient over main WebSocket =====
// Implements the same interface as lsp-client.js but routes via WS

export class WsLspClient {
    constructor() {
        this._id = 0;
        this._pending = new Map();   // lsp_id -> { resolve, reject, timer }
        this._notifHandlers = new Map(); // method -> handler
        this._sendFn = null;
        this.ready = false;
        this.capabilities = null;
        this._documentUri = null;
        this._version = 0;
        this._view = null;  // set by lspDiagnostics extension
    }

    setSendFunction(fn) {
        this._sendFn = fn;
    }

    open(path, content, languageId) {
        this.ready = false;
        this._version = 0;
        this._send({
            type: 'lsp_document_open',
            file_path: path,
            content: content,
        });
    }

    close() {
        if (this._documentUri) {
            this._send({
                type: 'lsp_document_close',
                file_path: this._documentUri,
            });
        }
        this.ready = false;
        this.capabilities = null;
        this._documentUri = null;
        this._version = 0;
        this._view = null;
        // Reject all pending requests
        for (const [id, entry] of this._pending) {
            clearTimeout(entry.timer);
            entry.reject(new Error('Connection closed'));
        }
        this._pending.clear();
    }

    request(method, params, timeout = 10000) {
        return new Promise((resolve, reject) => {
            const lsp_id = ++this._id;
            const timer = setTimeout(() => {
                this._pending.delete(lsp_id);
                reject(new Error(`LSP request timeout: ${method}`));
            }, timeout);

            this._pending.set(lsp_id, { resolve, reject, timer });
            this._send({
                type: 'lsp_request',
                lsp_id,
                method,
                params,
            });
        });
    }

    notify(method, params) {
        this._send({
            type: 'lsp_notification',
            method,
            params,
        });
    }

    onNotification(method, handler) {
        this._notifHandlers.set(method, handler);
    }

    sendChange(documentUri, text) {
        this._version++;
        this.notify('textDocument/didChange', {
            textDocument: { uri: documentUri, version: this._version },
            contentChanges: [{ text }],
        });
    }

    handleMessage(data) {
        switch (data.type) {
            case 'lsp_open_result': {
                this._documentUri = data.uri;
                this.capabilities = data.capabilities || {};
                if (!data.error) {
                    this.ready = true;
                }
                break;
            }
            case 'lsp_response': {
                const entry = this._pending.get(data.lsp_id);
                if (entry) {
                    clearTimeout(entry.timer);
                    this._pending.delete(data.lsp_id);
                    if (data.error) {
                        entry.reject(new Error(data.error.message || 'LSP error'));
                    } else {
                        entry.resolve(data.result);
                    }
                }
                break;
            }
            case 'lsp_notification': {
                const handler = this._notifHandlers.get(data.method);
                if (handler) {
                    handler(data.params);
                }
                break;
            }
        }
    }

    destroy() {
        this.close();
        this._sendFn = null;
        this._notifHandlers.clear();
    }

    _send(data) {
        if (this._sendFn) {
            this._sendFn(data);
        }
    }
}
