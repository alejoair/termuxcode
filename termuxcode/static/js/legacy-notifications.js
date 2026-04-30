// ===== Notificaciones de escritorio =====

let _tauriNotification = null;
let _permissionGranted = false;

async function init() {
    if (window.__TAURI__ && window.__TAURI__.notification) {
        _tauriNotification = window.__TAURI__.notification;
        try {
            let granted = await _tauriNotification.isPermissionGranted();
            if (!granted) {
                const permission = await _tauriNotification.requestPermission();
                granted = permission === 'granted';
            }
            _permissionGranted = granted;
        } catch (e) {
            console.warn('Notification permission error:', e);
        }
    } else if ('Notification' in window) {
        if (Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            _permissionGranted = permission === 'granted';
        } else {
            _permissionGranted = Notification.permission === 'granted';
        }
    }
}

function notify(title, body) {
    if (!document.hidden) return;

    if (_tauriNotification && _permissionGranted) {
        _tauriNotification.sendNotification({ title, body });
    } else if ('Notification' in window && _permissionGranted) {
        new Notification(title, { body });
    }
}

export function notifyResult() {
    notify('TermuxCode', 'Claude finished working');
}

export function notifyAskUserQuestion() {
    notify('TermuxCode', 'Claude is asking a question');
}

export function notifyToolApproval(toolName) {
    notify('TermuxCode', `Tool approval needed: ${toolName || 'unknown'}`);
}

export function notifyPlanApproval() {
    notify('TermuxCode', 'Plan needs your approval');
}

export function notifyDisconnect() {
    notify('TermuxCode', 'Disconnected from server');
}

export function notifyConnectionError() {
    notify('TermuxCode', 'Connection error');
}

export { init as initNotifications };
