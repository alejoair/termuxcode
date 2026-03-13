"""Estilos de gamificación - Overlays posicionados"""

GAMIFICATION_CSS = """
/* ═══════════════════════════════════════════════════════════════
   ACHIEVEMENT POPUP - Overlay en la parte inferior
   ═══════════════════════════════════════════════════════════════ */
AchievementPopup {
    display: none;
    height: 2;
    width: 100%;
    background: $primary 20%;
    color: $text;
    padding: 0 1;
    border-top: solid $primary;
    dock: bottom;
    layer: overlay;
}

AchievementPopup.visible {
    display: block;
}

/* ═══════════════════════════════════════════════════════════════
   LEVEL UP BANNER - Overlay en la parte superior
   ═══════════════════════════════════════════════════════════════ */
LevelUpBanner {
    display: none;
    height: 1;
    width: 100%;
    background: $success 30%;
    color: $success;
    text-style: bold;
    padding: 0 1;
    content-align: center middle;
    dock: top;
    layer: overlay;
}

LevelUpBanner.visible {
    display: block;
}
"""
