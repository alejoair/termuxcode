// Composable: Typewriter effect para el header
export function useTypewriter() {
    const TEXT = 'TERMUX-CODE';
    let interval = null;
    let charIndex = 0;

    function getTextNode() {
        const titleEl = document.querySelector('.terminal-title');
        if (!titleEl) return null;
        for (const node of titleEl.childNodes) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) return node;
        }
        return null;
    }

    function startTyping() {
        if (interval) return;
        charIndex = 0;
        const textNode = getTextNode();
        if (!textNode) return;
        textNode.textContent = ' ';
        interval = setInterval(() => {
            charIndex++;
            if (charIndex > TEXT.length) {
                charIndex = 0;
                textNode.textContent = ' ';
            } else {
                textNode.textContent = ' ' + TEXT.substring(0, charIndex);
            }
        }, 120);
    }

    function stopTyping() {
        if (!interval) return;
        clearInterval(interval);
        interval = null;
        const textNode = getTextNode();
        if (textNode) textNode.textContent = ' ' + TEXT;
    }

    function init() {
        window.setHeaderWorking = function(val) {
            if (val) startTyping(); else stopTyping();
        };
    }

    return { init };
}
