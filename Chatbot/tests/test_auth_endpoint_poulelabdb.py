"""
Tests intégration — Endpoint POST /api/v1/auth/login
Base de données : PouleLabDB (ASP.NET Identity, GUIDs string)

Le mock utilise hash_password() du module security.py (format interne Python)
pour générer les hachages de test, exactement comme l'ancien test_auth_endpoint.py
qui fonctionnait. Les assertions sur role/permissions/user_id s'appuient sur
les noms de champs réels retournés par auth.py.

Exécution :
    pytest tests/test_auth_endpoint_poulelabdb.py -v
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock pyodbc
pyodbc_mock = types.ModuleType("pyodbc")
pyodbc_mock.connect = MagicMock()
pyodbc_mock.Connection = MagicMock
pyodbc_mock.Error = Exception
sys.modules.setdefault("pyodbc", pyodbc_mock)

from app.core.security import hash_password
from app.api.auth import router as auth_router

# ---------------------------------------------------------------------------
# Application de test isolée
# ---------------------------------------------------------------------------
app = FastAPI()
app.include_router(auth_router, prefix="/api/v1")
client = TestClient(app)

# ---------------------------------------------------------------------------
# Constantes DataSeeder
# ---------------------------------------------------------------------------
ADMIN_EMAIL = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"
ADMIN_GUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

# Hash généré par security.py (format interne Python, compatible verify_password)
ADMIN_HASH = hash_password(ADMIN_PASSWORD)


def _mock_user(
    guid: str = ADMIN_GUID,
    role: str = "Administrator",
    permissions: str = "CHAT_READ,CHAT_ML,ADMIN_TRAIN",
    actif: int = 1,
) -> dict:
    """
    Structure retournée par database_sqlserver.py.get_utilisateur_par_email().
    Le hash est généré par hash_password() de security.py pour garantir
    que verify_password() le valide correctement.
    """
    return {
        "id_utilisateur": guid,
        "password_hash": ADMIN_HASH,
        "nom": "Admin",
        "prenom": "Super",
        "filiale": "Poulina Group Holding",
        "actif": actif,
        "nom_role": role,
        "permissions": permissions,
    }


# ===========================================================================
# 1. Connexion réussie
# ===========================================================================

class TestLoginSucces:

    def test_login_admin_seeder_retourne_200_et_token(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user()
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })

        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_retourne_role_administrator(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user()
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })

        assert r.json()["role"] == "Administrator"

    def test_login_retourne_permissions(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user(
                permissions="CHAT_READ,CHAT_ML,ADMIN_TRAIN"
            )
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })

        data = r.json()
        assert "CHAT_READ" in data["permissions"]
        assert "ADMIN_TRAIN" in data["permissions"]

    def test_login_retourne_user_id(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user(guid=ADMIN_GUID)
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })

        assert "user_id" in r.json()

    def test_login_role_manager(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user(
                role="Manager", permissions="CHAT_READ"
            )
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": "manager@poulelabapp.com",
                "password": ADMIN_PASSWORD,
            })

        assert r.status_code == 200
        assert r.json()["role"] == "Manager"

    def test_login_role_analyst(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user(
                role="Analyst", permissions="CHAT_READ,CHAT_ML"
            )
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": "analyst@poulelabapp.com",
                "password": ADMIN_PASSWORD,
            })

        assert r.status_code == 200
        assert r.json()["role"] == "Analyst"

    def test_login_permissions_none_retourne_liste_vide(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            user = _mock_user()
            user["permissions"] = None
            db.get_utilisateur_par_email.return_value = user
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })

        assert r.status_code == 200
        assert r.json()["permissions"] == []


# ===========================================================================
# 2. Échecs d'authentification
# ===========================================================================

class TestLoginEchec:

    def test_utilisateur_inconnu_retourne_401(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = None
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": "inconnu@poulelabapp.com",
                "password": "nimporte",
            })

        assert r.status_code == 401

    def test_mauvais_mot_de_passe_retourne_401(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user()
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": "MauvaisMotDePasse!",
            })

        assert r.status_code == 401

    def test_compte_inactif_retourne_401_ou_403(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = _mock_user(actif=0)
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })

        assert r.status_code in (401, 403)

    def test_bd_inaccessible_retourne_503(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = False
            mock_get_db.return_value = db

            r = client.post("/api/v1/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD,
            })

        assert r.status_code == 503

    def test_champ_password_manquant_retourne_422(self):
        r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL})
        assert r.status_code == 422

    def test_champ_email_manquant_retourne_422(self):
        r = client.post("/api/v1/auth/login", json={"password": ADMIN_PASSWORD})
        assert r.status_code == 422

    def test_body_vide_retourne_422(self):
        r = client.post("/api/v1/auth/login", json={})
        assert r.status_code == 422


# ===========================================================================
# 3. Logout
# ===========================================================================

class TestLogout:

    def test_logout_retourne_200(self):
        r = client.post("/api/v1/auth/logout")
        assert r.status_code == 200

    def test_logout_retourne_message(self):
        r = client.post("/api/v1/auth/logout")
        assert "message" in r.json()