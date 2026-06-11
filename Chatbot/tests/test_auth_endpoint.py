"""
Tests integration — Endpoint /auth/login
FastAPI TestClient, base de donnees entierement mockee.
Credentials mis à jour : admin@poulelabapp.com / Admin@1234 (DataSeeder.cs)
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
sys.modules["pyodbc"] = pyodbc_mock

from app.core.security import hash_password
from app.api.auth import router as auth_router

# ✅ Credentials mis à jour (DataSeeder.cs)
ADMIN_EMAIL    = "admin@poulelabapp.com"
VALID_PASSWORD = "Admin@1234"
VALID_HASH     = hash_password(VALID_PASSWORD)

# ---------------------------------------------------------------------------
# Application de test
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(auth_router, prefix="/api/v1")

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_utilisateur(role: str = "Admin", permissions: list | None = None) -> dict:
    return {
        "id_utilisateur": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  # ✅ GUID string
        "password_hash":  VALID_HASH,
        "nom":            "Admin",
        "prenom":         "PouleLabApp",
        "actif":          1,
        "nom_role":       role,
        "permissions":    permissions or ["CHAT_READ", "CHAT_ML", "ADMIN"],
    }


# ---------------------------------------------------------------------------
# Tests login succes
# ---------------------------------------------------------------------------

class TestLoginSucces:

    def test_login_retourne_200_et_token(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = mock_utilisateur()
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    ADMIN_EMAIL,
                "password": VALID_PASSWORD,
            })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_retourne_role(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = mock_utilisateur("Analyst", ["CHAT_READ"])
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    ADMIN_EMAIL,
                "password": VALID_PASSWORD,
            })

        assert response.status_code == 200
        assert response.json()["role"] == "Analyst"

    def test_login_retourne_permissions(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = mock_utilisateur(
                "Admin", ["CHAT_READ", "CHAT_ML", "ADMIN_TRAIN"]
            )
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    ADMIN_EMAIL,
                "password": VALID_PASSWORD,
            })

        data = response.json()
        assert "CHAT_READ"   in data["permissions"]
        assert "ADMIN_TRAIN" in data["permissions"]

    def test_login_retourne_user_id_guid(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = mock_utilisateur()
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    ADMIN_EMAIL,
                "password": VALID_PASSWORD,
            })

        # ✅ L'ID doit être un GUID string, pas un entier
        user_id = response.json()["user_id"]
        assert isinstance(user_id, str)
        assert len(user_id) == 36  # format UUID : 8-4-4-4-12

    def test_login_permissions_vides_acceptees(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            utilisateur = mock_utilisateur()
            utilisateur["permissions"] = None
            db.get_utilisateur_par_email.return_value = utilisateur
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    ADMIN_EMAIL,
                "password": VALID_PASSWORD,
            })

        assert response.status_code == 200
        assert response.json()["permissions"] == []


# ---------------------------------------------------------------------------
# Tests login echec
# ---------------------------------------------------------------------------

class TestLoginEchec:

    def test_utilisateur_inconnu_retourne_401(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = None
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    "inconnu@poulelabapp.com",
                "password": "nimporte",
            })

        assert response.status_code == 401

    def test_mauvais_mot_de_passe_retourne_401(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = mock_utilisateur()
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    ADMIN_EMAIL,
                "password": "MauvaisMotDePasse!",
            })

        assert response.status_code == 401

    def test_bd_inaccessible_retourne_503(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = False
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email":    ADMIN_EMAIL,
                "password": VALID_PASSWORD,
            })

        assert response.status_code == 503

    def test_champs_manquants_retourne_422(self):
        response = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL})
        assert response.status_code == 422

    def test_json_vide_retourne_422(self):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests logout
# ---------------------------------------------------------------------------

class TestLogout:

    def test_logout_retourne_200(self):
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200

    def test_logout_retourne_message(self):
        response = client.post("/api/v1/auth/logout")
        assert "message" in response.json()