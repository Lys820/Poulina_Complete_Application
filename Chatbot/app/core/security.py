"""
app/core/security.py
Sécurité : hachage, vérification de mot de passe, JWT

verify_password supporte deux formats :
  1. Format Python natif (hex 128 chars) : sel 32 octets + clé 32 octets, PBKDF2-SHA256
     Utilisé par hash_password() — pour les utilisateurs créés directement en Python.

  2. Format ASP.NET Identity v3 (Base64) : en-tête binaire + sel + clé, PBKDF2-SHA256/SHA512
     Utilisé par UserManager<ApplicationUser> dans PouleLabApp.API.
     Structure : [0x01][PRF:4 BE][iter:4 BE][saltLen:4 BE][salt][subkey]
     PRF = 1 → HMACSHA256, PRF = 2 → HMACSHA512 (défaut Identity Core 3+)

require_permission(permission) s'utilise sans secret_key dans les endpoints :
    Depends(require_permission("CHAT_READ"))
La clé JWT est lue depuis JWT_SECRET_KEY dans les variables d'environnement.

En test unitaire, on peut passer secret_key explicitement :
    checker = require_permission("CHAT_READ", secret_key=SECRET)
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
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hachage — format Python natif (hex)
# ---------------------------------------------------------------------------

_ITERATIONS = 200_000
_HASH_NAME  = "sha256"
_SALT_LEN   = 32
_KEY_LEN    = 32


def hash_password(password: str) -> str:
    """
    Hache un mot de passe avec PBKDF2-SHA256.
    Format de sortie : hex 128 chars (sel 32 octets + clé 32 octets).
    """
    import os as _os
    salt = _os.urandom(_SALT_LEN)
    key  = hashlib.pbkdf2_hmac(
        _HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS, _KEY_LEN
    )
    return (salt + key).hex()


def _verify_python_hex(password: str, stored: str) -> bool:
    """Vérifie un hash au format Python natif (hex 128 chars)."""
    try:
        raw  = bytes.fromhex(stored)
        salt = raw[:_SALT_LEN]
        key  = raw[_SALT_LEN:]
        candidate = hashlib.pbkdf2_hmac(
            _HASH_NAME, password.encode("utf-8"), salt, _ITERATIONS, _KEY_LEN
        )
        return candidate == key
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Vérification — format ASP.NET Identity v3 (Base64)
# ---------------------------------------------------------------------------

_ASPNET_V3_HEADER_SIZE = 13  # 1 octet version + 3 x 4 octets uint32


def _verify_aspnet_v3(password: str, stored: str) -> bool:
    """Vérifie un hash au format ASP.NET Identity v3 (Base64)."""
    try:
        raw = base64.b64decode(stored)
        if len(raw) < _ASPNET_V3_HEADER_SIZE + 1:
            return False
        version = raw[0]
        if version != 0x01:
            return False
        prf, iterations, salt_len = struct.unpack_from(">III", raw, 1)
        if prf not in (1, 2):
            return False
        offset    = _ASPNET_V3_HEADER_SIZE
        salt      = raw[offset : offset + salt_len]
        subkey    = raw[offset + salt_len :]
        key_len   = len(subkey)
        hash_name = "sha512" if prf == 2 else "sha256"
        candidate = hashlib.pbkdf2_hmac(
            hash_name, password.encode("utf-8"), salt, iterations, key_len
        )
        return candidate == subkey
    except Exception:
        return False


def _is_hex(s: str) -> bool:
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Vérifie un mot de passe contre un hash stocké.
    Détecte automatiquement le format (Python hex vs ASP.NET Identity v3 Base64).
    """
    if not stored_hash:
        return False
    if len(stored_hash) == 128 and _is_hex(stored_hash):
        return _verify_python_hex(password, stored_hash)
    return _verify_aspnet_v3(password, stored_hash)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"


def _get_jwt_secret() -> str:
    """Lit la clé JWT depuis l'environnement (fallback sur valeur vide)."""
    return os.environ.get("JWT_SECRET_KEY", "")


def create_access_token(
    user_id,
    email: str,
    role: str,
    permissions: list[str],
    expire_minutes: int = 480,
    secret_key: str = "",
) -> str:
    """
    Génère un token JWT.
    user_id peut être un int ou un GUID string (PouleLabDB).
    Si secret_key est vide, lit JWT_SECRET_KEY depuis l'environnement.
    """
    key = secret_key or _get_jwt_secret()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub":         str(user_id),
        "email":       email,
        "role":        role,
        "permissions": permissions,
        "exp":         expire,
    }
    return jwt.encode(payload, key, algorithm=_ALGORITHM)


def decode_token(token: str, secret_key: str = "") -> dict:
    """
    Décode et valide un token JWT.
    Si secret_key est vide, lit JWT_SECRET_KEY depuis l'environnement.
    Lève HTTP 401 si invalide ou expiré.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Token manquant.")
    key = secret_key or _get_jwt_secret()
    try:
        return jwt.decode(token, key, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré.")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Token invalide : {exc}")


def get_current_user(
    credentials: HTTPAuthorizationCredentials,
    secret_key: str = "",
) -> dict:
    """Extrait l'utilisateur courant depuis les credentials Bearer."""
    return decode_token(credentials.credentials, secret_key)


# Bearer scheme partagé
_bearer = HTTPBearer(auto_error=False)


def require_permission(permission: str, secret_key: str = ""):
    """
    Retourne une dépendance FastAPI qui vérifie la présence d'une permission
    dans le token JWT.

    Utilisation dans les endpoints (sans secret_key) :
        Depends(require_permission("CHAT_READ"))
    La clé est lue depuis JWT_SECRET_KEY dans l'environnement.

    Utilisation dans les tests unitaires (avec secret_key) :
        checker = require_permission("CHAT_READ", SECRET)
        user = checker(creds)

    Lève HTTP 401 si token absent ou invalide, HTTP 403 si permission absente.
    """
    def checker(
        credentials: Optional[HTTPAuthorizationCredentials] = None,
    ) -> dict:
        if credentials is None:
            raise HTTPException(status_code=401, detail="Authentification requise.")
        key = secret_key or _get_jwt_secret()
        payload = decode_token(credentials.credentials, key)
        perms = payload.get("permissions", [])
        if permission not in perms:
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{permission}' requise.",
            )
        return payload

    return checker