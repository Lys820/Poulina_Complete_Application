"""
Pydantic models – Validation des requêtes/réponses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date


# ── Requêtes Chat ────────────────────────────────────────────────────────────
class SouchePredictRequest(BaseModel):
    type_production: str = Field(..., description="Poulet / Oeuf / Dinde")
    biosecurite_score: float = Field(..., ge=0, le=10)
    taux_mortalite: float = Field(..., ge=0, le=100)
    temperature_moyenne: float = Field(..., ge=10, le=40)
    humidite: float = Field(..., ge=0, le=100)
    fertilite_visee: float = Field(..., ge=0, le=100)
    capacite: float = Field(..., ge=100, le=100000)
    surface_m2: float = Field(..., ge=10, le=10000)
    experience_equipe: float = Field(..., ge=0, le=50)
    distance_labo: float = Field(..., ge=0, le=200)
    budget: float = Field(..., ge=1000, le=500000)
    saison: str = Field(default="Ete", description="Ete / Hiver / Printemps / Automne")
    demande_marche: str = Field(default="Moyen", description="Bas / Moyen / Élevé")
    cout_aliment: float = Field(default=5.0, ge=2, le=10)

    class Config:
        json_schema_extra = {
            "example": {
                "type_production": "Poulet de chair",
                "biosecurite_score": 9.0,
                "taux_mortalite": 2.0,
                "temperature_moyenne": 28,
                "humidite": 55,
                "fertilite_visee": 94,
                "capacite": 15000,
                "surface_m2": 800,
                "experience_equipe": 8,
                "distance_labo": 10,
                "budget": 80000,
                "saison": "Ete",
                "demande_marche": "Élevé",
                "cout_aliment": 5.2
            }
        }


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    predict_souche: Optional[SouchePredictRequest] = None
    filtre_centre: Optional[str] = None
    filtre_ville: Optional[str] = None
    force_collection: Optional[str] = None


# ── Réponses ─────────────────────────────────────────────────────────────────
class SouchePrediction(BaseModel):
    souche: str
    confiance_pct: float = Field(..., ge=0, le=100)
    model: str
    alternatives: List[Dict[str, Any]] = []


class ChatResponse(BaseModel):
    question: str
    answer: str
    retrieved_analyses: List[Dict[str, Any]] = []
    retrieved_labos: List[Dict[str, Any]] = []
    souche_prediction: Optional[SouchePrediction] = None
    model_used: str
    execution_time_ms: float


class RecommendationResponse(BaseModel):
    type_recommandation: str  # "souche" / "labo" / "analyse"
    principale_recommandation: str
    alternatives: List[Dict[str, Any]]
    justification: str
    confiance_pct: float
    data_sources: List[str]  # ["BD", "ML", "Historique"]


# ── Requêtes données BD ──────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    sql_query: str = Field(..., min_length=10, max_length=2000)
    description: str = Field(default="", description="Contexte de la requête")


class CentreFilter(BaseModel):
    gouvernorat: Optional[str] = None
    id_marque: Optional[int] = None
    type_production: Optional[str] = None
    actif: Optional[bool] = True


class LaboratoireFilter(BaseModel):
    gouvernorat: Optional[str] = None
    accepte_urgence: Optional[bool] = None
    certifie_iso: Optional[bool] = True
    actif: Optional[bool] = True


class SoucheFilter(BaseModel):
    type_produit_final: Optional[str] = None
    fertilite_min: Optional[float] = None
    taux_mortalite_max: Optional[float] = None
    resistance_maladies: Optional[str] = None


# ── Réponses données ─────────────────────────────────────────────────────────
class CentreResponse(BaseModel):
    id_centre: int
    nom_centre: str
    localisation: str
    gouvernorat: str
    type_production: str
    capacite_totale: int
    date_creation: date
    actif: bool

    class Config:
        from_attributes = True


class SoucheResponse(BaseModel):
    id_souche: int
    nom_souche: str
    type_produit_final: str
    fertilite_score: float
    taux_mortalite: float
    resistance_maladies: str
    cout_unitaire: float
    pays_origine: str

    class Config:
        from_attributes = True


class LaboratoireResponse(BaseModel):
    id_labo: int
    nom_labo: str
    gouvernorat: str
    latitude: float
    longitude: float
    telephone: str
    email: str
    score_global: float
    tier_labo: str
    delai_standard_jours: int
    delai_urgence_heures: int
    accepte_urgence: bool
    taux_reussite_pct: float

    class Config:
        from_attributes = True


class AnalyseResponse(BaseModel):
    id_demande: int
    num_analyse: str
    centre_id: int
    centre_nom: str
    type_analyse: str
    date_prelevement: date
    date_resultat: Optional[date]
    statut: str
    est_conforme: bool
    pourcentage_securite: float
    priorite: int

    class Config:
        from_attributes = True


# ── Recommandation souche détaillée ──────────────────────────────────────────
class RecommandationSoucheRequest(BaseModel):
    centre_id: Optional[int] = None
    type_production: str
    gouvernorat: str
    budget: float
    biosecurite_score: float
    taux_mortalite_acceptable: float
    prefer_local: bool = False


class SoucheDetailled(BaseModel):
    nom_souche: str
    type_produit_final: str
    fertilite_score: float
    taux_mortalite: float
    cout_unitaire: float
    resistance_maladies: str
    score_match_pct: float  # Relevance score
    raison_recommandation: str


class RecommandationSoucheResponse(BaseModel):
    souche_principale: SoucheDetailled
    alternatives: List[SoucheDetailled]
    analyse_couts: Dict[str, float]  # {"switch_cost": 5000, "annuel": 2500}
    recommandations_additionnelles: List[str]


# ── Recommandation labo détaillée ────────────────────────────────────────────
class RecommandationLaboRequest(BaseModel):
    gouvernorat: str
    type_analyse: str
    urgence: bool = False
    max_delai_jours: int = 10


class LaboratoireDetailled(BaseModel):
    nom_labo: str
    gouvernorat: str
    distance_km: Optional[float]
    delai_jours: int
    score_global: float
    tier_labo: str  # Excellent / Bon / Passable
    taux_reussite_pct: float
    cout_analyse_tnd: float
    competences: List[str]
    score_match_pct: float


class RecommandationLaboResponse(BaseModel):
    labo_principal: LaboratoireDetailled
    alternatives: List[LaboratoireDetailled]
    analyse_urgence: Dict[str, Any]  # delai, cout_urgence, etc.
    recommandations: List[str]


# ── Analyse fréquence ────────────────────────────────────────────────────────
class AnalyseFrequenceRequest(BaseModel):
    maladie_detectee: str  # Salmonelle, Newcastle, etc.
    centre_id: int
    type_production: str
    gouvernorat: str


class AnalyseFrequenceResponse(BaseModel):
    maladie: str
    frequence_recommandee: str  # "Hebdomadaire" / "Bi-hebdomadaire" / "Mensuelle"
    nombre_analyses: int
    duree_recommandee_jours: int
    raison: str
    laboratoires_recommandes: List[str]
    coût_estimé_tnd: float