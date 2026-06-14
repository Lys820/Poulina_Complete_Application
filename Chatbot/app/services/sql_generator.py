"""
SQL Generator – Génère requêtes SQL depuis langage naturel (léger)
Pas de LLM ici, juste pattern matching et templates
"""
import logging
from typing import Optional, Tuple

log = logging.getLogger(__name__)


class SimpleSQLGenerator:
    """
    Génère requêtes SQL simples sans LLM.
    Pour questions complexes → fallback à RAG + LLM.
    """

    PATTERNS = {
        # Centres
        "centre.*bizerte|bizerte.*centre": (
            "SELECT id_centre, nom_centre, localisation, gouvernorat, type_production, capacite_totale "
            "FROM centre_elevage WHERE gouvernorat = 'Bizerte' AND actif = 1"
        ),
        "centre.*sfax|sfax.*centre": (
            "SELECT id_centre, nom_centre, localisation, gouvernorat, type_production, capacite_totale "
            "FROM centre_elevage WHERE gouvernorat = 'Sfax' AND actif = 1"
        ),
        "tous.*centre|centre.*tous": (
            "SELECT id_centre, nom_centre, localisation, gouvernorat, type_production, capacite_totale "
            "FROM centre_elevage WHERE actif = 1 ORDER BY nom_centre"
        ),
        "combien.*centre": (
            "SELECT COUNT(*) as nb_centres FROM centre_elevage WHERE actif = 1"
        ),

        # Labos
        "laboratoire.*tunis|tunis.*labo": (
            "SELECT id_labo, nom_labo, gouvernorat, delai_standard_jours, score_global, tier_labo "
            "FROM laboratoire WHERE gouvernorat = 'Tunis' AND actif = 1"
        ),
        "tous.*labo|labo.*tous": (
            "SELECT id_labo, nom_labo, gouvernorat, score_global, tier_labo, taux_reussite_pct "
            "FROM laboratoire WHERE actif = 1 ORDER BY score_global DESC"
        ),
        "combien.*labo": (
            "SELECT COUNT(*) as nb_labos FROM laboratoire WHERE actif = 1"
        ),

        # Souches
        "poulet": (
            "SELECT id_souche, nom_souche, type_produit_final, fertilite_score, taux_mortalite, cout_unitaire "
            "FROM souche WHERE type_produit_final = 'Poulet' ORDER BY fertilite_score DESC"
        ),
        "oeuf": (
            "SELECT id_souche, nom_souche, type_produit_final, fertilite_score, taux_mortalite, cout_unitaire "
            "FROM souche WHERE type_produit_final = 'Oeuf' ORDER BY fertilite_score DESC"
        ),
        "dinde": (
            "SELECT id_souche, nom_souche, type_produit_final, fertilite_score, taux_mortalite, cout_unitaire "
            "FROM souche WHERE type_produit_final = 'Dinde'"
        ),
        "toutes.*souche|souche.*toutes": (
            "SELECT id_souche, nom_souche, type_produit_final, fertilite_score, taux_mortalite, cout_unitaire "
            "FROM souche ORDER BY type_produit_final, fertilite_score DESC"
        ),

        # Analyses
        "analyse.*critique|critique.*analyse": (
            "SELECT id_demande, num_analyse, statut, priorite, date_resultat "
            "FROM demande_analyse WHERE statut = 'Critique' ORDER BY priorite DESC"
        ),
        "non.*conforme|conforme.*non": (
            "SELECT id_demande, num_analyse, statut, raison_non_conformite, date_resultat "
            "FROM demande_analyse WHERE est_conforme = 0 ORDER BY date_resultat DESC"
        ),
    }

    def generate(self, question: str) -> Optional[Tuple[str, str]]:
        """
        Génère une requête SQL à partir d'une question.
        Retourne : (query, confidence_level: "high" / "medium" / "low")
        
        Si pattern non trouvé → None
        """
        q = question.lower().strip()
        log.debug(f"SQLGen input: {q[:50]}")

        for pattern, query in self.PATTERNS.items():
            # Pattern matching simple
            if all(word in q for word in pattern.split("|")[0].split(".*")):
                log.info(f"Matched pattern: {pattern}")
                return (query, "high")

        # Si aucun pattern → None (fallback)
        return None

    @staticmethod
    def sanitize_input(question: str) -> str:
        """Nettoie l'input pour éviter injection SQL"""
        # Basique mais utile
        dangerous_chars = ["';", "--", "/*", "*/", "xp_", "sp_"]
        clean = question.lower()
        for char in dangerous_chars:
            clean = clean.replace(char, "")
        return clean