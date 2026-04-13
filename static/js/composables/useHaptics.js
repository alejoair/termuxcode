// Composable: Haptic feedback
export function useHaptics() {
    function vibrate(duration) {
        if (navigator.vibrate) navigator.vibrate(duration);
    }

    function vibrateSend() {
        vibrate(10);
    }

    function vibrateReceive() {
        vibrate(10);
    }

    function vibrateResult() {
        vibrate([10, 50, 10]);
    }

    return { vibrateSend, vibrateReceive, vibrateResult };
}
