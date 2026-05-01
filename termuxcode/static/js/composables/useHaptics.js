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

    function vibrateAttention() {
        vibrate([50, 80]);
    }

    return { vibrateSend, vibrateReceive, vibrateResult, vibrateAttention };
}
