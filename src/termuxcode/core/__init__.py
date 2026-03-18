"""Core - Lógica general reutilizable"""
from termuxcode.core.agents import MainAgentClient
from termuxcode.core.history_manager import MessageHistory
from termuxcode.core.session_manager import SessionManager, Session, SessionState
from termuxcode.core.background_manager import BackgroundTaskManager
from termuxcode.core.notification_system import NotificationQueue, NotificationType
