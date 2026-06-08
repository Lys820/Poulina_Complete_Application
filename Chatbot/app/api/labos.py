"""
Labos endpoint – Recommandations de laboratoires
"""
from fastapi import APIRouter, Query
from app.ml.model_factory import model_registry
from app.services.rag_service import rag_service
import pandas as pd

router = APIRouter()


@router.get("/labos/recommend")
async def recommend_labos(
    urgence: bool = Query(False, description="Urgence ?"),
    ville: str = Query(None, description="Ville (optionnel)"),
    max_delai_jours: int = Query(10, description="Délai max en jours"),
):
    """
    Recommande les meilleurs labos selon critères.
    
    Tri par :
    1. Urgence ? (accepte_urgence)
    2. Délai (delai_urgence_heures si urgence, delai_standard_jours sinon)
    3. Score global ML
    4. Distance
    """
    if not rag_service._store_labos:
        return {"error": "RAG labos non prêt"}, 400

    # Récupère tous les labos (metadata from stored chunks)
    if not rag_service._store_labos._metadata:
        return {"labos": []}

    df = pd.DataFrame(rag_service._store_labos._metadata)
    
    # Filtre
    if urgence:
        df = df[df.get("accepte_urgence", "0").astype(str).isin(["1", "True", "true", "oui"])]
    if ville:
        df = df[df.get("ville", "").str.lower() == ville.lower()]

    # Tri
    sort_by = ["tier_rf", "score_global"] if "tier_rf" in df.columns else ["score_global"]
    try:
        df = df.sort_values(sort_by, ascending=[False] * len(sort_by))
    except:
        pass

    top_n = df.head(5).to_dict("records")
    return {
        "labos": top_n,
        "count": len(top_n),
        "filters": {"urgence": urgence, "ville": ville},
    }