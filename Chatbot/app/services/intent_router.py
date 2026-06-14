"""
Intent Router – Décide si la question relève de BD, RAG, ou ML
"""
import logging
from enum import Enum
from typing import Tuple

log = logging.getLogger(__name__)


class Intent(str, Enum):
    """Types de traitement de question"""
    BD_DIRECT = "bd"           # Requête structurée directe
    BD_WITH_RAG = "rag"        # Historique + contexte + LLM
    ML_INFERENCE = "ml"        # Prédiction + recommandation
    COMBINED = "combined"      # Plusieurs approches


class IntentRouter:
    """
    Analyse la question et décide du traitement optimal.
    Pas de ML lourd, juste keyword matching + heuristiques.
    """

    # Keywords pour requêtes BD directes
    KEYWORDS_BD = {
        # Existence / Comptage
        "combien": 1.0,
        "existe": 0.9,
        "quel": 0.6,
        "quels": 0.6,
        "qui": 0.7,
        "où": 0.8,
        "adresse": 1.0,
        "telephone": 1.0,
        "email": 1.0,
        "localisation": 0.9,
        "contact": 0.8,
        "liste": 0.7,
        "total": 0.8,
        "nombre": 0.9,
        "actif": 0.7,
        "capacité": 0.8,

        # Spécificités
        "centre": 0.5,
        "labo": 0.5,
        "souche": 0.4,
        "gouvernorat": 0.8,
    }

    # Keywords pour ML / recommandation
    KEYWORDS_ML = {
        "meilleur": 1.0,
        "meilleure": 1.0,
        "recommande": 0.95,
        "recommandes": 0.95,
        "quelle souche": 1.0,
        "quel labo": 0.95,
        "risque": 0.8,
        "coût": 0.7,
        "cout": 0.7,
        "prix": 0.7,
        "fréquence": 0.6,
        "frequence": 0.6,
        "optimal": 0.9,
        "adapté": 0.8,
        "adapte": 0.8,
        "profil": 0.6,
        "indicateur": 0.5,
    }

    # Keywords pour RAG (contexte + historique)
    KEYWORDS_RAG = {
        "pourquoi": 0.7,
        "comment": 0.6,
        "raison": 0.8,
        "historique": 1.0,
        "recent": 0.7,
        "récent": 0.7,
        "alertes": 0.9,
        "alerte": 0.9,
        "maladie": 0.7,
        "conforme": 0.6,
        "non conforme": 0.9,
        "critique": 0.8,
        "analyse": 0.5,
        "contexte": 0.8,
        "évolution": 0.8,
        "tendance": 0.7,
    }

    def __init__(self):
        self.confidences = {}

    def route(self, question: str) -> Tuple[Intent, float]:
        """
        Détermine l'intent de la question.
        
        Retourne: (Intent, confidence_score)
        """
        q = question.lower().strip()
        log.debug(f"Routing question: {q[:50]}...")

        # Calcule scores
        score_bd = self._calculate_score(q, self.KEYWORDS_BD)
        score_ml = self._calculate_score(q, self.KEYWORDS_ML)
        score_rag = self._calculate_score(q, self.KEYWORDS_RAG)

        self.confidences = {
            "bd": score_bd,
            "ml": score_ml,
            "rag": score_rag,
        }

        log.debug(f"Scores: BD={score_bd:.2f}, ML={score_ml:.2f}, RAG={score_rag:.2f}")

        # Logique de décision
        max_score = max(score_bd, score_ml, score_rag)
        min_score = min(score_bd, score_ml, score_rag)

        # Si deux scores très proches → combined
        if max_score - min_score < 0.5 and max_score > 1.0:
            return Intent.COMBINED, max_score

        # Décision par score dominant
        if score_bd >= score_ml and score_bd >= score_rag and score_bd > 0.3:
            return Intent.BD_DIRECT, score_bd

        if score_ml > score_bd and score_ml > score_rag and score_ml > 1.0:
            return Intent.ML_INFERENCE, score_ml

        if score_rag > score_bd and score_rag > score_ml and score_rag > 0.5:
            return Intent.BD_WITH_RAG, score_rag

        # Default : COMBINED (sûr)
        return Intent.COMBINED, max(score_bd, score_ml, score_rag)

    def _calculate_score(self, question: str, keywords_dict: dict) -> float:
        """Calcule le score de correspondance avec un set de keywords"""
        total_score = 0.0
        matches = 0

        for keyword, weight in keywords_dict.items():
            if keyword in question:
                total_score += weight
                matches += 1

        return total_score

    def should_use_ml_prediction(self, intent: Intent, question: str) -> bool:
        """Détermine si prédiction ML doit être incluse"""
        return intent in (Intent.ML_INFERENCE, Intent.COMBINED)

    def should_use_rag(self, intent: Intent, question: str) -> bool:
        """Détermine si RAG doit être inclus"""
        return intent in (Intent.BD_WITH_RAG, Intent.COMBINED)

    def should_query_bd(self, intent: Intent, question: str) -> bool:
        """Détermine si BD doit être interrogée"""
        return intent in (Intent.BD_DIRECT, Intent.BD_WITH_RAG, Intent.COMBINED)


# Singleton
intent_router = IntentRouter()