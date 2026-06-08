"""
Memory endpoints - Gestion session et historique
"""
from fastapi import APIRouter, Depends, HTTPException
from app.services.memory_service import get_memory_service
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()
memory_service = get_memory_service()


class NewSessionResponse(BaseModel):
    session_id: str
    message: str


class HistoryResponse(BaseModel):
    session_id: str
    message_count: int
    messages: List[Dict[str, Any]]


class SessionStatsResponse(BaseModel):
    session_id: str
    created_at: str
    last_activity: str
    duration_seconds: float
    message_count: int
    messages_per_minute: float


@router.post("/memory/session/new", response_model=NewSessionResponse)
async def create_new_session():
    """Crée nouvelle session conversation"""
    session_id = memory_service.create_session()
    return NewSessionResponse(
        session_id=session_id,
        message="Session créée"
    )


@router.get("/memory/session/{session_id}/history", response_model=HistoryResponse)
async def get_history(session_id: str):
    """Récupère historique complet session"""
    messages = memory_service.get_full_history(session_id)
    
    return HistoryResponse(
        session_id=session_id,
        message_count=len(messages),
        messages=messages
    )


@router.get("/memory/session/{session_id}/stats", response_model=SessionStatsResponse)
async def get_stats(session_id: str):
    """Stats session"""
    stats = memory_service.get_session_stats(session_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return stats


@router.delete("/memory/session/{session_id}")
async def delete_session(session_id: str):
    """Efface session"""
    memory_service.clear_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@router.get("/memory/sessions/active")
async def list_active_sessions():
    """Liste sessions actives"""
    sessions = memory_service.get_active_sessions()
    stats = [memory_service.get_session_stats(s) for s in sessions]
    
    return {
        "count": len(sessions),
        "sessions": stats
    }


@router.post("/memory/cleanup")
async def cleanup():
    """Nettoie sessions expirées (maintenance)"""
    cleaned = memory_service.cleanup_expired_sessions()
    return {"cleaned": cleaned, "status": "done"}