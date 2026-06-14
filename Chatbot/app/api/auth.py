"""
Authentification : login, logout
Connecté à PouleLabDB via ASP.NET Identity
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.security import verify_password, create_access_token
from app.data.database_sqlserver import get_db

log = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    nom: str
    prenom: str
    role: str
    permissions: list[str]


@router.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, settings=Depends(get_settings)):
    db = get_db(settings)
    if not db.connect():
        raise HTTPException(status_code=503, detail="Base de donnees inaccessible.")

    row = db.get_utilisateur_par_email(req.email)
    if not row:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    if not row.get("actif"):
        raise HTTPException(status_code=403, detail="Compte inactif.")

    if not verify_password(req.password, row["password_hash"] or ""):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    permissions_str = row.get("permissions") or ""
    permissions = [p for p in permissions_str.split(",") if p]

    token = create_access_token(
        user_id=row["id_utilisateur"],
        email=req.email,
        role=row["nom_role"] or "",
        permissions=permissions,
        expire_minutes=settings.JWT_EXPIRE_MINUTES,
        secret_key=settings.JWT_SECRET_KEY,
    )

    db.close()

    return LoginResponse(
        access_token=token,
        user_id=str(row["id_utilisateur"]),
        nom=row["nom"] or "",
        prenom=row["prenom"] or "",
        role=row["nom_role"] or "",
        permissions=permissions,
    )


@router.post("/auth/logout")
async def logout():
    return {"message": "Deconnexion effectuee"}