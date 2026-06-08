"""
Tests unitaires — Security (JWT, hachage)
"""
from __future__ import annotations

import time
import pytest
import jwt as pyjwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    require_permission,
)
from fastapi import HTTPException

SECRET = "cle-secrete-test-unitaire"


# ---------------------------------------------------------------------------
# Tests hachage mot de passe
# ---------------------------------------------------------------------------

class TestHashPassword:

    def test_hash_different_du_mot_de_passe(self):
        h = hash_password("Admin123!")
        assert h != "Admin123!"

    def test_hash_non_reproductible(self):
        # Deux appels consecutifs produisent des hash differents (salt aleatoire)
        h1 = hash_password("Admin123!")
        h2 = hash_password("Admin123!")
        assert h1 != h2

    def test_hash_est_une_chaine_hexadecimale(self):
        h = hash_password("Admin123!")
        int(h, 16)  # leve ValueError si non-hex

    def test_longueur_hash(self):
        h = hash_password("Admin123!")
        # 32 octets sel + 32 octets cle = 64 octets = 128 chars hex
        assert len(h) == 128


class TestVerifyPassword:

    def test_mot_de_passe_correct(self):
        h = hash_password("Admin123!")
        assert verify_password("Admin123!", h) is True

    def test_mot_de_passe_incorrect(self):
        h = hash_password("Admin123!")
        assert verify_password("Mauvais!", h) is False

    def test_hash_corrompu_retourne_false(self):
        assert verify_password("Admin123!", "hash_invalide") is False

    def test_chaine_vide(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("quelquechose", h) is False

    def test_mot_de_passe_long(self):
        pwd = "A" * 500
        h = hash_password(pwd)
        assert verify_password(pwd, h) is True
        assert verify_password(pwd[:-1], h) is False


# ---------------------------------------------------------------------------
# Tests JWT
# ---------------------------------------------------------------------------

class TestCreateAccessToken:

    def test_token_decodable(self):
        token = create_access_token(1, "a@b.tn", "ADMIN", ["CHAT_READ"], 60, SECRET)
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert payload["sub"] == "1"
        assert payload["email"] == "a@b.tn"
        assert payload["role"] == "ADMIN"
        assert "CHAT_READ" in payload["permissions"]

    def test_token_contient_expiration(self):
        token = create_access_token(1, "a@b.tn", "ADMIN", [], 60, SECRET)
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert "exp" in payload

    def test_token_expire(self):
        token = create_access_token(1, "a@b.tn", "ADMIN", [], expire_minutes=0, secret_key=SECRET)
        time.sleep(1)
        with pytest.raises(HTTPException) as exc:
            decode_token(token, SECRET)
        assert exc.value.status_code == 401

    def test_permissions_vides(self):
        token = create_access_token(1, "a@b.tn", "VIEWER", [], 60, SECRET)
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert payload["permissions"] == []

    def test_plusieurs_permissions(self):
        perms = ["CHAT_READ", "CHAT_ML", "ADMIN_TRAIN"]
        token = create_access_token(1, "a@b.tn", "ADMIN", perms, 60, SECRET)
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert set(payload["permissions"]) == set(perms)


class TestDecodeToken:

    def test_token_valide(self):
        token = create_access_token(42, "x@y.tn", "GESTIONNAIRE", ["ANALYSE_READ"], 60, SECRET)
        payload = decode_token(token, SECRET)
        assert payload["sub"] == "42"

    def test_token_signe_avec_mauvaise_cle(self):
        token = create_access_token(1, "a@b.tn", "ADMIN", [], 60, "bonne-cle")
        with pytest.raises(HTTPException) as exc:
            decode_token(token, "mauvaise-cle")
        assert exc.value.status_code == 401

    def test_token_completement_invalide(self):
        with pytest.raises(HTTPException) as exc:
            decode_token("pas.un.token", SECRET)
        assert exc.value.status_code == 401

    def test_token_vide(self):
        with pytest.raises(HTTPException) as exc:
            decode_token("", SECRET)
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Tests require_permission
# ---------------------------------------------------------------------------

class TestRequirePermission:

    def test_permission_presente_retourne_user(self):
        from unittest.mock import MagicMock
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(1, "a@b.tn", "ADMIN", ["CHAT_READ", "CHAT_ML"], 60, SECRET)
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token

        checker = require_permission("CHAT_READ", SECRET)
        user = checker(creds)
        assert user["sub"] == "1"

    def test_permission_absente_leve_403(self):
        from unittest.mock import MagicMock
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(1, "a@b.tn", "VIEWER", ["CHAT_READ"], 60, SECRET)
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token

        checker = require_permission("ADMIN_TRAIN", SECRET)
        with pytest.raises(HTTPException) as exc:
            checker(creds)
        assert exc.value.status_code == 403