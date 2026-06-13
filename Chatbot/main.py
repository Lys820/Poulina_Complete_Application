"""
main.py
────────────────────────────────────────────────────────────────────────────
Point d'entrée FastAPI du chatbot PouleLabApp.

Modifications par rapport à la version originale :
  ✅ Ajout du lifespan → entraînement ML automatique au démarrage
  ✅ Redis désactivé proprement si REDIS_URL est absent du .env
"""

from contextlib import asynccontextmanager
import logging
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# ── Import des routers (adapte selon ta structure réelle) ─────────────────────
from app.api import health, chat, analyses, souches, labos, auth, data

# ── Startup trainer ───────────────────────────────────────────────────────────
from app.core.startup_trainer import auto_train_on_startup

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ── Lifespan : s'exécute une fois au démarrage, une fois à l'arrêt ────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Bloc exécuté au démarrage (avant yield) et à l'arrêt (après yield).
    L'entraînement ML se fait ici pour que le chatbot soit opérationnel
    dès la première requête, sans appel manuel à /analyses/train-from-sqlserver.
    """
    log.info("=" * 60)
    log.info("  PouleLabApp Chatbot — démarrage")
    log.info("=" * 60)

    # Entraîner ML + RAG depuis PouleLabDB (non-bloquant si SQL indisponible)
    await auto_train_on_startup()

    yield  # ← l'application tourne ici

    log.info("Chatbot arrêté proprement.")


# ── Application FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="PouleLabApp Chatbot",
    version="3.0.0",
    description="Chatbot IA pour l'analyse avicole — FastAPI + RAG + ML",
    lifespan=lifespan,
)

app.include_router(data.router, prefix="/api/v1")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
PREFIX = "/api/v1"
app.include_router(health.router,   prefix=PREFIX)
app.include_router(auth.router,     prefix=PREFIX)
app.include_router(chat.router,     prefix=PREFIX)
app.include_router(analyses.router, prefix=PREFIX)
app.include_router(souches.router,  prefix=PREFIX)
app.include_router(labos.router,    prefix=PREFIX)


# ── Entrée ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,   # désactiver en production
        log_level="info",
    )