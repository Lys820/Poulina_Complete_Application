"""
Service de mémoire conversationnelle.
Stocke et récupère l'historique de session depuis SQL Server.
"""
from __future__ import annotations

import logging
import uuid

log = logging.getLogger(__name__)

MAX_MESSAGES_IN_CONTEXT = 10


class MemoryService:

    def __init__(self, db):
        self._db = db

    def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        self._db.create_session(session_id, user_id)
        return session_id

    def get_history(self, session_id: str) -> list[dict]:
        return self._db.get_messages(session_id, limit=MAX_MESSAGES_IN_CONTEXT * 2)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        # SqlServerDatabase expose save_message (pas add_message)
        self._db.save_message(session_id, role, content)

    def close_session(self, session_id: str) -> None:
        self._db.update_session_inactive(session_id)

    def session_belongs_to_user(self, session_id: str, user_id: str) -> bool:
        # Sessions gérées en RAM (stubs) — autorisé par défaut
        return True
# Alias pour compatibilité avec memory.py (endpoints mémoire standalone)
def get_memory_service():
    """
    Retourne un MemoryService sans DB (usage dans les endpoints /memory/*).
    Pour une utilisation complète, instancier directement MemoryService(db).
    """
    return _StandaloneMemoryService()


class _StandaloneMemoryService:
    """
    Version standalone pour les endpoints /memory/* (sans DB active à l'init).
    Utilise un dict en RAM — à remplacer par un appel DB si nécessaire.
    """

    def __init__(self):
        self._sessions: dict[str, list[dict]] = {}
        self._meta: dict[str, dict] = {}

    def create_session(self, user_id: int = 0) -> str:
        import uuid
        from datetime import datetime
        sid = str(uuid.uuid4())
        self._sessions[sid] = []
        self._meta[sid] = {
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "user_id": user_id,
        }
        return sid

    def get_full_history(self, session_id: str) -> list[dict]:
        return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str) -> None:
        from datetime import datetime
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({
            "role": role, "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        if session_id in self._meta:
            self._meta[session_id]["last_activity"] = datetime.utcnow().isoformat()

    def get_session_stats(self, session_id: str) -> dict | None:
        if session_id not in self._meta:
            return None
        from datetime import datetime
        meta = self._meta[session_id]
        created = datetime.fromisoformat(meta["created_at"])
        last = datetime.fromisoformat(meta["last_activity"])
        duration = (last - created).total_seconds()
        nb = len(self._sessions.get(session_id, []))
        return {
            "session_id": session_id,
            "created_at": meta["created_at"],
            "last_activity": meta["last_activity"],
            "duration_seconds": duration,
            "message_count": nb,
            "messages_per_minute": round((nb / max(duration / 60, 1)), 2),
        }

    def clear_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._meta.pop(session_id, None)

    def get_active_sessions(self) -> list[str]:
        return list(self._sessions.keys())

    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        to_delete = [
            sid for sid, meta in self._meta.items()
            if datetime.fromisoformat(meta["last_activity"]) < cutoff
        ]
        for sid in to_delete:
            self.clear_session(sid)
        return len(to_delete)
