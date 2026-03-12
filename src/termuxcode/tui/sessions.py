"""Módulo para gestionar múltiples sesiones de chat"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import uuid


@dataclass
class Session:
    """Representa una sesión de chat"""
    id: str
    name: str
    created_at: str
    history_file: Path

    @classmethod
    def from_dict(cls, data: dict, sessions_dir: Path) -> "Session":
        """Crear Session desde dict JSON"""
        return cls(
            id=data["id"],
            name=data["name"],
            created_at=data["created_at"],
            history_file=sessions_dir / f"messages_{data['id']}.jsonl"
        )

    def to_dict(self) -> dict:
        """Convertir a dict para JSON"""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at
        }


class SessionManager:
    """Gestiona múltiples sesiones de chat"""

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = sessions_dir / "sessions.json"
        self._sessions: dict[str, Session] = {}
        self._load_sessions()

    def _load_sessions(self):
        """Cargar sesiones desde el archivo de índice"""
        if self._index_file.exists():
            data = json.loads(self._index_file.read_text())
            for s in data:
                session = Session.from_dict(s, self.sessions_dir)
                self._sessions[session.id] = session

    def _save_sessions(self):
        """Guardar sesiones al archivo de índice"""
        data = [s.to_dict() for s in self._sessions.values()]
        self._index_file.write_text(json.dumps(data, indent=2))

    def create_session(self, name: str = None) -> Session:
        """Crear una nueva sesión"""
        session_id = str(uuid.uuid4())[:8]
        name = name or f"Session {len(self._sessions) + 1}"
        session = Session(
            id=session_id,
            name=name,
            created_at=datetime.now().isoformat(),
            history_file=self.sessions_dir / f"messages_{session_id}.jsonl"
        )
        self._sessions[session_id] = session
        self._save_sessions()
        return session

    def list_sessions(self) -> list[Session]:
        """Listar todas las sesiones, ordenadas por fecha descendente"""
        return sorted(
            self._sessions.values(),
            key=lambda s: s.created_at,
            reverse=True
        )

    def get_session(self, session_id: str) -> Session | None:
        """Obtener una sesión por ID"""
        return self._sessions.get(session_id)

    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Renombrar una sesión"""
        if session_id in self._sessions:
            self._sessions[session_id].name = new_name
            self._save_sessions()
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        """Eliminar una sesión y su archivo de historial"""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            if session.history_file.exists():
                session.history_file.unlink()
            del self._sessions[session_id]
            self._save_sessions()
            return True
        return False

    def get_last_active(self) -> str | None:
        """Obtener el ID de la última sesión activa"""
        last_file = self.sessions_dir / ".last_active"
        if last_file.exists():
            return last_file.read_text().strip()
        return None

    def set_last_active(self, session_id: str) -> None:
        """Establecer la última sesión activa"""
        (self.sessions_dir / ".last_active").write_text(session_id)
