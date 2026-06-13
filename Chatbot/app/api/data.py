"""
app/api/data.py
Routes /data/* — reference data from PouleLabDB (Breeds, FarmCenters, Laboratories)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import get_settings
from app.data.database_sqlserver import get_db

log = logging.getLogger(__name__)
router = APIRouter()


def _connect(settings):
    db = get_db(settings)
    if not db.connect():
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return db


@router.get("/data/count")
async def data_count(settings=Depends(get_settings)):
    db = _connect(settings)
    try:
        return db.get_count()
    except HTTPException:
        raise
    except Exception as e:
        log.error("data_count: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/data/labos")
async def data_labos(settings=Depends(get_settings)):
    db = _connect(settings)
    try:
        df = db.get_labos()
        return df.to_dict(orient="records") if not df.empty else []
    except HTTPException:
        raise
    except Exception as e:
        log.error("data_labos: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/data/souches")
async def data_souches(
    type_production: str = Query(None, description="Filter by production type: Broiler, Layer, Turkey"),
    settings=Depends(get_settings),
):
    """Returns poultry breeds from the Breeds table."""
    db = _connect(settings)
    try:
        breeds = db.get_breeds()
        if type_production:
            breeds = [b for b in breeds if b.get("type_production") == type_production]
        return breeds
    except HTTPException:
        raise
    except Exception as e:
        log.error("data_souches: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/data/centres")
async def data_centres(
    governorate: str = Query(None, description="Filter by governorate"),
    farming_type: str = Query(None, description="Filter by farming type: Broiler, Layer, Turkey, Mixed"),
    settings=Depends(get_settings),
):
    """Returns farm centers from the FarmCenters table."""
    db = _connect(settings)
    try:
        centers = db.get_farm_centers()
        if governorate:
            centers = [c for c in centers if c.get("gouvernorat") == governorate]
        if farming_type:
            centers = [c for c in centers if c.get("type_elevage") == farming_type]
        return centers
    except HTTPException:
        raise
    except Exception as e:
        log.error("data_centres: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()