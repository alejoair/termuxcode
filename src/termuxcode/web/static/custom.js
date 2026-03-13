// Custom JavaScript for termuxcode web mode
// Handles Android keyboard behavior and viewport adjustments

(function() {
    "use strict";

    // Guardar la altura inicial del viewport (antes de que se despliegue el teclado)
    let originalViewportHeight = window.innerHeight;
    let keyboardVisible = false;
    let keyboardCheckInterval = null;

    // Detectar si es un dispositivo móvil
    function isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
            navigator.userAgent
        );
    }

    // Manejar cambios en el tamaño del viewport (teclado de Android)
    function handleViewportResize() {
        const currentHeight = window.innerHeight;
        const heightDiff = originalViewportHeight - currentHeight;

        // Si la altura disminuyó significativamente, el teclado está desplegado
        // Usamos un umbral de 150px para evitar falsos positivos
        if (heightDiff > 150) {
            if (!keyboardVisible) {
                keyboardVisible = true;
                document.body.classList.add('-keyboard-visible');

                // Ajustar CSS variables
                const inputHeight = Math.min(currentHeight * 0.3, 200);
                document.documentElement.style.setProperty('--input-height', `${inputHeight}px`);
            }
        } else if (heightDiff < 50) {
            // Si la altura se recuperó, el teclado se cerró
            if (keyboardVisible) {
                keyboardVisible = false;
                document.body.classList.remove('-keyboard-visible');

                // Reset CSS variables
                document.documentElement.style.removeProperty('--input-height');
            }
        }

        // Ajustar altura del body para evitar scroll
        document.body.style.height = currentHeight + 'px';
        document.body.style.width = window.innerWidth + 'px';
    }

    // Prevenir scroll en toda la página
    function preventPageScroll() {
        window.addEventListener('scroll', function(e) {
            window.scrollTo(0, 0);
        }, { passive: false });

        // Prevenir scroll en touch events
        document.addEventListener('touchmove', function(e) {
            // Permitir scroll solo dentro del terminal
            const terminal = document.getElementById('terminal');
            if (!terminal.contains(e.target)) {
                e.preventDefault();
            }
        }, { passive: false });
    }

    // Configurar visual viewport API si está disponible (mejor soporte en móviles modernos)
    function setupVisualViewport() {
        if ('visualViewport' in window) {
            const viewport = window.visualViewport;

            viewport.addEventListener('resize', function() {
                // Ajustar el tamaño del contenido al visual viewport
                const width = viewport.width;
                const height = viewport.height;
                const scale = viewport.scale;

                document.documentElement.style.setProperty('--vv-width', width + 'px');
                document.documentElement.style.setProperty('--vv-height', height + 'px');
                document.documentElement.style.setProperty('--vv-scale', scale);

                // Ajustar altura del body
                document.body.style.height = height + 'px';
            });
        }
    }

    // Prevenir zoom en input focus
    function preventInputZoom() {
        const inputs = document.querySelectorAll('input, textarea, [contenteditable]');

        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                // En Android, esto ayuda a prevenir el zoom
                this.style.fontSize = '16px';
            });

            input.addEventListener('blur', function() {
                this.style.fontSize = '';
            });
        });
    }

    // Inicializar cuando el DOM está listo
    function init() {
        if (!isMobile()) {
            // Si no es móvil, no necesitamos estos ajustes
            return;
        }

        // Esperar un poco para capturar la altura inicial correctamente
        setTimeout(() => {
            originalViewportHeight = window.innerHeight;
        }, 500);

        // Event listeners
        window.addEventListener('resize', handleViewportResize);
        window.addEventListener('orientationchange', function() {
            // Recalcular altura inicial cuando cambia la orientación
            setTimeout(() => {
                originalViewportHeight = window.innerHeight;
                handleViewportResize();
            }, 300);
        });

        // Prevenir scroll de página
        preventPageScroll();

        // Configurar visual viewport API
        setupVisualViewport();

        // Prevenir zoom en inputs
        preventInputZoom();

        // Aplicar ajustes iniciales
        handleViewportResize();
    }

    // Ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // También ejecutar cuando se carga el terminal
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.id === 'terminal' || (node.classList && node.classList.contains('textual-terminal'))) {
                        // Terminal cargado, aplicar ajustes
                        setTimeout(handleViewportResize, 100);
                        setTimeout(preventInputZoom, 200);
                    }
                });
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

})();
