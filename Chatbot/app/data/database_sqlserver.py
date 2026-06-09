"""
app/data/database_sqlserver.py
────────────────────────────────────────────────────────────────────────────
Accès à la base PouleLabDB (partagée avec l'API .NET / ASP.NET Identity).

⚠️  CHANGEMENTS MAJEURS par rapport à l'ancienne base POULINA :
  - Base         : POULINA           → PouleLabDB
  - Table users  : dbo.utilisateur   → dbo.AspNetUsers
  - Colonne ID   : id_utilisateur (int) → Id (nvarchar GUID)
  - Colonne email: email             → Email (+ NormalizedEmail)
  - Colonne mdp  : password_hash     → PasswordHash (Base64 PBKDF2-v3)
  - Colonne actif: actif (bit)       → IsActive (bit)
  - Rôles        : colonne nom_role  → table AspNetUserRoles + AspNetRoles
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import pyodbc
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

def _build_connection_string() -> str:
    server   = os.getenv("SQLSERVER_SERVER", r"localhost\SQLEXPRESS")
    database = os.getenv("SQLSERVER_DATABASE", "PouleLabDB")   # ✅ défaut corrigé
    driver   = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")
    trusted  = os.getenv("SQLSERVER_TRUSTED", "yes").lower() == "yes"
    user     = os.getenv("SQLSERVER_USER", "")
    password = os.getenv("SQLSERVER_PASSWORD", "")

    base = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "TrustServerCertificate=yes;"
    )

    if trusted or not user:
        return base + "Trusted_Connection=yes;"
    else:
        return base + f"UID={user};PWD={password};"


# ──────────────────────────────────────────────────────────────────────────────
# Classe principale
# ──────────────────────────────────────────────────────────────────────────────

class SqlServerDatabase:
    """
    Accès à PouleLabDB.
    Les IDs utilisateurs sont des GUIDs (string), pas des entiers.
    """

    def __init__(self):
        self._conn_str = _build_connection_string()
        self._conn: Optional[pyodbc.Connection] = None

    # ── Connexion ──────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        try:
            self._conn = pyodbc.connect(self._conn_str, timeout=5)
            log.info("✅ Connecté à PouleLabDB")
            return True
        except pyodbc.Error as e:
            log.error(f"❌ Connexion PouleLabDB échouée : {e}")
            return False

    def disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _cursor(self):
        if not self._conn:
            self.connect()
        return self._conn.cursor()

    # ── Utilisateurs (ASP.NET Identity) ───────────────────────────────────────

    def get_utilisateur_par_email(self, email: str) -> Optional[dict]:
        """
        Recherche un utilisateur dans AspNetUsers.
        Retourne un dict avec les champs nécessaires à l'authentification,
        ou None si introuvable.

        ✅ Id est un GUID string (ex: "a1b2c3d4-e5f6-...")
        ✅ Rôle récupéré via AspNetUserRoles + AspNetRoles
        """
        try:
            cur = self._cursor()

            # NormalizedEmail est stocké en majuscules par ASP.NET Identity
            normalized = email.upper()

            cur.execute("""
                SELECT
                    u.Id,
                    u.Email,
                    u.PasswordHash,
                    u.IsActive,
                    u.FirstName,
                    u.LastName,
                    r.Name AS RoleName
                FROM dbo.AspNetUsers u
                LEFT JOIN dbo.AspNetUserRoles ur ON ur.UserId = u.Id
                LEFT JOIN dbo.AspNetRoles r      ON r.Id = ur.RoleId
                WHERE u.NormalizedEmail = ?
            """, normalized)

            row = cur.fetchone()
            if row is None:
                return None

            return {
                "id_utilisateur": row.Id,          # GUID string
                "email":          row.Email,
                "password_hash":  row.PasswordHash, # Base64 PBKDF2-v3
                "actif":          row.IsActive,
                "nom":            row.LastName  or "",
                "prenom":         row.FirstName or "",
                "nom_role":       row.RoleName  or "Client",
                # Permissions par défaut selon le rôle
                "permissions":    _permissions_pour_role(row.RoleName),
            }

        except pyodbc.Error as e:
            log.error(f"get_utilisateur_par_email({email}) : {e}")
            return None

    # ── Données métier ─────────────────────────────────────────────────────────

    def get_analyses(self, limit: int = 1000) -> list[dict]:
        """Retourne les demandes d'analyse pour l'entraînement du modèle ML."""
        try:
            cur = self._cursor()
            cur.execute(f"""
                SELECT TOP {limit} *
                FROM dbo.AnalysisRequests
                ORDER BY CreatedAt DESC
            """)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except pyodbc.Error as e:
            log.error(f"get_analyses : {e}")
            return []

    def get_labos(self) -> list[dict]:
        """Retourne les laboratoires actifs."""
        try:
            cur = self._cursor()
            cur.execute("""
                SELECT *
                FROM dbo.Laboratories
                ORDER BY Name
            """)
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except pyodbc.Error as e:
            log.error(f"get_labos : {e}")
            return []

    def get_centres(self, gouvernorat: Optional[str] = None) -> list[dict]:
        """Retourne les centres d'élevage, avec filtre optionnel par gouvernorat."""
        try:
            cur = self._cursor()
            if gouvernorat:
                cur.execute(
                    "SELECT * FROM dbo.Farms WHERE Gouvernorat = ? ORDER BY Name",
                    gouvernorat
                )
            else:
                cur.execute("SELECT * FROM dbo.Farms ORDER BY Name")
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except pyodbc.Error as e:
            log.error(f"get_centres : {e}")
            return []

    # ── Health check ───────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Vérifie que la connexion est vivante."""
        try:
            cur = self._cursor()
            cur.execute("SELECT 1")
            return True
        except Exception:
            return False


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _permissions_pour_role(role: Optional[str]) -> list[str]:
    """
    Mappe un rôle ASP.NET Identity vers des permissions Python.
    Adapte selon les rôles définis dans DataSeeder.cs.
    """
    mapping = {
        "Admin":    ["CHAT_READ", "CHAT_ML", "ADMIN", "DATA_WRITE"],
        "Analyst":  ["CHAT_READ", "CHAT_ML", "DATA_WRITE"],
        "Client":   ["CHAT_READ"],
    }
    return mapping.get(role or "", ["CHAT_READ"])


# ──────────────────────────────────────────────────────────────────────────────
# Singleton
# ──────────────────────────────────────────────────────────────────────────────

_db_instance: Optional[SqlServerDatabase] = None


def get_db() -> SqlServerDatabase:
    """Retourne l'instance singleton de la base de données."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SqlServerDatabase()
        _db_instance.connect()
    return _db_instance