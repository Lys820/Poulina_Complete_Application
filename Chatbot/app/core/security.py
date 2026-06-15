"""
app/core/security.py
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import struct
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger(__name__)

_ITERATIONS = 200_000
_HASH_NAME  = "sha256"
_SALT_LEN   = 32
_KEY_LEN    = 32


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_LEN)
    key  = hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS, _KEY_LEN)
    return (salt + key).hex()


def _verify_python_hex(password: str, stored: str) -> bool:
    try:
        raw  = bytes.fromhex(stored)
        salt = raw[:_SALT_LEN]
        key  = raw[_SALT_LEN:]
        return hashlib.pbkdf2_hmac(_HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS, _KEY_LEN) == key
    except Exception:
        return False


_ASPNET_V3_HEADER_SIZE = 13


def _verify_aspnet_v3(password: str, stored: str) -> bool:
    try:
        raw = base64.b64decode(stored)
        if len(raw) < _ASPNET_V3_HEADER_SIZE + 1 or raw[0] != 0x01:
            return False
        prf, iterations, salt_len = struct.unpack_from(">III", raw, 1)
        if prf not in (1, 2):
            return False
        salt      = raw[_ASPNET_V3_HEADER_SIZE : _ASPNET_V3_HEADER_SIZE + salt_len]
        subkey    = raw[_ASPNET_V3_HEADER_SIZE + salt_len :]
        hash_name = "sha512" if prf == 2 else "sha256"
        return hashlib.pbkdf2_hmac(hash_name, password.encode("utf-8"), salt, iterations, len(subkey)) == subkey
    except Exception:
        return False


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if len(stored_hash) == 128:
        try:
            int(stored_hash, 16)
            return _verify_python_hex(password, stored_hash)
        except ValueError:
            pass
    return _verify_aspnet_v3(password, stored_hash)


_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    return os.environ.get("JWT_SECRET_KEY", "")


def create_access_token(
    user_id, email: str, role: str, permissions: list[str],
    expire_minutes: int = 480, secret_key: str = "",
) -> str:
    key    = secret_key or _get_jwt_secret()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "role": role,
         "permissions": permissions, "exp": expire},
        key, algorithm=_ALGORITHM,
    )


def decode_token(token: str, secret_key: str = "") -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Token manquant.")
    key = secret_key or _get_jwt_secret()
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=[_ALGORITHM],
            options={
                "verify_aud": False,   # le token .NET a aud="PouleLabApp"
                "verify_iss": False,   # le token .NET a iss="PouleLabApp"
            },
        )

        # Le token .NET ne contient pas "permissions" — on le déduit du rôle
        if "permissions" not in payload:
            role = payload.get("role", "")
            # Récupérer le rôle depuis le claim Microsoft Identity si présent
            ms_role_claim = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
            if not role and ms_role_claim in payload:
                role = payload[ms_role_claim]
            payload["permissions"] = _permissions_for_role(role)

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Token invalide : {exc}")


def _permissions_for_role(role: str) -> list[str]:
    """
    Déduit les permissions du chatbot à partir du rôle ASP.NET Identity.
    Miroir de la logique définie dans DataSeeder / AspNetUserClaims.
    """
    mapping = {
        "Administrator": ["CHAT_READ", "CHAT_ML", "ADMIN_TRAIN", "DATA_READ"],
        "Manager":       ["CHAT_READ", "CHAT_ML", "DATA_READ"],
        "Analyst":       ["CHAT_READ", "CHAT_ML", "DATA_READ"],
        "LabChief":      ["CHAT_READ", "DATA_READ"],
        "Receptionist":  ["CHAT_READ", "DATA_READ"],
        "Client":        ["CHAT_READ"],
    }
    return mapping.get(role, [])

def get_current_user(credentials: HTTPAuthorizationCredentials, secret_key: str = "") -> dict:
    return decode_token(credentials.credentials, secret_key)


def require_permission(permission: str, secret_key: str = ""):
    """
    Dépendance FastAPI : vérifie la permission dans le token Bearer.

    Dans les endpoints :
        Depends(require_permission("CHAT_READ"))
        FastAPI injecte automatiquement le Bearer token via Depends(HTTPBearer()).

    Dans les tests unitaires (avec secret_key explicite) :
        checker = require_permission("CHAT_READ", SECRET)
        user = checker(creds)
    """
    # Mode test unitaire — retourne un callable simple sans Depends
    if secret_key:
        def test_checker(credentials: HTTPAuthorizationCredentials = None) -> dict:
            if credentials is None:
                raise HTTPException(status_code=401, detail="Authentification requise.")
            payload = decode_token(credentials.credentials, secret_key)
            if permission not in payload.get("permissions", []):
                raise HTTPException(status_code=403, detail=f"Permission '{permission}' requise.")
            return payload
        return test_checker

    # Mode production — FastAPI injecte le Bearer via Depends
    def checker(
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    ) -> dict:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Authentification requise.")
        key     = _get_jwt_secret()
        payload = decode_token(credentials.credentials, key)
        if permission not in payload.get("permissions", []):
            raise HTTPException(status_code=403, detail=f"Permission '{permission}' requise.")
        return payload

    return checker