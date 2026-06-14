"""
Health check et status de l'API
"""
from fastapi import APIRouter, Depends
from app.core.config import get_settings
from app.ml.model_factory import model_registry
from app.services.rag_service import rag_service

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health():
    """Vérifie que le serveur tourne."""
    return {
        "status": "ok",
        "version": "3.0.0",
        "llm_provider": settings.LLM_PROVIDER,
        "embedding": settings.EMBEDDING_METHOD,
    }


@router.get("/status")
async def status():
    """État détaillé : RAG, ML, modèles, dernière mise à jour."""
    return {
        "rag_ready": rag_service.is_ready,
        "ml_ready": model_registry.is_ready,
        "embedding_method": settings.EMBEDDING_METHOD,
        "ml_models": {
            "souche": {
                "model": model_registry._souche_model.name if model_registry._souche_model else None,
                "accuracy": model_registry._souche_accuracy,
            },
            "labo": {
                "model": model_registry._labo_model.name if model_registry._labo_model else None,
                "accuracy": model_registry._labo_accuracy,
            },
        },
        "trained_at": model_registry._trained_at,
    }