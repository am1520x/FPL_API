from fastapi import APIRouter, HTTPException
from typing import Optional
from app.services.fpl_entry_service import FPLEntryService

router = APIRouter(prefix="/strategy", tags=["strategy"])

service = FPLEntryService()

@router.get("/{entry_id}/optimize-transfer", description="Suggest optimal 1 free transfer to maximize expected points for next gameweek.")
def optimize_transfer(entry_id: int, gameweek: Optional[int] = None):
    """
    Suggests optimal 1 free transfer to maximize expected points for next gameweek.
    
    - **entry_id**: FPL manager ID
    - **gameweek**: Optional gameweek (defaults to current)
    """
    try:
        result = service.optimize_transfer(entry_id, gameweek)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result