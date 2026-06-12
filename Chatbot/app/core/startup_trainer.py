"""
app/core/startup_trainer.py
────────────────────────────────────────────────────────────────────────────
Entraîne automatiquement le modèle ML et le RAG au démarrage de FastAPI,
en appelant directement les services (sans HTTP interne).

Pourquoi appel direct et non HTTP :
  - Au moment du lifespan startup, Uvicorn n'a pas encore ouvert le socket.
  - Un appel httpx vers localhost:8000 échoue avec ConnectError ou message
    vide, d'où "Entraînement startup impossible ()".
  - La solution correcte est d'appeler les fonctions de service directement,
    exactement comme le fait l'endpoint /analyses/train-from-sqlserver.

Intégration dans main.py :
  from contextlib import asynccontextmanager
  from app.core.startup_trainer import auto_train_on_startup

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      await auto_train_on_startup()
      yield

  app = FastAPI(lifespan=lifespan)
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


async def auto_train_on_startup() -> None:
    """
    Appelé une fois au démarrage via le lifespan FastAPI.
    Charge les données depuis PouleLabDB et entraîne ML + RAG en mémoire.
    Ne bloque jamais le démarrage si la base est inaccessible.
    """
    log.info("Startup : entraînement automatique ML + RAG...")

    try:
        # ── 1. Données ────────────────────────────────────────────────
        from app.data.database_sqlserver import get_db

        db = get_db()
        if not db.connect():
            log.warning(
                "Entraînement startup impossible — connexion SQL Server échouée. "
                "Vérifier SQLSERVER_SERVER / SQLSERVER_DATABASE dans .env. "
                "Le chatbot démarre sans ML."
            )
            return

        df_analyses, df_labos = db.get_all_data()
        db.close()

        if df_analyses.empty and df_labos.empty:
            log.warning(
                "Startup : aucune donnée dans PouleLabDB "
                "(AnalysisRequests vide ?). Le chatbot démarre sans ML."
            )
            return

        # ── 2. RAG ────────────────────────────────────────────────────
        # rag_service est un singleton global dans app.services.rag_service
        from app.services.rag_service import rag_service

        embedding_method = os.getenv("EMBEDDING_METHOD", "tfidf")
        rag_result = rag_service.build_from_dataframes(
            df_analyses, df_labos, embedding_method=embedding_method
        )
        log.info(
            "RAG prêt — analyses=%d docs [%s], labos=%d docs [%s]",
            rag_result["analyses"]["docs"],
            rag_result["analyses"]["embedder"],
            rag_result["labos"]["docs"],
            rag_result["labos"]["embedder"],
        )

        # ── 3. ML ─────────────────────────────────────────────────────
        # model_registry est un singleton global dans app.ml.model_factory
        # On importe après avoir vérifié rag pour isoler les erreurs
        try:
            from app.ml.model_factory import model_registry

            ml_model = os.getenv("ML_MODEL", "auto")
            ml_result = model_registry.train_from_dataframes(
                df_analyses, df_labos, ml_model_name=ml_model
            )
            souche = ml_result.get("souche", {})
            labo   = ml_result.get("labo",   {})
            log.info(
                "Modèle souche : %s  acc=%.3f",
                souche.get("model", "?"),
                souche.get("accuracy", 0.0),
            )
            log.info(
                "Modèle labo   : %s  acc=%.3f",
                labo.get("model", "?"),
                labo.get("accuracy", 0.0),
            )
        except Exception as ml_exc:
            log.warning("Entraînement ML échoué (RAG reste actif) : %s", ml_exc)

        log.info(
            "Startup terminé — analyses=%d, labos=%d",
            len(df_analyses),
            len(df_labos),
        )

    except Exception as exc:
        log.warning(
            "Entraînement startup impossible (%s) — "
            "SQL Server accessible ? Le chatbot continue sans ML.",
            exc,
        )