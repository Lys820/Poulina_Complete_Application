"""
Recommendations endpoint – Recommandations combinées
Utilise BD + ML + Métier
"""
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from app.core.config import get_settings
from app.data.database_sqlserver import get_db
from app.data.models import (
    RecommandationSoucheRequest,
    RecommandationSoucheResponse,
    RecommandationLaboRequest,
    RecommandationLaboResponse,
    AnalyseFrequenceRequest,
    AnalyseFrequenceResponse,
)
from app.services.recommendation_engine import (
    SoucheRecommendationEngine,
    LaboratoireRecommendationEngine,
)
from app.ml.model_factory import model_registry
from app.services.llm_service import create_llm

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/recommend/souche", response_model=RecommandationSoucheResponse)
async def recommend_souche(
    req: RecommandationSoucheRequest,
    settings = Depends(get_settings),
    db = Depends(get_db),
):
    """
    Recommande meilleure souche pour profil d'élevage.
    
    Étapes:
    1. BD: Récupère souches actives + contexte marché
    2. ML: Prédiction Random Forest
    3. Métier: Filtrage par budget, localisation
    4. LLM: Justification (optionnel)
    """
    t0 = time.time()
    
    try:
        engine = SoucheRecommendationEngine(db)
        llm = create_llm(settings.LLM_PROVIDER, settings)

        # 1. BD: Souches candidates
        souches = db.get_souches({
            "type_produit_final": req.type_production,
            "actif": True
        })

        if souches.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Aucune souche {req.type_production} disponible"
            )

        # 2. ML: Prédiction si modèle entraîné
        ml_prediction = None
        if model_registry._souche_model:
            try:
                ml_prediction = model_registry.predict_souche(req.dict())
                log.info(f"ML prediction: {ml_prediction['souche']} ({ml_prediction['confiance_pct']}%)")
            except Exception as e:
                log.warning(f"ML prediction failed: {e}")

        # 3. Scoring avec engine métier
        souches["score_match"] = souches.apply(
            lambda row: engine.calculate_match_score(row, req.dict()),
            axis=1
        )

        # 4. Filtrage et tri
        top_souches = souches.nlargest(3, "score_match")

        if top_souches.empty:
            raise HTTPException(status_code=404, detail="No suitable souche found")

        # 5. Coût changement
        main_souche_name = top_souches.iloc[0]["nom_souche"]
        cost_estimate = engine.estimate_switch_cost(
            from_souche="Ross 308",  # Défaut
            to_souche=main_souche_name,
            capacity=int(req.type_production == "Oeuf" and 10000 or 12000),
        )

        # 6. LLM: Justification
        context = f"""
        Profil d'élevage: {req.type_production} à {req.gouvernorat}
        Budget: {req.budget} TND
        Biosécurité: {req.biosecurite_score}/10
        Taux de mortalité acceptable: {req.taux_mortalite_acceptable}%
        
        Souche recommandée: {main_souche_name}
        Score match: {top_souches.iloc[0]['score_match']:.1f}%
        Fertilité: {top_souches.iloc[0]['fertilite_score']:.1f}%
        Taux mortalité: {top_souches.iloc[0]['taux_mortalite']:.1f}%
        Coût unitaire: {top_souches.iloc[0]['cout_unitaire']:.2f} TND
        """

        try:
            justification = await llm.generate(
                "Justifie pourquoi cette souche est la meilleure pour ce profil",
                context
            )
        except Exception as e:
            log.warning(f"LLM justification failed: {e}")
            justification = "Justification non disponible"

        # Formattage réponse
        main_detail = {
            "nom_souche": top_souches.iloc[0]["nom_souche"],
            "type_produit_final": top_souches.iloc[0]["type_produit_final"],
            "fertilite_score": float(top_souches.iloc[0]["fertilite_score"]),
            "taux_mortalite": float(top_souches.iloc[0]["taux_mortalite"]),
            "cout_unitaire": float(top_souches.iloc[0]["cout_unitaire"]),
            "resistance_maladies": str(top_souches.iloc[0].get("resistance_maladies", "")),
            "score_match_pct": float(top_souches.iloc[0]["score_match"]),
            "raison_recommandation": "Meilleur compromis entre fertilité, santé et budget"
        }

        alternatives = [
            {
                "nom_souche": row["nom_souche"],
                "type_produit_final": row["type_produit_final"],
                "fertilite_score": float(row["fertilite_score"]),
                "taux_mortalite": float(row["taux_mortalite"]),
                "cout_unitaire": float(row["cout_unitaire"]),
                "resistance_maladies": str(row.get("resistance_maladies", "")),
                "score_match_pct": float(row["score_match"]),
                "raison_recommandation": f"Alternative avec score {row['score_match']:.1f}%"
            }
            for _, row in top_souches.iloc[1:].iterrows()
        ]

        log.info(f"recommend_souche: {main_detail['nom_souche']} ({time.time()-t0:.2f}s)")

        return RecommandationSoucheResponse(
            souche_principale=main_detail,
            alternatives=alternatives,
            analyse_couts=cost_estimate,
            recommandations_additionnelles=[
                f"Consulter un vétérinaire pour adaptation au contexte local",
                f"Prévoir quarantaine des poussins de 3-5 jours",
                f"Adapter l'alimentation si changement de souche",
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"recommend_souche error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/labo", response_model=RecommandationLaboResponse)
async def recommend_labo(
    req: RecommandationLaboRequest,
    settings = Depends(get_settings),
    db = Depends(get_db),
):
    """
    Recommande meilleur laboratoire pour analyse.
    """
    try:
        engine = LaboratoireRecommendationEngine(db)

        # 1. BD: Labos candidats
        labos = db.get_labos({
            "gouvernorat": req.gouvernorat,
            "accepte_urgence": req.urgence if req.urgence else None,
            "actif": True
        })

        if labos.empty:
            raise HTTPException(status_code=404, detail="No lab available")

        # 2. Scoring métier
        requirement = {
            "type_analyse": req.type_analyse,
            "urgence": req.urgence,
            "distance_km": 0,  # À déterminer avec géolocalisation
        }

        labos["score_match"] = labos.apply(
            lambda row: engine.calculate_match_score(row, requirement),
            axis=1
        )

        # 3. Top 3
        top_labos = labos.nlargest(3, "score_match")

        main = top_labos.iloc[0].to_dict()
        alts = [row.to_dict() for _, row in top_labos.iloc[1:].iterrows()]

        return RecommandationLaboResponse(
            labo_principal=main,
            alternatives=alts,
            analyse_urgence={
                "delai_heures": main.get("delai_urgence_heures", 24) if req.urgence else main.get("delai_standard_jours", 5) * 24,
                "cout_urgence": main.get("cout_analyse_moyen_tnd", 150) * 1.5 if req.urgence else main.get("cout_analyse_moyen_tnd", 150),
            },
            recommandations=[
                f"Prélèvement à effectuer le matin pour meilleure qualité",
                f"Transporter échantillon dans les délais requis",
            ]
        )

    except Exception as e:
        log.error(f"recommend_labo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend/analyse-frequence", response_model=AnalyseFrequenceResponse)
async def recommend_analyse_frequence(
    req: AnalyseFrequenceRequest,
    db = Depends(get_db),
):
    """Fréquence d'analyse recommandée selon maladie"""
    try:
        engine = LaboratoireRecommendationEngine(db)
        freq = engine.get_frequency_recommendation(req.maladie_detectee)

        return AnalyseFrequenceResponse(
            maladie=req.maladie_detectee,
            frequence_recommandee=freq["frequence"],
            nombre_analyses=freq["nb_analyses"],
            duree_recommandee_jours=freq["jours"],
            raison=freq["raison"],
            laboratoires_recommandes=["Labo Central Tunis", "Pasteur Tunis"],
            coût_estimé_tnd=freq["nb_analyses"] * 120,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))