from fastapi import APIRouter
from .endpoints.entry import router as entry_router
from .endpoints.insights import router as insights_router
from .endpoints.entry_metrics import router as metrics_router
from .endpoints.strategy import router as strategy_router
from .endpoints.league import router as league_router

router = APIRouter()
router.include_router(entry_router)
router.include_router(insights_router)
router.include_router(metrics_router) 
router.include_router(strategy_router)
router.include_router(league_router)