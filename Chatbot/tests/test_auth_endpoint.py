"""
Tests integration — Endpoint /auth/login
FastAPI TestClient, base de donnees entierement mockee.
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


# ---------------------------------------------------------------------------
# Application de test
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(auth_router, prefix="/api/v1")

client = TestClient(app)

# Hash d un mot de passe connu pour les tests
VALID_PASSWORD = "Admin123!"
VALID_HASH = hash_password(VALID_PASSWORD)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def mock_utilisateur(role: str = "ADMIN", permissions: str = "CHAT_READ,CHAT_ML") -> dict:
    return {
        "id_utilisateur": 1,
        "password_hash": VALID_HASH,
        "nom": "Administrateur",
        "prenom": "Poulina",
        "actif": 1,
        "nom_role": role,
        "permissions": permissions,
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
                "email": "admin@poulina.tn",
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
            db.get_utilisateur_par_email.return_value = mock_utilisateur("GESTIONNAIRE", "CHAT_READ")
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email": "gestionnaire@poulina.tn",
                "password": VALID_PASSWORD,
            })

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "GESTIONNAIRE"

    def test_login_retourne_permissions(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = mock_utilisateur(
                "ADMIN", "CHAT_READ,CHAT_ML,ADMIN_TRAIN"
            )
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email": "admin@poulina.tn",
                "password": VALID_PASSWORD,
            })

        data = response.json()
        assert "CHAT_READ" in data["permissions"]
        assert "ADMIN_TRAIN" in data["permissions"]

    def test_login_retourne_user_id(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            db.get_utilisateur_par_email.return_value = mock_utilisateur()
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email": "admin@poulina.tn",
                "password": VALID_PASSWORD,
            })

        assert response.json()["user_id"] == 1

    def test_login_permissions_vides_acceptees(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = True
            utilisateur = mock_utilisateur()
            utilisateur["permissions"] = None
            db.get_utilisateur_par_email.return_value = utilisateur
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email": "admin@poulina.tn",
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
                "email": "inconnu@poulina.tn",
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
                "email": "admin@poulina.tn",
                "password": "MauvaisMotDePasse!",
            })

        assert response.status_code == 401

    def test_bd_inaccessible_retourne_503(self):
        with patch("app.api.auth.get_db") as mock_get_db:
            db = MagicMock()
            db.connect.return_value = False
            mock_get_db.return_value = db

            response = client.post("/api/v1/auth/login", json={
                "email": "admin@poulina.tn",
                "password": VALID_PASSWORD,
            })

        assert response.status_code == 503

    def test_champs_manquants_retourne_422(self):
        response = client.post("/api/v1/auth/login", json={"email": "admin@poulina.tn"})
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