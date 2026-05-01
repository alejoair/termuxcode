// Composable: Desktop notifications
export function useNotifications() {
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

    function _notify(title, body) {
        if (!document.hidden) return;

        if (_tauriNotification && _permissionGranted) {
            _tauriNotification.sendNotification({ title, body });
        } else if ('Notification' in window && _permissionGranted) {
            new Notification(title, { body });
        }
    }

    function notifyResult() {
        _notify('TermuxCode', 'Claude finished working');
    }

    function notifyQuestion() {
        _notify('TermuxCode', 'Claude is asking a question');
    }

    function notifyApproval(toolName) {
        _notify('TermuxCode', `Tool approval needed: ${toolName || 'unknown'}`);
    }

    function notifyDisconnect() {
        _notify('TermuxCode', 'Disconnected from server');
    }

    return { init, notifyResult, notifyQuestion, notifyApproval, notifyDisconnect };
}
