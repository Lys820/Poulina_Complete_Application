"""
Tests unitaires — Security (JWT + hachage PBKDF2)
Base : PouleLabDB, compte seeder admin@poulelabapp.com / Admin@1234

Le test d'interopérabilité ASP.NET Identity v3 vérifie que verify_password()
supporte le format réel produit par UserManager<ApplicationUser> :
  - version byte : 0x01
  - PRF : 2 (HMACSHA512, valeur par défaut depuis ASP.NET Core Identity 3+)
  - iterations : 100 000
  - saltLen : 16 octets
  - données : [version][PRF][iterations][saltLen][salt][subkey], Base64

Exécution :
    pytest tests/test_security_poulelabdb.py -v
"""
from __future__ import annotations

import base64
import hashlib
import os
import struct
import time

import pytest

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    require_permission,
)
from fastapi import HTTPException

SECRET = "cle-secrete-test-unitaire-poulelabdb-32chars!"

ADMIN_EMAIL = "admin@poulelabapp.com"
ADMIN_PASSWORD = "Admin@1234"


def _aspnet_v3_hash(password: str, prf: int = 2) -> str:
    """
    Format ASP.NET Identity v3 (KeyDerivation.Pbkdf2).
    prf=1 = HMACSHA256, prf=2 = HMACSHA512 (défaut Identity Core 3+).
    Utiliser prf=2 pour correspondre au comportement réel de UserManager.
    """
    salt = os.urandom(16)
    hash_name = "sha512" if prf == 2 else "sha256"
    subkey = hashlib.pbkdf2_hmac(hash_name, password.encode("utf-8"), salt, 100_000, 32)
    header = struct.pack(">BIII", 0x01, prf, 100_000, 16)
    return base64.b64encode(header + salt + subkey).decode("ascii")


# ===========================================================================
# 1. Hachage mot de passe
# ===========================================================================

class TestHashPassword:

    def test_hash_different_du_mot_de_passe_clair(self):
        h = hash_password(ADMIN_PASSWORD)
        assert h != ADMIN_PASSWORD

    def test_deux_appels_produisent_des_hash_distincts(self):
        h1 = hash_password(ADMIN_PASSWORD)
        h2 = hash_password(ADMIN_PASSWORD)
        assert h1 != h2

    def test_hash_non_vide(self):
        assert len(hash_password(ADMIN_PASSWORD)) > 0

    def test_mot_de_passe_vide_accepte(self):
        assert hash_password("") != ""

    def test_mot_de_passe_tres_long(self):
        pwd = "A" * 500
        assert hash_password(pwd) != pwd


# ===========================================================================
# 2. Vérification mot de passe
# ===========================================================================

class TestVerifyPassword:

    def test_mot_de_passe_admin_seeder_correct(self):
        h = hash_password(ADMIN_PASSWORD)
        assert verify_password(ADMIN_PASSWORD, h) is True

    def test_mot_de_passe_incorrect_retourne_false(self):
        h = hash_password(ADMIN_PASSWORD)
        assert verify_password("MauvaisMotDePasse!", h) is False

    def test_hash_vide_retourne_false(self):
        assert verify_password(ADMIN_PASSWORD, "") is False

    def test_hash_corrompu_retourne_false(self):
        assert verify_password(ADMIN_PASSWORD, "ZZZinvalide") is False

    def test_mot_de_passe_vide_versus_hash_vide(self):
        h = hash_password("")
        assert verify_password("", h) is True
        assert verify_password("quelquechose", h) is False

    def test_verify_aspnet_identity_v3_sha512(self):
        """
        security.py doit valider un hash au format ASP.NET Identity v3
        avec PRF=2 (HMACSHA512), qui est la valeur par défaut d'Identity Core 3+.
        Ce test vérifie l'interopérabilité avec PouleLabDB.
        """
        aspnet_hash = _aspnet_v3_hash(ADMIN_PASSWORD, prf=2)
        assert verify_password(ADMIN_PASSWORD, aspnet_hash) is True

    def test_verify_aspnet_identity_v3_sha512_mauvais_mdp(self):
        aspnet_hash = _aspnet_v3_hash(ADMIN_PASSWORD, prf=2)
        assert verify_password("Admin@WRONG", aspnet_hash) is False


# ===========================================================================
# 3. Génération de tokens JWT
# ===========================================================================

class TestCreateAccessToken:

    def test_token_decodable(self):
        import jwt as pyjwt
        token = create_access_token(
            "guid-admin-1234", ADMIN_EMAIL, "Administrator",
            ["CHAT_READ", "CHAT_ML"], 60, SECRET
        )
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert payload["sub"] == "guid-admin-1234"
        assert payload["email"] == ADMIN_EMAIL
        assert payload["role"] == "Administrator"

    def test_token_contient_expiration(self):
        import jwt as pyjwt
        token = create_access_token(
            "guid-admin-1234", ADMIN_EMAIL, "Administrator", [], 60, SECRET
        )
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert "exp" in payload

    def test_token_expire(self):
        token = create_access_token(
            "guid-admin-1234", ADMIN_EMAIL, "Administrator",
            [], expire_minutes=0, secret_key=SECRET
        )
        time.sleep(1)
        with pytest.raises(HTTPException) as exc:
            decode_token(token, SECRET)
        assert exc.value.status_code == 401

    def test_roles_aspnet_identity_inclus(self):
        import jwt as pyjwt
        for role in ["Administrator", "Manager", "Receptionist", "Analyst", "LabChief", "Client"]:
            token = create_access_token("some-guid", "u@test.com", role, [], 60, SECRET)
            payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
            assert payload["role"] == role

    def test_sub_est_un_guid_string(self):
        import jwt as pyjwt
        guid = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        token = create_access_token(guid, ADMIN_EMAIL, "Administrator", [], 60, SECRET)
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert payload["sub"] == guid

    def test_permissions_vides_acceptees(self):
        import jwt as pyjwt
        token = create_access_token("guid", "u@test.com", "Client", [], 60, SECRET)
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert payload["permissions"] == []

    def test_plusieurs_permissions(self):
        import jwt as pyjwt
        perms = ["CHAT_READ", "CHAT_ML", "ADMIN_TRAIN"]
        token = create_access_token("guid", "u@test.com", "Administrator", perms, 60, SECRET)
        payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
        assert set(payload["permissions"]) == set(perms)


# ===========================================================================
# 4. Décodage de tokens JWT
# ===========================================================================

class TestDecodeToken:

    def test_token_valide(self):
        token = create_access_token(
            "guid-analyst-abc", "analyst@poulelabapp.com",
            "Analyst", ["CHAT_READ"], 60, SECRET
        )
        payload = decode_token(token, SECRET)
        assert payload["sub"] == "guid-analyst-abc"

    def test_mauvaise_cle_leve_401(self):
        token = create_access_token(
            "guid", "u@test.com", "Manager", [], 60,
            "bonne-cle-suffisamment-longue-32c"
        )
        with pytest.raises(HTTPException) as exc:
            decode_token(token, "mauvaise-cle-suffisamment-longue!")
        assert exc.value.status_code == 401

    def test_token_completement_invalide(self):
        with pytest.raises(HTTPException) as exc:
            decode_token("pas.un.token.valide", SECRET)
        assert exc.value.status_code == 401

    def test_token_vide(self):
        with pytest.raises(HTTPException) as exc:
            decode_token("", SECRET)
        assert exc.value.status_code == 401


# ===========================================================================
# 5. require_permission
# ===========================================================================

class TestRequirePermission:

    def test_permission_presente_retourne_user(self):
        from unittest.mock import MagicMock
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(
            "guid-admin", ADMIN_EMAIL, "Administrator",
            ["CHAT_READ", "CHAT_ML", "ADMIN_TRAIN"], 60, SECRET
        )
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token

        checker = require_permission("CHAT_READ", SECRET)
        user = checker(creds)
        assert user["sub"] == "guid-admin"

    def test_permission_absente_leve_403(self):
        from unittest.mock import MagicMock
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(
            "guid-client", "client@test.com", "Client", ["CHAT_READ"], 60, SECRET
        )
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token

        checker = require_permission("ADMIN_TRAIN", SECRET)
        with pytest.raises(HTTPException) as exc:
            checker(creds)
        assert exc.value.status_code == 403

    def test_token_expire_leve_401(self):
        from unittest.mock import MagicMock
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token(
            "guid-admin", ADMIN_EMAIL, "Administrator",
            ["CHAT_READ"], expire_minutes=0, secret_key=SECRET
        )
        time.sleep(1)
        creds = MagicMock(spec=HTTPAuthorizationCredentials)
        creds.credentials = token

        checker = require_permission("CHAT_READ", SECRET)
        with pytest.raises(HTTPException) as exc:
            checker(creds)
        assert exc.value.status_code == 401