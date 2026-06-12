"""
app/data/database_sqlserver.py
Couche d'accès aux données — base PouleLabDB (VICTUSL\\SQLEXPRESS)

Tables ciblées (schéma EF Core / ASP.NET Identity) :
  - AspNetUsers / AspNetRoles / AspNetUserRoles  → authentification
  - Laboratories                                  → labos d'analyse
  - AnalysisRequests                              → demandes
  - Samples                                       → échantillons
  - AnalysisResults                               → résultats
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd
import pyodbc
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


class SqlServerDatabase:
    """
    Connexion Windows Authentication à PouleLabDB.
    Toutes les requêtes ciblent les tables générées par EF Core.
    """

    def __init__(
        self,
        server: Optional[str] = None,
        database: Optional[str] = None,
        driver: Optional[str] = None,
    ) -> None:
        self._server   = server   or os.getenv("SQLSERVER_SERVER",   r"VICTUSL\SQLEXPRESS")
        self._database = database or os.getenv("SQLSERVER_DATABASE", "PouleLabDB")
        self._driver   = driver   or os.getenv("SQLSERVER_DRIVER",   "ODBC Driver 17 for SQL Server")
        self._conn: Optional[pyodbc.Connection] = None

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        try:
            conn_str = (
                f"DRIVER={{{self._driver}}};"
                f"SERVER={self._server};"
                f"DATABASE={self._database};"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            )
            self._conn = pyodbc.connect(conn_str, timeout=5)
            log.info("Connexion SQL Server OK — %s / %s", self._server, self._database)
            return True
        except Exception as e:
            log.error("Connexion SQL Server impossible : %s", e)
            self._conn = None
            return False

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def _ensure_connected(self) -> bool:
        if self._conn is None:
            return self.connect()
        return True

    # ------------------------------------------------------------------
    # Authentification  (AspNetUsers + AspNetRoles)
    # ------------------------------------------------------------------

    def get_utilisateur_par_email(self, email: str) -> Optional[dict]:
        if not self._ensure_connected():
            return None
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT
                    u.Id                AS id_utilisateur,
                    u.PasswordHash      AS password_hash,
                    u.LastName          AS nom,
                    u.FirstName         AS prenom,
                    u.FilialeName       AS filiale,
                    u.IsActive          AS actif,
                    ISNULL(r.Name, '')  AS nom_role,
                    NULL                AS permissions
                FROM AspNetUsers u
                LEFT JOIN AspNetUserRoles ur ON ur.UserId = u.Id
                LEFT JOIN AspNetRoles r      ON r.Id      = ur.RoleId
                WHERE u.NormalizedEmail = ?
                """,
                email.upper(),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "id_utilisateur": row.id_utilisateur,
                "password_hash":  row.password_hash,
                "nom":            row.nom,
                "prenom":         row.prenom,
                "filiale":        row.filiale,
                "actif":          int(row.actif) if row.actif is not None else 0,
                "nom_role":       row.nom_role,
                "permissions":    row.permissions,
            }
        except Exception as exc:
            log.error("get_utilisateur_par_email(%s) : %s", email, exc)
            return None

    # ------------------------------------------------------------------
    # Données d'entraînement ML / RAG
    # ------------------------------------------------------------------

    def get_analyses(self) -> pd.DataFrame:
        """
        Retourne les analyses de PouleLabDB pour l'entraînement ML et le RAG.

        Colonnes réelles de PouleLabDB + colonnes synthétiques compatibles
        avec SOUCHE_NUM_FEATURES / SOUCHE_CAT_FEATURES / SOUCHE_TARGET de
        model_factory.py. Les colonnes absentes du schéma EF Core sont
        dérivées ou initialisées à des valeurs neutres pour que le modèle
        souche puisse s'entraîner dès la mise en production.

        Colonnes synthétiques ajoutées :
          meilleure_souche   ← dérivé du Brand de la demande (cible ML souche)
          biosecurite_score  ← 7.0 par défaut
          taux_mortalite     ← 3.0 par défaut
          fertilite_visee    ← 90.0 par défaut
          capacite           ← 10000 par défaut
          surface_m2         ← 500 par défaut
          altitude           ← 0 par défaut
          cout_aliment       ← 5.0 par défaut
          experience_equipe  ← 5 par défaut
          distance_labo      ← 20 par défaut
          budget             ← 50000 par défaut
          temperature_moyenne← 25.0 par défaut
          humidite           ← 60.0 par défaut
          type_production    ← dérivé du type d'échantillon
          saison             ← dérivé du mois de création
          region             ← 'Non renseigné' par défaut
          demande_marche     ← 'Moyen' par défaut
          conforme           ← 1 si statut Completed, 0 sinon
          historique_maladie ← dérivé du nom d'analyse
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        try:
            query = """
                SELECT
                    ar.Id               AS id_demande,
                    ar.Status           AS statut,
                    ar.Brand            AS marque,
                    ar.Notes            AS notes,
                    ar.CreatedAt        AS date_creation,
                    ar.SubmittedAt      AS date_soumission,
                    ar.ReceivedAt       AS date_reception,
                    l.Name              AS nom_laboratoire,
                    l.Address           AS adresse_labo,
                    u.FilialeName       AS filiale_client,
                    u.FirstName + ' ' + u.LastName AS nom_client,
                    s.Id                AS id_echantillon,
                    s.Type              AS type_echantillon,
                    s.Characteristics   AS caracteristiques,
                    s.Quantity          AS quantite,
                    s.Unit              AS unite,
                    res.Id              AS id_resultat,
                    res.AnalysisName    AS type_analyse,
                    res.MeasuredValue   AS valeur_mesuree,
                    res.LowerBound      AS borne_inf,
                    res.UpperBound      AS borne_sup,
                    res.IsAnomaly       AS est_anomalie,
                    res.RecordedAt      AS date_resultat,
                    -- ── Colonne cible ML souche ──────────────────────────
                    -- Brand encode la souche/marque analysée.
                    -- Valeur de repli : 'Standard' si Brand est NULL.
                    ISNULL(ar.Brand, 'Standard')  AS meilleure_souche,
                    -- ── Features numériques (valeurs neutres) ───────────
                    7.0     AS biosecurite_score,
                    3.0     AS taux_mortalite,
                    90.0    AS fertilite_visee,
                    10000   AS capacite,
                    500     AS surface_m2,
                    0       AS altitude,
                    5.0     AS cout_aliment,
                    5       AS experience_equipe,
                    20      AS distance_labo,
                    50000   AS budget,
                    25.0    AS temperature_moyenne,
                    60.0    AS humidite,
                    -- ── Features catégorielles dérivées ─────────────────
                    -- type_production : déduit du type d'échantillon
                    ISNULL(s.Type, 'Poulet de chair') AS type_production,
                    -- saison : déduite du mois de création
                    CASE
                        WHEN MONTH(ar.CreatedAt) IN (12,1,2)  THEN 'Hiver'
                        WHEN MONTH(ar.CreatedAt) IN (3,4,5)   THEN 'Printemps'
                        WHEN MONTH(ar.CreatedAt) IN (6,7,8)   THEN 'Ete'
                        ELSE 'Automne'
                    END                               AS saison,
                    'Non renseigné'                   AS region,
                    'Moyen'                           AS demande_marche,
                    -- conforme : 1 si la demande est terminée et sans anomalie
                    CASE
                        WHEN ar.Status = 'Completed'
                             AND (res.IsAnomaly IS NULL OR res.IsAnomaly = 0)
                        THEN 1 ELSE 0
                    END                               AS conforme,
                    -- historique_maladie : nom de l'analyse réalisée
                    ISNULL(res.AnalysisName, 'Aucune') AS historique_maladie
                FROM AnalysisRequests ar
                INNER JOIN Laboratories l  ON l.Id = ar.LaboratoryId
                INNER JOIN AspNetUsers  u  ON u.Id = ar.ClientId
                LEFT  JOIN Samples      s  ON s.RequestId  = ar.Id
                LEFT  JOIN AnalysisResults res ON res.SampleId = s.Id
                WHERE ar.IsDraft = 0
                ORDER BY ar.CreatedAt DESC
            """
            df = pd.read_sql(query, self._conn)
            log.info("get_analyses : %d lignes chargées", len(df))
            return df
        except Exception as exc:
            log.error("get_analyses : %s", exc)
            return pd.DataFrame()

    def get_analyses_data(self) -> pd.DataFrame:
        return self.get_analyses()

    def get_labos(self) -> pd.DataFrame:
        """
        Retourne les laboratoires de PouleLabDB pour le RAG et le scoring.
        Les colonnes absentes du schéma EF Core sont fournies avec des valeurs
        par défaut pour éviter les UserWarning de sklearn lors de l'imputation.
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        try:
            query = """
                SELECT
                    l.Id            AS id_laboratoire,
                    l.Name          AS nom_laboratoire,
                    l.Address       AS adresse,
                    l.Description   AS description,
                    l.TemplateType  AS template_type,
                    l.CreatedAt     AS date_creation,
                    -- Score et tier calculés (valeurs par défaut)
                    7.0             AS score_global,
                    'B'             AS tier_labo,
                    1               AS accepte_urgence,
                    1               AS certifie_iso,
                    -- Colonnes attendues par LABO_CAT_FEATURES
                    'Polyvalent'    AS type_laboratoire,
                    'Non renseigné' AS region,
                    0               AS agree_ministere_agriculture,
                    1               AS equipement_pcr,
                    1               AS equipement_elisa,
                    0               AS equipement_sequencage,
                    -- Colonnes attendues par LABO_NUM_FEATURES
                    0.0             AS taux_reussite_pct,
                    0.0             AS note_satisfaction,
                    5               AS delai_standard_jours,
                    24              AS delai_urgence_heures,
                    50              AS capacite_journaliere_analyses,
                    50.0            AS charge_actuelle_pct,
                    10              AS slots_disponibles_semaine,
                    3               AS delai_prochain_rdv_jours,
                    100.0           AS cout_analyse_moyen_tnd,
                    50.0            AS distance_moyenne_centres_km,
                    5               AS annees_experience_labo,
                    0               AS nb_analyses_avicoles
                FROM Laboratories l
                ORDER BY l.Id
            """
            df = pd.read_sql(query, self._conn)
            log.info("get_labos : %d laboratoires chargés", len(df))
            return df
        except Exception as exc:
            log.error("get_labos : %s", exc)
            return pd.DataFrame()

    def get_labos_data(self) -> pd.DataFrame:
        return self.get_labos()

    def get_all_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        if not self._ensure_connected():
            return pd.DataFrame(), pd.DataFrame()
        return self.get_analyses(), self.get_labos()

    # ------------------------------------------------------------------
    # Données de référence pour les endpoints /data/*
    # ------------------------------------------------------------------

    def get_centres(self) -> list[dict]:
        if not self._ensure_connected():
            return []
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT
                    u.FilialeName   AS nom_centre,
                    COUNT(ar.Id)    AS nb_demandes
                FROM AspNetUsers u
                LEFT JOIN AspNetUserRoles ur ON ur.UserId = u.Id
                LEFT JOIN AspNetRoles r      ON r.Id      = ur.RoleId
                LEFT JOIN AnalysisRequests ar ON ar.ClientId = u.Id
                WHERE r.NormalizedName = 'CLIENT'
                  AND u.FilialeName IS NOT NULL
                  AND u.FilialeName <> ''
                GROUP BY u.FilialeName
                ORDER BY nb_demandes DESC
                """
            )
            rows = cursor.fetchall()
            return [{"nom_centre": row[0], "nb_demandes": row[1]} for row in rows]
        except Exception as exc:
            log.error("get_centres : %s", exc)
            return []

    def get_souches(self) -> list[dict]:
        if not self._ensure_connected():
            return []
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT
                    s.Type           AS type_echantillon,
                    res.AnalysisName AS type_analyse,
                    COUNT(*)         AS nb_analyses
                FROM Samples s
                INNER JOIN AnalysisResults res ON res.SampleId = s.Id
                GROUP BY s.Type, res.AnalysisName
                ORDER BY nb_analyses DESC
                """
            )
            rows = cursor.fetchall()
            return [
                {"type_echantillon": row[0], "type_analyse": row[1], "nb_analyses": row[2]}
                for row in rows
            ]
        except Exception as exc:
            log.error("get_souches : %s", exc)
            return []

    def get_count(self) -> dict:
        if not self._ensure_connected():
            return {"analyses": 0, "labos": 0, "souches": 0, "centres": 0}
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM AnalysisRequests WHERE IsDraft = 0")
            nb_analyses = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Laboratories")
            nb_labos = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT s.Type) FROM Samples s")
            nb_souches = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(DISTINCT u.FilialeName) FROM AspNetUsers u "
                "WHERE u.FilialeName IS NOT NULL AND u.FilialeName <> ''"
            )
            nb_centres = cursor.fetchone()[0]
            return {"analyses": nb_analyses, "labos": nb_labos, "souches": nb_souches, "centres": nb_centres}
        except Exception as exc:
            log.error("get_count : %s", exc)
            return {"analyses": 0, "labos": 0, "souches": 0, "centres": 0}

    # ------------------------------------------------------------------
    # Sessions de chat (stubs RAM)
    # ------------------------------------------------------------------

    def create_session(self, session_id: str, user_id: str) -> bool:
        return True

    def save_message(self, session_id: str, role: str, content: str) -> bool:
        return True

    def get_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        return []

    def update_session_inactive(self, session_id: str) -> None:
        pass


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------

def get_db(settings=None) -> SqlServerDatabase:
    if settings is not None:
        server   = getattr(settings, "SQLSERVER_SERVER",   None)
        database = getattr(settings, "SQLSERVER_DATABASE", None)
        driver   = getattr(settings, "SQLSERVER_DRIVER",   None)
        return SqlServerDatabase(server=server, database=database, driver=driver)
    return SqlServerDatabase()