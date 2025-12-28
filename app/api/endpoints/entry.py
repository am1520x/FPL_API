# app/api/endpoints/entry.py
from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.fpl_entry_service import FPLEntryService

router = APIRouter(prefix="/entry", tags=["entry"])

service = FPLEntryService()

@router.get("/{entry_id}/history")
def entry_history(entry_id: int):
    try:
        result = service.get_entry_history(entry_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

@router.get("/{entry_id}/picks")
def entry_picks(entry_id: int, event_id: Optional[int] = None):
    try:
        result = service.get_entry_picks(entry_id, event_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

@router.get("/{entry_id}/transfers")
def entry_transfers(entry_id: int):
    try:
        result = service.get_entry_transfers(entry_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

@router.get("/current_event")
def current_event():
    try:
        result = service.get_current_event()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"current_event": result}
