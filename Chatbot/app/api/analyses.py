"""
Analyses upload – Recharge CSV et entraîne ML à chaud
+ Entraînement direct depuis SQL Server
"""

import logging
import asyncio
import io
import pandas as pd

from fastapi import APIRouter, UploadFile, Depends, HTTPException

from app.ml.model_factory import model_registry
from app.services.rag_service import rag_service
from app.core.config import get_settings

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyses/upload")
async def upload_analyses(
    file_analyses: UploadFile,
    file_labos: UploadFile,
    settings=Depends(get_settings),
):
    try:
        content_a = await file_analyses.read()
        df_analyses = pd.read_csv(io.BytesIO(content_a))

        content_l = await file_labos.read()
        df_labos = pd.read_csv(io.BytesIO(content_l))

        log.info(f"CSV analyses: {len(df_analyses)} lignes")
        log.info(f"CSV labos: {len(df_labos)} lignes")

        ml_results = await asyncio.to_thread(
            model_registry.train_from_dataframes,
            df_analyses, df_labos,
            ml_model_name=settings.ML_MODEL,
        )

        rag_results = await asyncio.to_thread(
            rag_service.build_from_dataframes,
            df_analyses, df_labos,
            embedding_method=settings.EMBEDDING_METHOD,
        )

        return {
            "status": "trained",
            "message": "CSV chargé, ML entraîné, RAG indexé",
            "analyses": rag_results["analyses"],
            "labos": rag_results["labos"],
            "model_status": {
                "souche": ml_results.get("souche", {}),
                "labo": ml_results.get("labo", {}),
            },
            "trained_at": str(model_registry._trained_at),
        }

    except Exception as e:
        log.exception("Upload/training error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyses/train-from-sqlserver")
async def train_from_sqlserver(settings=Depends(get_settings)):
    """Entraîne directement depuis SQL Server."""
    from app.data.database_sqlserver import get_db

    if not settings.SQLSERVER_SERVER:
        raise HTTPException(status_code=400, detail="SQLSERVER_SERVER manquant dans .env")
    if not settings.SQLSERVER_DATABASE:
        raise HTTPException(status_code=400, detail="SQLSERVER_DATABASE manquant dans .env")

    db = get_db(settings)
    log.info(f"Connexion SQL Server: {settings.SQLSERVER_SERVER} / {settings.SQLSERVER_DATABASE}")

    if not db.connect():
        raise HTTPException(status_code=500, detail="Impossible de se connecter à SQL Server")

    try:
        df_analyses, df_labos = db.get_all_data()
    except Exception as e:
        log.exception("Erreur lecture SQL Server")
        raise HTTPException(status_code=500, detail=f"Erreur SQL Server: {str(e)}")
    finally:
        db.close()

    if df_analyses.empty:
        raise HTTPException(status_code=400, detail="0 lignes dans analyses")
    if df_labos.empty:
        raise HTTPException(status_code=400, detail="0 lignes dans labos")

    log.info(f"SQL Server: {len(df_analyses)} analyses, {len(df_labos)} labos")

    try:
        ml_results = await asyncio.to_thread(
            model_registry.train_from_dataframes,
            df_analyses, df_labos,
            ml_model_name=settings.ML_MODEL,
        )
        rag_results = await asyncio.to_thread(
            rag_service.build_from_dataframes,
            df_analyses, df_labos,
            embedding_method=settings.EMBEDDING_METHOD,
        )
    except Exception as e:
        log.exception("ML/RAG training error")
        raise HTTPException(status_code=500, detail=f"Erreur entraînement ML/RAG: {str(e)}")

    return {
        "status": "trained_from_sqlserver",
        "message": f"SQL Server: {len(df_analyses)} analyses + {len(df_labos)} labos",
        "analyses": rag_results["analyses"],
        "labos": rag_results["labos"],
        "model_status": {
            "souche": ml_results.get("souche", {}),
            "labo": ml_results.get("labo", {}),
        },
        "trained_at": str(model_registry._trained_at),
    }