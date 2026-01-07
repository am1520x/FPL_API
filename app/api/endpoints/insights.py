# app/api/endpoints/insights.py
from fastapi import APIRouter, HTTPException
from typing import List, Any, Dict
import pandas as pd

from app.services.fpl_entry_service import FPLEntryService
from app.services.insights_service import InsightsService
from app.services.utils.enrichment import build_current_gw_stats, build_future_stats
from app.services.utils.bootstrap_cache import BootstrapCache

router = APIRouter(prefix="/entry", tags=["insights"])
bootstrap = BootstrapCache()
# Create service instances
fpl_service = FPLEntryService()
insights_service = InsightsService(fpl_service, bootstrap_cache=bootstrap.get())


@router.get("/{entry_id}/insights", response_model=List[Dict[str, Any]], description="Generate insights for an entry for a given gameweek and horizon.")
def get_insights(entry_id: int, gw: int | None = None, horizon: int = 5):
    """
    Generate insights for an entry for a given gameweek and horizon.
    **entry_id**: FPL manager ID
    """
    try:
        fpl_service = FPLEntryService()

        # 1) picks (JSON) → DataFrame with at least 'element' column
        if gw is None:
            gw = fpl_service.get_current_event()
        picks_json = fpl_service.get_entry_picks(entry_id, gw)
        picks = picks_json.get("picks") or []
        if not picks:
            return [{"title": "No data", "items": [f"No picks found for entry {entry_id} GW {gw}."]}]
        picks_df = pd.DataFrame(picks)

        # 2) build enriched_df (current GW) and future_df (next horizon)
        enriched_df = build_current_gw_stats(picks_df, gw=gw)
        future_df   = build_future_stats(picks_df, start_gw=gw + 1, horizon=horizon)

        # 3) generate insights
        insights_service = InsightsService(fpl_service, bootstrap_cache=None)
        insights = insights_service.generate_insights(
            enriched_df=enriched_df,
            future_df=future_df,
            gw=gw,
            get_element_summaries_fn=fpl_service.fetch_element_summaries,
            horizon=horizon
        )

        # 4) return as plain JSON
        return [{"title": i.title, "items": i.items} for i in insights]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

