# tests/conftest.py
import types
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Use your real FastAPI app
from app.main import app

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

#
# Common monkeypatch helpers
#

@pytest.fixture
def patch_fpl_service(monkeypatch):
    """
    Patch the FPLEntryService methods used by the insights and metrics endpoints,
    to avoid network calls.
    """
    import app.services.fpl_entry_service as svc

    # current event (e.g., GW 9)
    monkeypatch.setattr(svc.FPLEntryService, "get_current_event", lambda self: 9)

    # picks for the GW (minimal schema with 'element')
    def fake_get_entry_picks(self, entry_id: int, event_id=None):
        return {
            "picks": [
                {"element": 101, "multiplier": 2, "is_captain": True,  "is_vice_captain": False, "position": 1},
                {"element": 202, "multiplier": 1, "is_captain": False, "is_vice_captain": True,  "position": 2},
            ]
        }
    monkeypatch.setattr(svc.FPLEntryService, "get_entry_picks", fake_get_entry_picks)

    # element summaries (not actually used by our mocked insights here, but provided)
    def fake_fetch_element_summaries(self, element_ids, sleep_between: float = 0.0):
        return {int(e): {"history": [], "fixtures": []} for e in element_ids}
    monkeypatch.setattr(svc.FPLEntryService, "fetch_element_summaries", fake_fetch_element_summaries)

    # expected_points + value_efficiency + performance_analysis + fixture_run
    # If your metrics endpoints call these service methods, stub them to deterministic values
    def fake_expected_points(self, entry_id: int, horizon: int = 1):
        return {
            "entry_id": entry_id,
            "horizon": horizon,
            "team_expected_points": 42.5,
            "players": [{"element": 101, "player_name": "Demo", "expected_basic": 5.0, "expected_adj": 5.5}],
        }
    monkeypatch.setattr(svc.FPLEntryService, "compute_expected_points_for_entry", fake_expected_points)

    def fake_value_efficiency(self, entry_id: int):
        return {
            "entry_id": entry_id,
            "team_average_value_efficiency": 1.23,
            "players": [{"element": 101, "player_name": "Demo", "cost_m": 5.5, "expected_basic": 6.0, "value_eff": 1.09}],
            "recommendations": [],
        }
    monkeypatch.setattr(svc.FPLEntryService, "compute_value_efficiency", fake_value_efficiency)

    def fake_performance_analysis(self, entry_id: int):
        return {
            "entry_id": entry_id,
            "players": [{"gameweek": 9, "points_per_game": 5.2, "ep_this": 4.8, "delta": 0.4, "status": "Normal"}],
            "summary": {"under_performers_count": 0, "over_performers_count": 0},
        }
    monkeypatch.setattr(svc.FPLEntryService, "compute_performance_analysis", fake_performance_analysis)

    def fake_fixture_run(self, entry_id: int, horizon: int = 5):
        return {
            "entry_id": entry_id,
            "horizon": horizon,
            "team_avg_fdr": 2.8,
            "players": [{"element": 101, "now_price": 5.5, "next_fdr": [2,3,2], "avg_fdr_nextN": 2.33, "fixture_status": "favourable"}],
            "summary": {"favourable_players_count": 1, "tough_run_players_count": 0},
        }
    monkeypatch.setattr(svc.FPLEntryService, "compute_fixture_run", fake_fixture_run)


@pytest.fixture
def patch_enrichment(monkeypatch):
    """
    Patch build_current_gw_stats and build_future_stats to return tiny DataFrames.
    This isolates the insights endpoint from any external HTTP calls.
    """
    import app.services.utils.enrichment as enrich

    def fake_build_current_gw_stats(picks_df: pd.DataFrame, gw: int, session=None):
        # minimal columns used by your endpoint -> InsightsService.generate_insights
        return pd.DataFrame([
            {
                "element": 101,
                "web_name": "PlayerA",
                "ep_next": 5.0,
                "form": 3.2,
                "home_away": "H",     # used for home/away adjustment in expected points calc
                "multiplier": 2,      # optional, handy for bench/captain logic
                "team_short": "AAA",
                "points": 6,
            },
            {
                "element": 202,
                "web_name": "PlayerB",
                "ep_next": 4.0,
                "form": 1.1,
                "home_away": "A",
                "multiplier": 1,
                "team_short": "BBB",
                "points": 2,
            },
        ])

    def fake_build_future_stats(picks_df: pd.DataFrame, start_gw: int, horizon: int, session=None):
        return pd.DataFrame([
            {
                "element": 101,
                "now_price": 5.5,
                "next_fdr": [2, 3, 2],
                "avg_fdr_nextN": 2.33,
                "sum_fdr_nextN": 7,
                "next_opponents": ["BBB", "CCC", "DDD"],
                "next_is_home": [True, False, True],
            },
            {
                "element": 202,
                "now_price": 4.5,
                "next_fdr": [4, 4, 5],
                "avg_fdr_nextN": 4.33,
                "sum_fdr_nextN": 13,
                "next_opponents": ["EEE", "FFF", "GGG"],
                "next_is_home": [False, True, False],
            },
        ])

    monkeypatch.setattr(enrich, "build_current_gw_stats", fake_build_current_gw_stats)
    monkeypatch.setattr(enrich, "build_future_stats", fake_build_future_stats)


@pytest.fixture
def patch_insights_generate(monkeypatch):
    """
    Patch InsightsService.generate_insights to a deterministic output.
    """
    import app.services.insights_service as insvc

    def fake_generate_insights(self, enriched_df, future_df, gw, get_element_summaries_fn, horizon: int = 5, **kwargs):
        # return objects with .title and .items (like your dataclass Insight)
        return [
            types.SimpleNamespace(title="Bench hauls (≥4 pts)", items=["PlayerA (AAA) scored 6 on the bench."]),
            types.SimpleNamespace(title="Easiest upcoming runs", items=["PlayerA (AAA) avg FDR 2.33 over next 3."]),
        ]

    monkeypatch.setattr(insvc.InsightsService, "generate_insights", fake_generate_insights)
