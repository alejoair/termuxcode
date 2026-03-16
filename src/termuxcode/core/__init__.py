"""Core - Lógica general reutilizable"""
from .agent import AgentClient
from .history import MessageHistory
from .sessions import SessionManager
from .session_state import SessionState
from .background_manager import BackgroundTaskManager
from .notification_system import NotificationQueue, NotificationType
