"""
app/api/labos.py
Recommandations de laboratoires
"""
from fastapi import APIRouter, Query
from app.ml.model_factory import model_registry
from app.services.rag_service import rag_service
import pandas as pd

router = APIRouter()


@router.get("/labos/recommend")
async def recommend_labos(
    urgence: bool = Query(False, description="Urgence ?"),
    ville: str = Query(None, description="Ville (filtre partiel sur adresse ou nom)"),
    max_delai_jours: int = Query(10, description="Délai max en jours"),
):
    """
    Recommande les meilleurs labos selon critères.
    Le filtre 'ville' cherche dans le champ adresse (recherche partielle,
    insensible à la casse) — ex: ville=Tunis trouve 'Zone Industrielle, Tunis'.
    """
    if not rag_service._store_labos or not rag_service._store_labos._metadata:
        return {"labos": [], "count": 0, "filters": {"urgence": urgence, "ville": ville}}

    df = pd.DataFrame(rag_service._store_labos._metadata)

    # Filtre urgence
    if urgence and "accepte_urgence" in df.columns:
        df = df[df["accepte_urgence"].astype(str).isin(["1", "True", "true", "oui"])]

    # Filtre ville — recherche partielle sur adresse ET nom_laboratoire
    if ville:
        ville_lower = ville.lower()
        masque_adresse = df.get("adresse", pd.Series(dtype=str)).str.lower().str.contains(
            ville_lower, na=False
        )
        masque_nom = df.get("nom_laboratoire", pd.Series(dtype=str)).str.lower().str.contains(
            ville_lower, na=False
        )
        df = df[masque_adresse | masque_nom]

    # Tri
    sort_cols = [c for c in ["tier_rf", "score_global"] if c in df.columns]
    if sort_cols:
        try:
            df = df.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        except Exception:
            pass

    top_n = df.head(5).to_dict("records")
    return {
        "labos": top_n,
        "count": len(top_n),
        "filters": {"urgence": urgence, "ville": ville},
    }