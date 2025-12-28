# tests/test_insights_endpoint.py
import json
import pandas as pd

def test_insights_happy_path(client, patch_fpl_service, patch_enrichment, patch_insights_generate):
    resp = client.get("/entry/3982786/insights?gw=9&horizon=3")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["title"].startswith("Bench hauls") for item in data)
    assert any("avg FDR" in item["items"][0] for item in data if item["title"].startswith("Easiest"))

def test_insights_no_picks(client, patch_fpl_service, patch_enrichment, monkeypatch):
    # Force no picks
    import app.services.fpl_entry_service as svc
    def no_picks(self, entry_id: int, event_id=None):
        return {"picks": []}
    monkeypatch.setattr(svc.FPLEntryService, "get_entry_picks", no_picks)

    resp = client.get("/entry/3982786/insights?gw=9")
    assert resp.status_code == 200
    data = resp.json()
    assert data and data[0]["title"] == "No data"
    assert "No picks found" in data[0]["items"][0]

def test_insights_build_raises_500(client, patch_fpl_service, monkeypatch):
    # Make build_current_gw_stats raise to check 500 handling
    import app.services.utils.enrichment as enrich
    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")
    monkeypatch.setattr(enrich, "build_current_gw_stats", boom)

    resp = client.get("/entry/3982786/insights?gw=9")
    assert resp.status_code == 500
    assert "kaboom" in resp.json()["detail"]
