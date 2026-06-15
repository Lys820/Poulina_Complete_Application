"""
app/data/database_mysql.py  (remplace database_sqlserver.py)
Couche d'accès aux données — base PouleLabDB sur MySQL local.

Tables ciblées (schéma EF Core / ASP.NET Identity migré vers MySQL) :
  - AspNetUsers / AspNetRoles / AspNetUserRoles  → authentification
  - Laboratories                                  → labos d'analyse
  - AnalysisRequests                              → demandes
  - Samples                                       → échantillons
  - AnalysisResults                               → résultats
  - Breeds                                        → souches avicoles
  - FarmCenters                                   → centres d'élevage
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)


class SqlServerDatabase:
    """
    Connexion MySQL locale à PouleLabDB.
    Le nom de classe est conservé pour ne pas modifier les imports existants.
    """

    def __init__(
        self,
        server: Optional[str] = None,
        database: Optional[str] = None,
        driver: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        # Accepte les anciens paramètres (server, database) ET les nouveaux (host, port)
        self._host     = host or server or os.getenv("MYSQL_HOST", "localhost")
        self._port     = port or int(os.getenv("MYSQL_PORT", "3306"))
        self._database = database or os.getenv("MYSQL_DATABASE", "PouleLabDB")
        self._user     = user or os.getenv("MYSQL_USER", "root")
        self._password = password or os.getenv("MYSQL_PASSWORD", "")
        self._conn     = None

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        try:
            import mysql.connector
            self._conn = mysql.connector.connect(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._user,
                password=self._password,
                connection_timeout=5,
                charset="utf8mb4",
            )
            log.info("Connexion MySQL OK — %s:%s / %s", self._host, self._port, self._database)
            return True
        except Exception as exc:
            log.error("Connexion MySQL impossible : %s", exc)
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
        try:
            self._conn.ping(reconnect=True)
            return True
        except Exception:
            return self.connect()

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
            cursor = self._cursor()
            cursor.execute(
                """
                SELECT
                    u.Id              AS id_utilisateur,
                    u.PasswordHash    AS password_hash,
                    u.LastName        AS nom,
                    u.FirstName       AS prenom,
                    u.FilialeName     AS filiale,
                    u.IsActive        AS actif,
                    IFNULL(r.Name, '') AS nom_role,
                    c.ClaimValue      AS permissions
                FROM AspNetUsers u
                LEFT JOIN AspNetUserRoles ur ON ur.UserId  = u.Id
                LEFT JOIN AspNetRoles r      ON r.Id       = ur.RoleId
                LEFT JOIN AspNetUserClaims c ON c.UserId   = u.Id
                                            AND c.ClaimType = 'permissions'
                WHERE UPPER(u.NormalizedEmail) = %s
                """,
                (email.upper(),),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return {
                "id_utilisateur": row["id_utilisateur"],
                "password_hash":  row["password_hash"],
                "nom":            row["nom"],
                "prenom":         row["prenom"],
                "filiale":        row["filiale"],
                "actif":          int(row["actif"]) if row["actif"] is not None else 0,
                "nom_role":       row["nom_role"],
                "permissions":    row["permissions"],
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
                    IFNULL(ar.Brand, 'Standard')            AS meilleure_souche,
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
                    IFNULL(s.Type, 'Poulet de chair')       AS type_production,
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
                    IFNULL(res.AnalysisName, 'Aucune')      AS historique_maladie
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
        return SqlServerDatabase(
            host=getattr(settings, "MYSQL_HOST", "localhost"),
            port=getattr(settings, "MYSQL_PORT", 3306),
            database=getattr(settings, "MYSQL_DATABASE", "PouleLabDB"),
            user=getattr(settings, "MYSQL_USER", "root"),
            password=getattr(settings, "MYSQL_PASSWORD", ""),
        )
    return SqlServerDatabase()