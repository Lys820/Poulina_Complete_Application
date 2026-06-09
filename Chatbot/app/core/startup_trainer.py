"""
app/core/startup_trainer.py
────────────────────────────────────────────────────────────────────────────
Entraîne automatiquement le modèle ML et le RAG au démarrage de FastAPI,
en lisant les données directement depuis PouleLabDB.

Pourquoi c'est nécessaire :
  - InMemoryVectorStore et le modèle RF/GB/XGB ne persistent PAS sur disque.
  - À chaque redémarrage du chatbot, la RAM est vide → chat et prédictions
    retournent des erreurs tant que /analyses/train-from-sqlserver n'a pas
    été appelé manuellement.
  - Ce module règle le problème en s'entraînant automatiquement au startup.

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
import httpx

log = logging.getLogger(__name__)

INTERNAL_TRAIN_URL = "http://localhost:8000/api/v1/analyses/train-from-sqlserver"


async def auto_train_on_startup(base_url: str = "http://localhost:8000") -> None:
    """
    Appelé une fois au démarrage via le lifespan FastAPI.
    Appelle l'endpoint /analyses/train-from-sqlserver en interne.
    Loggue le résultat mais ne bloque jamais le démarrage si ça échoue.
    """
    url = f"{base_url}/api/v1/analyses/train-from-sqlserver"
    log.info("🚀 Startup : entraînement automatique ML + RAG...")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url)

        if r.status_code == 200:
            data = r.json()
            analyses_docs = data.get("analyses", {}).get("docs", 0)
            labos_docs    = data.get("labos",    {}).get("docs", 0)
            souche_model  = data.get("model_status", {}).get("souche", {}).get("model", "?")
            souche_acc    = data.get("model_status", {}).get("souche", {}).get("accuracy", 0)
            log.info(f"✅ ML prêt — analyses={analyses_docs} docs, labos={labos_docs} docs")
            log.info(f"✅ Modèle souche : {souche_model}  acc={souche_acc:.3f}")
        else:
            log.warning(
                f"⚠️  Entraînement startup échoué (HTTP {r.status_code}) — "
                f"le chatbot démarre sans modèle ML. "
                f"Appelle manuellement POST /api/v1/analyses/train-from-sqlserver."
            )

    except Exception as e:
        log.warning(
            f"⚠️  Entraînement startup impossible ({e}) — "
            f"SQL Server accessible ? Le chatbot continue sans ML."
        )