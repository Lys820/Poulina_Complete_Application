# app/dependencies.py  ← NOUVEAU FICHIER
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
import jwt

bearer = HTTPBearer()
SECRET_KEY = "..."  # Même clé que Angular/auth backend

def get_current_user(token=Depends(bearer)):
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload  # {"user_id": "u123", "role": "eleveur", "centres": [1, 3]}
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide")

def require_role(*roles):
    def checker(user=Depends(get_current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Accès refusé")
        return user
    return checker