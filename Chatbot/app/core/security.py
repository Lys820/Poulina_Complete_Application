"""
Securite : JWT, hachage mot de passe, verification permissions
"""
from __future__ import annotations

import hashlib
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import get_settings

log = logging.getLogger(__name__)

ALGORITHM = "HS256"
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return (salt + key).hex()


def verify_password(password: str, hashed: str) -> bool:
    try:
        data = bytes.fromhex(hashed)
        salt, stored_key = data[:32], data[32:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
        return key == stored_key
    except Exception:
        return False


def create_access_token(
    user_id: int,
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
