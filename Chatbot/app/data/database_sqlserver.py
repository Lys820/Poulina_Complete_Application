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
        self._server = server or os.getenv("SQLSERVER_SERVER", r"VICTUSL\SQLEXPRESS")
        self._database = database or os.getenv("SQLSERVER_DATABASE", "PouleLabDB")
        self._driver = driver or os.getenv(
            "SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server"
        )
        self._conn_str = (
            f"DRIVER={{{self._driver}}};"
            f"SERVER={self._server};"
            f"DATABASE={self._database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        self._conn: Optional[pyodbc.Connection] = None

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        try:
            self._conn = pyodbc.connect(self._conn_str, timeout=10)
            log.info("Connexion PouleLabDB OK (%s / %s)", self._server, self._database)
            return True
        except Exception as exc:
            log.error("Connexion PouleLabDB échouée : %s", exc)
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
        """
        Retourne un dict avec les champs attendus par app/api/auth.py.
        Jointure : AspNetUsers → AspNetUserRoles → AspNetRoles.
        """
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
        Jointure : AnalysisRequests → Samples → AnalysisResults → Laboratories → AspNetUsers.
        Retourne un DataFrame vide si la base ne contient pas encore de données.
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
                    u.FirstName + ' ' + u.LastName  AS nom_client,
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
                    res.RecordedAt      AS date_resultat
                FROM AnalysisRequests ar
                INNER JOIN Laboratories l  ON l.Id  = ar.LaboratoryId
                INNER JOIN AspNetUsers  u  ON u.Id  = ar.ClientId
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

    # Alias pour compatibilité avec l'ancien nom utilisé dans certains tests
    def get_analyses_data(self) -> pd.DataFrame:
        return self.get_analyses()

    def get_labos(self) -> pd.DataFrame:
        """
        Retourne les laboratoires de PouleLabDB pour le RAG et le scoring.
        Les colonnes calculées (score_global, tier_labo, etc.) sont fournies
        avec des valeurs par défaut quand elles ne sont pas en base.
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
                    -- Colonnes calculées/dérivées (valeurs par défaut)
                    7.0             AS score_global,
                    'B'             AS tier_labo,
                    1               AS accepte_urgence,
                    1               AS certifie_iso
                FROM Laboratories l
                ORDER BY l.Id
            """
            df = pd.read_sql(query, self._conn)
            log.info("get_labos : %d laboratoires chargés", len(df))
            return df
        except Exception as exc:
            log.error("get_labos : %s", exc)
            return pd.DataFrame()

    # Alias
    def get_labos_data(self) -> pd.DataFrame:
        return self.get_labos()

    def get_all_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Retourne (df_analyses, df_labos) en une seule connexion."""
        if not self._ensure_connected():
            return pd.DataFrame(), pd.DataFrame()
        return self.get_analyses(), self.get_labos()

    # ------------------------------------------------------------------
    # Données de référence pour les endpoints /data/*
    # ------------------------------------------------------------------

    def get_centres(self) -> list[dict]:
        """
        Les centres d'élevage sont les filiales des clients dans PouleLabDB.
        Retourne les filiales distinctes des utilisateurs avec rôle Client.
        """
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
            return [
                {"nom_centre": row[0], "nb_demandes": row[1]}
                for row in rows
            ]
        except Exception as exc:
            log.error("get_centres : %s", exc)
            return []

    def get_souches(self) -> list[dict]:
        """
        Les souches sont déduites des types d'échantillons et des analyses.
        Retourne les combinaisons type_echantillon / type_analyse distinctes.
        """
        if not self._ensure_connected():
            return []
        try:
            cursor = self._conn.cursor()
            cursor.execute(
                """
                SELECT DISTINCT
                    s.Type          AS type_echantillon,
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
                {
                    "type_echantillon": row[0],
                    "type_analyse":     row[1],
                    "nb_analyses":      row[2],
                }
                for row in rows
            ]
        except Exception as exc:
            log.error("get_souches : %s", exc)
            return []

    def get_count(self) -> dict:
        """Compteurs globaux pour l'endpoint /data/count."""
        if not self._ensure_connected():
            return {"analyses": 0, "labos": 0, "souches": 0, "centres": 0}
        try:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM AnalysisRequests WHERE IsDraft = 0")
            nb_analyses = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Laboratories")
            nb_labos = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(DISTINCT s.Type) FROM Samples s"
            )
            nb_souches = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(DISTINCT u.FilialeName) "
                "FROM AspNetUsers u "
                "WHERE u.FilialeName IS NOT NULL AND u.FilialeName <> ''"
            )
            nb_centres = cursor.fetchone()[0]
            return {
                "analyses": nb_analyses,
                "labos":    nb_labos,
                "souches":  nb_souches,
                "centres":  nb_centres,
            }
        except Exception as exc:
            log.error("get_count : %s", exc)
            return {"analyses": 0, "labos": 0, "souches": 0, "centres": 0}

    # ------------------------------------------------------------------
    # Sessions de chat (compatibilité avec les anciens appels)
    # ------------------------------------------------------------------

    def create_session(self, session_id: str, user_id: str) -> bool:
        """Stub — les sessions sont en RAM dans cette version."""
        return True

    def save_message(
        self, session_id: str, role: str, content: str
    ) -> bool:
        """Stub — les messages sont en RAM dans cette version."""
        return True

    def get_messages(
        self, session_id: str, limit: int = 20
    ) -> list[dict]:
        """Stub — retourne une liste vide (mémoire RAM uniquement)."""
        return []

    def update_session_inactive(self, session_id: str) -> None:
        """Stub."""


# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------

def get_db(settings=None) -> SqlServerDatabase:
    """
    Retourne une instance de SqlServerDatabase.
    Si settings est fourni (injection FastAPI), utilise ses attributs.
    Sinon, lit les variables d'environnement.
    """
    if settings is not None:
        server   = getattr(settings, "SQLSERVER_SERVER",   None)
        database = getattr(settings, "SQLSERVER_DATABASE", None)
        driver   = getattr(settings, "SQLSERVER_DRIVER",   None)
        return SqlServerDatabase(server=server, database=database, driver=driver)
    return SqlServerDatabase()