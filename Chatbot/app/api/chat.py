"""
Chat endpoint avec mémoire conversationnelle et autorisation
"""
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.core.config import get_settings
from app.core.security import get_current_user, require_permission
from app.ml.model_factory import model_registry
from app.services.rag_service import rag_service
from app.services.llm_service import create_llm
from app.services.memory_service import MemoryService
from app.data.database_sqlserver import get_db

log = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    session_id: Optional[str] = None
    predict_souche: Optional[dict] = None
    filtre_centre: Optional[str] = None
    filtre_ville: Optional[str] = None
    force_collection: Optional[str] = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    session_id: str
    retrieved_analyses: list
    retrieved_labos: list
    souche_prediction: Optional[dict] = None
    model_used: str
    execution_time_ms: float


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    settings=Depends(get_settings),
    current_user: dict = Depends(require_permission("CHAT_READ")),
):
    t0 = time.time()

    if not rag_service.is_ready:
        raise HTTPException(status_code=503, detail="RAG non initialisé")

    db = get_db(settings)
    if not db.connect():
        raise HTTPException(status_code=503, detail="Base de données inaccessible")

    try:
        memory = MemoryService(db)

        # Création ou récupération de session
        user_id = current_user["sub"]
        if req.session_id:
            if not memory.session_belongs_to_user(req.session_id, user_id):
                raise HTTPException(status_code=403, detail="Session non autorisée")
            session_id = req.session_id
        else:
            session_id = memory.create_session(user_id)

        # Historique de conversation
        history = memory.get_history(session_id)

        # Vérification permission ML
        pred_souche = None
        if req.predict_souche:
            if "CHAT_ML" not in current_user.get("permissions", []):
                raise HTTPException(status_code=403, detail="Permission CHAT_ML requise")
            if model_registry._souche_model:
                try:
                    pred_souche = model_registry.predict_souche(req.predict_souche)
                except Exception as e:
                    log.warning(f"Prediction souche echouee: {e}")

        # Retrieval RAG
        chunks_a, chunks_l = rag_service.retrieve(
            req.question,
            force=req.force_collection,
            filtre_centre=req.filtre_centre,
            filtre_ville=req.filtre_ville,
        )

        # Construction du contexte
        context_parts = []
        if pred_souche:
            context_parts.append(
                f"PREDICTION ML SOUCHE : {pred_souche['souche']} "
                f"(confiance : {pred_souche['confiance_pct']}%)"
            )
        if chunks_a:
            context_parts.append("DONNEES ANALYSES / SOUCHES :")
            for i, r in enumerate(chunks_a, 1):
                context_parts.append(f"[Analyse {i} - score {r['score']}] {r['text']}")
        if chunks_l:
            context_parts.append("DONNEES LABORATOIRES :")
            for i, r in enumerate(chunks_l, 1):
                context_parts.append(f"[Labo {i} - score {r['score']}] {r['text']}")

        context = "\n".join(context_parts) if context_parts else "Aucune donnee pertinente."

        # Generation LLM avec historique
        llm = create_llm(settings.LLM_PROVIDER, settings)
        answer = await llm.generate_with_history(req.question, context, history)

        # Persistance en mémoire
        memory.add_message(session_id, "user", req.question)
        memory.add_message(session_id, "assistant", answer)

        return ChatResponse(
            question=req.question,
            answer=answer,
            session_id=session_id,
            retrieved_analyses=[{"score": r["score"], "text": r["text"][:200]} for r in chunks_a],
            retrieved_labos=[{"score": r["score"], "nom": r["metadata"].get("nom_laboratoire")} for r in chunks_l],
            souche_prediction=pred_souche,
            model_used=llm.provider,
            execution_time_ms=round(time.time() - t0, 2),
        )
    finally:
        db.close()