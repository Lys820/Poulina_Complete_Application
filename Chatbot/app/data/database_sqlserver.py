"""
Database Service — SQL Server (PouleLabDB)
Connecté à la BD de l'AnalyseApp (.NET / ASP.NET Identity)
Les tables auth (users, roles, sessions) viennent de PouleLabDB.
Les données métier (analyses, labos) viennent de la même BD via les vues/tables POULINA.
"""
from __future__ import annotations
import logging
from typing import Tuple, Optional
import pandas as pd
import pyodbc

log = logging.getLogger(__name__)


def _query_to_df(conn: pyodbc.Connection, query: str) -> pd.DataFrame:
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        columns = [desc[0].lower() for desc in cursor.description]
        rows = cursor.fetchall()
        return pd.DataFrame([list(r) for r in rows], columns=columns)
    finally:
        cursor.close()


class SQLServerDB:

    def __init__(self, server, database, user="", password="",
                 driver="ODBC Driver 17 for SQL Server", trusted="no"):
        self.server   = server
        self.database = database
        self.user     = user
        self.password = password
        self.driver   = driver
        self.trusted  = trusted
        self._conn: Optional[pyodbc.Connection] = None

    def connect(self) -> bool:
        try:
            if self.trusted.lower() == "yes":
                cs = (f"DRIVER={{{self.driver}}};SERVER={self.server};"
                      f"DATABASE={self.database};Trusted_Connection=yes;"
                      f"TrustServerCertificate=yes;")
            else:
                cs = (f"DRIVER={{{self.driver}}};SERVER={self.server};"
                      f"DATABASE={self.database};UID={self.user};PWD={self.password};"
                      f"TrustServerCertificate=yes;")
            self._conn = pyodbc.connect(cs)
            log.info("SQL Server connecté: %s/%s", self.server, self.database)
            return True
        except Exception as e:
            log.error("Erreur connexion SQL Server: %s", e)
            return False

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def query_one(self, query: str, params=None) -> Optional[dict]:
        cursor = self._conn.cursor()
        try:
            cursor.execute(query, params or [])
            row = cursor.fetchone()
            if not row:
                return None
            cols = [desc[0].lower() for desc in cursor.description]
            return dict(zip(cols, row))
        finally:
            cursor.close()

    # ── Auth — lecture sur PouleLabDB (ASP.NET Identity) ────────────────────

    def get_utilisateur_par_email(self, email: str) -> Optional[dict]:
        """
        Lit depuis les tables ASP.NET Identity de PouleLabDB.
        Retourne un dict compatible avec l'existant du chatbot :
          id_utilisateur, password_hash, nom, prenom, actif, nom_role, permissions
        """
        query = """
        SELECT
            u.Id                AS id_utilisateur,
            u.PasswordHash      AS password_hash,
            u.LastName          AS nom,
            u.FirstName         AS prenom,
            u.IsActive          AS actif,
            r.Name              AS nom_role
        FROM dbo.AspNetUsers u
        LEFT JOIN dbo.AspNetUserRoles ur ON ur.UserId = u.Id
        LEFT JOIN dbo.AspNetRoles r      ON r.Id = ur.RoleId
        WHERE u.Email = ?
          AND u.IsActive = 1
        """
        cursor = self._conn.cursor()
        try:
            cursor.execute(query, (email,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [desc[0].lower() for desc in cursor.description]
            result = dict(zip(cols, row))
            # Permissions : basées sur le rôle (mapping statique)
            result["permissions"] = _role_to_permissions(result.get("nom_role", ""))
            return result
        finally:
            cursor.close()

    # ── Sessions chat — tables gardées dans PouleLabDB ──────────────────────
    # On crée session_chat et message_chat dans PouleLabDB si elles n'existent pas.

    def ensure_chat_tables(self) -> None:
        """Crée les tables session_chat / message_chat dans PouleLabDB si absentes."""
        cursor = self._conn.cursor()
        try:
            cursor.execute("""
                IF OBJECT_ID('dbo.session_chat','U') IS NULL
                CREATE TABLE dbo.session_chat (
                    id_session              NVARCHAR(64) PRIMARY KEY,
                    user_id                 NVARCHAR(450) NOT NULL,  -- FK AspNetUsers.Id
                    date_debut              DATETIME2 DEFAULT GETDATE(),
                    date_derniere_activite  DATETIME2 DEFAULT GETDATE(),
                    actif                   BIT DEFAULT 1,
                    contexte_json           NVARCHAR(MAX) DEFAULT '{}'
                )
            """)
            cursor.execute("""
                IF OBJECT_ID('dbo.message_chat','U') IS NULL
                CREATE TABLE dbo.message_chat (
                    id_message   INT IDENTITY(1,1) PRIMARY KEY,
                    id_session   NVARCHAR(64) NOT NULL,
                    role         NVARCHAR(20) NOT NULL CHECK (role IN ('user','assistant')),
                    contenu      NVARCHAR(MAX) NOT NULL,
                    date_message DATETIME2 DEFAULT GETDATE()
                )
            """)
            self._conn.commit()
        finally:
            cursor.close()

    def get_session(self, session_id: str) -> Optional[dict]:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "SELECT id_session, user_id, actif FROM session_chat WHERE id_session = ?",
                (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            # Rétro-compatibilité : renommer user_id en id_utilisateur
            return {"id_session": row[0], "id_utilisateur": row[1], "actif": row[2]}
        finally:
            cursor.close()

    def create_session(self, session_id: str, user_id: str) -> None:
        """user_id est maintenant un GUID string (AspNetUsers.Id)."""
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO session_chat (id_session, user_id, date_debut, "
                "date_derniere_activite, actif, contexte_json) "
                "VALUES (?, ?, GETDATE(), GETDATE(), 1, '{}')",
                (session_id, user_id))
            self._conn.commit()
        finally:
            cursor.close()

    def get_messages(self, session_id: str, limit: int = 20) -> list[dict]:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "SELECT TOP (?) role, contenu FROM message_chat "
                "WHERE id_session = ? ORDER BY date_message ASC",
                (limit, session_id))
            return [{"role": r[0], "content": r[1]} for r in cursor.fetchall()]
        finally:
            cursor.close()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        cursor = self._conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO message_chat (id_session, role, contenu, date_message) "
                "VALUES (?, ?, ?, GETDATE())", (session_id, role, content))
            cursor.execute(
                "UPDATE session_chat SET date_derniere_activite=GETDATE() WHERE id_session=?",
                (session_id,))
            self._conn.commit()
        finally:
            cursor.close()

    def update_session_inactive(self, session_id: str) -> None:
        cursor = self._conn.cursor()
        try:
            cursor.execute("UPDATE session_chat SET actif=0 WHERE id_session=?", (session_id,))
            self._conn.commit()
        finally:
            cursor.close()

    # ── Données métier ───────────────────────────────────────────────────────

    def get_analyses_data(self) -> pd.DataFrame:
        query = """
        SELECT
            da.id_demande, da.num_analyse,
            ce.id_centre, ce.nom_centre,
            ce.gouvernorat AS ville, ce.gouvernorat AS region,
            ce.type_production,
            b.id_batiment, b.nom_batiment,
            s.id_souche, s.nom_souche AS meilleure_souche,
            s.fertilite_score AS fertilite_visee, s.taux_mortalite, s.resistance_maladies,
            ta.code_analyse AS type_analyse, ta.libelle AS libelle_analyse,
            da.type_echantillon, da.date_prelevement, da.date_analyse,
            da.date_resultat, da.priorite,
            da.est_conforme AS conforme, da.pourcentage_securite,
            da.statut, da.resultat_souche_detectee, da.niveau_satisfaction,
            lab.nom_labo, lab.gouvernorat AS labo_gouvernorat,
            CONCAT(lant.prenom,' ',lant.nom) AS nom_laborantin,
            lant.specialite AS specialite_laborantin,
            p.nom_pays AS pays_provenance,
            CASE
                WHEN MONTH(da.date_prelevement) IN (6,7,8)   THEN 'Ete'
                WHEN MONTH(da.date_prelevement) IN (3,4,5)   THEN 'Printemps'
                WHEN MONTH(da.date_prelevement) IN (9,10,11) THEN 'Automne'
                ELSE 'Hiver'
            END AS saison,
            b.capacite,
            ROUND(4.5  + (RAND(CHECKSUM(NEWID()))*2.0),  2) AS cout_aliment,
            ROUND(20.0 + (RAND(CHECKSUM(NEWID()))*20.0), 1) AS temperature_moyenne,
            ROUND(40.0 + (RAND(CHECKSUM(NEWID()))*30.0), 0) AS humidite,
            ROUND(85.0 + (RAND(CHECKSUM(NEWID()))*10.0), 0) AS biosecurite_score,
            ROUND(5.0  + (RAND(CHECKSUM(NEWID()))*25.0), 0) AS experience_equipe,
            ROUND(5.0  + (RAND(CHECKSUM(NEWID()))*25.0), 0) AS distance_labo,
            ROUND(30000+(RAND(CHECKSUM(NEWID()))*70000),  0) AS budget,
            COALESCE(hm_join.nom_maladie,'Aucune') AS historique_maladie,
            COALESCE(hm_join.est_critique,0)       AS maladie_critique
        FROM demande_analyse da
        LEFT JOIN centre_elevage ce  ON da.id_centre       = ce.id_centre
        LEFT JOIN batiment b         ON da.id_batiment     = b.id_batiment
        LEFT JOIN souche s           ON b.id_souche        = s.id_souche
        LEFT JOIN type_analyse ta    ON da.id_type_analyse = ta.id_type_analyse
        LEFT JOIN laboratoire lab    ON da.id_labo         = lab.id_labo
        LEFT JOIN laborantin lant    ON da.id_laborantin   = lant.id_laborantin
        LEFT JOIN pays p             ON da.id_pays_provenance = p.id_pays
        LEFT JOIN (
            SELECT hm2.id_centre, m2.nom_maladie, m2.est_critique
            FROM historique_maladie hm2
            JOIN maladie m2 ON hm2.id_maladie = m2.id_maladie
            WHERE hm2.id_historique IN (
                SELECT MAX(h3.id_historique) FROM historique_maladie h3 GROUP BY h3.id_centre
            )
        ) hm_join ON hm_join.id_centre = ce.id_centre
        WHERE ce.actif = 1
        ORDER BY da.date_analyse DESC
        OFFSET 0 ROWS FETCH NEXT 5000 ROWS ONLY
        """
        try:
            return _query_to_df(self._conn, query)
        except Exception as e:
            log.error("Erreur get_analyses_data: %s", e, exc_info=True)
            return pd.DataFrame()

    def get_labos_data(self) -> pd.DataFrame:
        query = """
        SELECT
            l.id_labo,
            l.nom_labo AS nom_laboratoire,
            l.gouvernorat AS ville, l.gouvernorat AS region,
            l.latitude, l.longitude, l.telephone, l.email, l.actif,
            COUNT(DISTINCT lab.id_laborantin) AS nb_laborantins,
            COALESCE(ROUND(AVG(sl.taux_conformite),1),95) AS taux_reussite_pct,
            COALESCE(SUM(sl.nb_analyses_effectuees),0)    AS nb_analyses_effectuees,
            COALESCE(ROUND(AVG(sl.duree_moy_jours),1),3)  AS delai_standard_jours,
            CASE
                WHEN COALESCE(ROUND(AVG(sl.duree_moy_jours),1),3) <= 2 THEN 12
                WHEN COALESCE(ROUND(AVG(sl.duree_moy_jours),1),3) <= 3 THEN 18
                ELSE 24
            END AS delai_urgence_heures,
            1 AS accepte_urgence, 1 AS certifie_iso,
            1 AS equipement_pcr,  1 AS equipement_elisa,
            COALESCE(MAX(lab.annees_experience),5) AS annees_experience_labo,
            ROUND(8.0+(COALESCE(ROUND(AVG(sl.taux_conformite),1),95)/100.0)*1.5,1) AS score_global,
            CASE
                WHEN ROUND(8.0+(COALESCE(ROUND(AVG(sl.taux_conformite),1),95)/100.0)*1.5,1)>=9.0 THEN 'Excellent'
                WHEN ROUND(8.0+(COALESCE(ROUND(AVG(sl.taux_conformite),1),95)/100.0)*1.5,1)>=8.0 THEN 'Bon'
                ELSE 'Passable'
            END AS tier_labo,
            'Prive' AS type_laboratoire
        FROM laboratoire l
        LEFT JOIN laborantin lab ON lab.id_labo = l.id_labo
        LEFT JOIN stats_labo sl  ON sl.id_labo  = l.id_labo
        WHERE l.actif = 1
        GROUP BY l.id_labo, l.nom_labo, l.gouvernorat, l.latitude, l.longitude,
                 l.telephone, l.email, l.actif
        """
        try:
            return _query_to_df(self._conn, query)
        except Exception as e:
            log.error("Erreur get_labos_data: %s", e, exc_info=True)
            return pd.DataFrame()

    def get_all_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if not self._conn:
            self.connect()
        return self.get_analyses_data(), self.get_labos_data()


# ── Mapping rôles → permissions ──────────────────────────────────────────────

def _role_to_permissions(role: str) -> str:
    """
    Convertit un rôle ASP.NET Identity en liste de permissions chatbot.
    Adapte selon les rôles définis dans DataSeeder.cs :
    Administrator, Manager, Receptionist, Analyst, LabChief, Client
    """
    mapping = {
        "Administrator": "CHAT_READ,CHAT_ML,ADMIN_TRAIN,ANALYSE_READ,ANALYSE_WRITE",
        "Manager":       "CHAT_READ,CHAT_ML,ADMIN_TRAIN,ANALYSE_READ",
        "LabChief":      "CHAT_READ,CHAT_ML,ANALYSE_READ,ANALYSE_WRITE",
        "Analyst":       "CHAT_READ,ANALYSE_READ,ANALYSE_WRITE",
        "Receptionist":  "CHAT_READ,ANALYSE_READ",
        "Client":        "CHAT_READ",
    }
    return mapping.get(role, "CHAT_READ")


# ── Dépendance FastAPI ────────────────────────────────────────────────────────

def get_db(settings=None) -> SQLServerDB:
    """
    Utilisable comme Depends(get_db) dans FastAPI.
    Pointe désormais vers PouleLabDB (BD de l'AnalyseApp .NET).
    """
    from app.core.config import get_settings
    if settings is None:
        settings = get_settings()
    return SQLServerDB(
        server=settings.SQLSERVER_SERVER,
        database=settings.SQLSERVER_DATABASE,
        user=getattr(settings, "SQLSERVER_USER", ""),
        password=getattr(settings, "SQLSERVER_PASSWORD", ""),
        driver=getattr(settings, "SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server"),
        trusted=getattr(settings, "SQLSERVER_TRUSTED", "no"),
    )