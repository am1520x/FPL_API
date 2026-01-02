from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Any
from app.services.league_service import LeagueService
from app.services.utils.bootstrap_cache import BootstrapCache


router = APIRouter(prefix="/league", tags=["league"])
bootstrap = BootstrapCache()


@router.get("/standings/{league_id}")
async def get_league_standings(league_id: int) -> Dict[str, Any]:
    """Get league standings."""
    standings = LeagueService.get_league_standings(league_id)
    if not standings:
        raise HTTPException(status_code=404, detail="League not found")
    return standings


@router.get("/analysis/top-bottom/{league_id}")
async def get_top_bottom_performers(
    league_id: int,
    current_gameweek: int = Query(None, description="Current gameweek number")
) -> List[Dict[str, Any]]:
    """Get top and bottom performers per gameweek."""
    if current_gameweek is None:
        # Get current gameweek from bootstrap
        events = bootstrap.get_events()
        current_gameweek = next((e['id'] for e in events if e['is_current']), None)
        if current_gameweek is None:
            raise HTTPException(status_code=400, detail="Could not determine current gameweek")
    
    
    data = LeagueService.get_top_bottom_performers(league_id, current_gameweek)
    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    return data


@router.get("/analysis/streaks/{league_id}")
async def get_streaks_analysis(
    league_id: int,
    current_gameweek: int = Query(None, description="Current gameweek number")
) -> Dict[str, Any]:
    """Get top and bottom streaks for all managers."""
    if current_gameweek is None:
        # Get current gameweek from bootstrap
        events = bootstrap.get_events()
        current_gameweek = next((e['id'] for e in events if e['is_current']), None)
        if current_gameweek is None:
            raise HTTPException(status_code=400, detail="Could not determine current gameweek")
    
    
    data = LeagueService.calculate_streaks(league_id, current_gameweek)
    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    return data


@router.get("/analysis/bench-points/{league_id}")
async def get_bench_points(
    league_id: int,
    current_gameweek: int = Query(None, description="Current gameweek number")
) -> List[Dict[str, Any]]:
    """Get total bench points per manager."""
    if current_gameweek is None:
        # Get current gameweek from bootstrap
        events = bootstrap.get_events()
        current_gameweek = next((e['id'] for e in events if e['is_current']), None)
        if current_gameweek is None:
            raise HTTPException(status_code=400, detail="Could not determine current gameweek")
    
    
    data = LeagueService.get_bench_points_analysis(league_id, current_gameweek)
    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    return data


@router.get("/analysis/squad-value/{league_id}")
async def get_squad_value(
    league_id: int,
    current_gameweek: int = Query(None, description="Current gameweek number")
) -> List[Dict[str, Any]]:
    """Get squad value analysis per manager."""
    if current_gameweek is None:
        # Get current gameweek from bootstrap
        events = bootstrap.get_events()
        current_gameweek = next((e['id'] for e in events if e['is_current']), None)
        if current_gameweek is None:
            raise HTTPException(status_code=400, detail="Could not determine current gameweek")
    
    
    data = LeagueService.get_squad_value_analysis(league_id, current_gameweek)
    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    return data


@router.get("/analysis/transfers/{league_id}")
async def get_transfers(
    league_id: int,
    current_gameweek: int = Query(None, description="Current gameweek number")
) -> List[Dict[str, Any]]:
    """Get total transfers per manager."""
    if current_gameweek is None:
        # Get current gameweek from bootstrap
        events = bootstrap.get_events()
        current_gameweek = next((e['id'] for e in events if e['is_current']), None)
        if current_gameweek is None:
            raise HTTPException(status_code=400, detail="Could not determine current gameweek")
    
    
    data = LeagueService.get_transfers_analysis(league_id, current_gameweek)
    if not data:
        raise HTTPException(status_code=404, detail="No data found")
    return data