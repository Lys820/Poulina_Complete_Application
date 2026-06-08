"""
Data endpoint – Requêtes BD directes (sans LLM)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.config import get_settings
from app.data.database_sqlserver import get_db, SQLServerDB
from app.data.models import (
    CentreFilter, LaboratoireFilter, SoucheFilter,
    CentreResponse, LaboratoireResponse, SoucheResponse,
)

log = logging.getLogger(__name__)
router = APIRouter()


def _connect(settings) -> SQLServerDB:
    db = get_db(settings)
    if not db.connect():
        raise HTTPException(status_code=503, detail="Base de données inaccessible")
    return db


@router.get("/data/centres", response_model=list[CentreResponse])
async def get_centres(
    gouvernorat: str = Query(None),
    type_production: str = Query(None),
    actif: bool = Query(True),
    settings=Depends(get_settings),
):
    db = _connect(settings)
    try:
        filters = CentreFilter(gouvernorat=gouvernorat, type_production=type_production, actif=actif)
        df = db.get_centres(filters)
        return df.to_dict("records")
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error get_centres: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/data/labos", response_model=list[LaboratoireResponse])
async def get_labos(
    gouvernorat: str = Query(None),
    accepte_urgence: bool = Query(None),
    certifie_iso: bool = Query(True),
    actif: bool = Query(True),
    settings=Depends(get_settings),
):
    db = _connect(settings)
    try:
        filters = LaboratoireFilter(gouvernorat=gouvernorat, accepte_urgence=accepte_urgence,
                                    certifie_iso=certifie_iso, actif=actif)
        df = db.get_labos(filters)
        return df.to_dict("records")
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error get_labos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/data/souches", response_model=list[SoucheResponse])
async def get_souches(
    type_produit: str = Query(None),
    fertilite_min: float = Query(None),
    taux_mortalite_max: float = Query(None),
    settings=Depends(get_settings),
):
    db = _connect(settings)
    try:
        filters = SoucheFilter(type_produit_final=type_produit,
                               fertilite_min=fertilite_min,
                               taux_mortalite_max=taux_mortalite_max)
        df = db.get_souches(filters)
        return df.to_dict("records")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/data/centre/{centre_id}", response_model=CentreResponse)
async def get_centre_by_id(centre_id: int, settings=Depends(get_settings)):
    db = _connect(settings)
    try:
        row = db.query_one(f"SELECT * FROM centre_elevage WHERE id_centre = {centre_id}")
        if not row:
            raise HTTPException(status_code=404, detail="Centre not found")
        return row
    finally:
        db.close()


@router.get("/data/labo/{labo_id}", response_model=LaboratoireResponse)
async def get_labo_by_id(labo_id: int, settings=Depends(get_settings)):
    db = _connect(settings)
    try:
        row = db.query_one(f"SELECT * FROM laboratoire WHERE id_labo = {labo_id}")
        if not row:
            raise HTTPException(status_code=404, detail="Laboratoire not found")
        return row
    finally:
        db.close()


@router.get("/data/count")
async def get_counts(settings=Depends(get_settings)):
    db = _connect(settings)
    try:
        return {
            "centres":  db.query_one("SELECT COUNT(*) as count FROM centre_elevage WHERE actif=1")["count"],
            "labos":    db.query_one("SELECT COUNT(*) as count FROM laboratoire WHERE actif=1")["count"],
            "souches":  db.query_one("SELECT COUNT(*) as count FROM souche")["count"],
            "analyses": db.query_one("SELECT COUNT(*) as count FROM demande_analyse")["count"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()