"""Core - Lógica general reutilizable"""
from termuxcode.core.agent import AgentClient
from termuxcode.core.history import MessageHistory
from termuxcode.core.sessions import SessionManager
from termuxcode.core.session_state import SessionState
from termuxcode.core.background_manager import BackgroundTaskManager
from termuxcode.core.notification_system import NotificationQueue, NotificationType
