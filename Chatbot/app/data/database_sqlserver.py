"""
app/data/database_sqlserver.py
Couche d'accès aux données — base PouleLabDB (localhost)
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

_DEFAULT_CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=PouleLabDB;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)


class SqlServerDatabase:
    """Connexion à PouleLabDB via chaîne de connexion ODBC."""

    def __init__(self, connection_string: Optional[str] = None) -> None:
        self._conn_str = (
            connection_string
            or os.getenv("SQLSERVER_CONNECTION_STRING", _DEFAULT_CONN_STR)
        )
        self._conn: Optional[pyodbc.Connection] = None

    def connect(self) -> bool:
        try:
            self._conn = pyodbc.connect(self._conn_str, timeout=5)
            log.info("Connexion SQL Server OK")
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

    # ... (le reste des méthodes — get_utilisateur_par_email, get_all_data, etc. — reste identique)

    def _cursor(self):
        """Retourne un curseur avec dictionnaire activé."""
        return self._conn.cursor(dictionary=True)

    # ------------------------------------------------------------------
    # Authentification
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
                    c.ClaimValue        AS permissions
                FROM AspNetUsers u
                LEFT JOIN AspNetUserRoles ur  ON ur.UserId  = u.Id
                LEFT JOIN AspNetRoles r       ON r.Id       = ur.RoleId
                LEFT JOIN AspNetUserClaims c  ON c.UserId   = u.Id
                                            AND c.ClaimType = 'permissions'
                WHERE u.NormalizedEmail = ?
                """,
                email.upper(),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            # Accès par index (0-7) — pyodbc ne supporte pas l'accès par attribut
            # sur les alias SQL en dehors du mode Row Factory
            return {
                "id_utilisateur": str(row[0]),
                "password_hash":  row[1],
                "nom":            row[2],
                "prenom":         row[3],
                "filiale":        row[4],
                "actif":          int(row[5]) if row[5] is not None else 0,
                "nom_role":       row[6],
                "permissions":    row[7],
            }
        except Exception as exc:
            log.error("get_utilisateur_par_email(%s) : %s", email, exc)
            return None
    # ------------------------------------------------------------------
    # Données d'entraînement ML / RAG
    # ------------------------------------------------------------------

    def get_analyses(self) -> pd.DataFrame:
        if not self._ensure_connected():
            return pd.DataFrame()
        try:
            query = """
                SELECT
                    ar.Id                                   AS id_demande,
                    ar.Status                               AS statut,
                    l.Name                                  AS nom_laboratoire,
                    l.Address                               AS adresse_laboratoire,
                    ISNULL(ar.Brand, 'Standard')            AS meilleure_souche,
                    7.0                                     AS biosecurite_score,
                    3.0                                     AS taux_mortalite,
                    90.0                                    AS fertilite_visee,
                    10000                                   AS capacite,
                    500                                     AS surface_m2,
                    0                                       AS altitude,
                    5.0                                     AS cout_aliment,
                    5                                       AS experience_equipe,
                    20                                      AS distance_labo,
                    50000                                   AS budget,
                    25.0                                    AS temperature_moyenne,
                    60.0                                    AS humidite,
                    ISNULL(s.Type, 'Poulet de chair')       AS type_production,
                    CASE
                        WHEN MONTH(ar.CreatedAt) IN (12,1,2)  THEN 'Hiver'
                        WHEN MONTH(ar.CreatedAt) IN (3,4,5)   THEN 'Printemps'
                        WHEN MONTH(ar.CreatedAt) IN (6,7,8)   THEN 'Ete'
                        ELSE 'Automne'
                    END                                     AS saison,
                    'Non renseigné'                         AS region,
                    'Moyen'                                 AS demande_marche,
                    CASE
                        WHEN ar.Status = 'Completed'
                             AND (res.IsAnomaly IS NULL OR res.IsAnomaly = 0)
                        THEN 1 ELSE 0
                    END                                     AS conforme,
                    ISNULL(res.AnalysisName, 'Aucune')      AS historique_maladie
                FROM AnalysisRequests ar
                INNER JOIN Laboratories l   ON l.Id = ar.LaboratoryId
                INNER JOIN AspNetUsers  u   ON u.Id = ar.ClientId
                LEFT  JOIN Samples      s   ON s.RequestId   = ar.Id
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
        if not self._ensure_connected():
            return pd.DataFrame()
        try:
            query = """
                SELECT
                    l.Id            AS id_labo,
                    l.Name          AS nom_laboratoire,
                    l.Address       AS ville,
                    l.Description   AS description,
                    l.TemplateType  AS type_template,
                    8.0             AS score_global,
                    1               AS accepte_urgence,
                    24              AS delai_urgence_heures,
                    95.0            AS taux_reussite_pct,
                    'Standard'      AS tier_labo,
                    5               AS nb_analyses_disponibles_semaine,
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
    # Endpoints /data/*
    # ------------------------------------------------------------------

    def get_centres(self) -> list[dict]:
        if not self._ensure_connected():
            return []
        try:
            cursor = self._cursor()
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
            return cursor.fetchall()
        except Exception as exc:
            log.error("get_centres : %s", exc)
            return []

    def get_souches(self) -> list[dict]:
        return self.get_breeds()

    def get_breeds(self) -> list[dict]:
        if not self._ensure_connected():
            return []
        try:
            cursor = self._cursor()
            cursor.execute(
                """
                SELECT Id, Name, ProductionType, Origin, Description, AverageScore
                FROM Breeds
                WHERE IsActive = 1
                ORDER BY ProductionType, AverageScore DESC
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "id":              row["Id"],
                    "nom":             row["Name"],
                    "type_production": row["ProductionType"],
                    "origine":         row["Origin"],
                    "description":     row["Description"],
                    "score_moyen":     row["AverageScore"],
                }
                for row in rows
            ]
        except Exception as exc:
            log.error("get_breeds : %s", exc)
            return []

    def get_farm_centers(self) -> list[dict]:
        if not self._ensure_connected():
            return []
        try:
            cursor = self._cursor()
            cursor.execute(
                """
                SELECT Id, Name, Governorate, Address, Capacity, FarmingType
                FROM FarmCenters
                WHERE IsActive = 1
                ORDER BY Name
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "id":           row["Id"],
                    "nom":          row["Name"],
                    "gouvernorat":  row["Governorate"],
                    "adresse":      row["Address"],
                    "capacite":     row["Capacity"],
                    "type_elevage": row["FarmingType"],
                }
                for row in rows
            ]
        except Exception as exc:
            log.error("get_farm_centers : %s", exc)
            return []

    def get_count(self) -> dict:
        if not self._ensure_connected():
            return {"analyses": 0, "labos": 0, "souches": 0, "centres": 0}
        try:
            cursor = self._cursor()
            cursor.execute("SELECT COUNT(*) AS n FROM AnalysisRequests WHERE IsDraft = 0")
            nb_analyses = cursor.fetchone()["n"]
            cursor.execute("SELECT COUNT(*) AS n FROM Laboratories")
            nb_labos = cursor.fetchone()["n"]
            cursor.execute("SELECT COUNT(*) AS n FROM Breeds WHERE IsActive = 1")
            nb_breeds = cursor.fetchone()["n"]
            cursor.execute("SELECT COUNT(*) AS n FROM FarmCenters WHERE IsActive = 1")
            nb_centers = cursor.fetchone()["n"]
            return {
                "analyses": nb_analyses,
                "labos":    nb_labos,
                "souches":  nb_breeds,
                "centres":  nb_centers,
            }
        except Exception as exc:
            log.error("get_count : %s", exc)
            return {"analyses": 0, "labos": 0, "souches": 0, "centres": 0}

    # ------------------------------------------------------------------
    # Sessions (RAM — stubs inchangés)
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
# Factory — compatible avec tous les imports existants
# ------------------------------------------------------------------

def get_db(settings=None) -> SqlServerDatabase:
    if settings is not None:
        conn_str = getattr(settings, "SQLSERVER_CONNECTION_STRING", None)
        return SqlServerDatabase(connection_string=conn_str)
    return SqlServerDatabase()