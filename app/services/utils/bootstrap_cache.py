# app/services/utils/bootstrap_cache.py
from __future__ import annotations
import time
from typing import Any, Dict, Optional
from app.services.utils.enrichment import get_bootstrap

class BootstrapCache:
    def __init__(self, ttl_seconds: int = 600):
        self._data: Optional[Dict[str, Any]] = None
        self._ts: float = 0.0
        self._ttl = ttl_seconds

    def get(self) -> Dict[str, Any]:
        now = time.time()
        if not self._data or (now - self._ts) > self._ttl:
            self._data = get_bootstrap()
            self._ts = now
        return self._data
