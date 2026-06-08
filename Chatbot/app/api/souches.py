"""
Souches endpoint – Prédiction directe (sans chat)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.ml.model_factory import model_registry

router = APIRouter()


class SouchePredictRequest(BaseModel):
    type_production: str = "Poulet de chair"
    biosecurite_score: float = 7.5
    taux_mortalite: float = 2.5
    temperature_moyenne: float = 28
    humidite: float = 55
    fertilite_visee: float = 90
    capacite: float = 5000
    surface_m2: float = 500
    experience_equipe: float = 5
    distance_labo: float = 15
    budget: float = 50000
    saison: str = "Été"
    demande_marche: str = "Élevé"
    cout_aliment: float = 5.2


@router.post("/souches/predict")
async def predict_souche(req: SouchePredictRequest):
    """Prédiction directe de souche via Random Forest (sans chat)."""
    try:
        if not model_registry._souche_model:
            raise HTTPException(status_code=400, detail="Modèle souche non entraîné. Upload CSV d'abord.")

        result = model_registry.predict_souche(req.dict())
        return result
    except Exception as e:
        import logging
        logging.error(f"Souche predict error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
