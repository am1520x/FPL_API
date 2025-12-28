# tests/test_metrics_endpoints.py

def test_expected_points_endpoint(client, patch_fpl_service):
    resp = client.get("/entry/3982786/expected_points?horizon=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entry_id"] == 3982786
    assert "team_expected_points" in data

def test_value_efficiency_endpoint(client, patch_fpl_service):
    resp = client.get("/entry/3982786/value_efficiency")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entry_id"] == 3982786
    assert "team_average_value_efficiency" in data

def test_performance_analysis_endpoint(client, patch_fpl_service):
    resp = client.get("/entry/3982786/performance_analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entry_id"] == 3982786
    assert "summary" in data

def test_fixture_run_endpoint(client, patch_fpl_service):
    resp = client.get("/entry/3982786/fixture_run?horizon=3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entry_id"] == 3982786
    assert "team_avg_fdr" in data
