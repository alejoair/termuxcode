// Composable: useIsMobile — singleton reactivo para detectar viewport < 768px
import { ref } from 'https://unpkg.com/vue@3/dist/vue.esm-browser.js';

const isMobile = ref(window.innerWidth < 768);

if (typeof window.matchMedia === 'function') {
    const mql = window.matchMedia('(max-width: 767px)');
    const handler = (e) => { isMobile.value = e.matches; };
    mql.addEventListener
        ? mql.addEventListener('change', handler)
        : mql.addListener(handler);
}

export function useIsMobile() {
    return { isMobile };
}
