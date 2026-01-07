# app/api/endpoints/entry.py
from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.fpl_entry_service import FPLEntryService

router = APIRouter(prefix="/entry", tags=["entry"])

service = FPLEntryService()

@router.get("/{entry_id}/history", description="Get the historical performance of an entry.")
def entry_history(entry_id: int):
    """
    Get the historical performance of an entry.
    **entry_id**: FPL manager ID
    """
    try:
        result = service.get_entry_history(entry_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

@router.get("/{entry_id}/picks", description="Get the picks of an entry for a specific event or all events.")
def entry_picks(entry_id: int, event_id: Optional[int] = None):
    """
    Get the picks of an entry for a specific event or all events.
    **entry_id**: FPL manager ID
    **event_id**: Optional event ID
    """
    try:
        result = service.get_entry_picks(entry_id, event_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

@router.get("/{entry_id}/transfers", description="Get the transfers of an entry.")
def entry_transfers(entry_id: int):
    """
    Get the transfers of an entry.
    **entry_id**: FPL manager ID
    """
    try:
        result = service.get_entry_transfers(entry_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result

@router.get("/current_event", description="Get the current event.")
def current_event():
    """
    Get the current event.
    """
    try:
        result = service.get_current_event()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"current_event": result}
