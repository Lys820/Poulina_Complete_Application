"""
Recommendation Engine – Logique métier pour recommandations
"""
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


class SoucheRecommendationEngine:
    """Logique recommandation souche"""

    COST_MULTIPLIER = 1.2  # Multiplier pour coût changement
    FERTILITE_WEIGHT = 0.35
    MORTALITE_WEIGHT = 0.25
    RESISTANCE_WEIGHT = 0.20
    COST_WEIGHT = 0.15
    LOCAL_BONUS = 0.05

    def __init__(self, db):
        self.db = db

    def calculate_match_score(
        self,
        souche_row: pd.Series,
        profile: Dict[str, Any],
    ) -> float:
        """
        Calcule un score de match entre souche et profil d'élevage.
        Score : 0-100
        """
        score = 0.0

        # Fertilité (plus haut = mieux)
        if souche_row["fertilite_score"] >= profile.get("fertilite_visee", 90):
            score += self.FERTILITE_WEIGHT * 100
        else:
            delta = profile.get("fertilite_visee", 90) - souche_row["fertilite_score"]
            penalty = (delta / 10) * self.FERTILITE_WEIGHT * 100
            score += max(0, self.FERTILITE_WEIGHT * 100 - penalty)

        # Mortalité (plus bas = mieux)
        max_mortality = profile.get("taux_mortalite_acceptable", 5.0)
        if souche_row["taux_mortalite"] <= max_mortality:
            score += self.MORTALITE_WEIGHT * 100
        else:
            delta = souche_row["taux_mortalite"] - max_mortality
            penalty = (delta / 5) * self.MORTALITE_WEIGHT * 100
            score += max(0, self.MORTALITE_WEIGHT * 100 - penalty)

        # Résistance maladies (heuristique)
        resistance = str(souche_row.get("resistance_maladies", "")).lower()
        if "salmonelle" in resistance or "très" in resistance or "bonne" in resistance:
            score += self.RESISTANCE_WEIGHT * 100
        elif "faible" in resistance or "moyenne" in resistance:
            score += self.RESISTANCE_WEIGHT * 50
        else:
            score += 0

        # Coût (plus bas = mieux)
        budget = profile.get("budget", 50000)
        cost_per_head = souche_row["cout_unitaire"]
        capacity = profile.get("capacite", 10000)
        total_cost = cost_per_head * capacity

        if total_cost <= budget:
            score += self.COST_WEIGHT * 100
        else:
            overbudget = (total_cost - budget) / budget
            if overbudget > 0.5:
                score += 0  # Rejet complet
            else:
                penalty = overbudget * 100 * self.COST_WEIGHT
                score += max(0, self.COST_WEIGHT * 100 - penalty)

        # Bonus localisation
        if profile.get("prefer_local") and souche_row.get("id_pays_origine") == 1:  # Tunisie
            score += self.LOCAL_BONUS * 100

        return min(100, max(0, score))

    def estimate_switch_cost(
        self,
        from_souche: str,
        to_souche: str,
        capacity: int,
        nb_batiments: int = 1,
    ) -> Dict[str, float]:
        """
        Estime coût de changement de souche
        """
        # Coûts fixes (poussins, fournitures, désinfection)
        fixed_cost_per_batiment = 2000  # TND

        # Coûts variables (différence prix unitaire)
        try:
            from_cost = self.db.query_one(
                f"SELECT cout_unitaire FROM souche WHERE nom_souche = '{from_souche}'"
            )
            to_cost = self.db.query_one(
                f"SELECT cout_unitaire FROM souche WHERE nom_souche = '{to_souche}'"
            )
            cost_delta = abs(to_cost - from_cost)
            var_cost = cost_delta * capacity
        except:
            var_cost = 500  # Défaut

        # Coûts d'ajustement (nutrition, lumière, etc.)
        adjustment_cost = 1500

        total = (fixed_cost_per_batiment * nb_batiments) + var_cost + adjustment_cost
        annual = var_cost * 2  # Estimation annuelle

        return {
            "setup_cost_tnd": total,
            "poussins_cost_tnd": from_cost * capacity if from_cost else 0,
            "var_cost_tnd": var_cost,
            "annual_cost_tnd": annual,
            "roi_days": int((total / annual) * 365) if annual > 0 else 0,
        }


class LaboratoireRecommendationEngine:
    """Logique recommandation laboratoire"""

    DISTANCE_WEIGHT = 0.15
    DELAY_WEIGHT = 0.25
    COMPETENCE_WEIGHT = 0.30
    RELIABILITY_WEIGHT = 0.20
    COST_WEIGHT = 0.10

    def __init__(self, db):
        self.db = db

    def calculate_match_score(
        self,
        labo_row: pd.Series,
        requirement: Dict[str, Any],
    ) -> float:
        """
        Calcule score match laboratoire vs demande d'analyse.
        """
        score = 0.0

        # Distance (si applicable)
        if "distance_km" in requirement:
            dist = labo_row.get("distance_km", 100)
            if dist <= 15:
                score += self.DISTANCE_WEIGHT * 100
            elif dist <= 50:
                score += self.DISTANCE_WEIGHT * 70
            else:
                score += self.DISTANCE_WEIGHT * 30

        # Délai
        urgence = requirement.get("urgence", False)
        if urgence:
            delai = labo_row.get("delai_urgence_heures", 48)
            if delai <= 12:
                score += self.DELAY_WEIGHT * 100
            elif delai <= 24:
                score += self.DELAY_WEIGHT * 80
            else:
                score += self.DELAY_WEIGHT * 50
        else:
            delai = labo_row.get("delai_standard_jours", 5)
            if delai <= 3:
                score += self.DELAY_WEIGHT * 100
            elif delai <= 5:
                score += self.DELAY_WEIGHT * 80
            else:
                score += self.DELAY_WEIGHT * 50

        # Compétences (type analyse)
        type_analyse = requirement.get("type_analyse", "")
        competences = str(labo_row.get("specialites_principales", "")).lower()
        if type_analyse.lower() in competences:
            score += self.COMPETENCE_WEIGHT * 100
        elif "pcr" in type_analyse.lower() and "pcr" in competences:
            score += self.COMPETENCE_WEIGHT * 100
        elif "elisa" in type_analyse.lower() and "elisa" in competences:
            score += self.COMPETENCE_WEIGHT * 100
        else:
            score += self.COMPETENCE_WEIGHT * 50

        # Fiabilité
        taux = labo_row.get("taux_reussite_pct", 90)
        satisfaction = labo_row.get("note_satisfaction", 3.5)
        reliability = (taux / 100) * 0.7 + (satisfaction / 5) * 0.3
        score += self.RELIABILITY_WEIGHT * (reliability * 100)

        # Coût
        cost = labo_row.get("cout_analyse_moyen_tnd", 150)
        if cost <= 100:
            score += self.COST_WEIGHT * 100
        elif cost <= 200:
            score += self.COST_WEIGHT * 80
        else:
            score += self.COST_WEIGHT * 50

        return min(100, max(0, score))

    def get_frequency_recommendation(self, maladie: str) -> Dict[str, Any]:
        """Retourne fréquence d'analyse recommandée selon maladie"""
        frequencies = {
            "Salmonelle": {
                "frequence": "Hebdomadaire",
                "jours": 7,
                "nb_analyses": 12,
                "raison": "Zoonose majeure, transmission fèces-eau. Surveillance étroite requise.",
            },
            "Newcastle": {
                "frequence": "Bi-hebdomadaire",
                "jours": 14,
                "nb_analyses": 6,
                "raison": "Maladie critique pandémique. Déclaration obligatoire.",
            },
            "Mycoplasme": {
                "frequence": "Mensuelle",
                "jours": 30,
                "nb_analyses": 4,
                "raison": "Maladie chronique respiratoire. Suivi à long terme.",
            },
            "Gumboro": {
                "frequence": "Hebdomadaire",
                "jours": 7,
                "nb_analyses": 8,
                "raison": "Virus immunodépresseur, impact sur jeunes poussins.",
            },
            "Coccidiose": {
                "frequence": "Bi-hebdomadaire",
                "jours": 14,
                "nb_analyses": 6,
                "raison": "Parasite intestinal fréquent en climat chaud.",
            },
        }

        return frequencies.get(
            maladie,
            {
                "frequence": "Mensuelle",
                "jours": 30,
                "nb_analyses": 4,
                "raison": "Suivi standard selon profil sanitaire.",
            },
        )