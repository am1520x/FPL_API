# app/api/endpoints/entry_metrics.py
from fastapi import APIRouter, HTTPException
from typing import Any
from app.services.fpl_entry_service import FPLEntryService

router = APIRouter(prefix="/entry", tags=["metrics"])

@router.get("/{entry_id}/expected_points", response_model=Any, description="Compute expected points for an entry over a given horizon.")
def expected_points(entry_id: int, horizon: int = 1):
    """
    Compute expected points for an entry over a given horizon.
    **entry_id**: FPL manager ID
    """
    service = FPLEntryService()
    try:
        return service.compute_expected_points_for_entry(entry_id, horizon=horizon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing expected_points: {e}")

@router.get("/{entry_id}/value_efficiency", response_model=Any, description="Compute value efficiency for an entry.")
def value_efficiency(entry_id: int):
    """
    Compute value efficiency for an entry.
    **entry_id**: FPL manager ID
    """
    service = FPLEntryService()
    try:
        return service.compute_value_efficiency(entry_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing value_efficiency: {e}")

@router.get("/{entry_id}/performance_analysis", response_model=Any, description="Compute performance analysis for an entry.")
def performance_analysis(entry_id: int):
    """
    Compute performance analysis for an entry.
    **entry_id**: FPL manager ID
    """
    service = FPLEntryService()
    try:
        return service.compute_performance_analysis(entry_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing performance_analysis: {e}")

@router.get("/{entry_id}/fixture_run", response_model=Any, description="Compute fixture run metrics for an entry over a given horizon.")
def fixture_run(entry_id: int, horizon: int = 5):
    """
    Compute fixture run metrics for an entry over a given horizon.
    **entry_id**: FPL manager ID
    """
    service = FPLEntryService()
    try:
        return service.compute_fixture_run(entry_id, horizon=horizon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing fixture_run: {e}")
