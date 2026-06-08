"""
Poulina AI Chatbot – Backend FastAPI
Auto-entraînement au démarrage si SQL Server configuré.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Entraîne ML + RAG au démarrage si SQL Server est configuré."""
    import asyncio
    from app.core.config import get_settings
    from app.data.database_sqlserver import get_db
    from app.ml.model_factory import model_registry
    from app.services.rag_service import rag_service

    settings = get_settings()

    if settings.SQLSERVER_SERVER and settings.SQLSERVER_DATABASE:
        log.info("Démarrage : entraînement automatique depuis SQL Server...")
        try:
            db = get_db(settings)
            if db.connect():
                df_analyses, df_labos = db.get_all_data()
                db.close()

                if not df_analyses.empty and not df_labos.empty:
                    await asyncio.to_thread(
                        model_registry.train_from_dataframes,
                        df_analyses, df_labos,
                        ml_model_name=settings.ML_MODEL,
                    )
                    await asyncio.to_thread(
                        rag_service.build_from_dataframes,
                        df_analyses, df_labos,
                        embedding_method=settings.EMBEDDING_METHOD,
                    )
                    log.info("Auto-entraînement OK : %d analyses, %d labos", len(df_analyses), len(df_labos))
                else:
                    log.warning("Auto-entraînement ignoré : données vides")
            else:
                log.warning("Auto-entraînement ignoré : SQL Server inaccessible")
        except Exception as e:
            log.error("Erreur auto-entraînement : %s", e)
    else:
        log.info("SQL Server non configuré — entraînement manuel via /analyses/train-from-sqlserver")

    yield  # serveur actif ici


app = FastAPI(
    title="Poulina AI Chatbot API",
    description="RAG + ML interchangeable pour recommandation souche/labo",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "https://poulina.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import chat, analyses, souches, labos, health, data, recommendation, auth, memory

app.include_router(health.router,          prefix="/api/v1", tags=["health"])
app.include_router(auth.router,            prefix="/api/v1", tags=["auth"])
app.include_router(chat.router,            prefix="/api/v1", tags=["chat"])
app.include_router(analyses.router,        prefix="/api/v1", tags=["analyses"])
app.include_router(souches.router,         prefix="/api/v1", tags=["souches"])
app.include_router(labos.router,           prefix="/api/v1", tags=["labos"])
app.include_router(data.router,            prefix="/api/v1", tags=["data"])
app.include_router(recommendation.router,  prefix="/api/v1", tags=["recommendations"])
app.include_router(memory.router,          prefix="/api/v1", tags=["memory"])

if __name__ == "__main__":
    import uvicorn
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)