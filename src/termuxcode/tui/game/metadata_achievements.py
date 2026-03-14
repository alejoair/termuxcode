"""Logros basados en metadata de respuestas estructuradas"""
from .stats import Achievement


# Logros extendidos para gamificación con metadata
METADATA_ACHIEVEMENTS: list[dict] = [
    # Por fases
    {
        "id": "phase_first_impl",
        "name": "First Implementation",
        "xp": 25,
        "icon": "⚙️",
        "description": "Completa tu primera acción de implementación"
    },
    {
        "id": "phase_master_impl",
        "name": "Implementation Master",
        "xp": 150,
        "icon": "⚙️",
        "description": "Realiza 50 acciones de implementación"
    },
    {
        "id": "phase_debugger",
        "name": "Bug Hunter",
        "xp": 100,
        "icon": "🐛",
        "description": "Resuelve 10 bugs en fase de debugging"
    },
    {
        "id": "phase_plan_master",
        "name": "Strategic Planner",
        "xp": 120,
        "icon": "📋",
        "description": "Realiza 30 acciones de planificación"
    },
    {
        "id": "phase_tester",
        "name": "Quality Assurance",
        "xp": 100,
        "icon": "✅",
        "description": "Realiza 20 acciones de testing"
    },
    {
        "id": "phase_analyst",
        "name": "Code Analyst",
        "xp": 80,
        "icon": "🔍",
        "description": "Realiza 15 acciones de análisis"
    },

    # Productividad
    {
        "id": "streak_avancer",
        "name": "On Fire",
        "xp": 75,
        "icon": "🔥",
        "description": "5 mensajes consecutivos que avanzan la tarea"
    },
    {
        "id": "streak_master",
        "name": "Unstoppable",
        "xp": 200,
        "icon": "💪",
        "description": "15 mensajes consecutivos que avanzan la tarea"
    },
    {
        "id": "efficiency_master",
        "name": "Efficient Coder",
        "xp": 100,
        "icon": "⚡",
        "description": "80% de tus mensajes avanzan la tarea (mínimo 20)"
    },
    {
        "id": "perfectionist",
        "name": "Perfectionist",
        "xp": 150,
        "icon": "💎",
        "description": "95% de tus mensajes avanzan la tarea (mínimo 50)"
    },

    # Sugerencias
    {
        "id": "suggestion_follower",
        "name": "Good Listener",
        "xp": 50,
        "icon": "👂",
        "description": "Sigue 10 sugerencias del asistente"
    },
    {
        "id": "suggestion_master",
        "name": "Autopilot",
        "xp": 200,
        "icon": "🤖",
        "description": "Sigue 50 sugerencias"
    },
    {
        "id": "suggestion_streak",
        "name": "Trusting User",
        "xp": 120,
        "icon": "🤝",
        "description": "Sigue el 80% de las últimas 10 sugerencias"
    },

    # Historial
    {
        "id": "history_cleaner",
        "name": "Minimalist",
        "xp": 30,
        "icon": "🧹",
        "description": "10 mensajes filtrados por no ser útiles"
    },
    {
        "id": "history_efficient",
        "name": "Efficient Historian",
        "xp": 100,
        "icon": "📊",
        "description": "70% de eficiencia en historial (mínimo 20 mensajes)"
    },
    {
        "id": "history_master",
        "name": "Curator",
        "xp": 180,
        "icon": "📚",
        "description": "90% de eficiencia en historial (mínimo 50 mensajes)"
    },

    # Otros
    {
        "id": "confident_coder",
        "name": "Confident Coder",
        "xp": 80,
        "icon": "🎯",
        "description": "10 respuestas con alta confianza (≥90%)"
    },
    {
        "id": "context_refresh_master",
        "name": "Context Refresh Master",
        "xp": 60,
        "icon": "🔄",
        "description": "5 refreshs de contexto solicitados"
    },
]


def get_all_metadata_achievements() -> list[Achievement]:
    """Retornar todos los logros de metadata"""
    return [Achievement(**a) for a in METADATA_ACHIEVEMENTS]


def merge_achievements(base_achievements: list[Achievement],
                      metadata_achievements: list[Achievement]) -> list[Achievement]:
    """Mezclar logros base con logros de metadata"""
    by_id = {a.id: a for a in base_achievements}
    for ach in metadata_achievements:
        if ach.id not in by_id:
            by_id[ach.id] = ach
        else:
            # Preservar estado de unlocked si existe
            ach.unlocked = by_id[ach.id].unlocked
            by_id[ach.id] = ach
    return list(by_id.values())
