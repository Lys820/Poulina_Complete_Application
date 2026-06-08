"""
Securite : JWT, hachage mot de passe, verification permissions
Supporte deux formats de hash :
  - Format PBKDF2 custom (ancienne BD chatbot)
  - Format ASP.NET Identity v3 (PouleLabDB / DataSeeder)
"""
from __future__ import annotations

import base64
import hashlib
import os
import struct
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings

log = logging.getLogger(__name__)

ALGORITHM = "HS256"
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash PBKDF2 custom (pour éventuels tests locaux)."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return (salt + key).hex()


def verify_password(password: str, hashed: str) -> bool:
    """
    Vérifie un mot de passe contre un hash.
    Détecte automatiquement le format :
      - Hash ASP.NET Identity v3 (base64, commence par AQAAAA==)
      - Hash PBKDF2 custom hex (ancienne BD chatbot)
    """
    if not hashed:
        return False

    # ── Format ASP.NET Identity v3 ──────────────────────────────────────────
    # Format : Base64( version[1] + prf[4] + iter[4] + saltlen[4] + salt[N] + subkey[N] )
    # version byte = 0x01 → PBKDF2-SHA256
    try:
        raw = base64.b64decode(hashed)
        if raw[0] == 0x01:
            # Lire les paramètres
            prf        = struct.unpack_from(">I", raw, 1)[0]   # KeyDerivationPrf (1 = HMACSHA256)
            iter_count = struct.unpack_from(">I", raw, 5)[0]   # nombre d'itérations
            salt_len   = struct.unpack_from(">I", raw, 9)[0]   # longueur du sel
            salt       = raw[13: 13 + salt_len]
            subkey     = raw[13 + salt_len:]

            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iter_count,
                dklen=len(subkey),
            )
            return derived == subkey
    except Exception:
        pass  # Pas du base64 ou format différent → essayer le format custom

    # ── Format PBKDF2 custom hex (ancienne BD chatbot) ──────────────────────
    try:
        data = bytes.fromhex(hashed)
        salt, stored_key = data[:32], data[32:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return key == stored_key
    except Exception:
        return False


def create_access_token(
    user_id: str,          # str car ASP.NET Identity utilise des GUIDs
    email: str,
    role: str,
    permissions: list[str],
    expire_minutes: int = 480,
    secret_key: str = "changez-cette-valeur",
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "permissions": permissions,
        "exp": expire,
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_token(token: str, secret_key: str) -> dict:
    try:
        return jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expire")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalide")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    settings=Depends(get_settings),
) -> dict:
    return decode_token(credentials.credentials, settings.JWT_SECRET_KEY)


def require_permission(permission: str):
    """Dépendance FastAPI : vérifie qu'un utilisateur possède la permission donnée."""
    def checker(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        settings=Depends(get_settings),
    ) -> dict:
        user = decode_token(credentials.credentials, settings.JWT_SECRET_KEY)
        if permission not in user.get("permissions", []):
            raise HTTPException(
                status_code=403,
                detail=f"Permission requise : {permission}",
            )
        return user
    return checker