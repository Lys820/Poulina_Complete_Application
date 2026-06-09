"""
app/core/security.py
────────────────────────────────────────────────────────────────────────────
Sécurité : hachage des mots de passe, JWT, dépendances FastAPI.

Exports attendus par les autres modules :
  - hash_password          ← app/api/auth.py
  - verify_password        ← app/api/auth.py
  - create_access_token    ← app/api/auth.py
  - decode_token           ← app/api/auth.py + tests
  - require_permission     ← app/api/chat.py, analyses.py, souches.py
  - get_current_user       ← app/api/chat.py  ← MANQUAIT → ImportError corrigé

Compatibilité ASP.NET Identity v3 :
  - PasswordHash stocké en Base64, format binaire PBKDF2-SHA256 v3
  - IDs utilisateurs = GUIDs (string)
"""

from __future__ import annotations

import base64
import hashlib
import os
import struct
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt as pyjwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# ── Lecture de la config JWT depuis .env ──────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

_JWT_SECRET    = os.getenv("JWT_SECRET_KEY", "cle-non-configuree")
_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM",  "HS256")
_JWT_EXPIRE    = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

# ── Schéma Bearer pour FastAPI ────────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=True)


# ════════════════════════════════════════════════════════════════════════════
# Hachage — format ASP.NET Identity v3 (PBKDF2-SHA256, Base64)
# ════════════════════════════════════════════════════════════════════════════

_FORMAT_VERSION   = 1        # octet 0
_PRF_HMACSHA256   = 2        # PRF identifier
_ITERATIONS       = 100_000
_SALT_SIZE        = 16
_KEY_SIZE         = 32


def hash_password(password: str) -> str:
    """
    Produit un hash PBKDF2-SHA256 au format ASP.NET Identity v3 (Base64).
    Utiliser pour créer de nouveaux utilisateurs côté Python.
    """
    salt = os.urandom(_SALT_SIZE)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS, dklen=_KEY_SIZE)
    payload = (
        struct.pack(">B", _FORMAT_VERSION)
        + struct.pack(">I", _PRF_HMACSHA256)
        + struct.pack(">I", _ITERATIONS)
        + struct.pack(">I", _SALT_SIZE)
        + salt
        + dk
    )
    return base64.b64encode(payload).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    """
    Vérifie un mot de passe contre le PasswordHash stocké dans AspNetUsers.
    Compatible format ASP.NET Identity v3 (Base64).
    """
    try:
        raw = base64.b64decode(hashed)
    except Exception:
        return False

    if len(raw) < 61:
        return False

    version  = struct.unpack(">B", raw[0:1])[0]
    prf      = struct.unpack(">I", raw[1:5])[0]
    iters    = struct.unpack(">I", raw[5:9])[0]
    salt_len = struct.unpack(">I", raw[9:13])[0]

    if version != _FORMAT_VERSION or prf != _PRF_HMACSHA256:
        return False

    salt_end     = 13 + salt_len
    expected_key = raw[salt_end: salt_end + _KEY_SIZE]

    if len(expected_key) < _KEY_SIZE:
        return False

    actual_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), raw[13:salt_end], iters, dklen=_KEY_SIZE
    )

    # Comparaison en temps constant
    result = 0
    for x, y in zip(actual_key, expected_key):
        result |= x ^ y
    return result == 0


# ════════════════════════════════════════════════════════════════════════════
# JWT
# ════════════════════════════════════════════════════════════════════════════

def create_access_token(
    user_id: Any,
    email: str,
    role: str,
    permissions: list[str],
    expire_minutes: int,
    secret_key: str,
) -> str:
    """Crée un JWT signé HMAC-SHA256. user_id peut être un GUID string ou int."""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub":         str(user_id),
        "email":       email,
        "role":        role,
        "permissions": permissions,
        "iat":         int(now.timestamp()),
        "exp":         int((now + timedelta(minutes=expire_minutes)).timestamp()),
    }
    return pyjwt.encode(payload, secret_key, algorithm="HS256")


def decode_token(token: str, secret_key: str) -> dict[str, Any]:
    """
    Décode et valide un JWT.
    Lève HTTPException 401 si invalide ou expiré.
    """
    try:
        return pyjwt.decode(token, secret_key, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré.")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide.")


# ════════════════════════════════════════════════════════════════════════════
# Dépendances FastAPI
# ════════════════════════════════════════════════════════════════════════════

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict[str, Any]:
    """
    Dépendance FastAPI — extrait et valide le JWT du header Authorization.
    Usage dans un endpoint :
        @router.get("/protected")
        def endpoint(user = Depends(get_current_user)):
            ...

    Retourne le payload JWT décodé (dict avec sub, email, role, permissions).
    Lève HTTPException 401 si le token est absent, invalide ou expiré.
    """
    return decode_token(credentials.credentials, _JWT_SECRET)


def require_permission(permission: str, secret_key: str | None = None):
    """
    Factory de dépendance FastAPI — vérifie qu'une permission précise est présente.
    Usage dans un endpoint :
        @router.post("/admin")
        def endpoint(user = Depends(require_permission("ADMIN_TRAIN"))):
            ...

    Lève HTTPException 403 si la permission est absente du token.
    """
    _key = secret_key or _JWT_SECRET

    def _checker(
        credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    ) -> dict[str, Any]:
        payload = decode_token(credentials.credentials, _key)
        if permission not in payload.get("permissions", []):
            raise HTTPException(
                status_code=403,
                detail=f"Permission requise : {permission}",
            )
        return payload

    return _checker