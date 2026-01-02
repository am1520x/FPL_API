# app/services/fpl_entry_service.py
import time
import requests
import pandas as pd
from typing import Optional, Dict, Any, List
from pulp import LpProblem, LpMaximize, LpVariable, lpSum
from app.core.config import settings
from app.services.utils.enrichment import (
    get_bootstrap,
    bootstrap_frames,
    build_current_gw_stats,
    build_future_stats
)

class FPLEntryService:
    base_url = "https://fantasy.premierleague.com/api"
    def __init__(self, session=None):
        self.session = session
        self.base_url = settings.FPL_BASE_URL

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _get(self, url: str) -> Any:
        for attempt in range(3):
            r = requests.get(url, timeout=20)
            if r.ok:
                return r.json()
            time.sleep(0.7 * (attempt+1))
        r.raise_for_status()

    def compute_expected_points_for_entry(self, entry_id: int, horizon: int = 1) -> Dict[str, Any]:
        # 1) Get picks for current GW
        picks_resp = self.fetch_entry_picks(entry_id)
        picks_list = picks_resp.get("picks") or []
        if not picks_list:
            return {
                "entry_id": entry_id,
                "horizon": horizon,
                "team_expected_points": 0.0,
                "players": [],
                "warning": "No picks data returned for this entry."
            }
        picks_df = pd.DataFrame(picks_list)
        current_event = self.get_current_event()
        # 2) Enriched table
        enriched_df = build_current_gw_stats(picks_df, gw=current_event)
        future_df   = build_future_stats(picks_df, start_gw=current_event+1, horizon=horizon)
        # 3) Compute expected_basic
        enriched_df["expected_basic"] = enriched_df["ep_next"].apply(lambda x: self._safe_float(x, 0.0))
        # 4) Enhanced fixture adjustment logic:
        #    - home/away: if home→ multiplier_up, away→ multiplier_down.
        #    - team strength: use now_price proxy or other metrics if available.
        #    - form: high form gets uplift.
        enriched_df["is_home"] = enriched_df["home_away"].apply(lambda x: True if x=="H" else False)
        enriched_df["home_multiplier"] = enriched_df["is_home"].apply(lambda h: 1.10 if h else 0.90)
        enriched_df["form_multiplier"] = enriched_df["form"].apply(lambda f: 1.05 if f>=3.0 else (0.95 if f<1.0 else 1.0))
        # integrate future fixture difficulty
        merged = enriched_df.merge(
            future_df[["element","avg_fdr_nextN"]], on="element", how="left"
        )
        max_fdr = merged["avg_fdr_nextN"].max() if merged["avg_fdr_nextN"].notna().any() else 5.0
        merged["fdr_multiplier"] = merged["avg_fdr_nextN"].apply(
            lambda x: (max_fdr + 1 - x)/max_fdr if pd.notna(x) else 1.0
        )
        # Adjusted expected:
        merged["expected_adj"] = merged["expected_basic"] * merged["home_multiplier"] * merged["form_multiplier"] * merged["fdr_multiplier"]
        # 5) Aggregate
        total_expected = float(merged["expected_adj"].sum())
        players_list = merged[["element","web_name","expected_basic","expected_adj"]].rename(
            columns={"web_name":"player_name"}).to_dict(orient="records")
        return {
            "entry_id": entry_id,
            "horizon": horizon,
            "team_expected_points": total_expected,
            "players": players_list
        }

    def compute_value_efficiency(self, entry_id: int) -> Dict[str, Any]:
        picks_resp = self.fetch_entry_picks(entry_id)
        picks_list = picks_resp.get("picks") or []
        if not picks_list:
            return {"entry_id": entry_id, "team_average_value_efficiency": 0.0, "players": [], "warning":"No picks data."}
        picks_df = pd.DataFrame(picks_list)
        current_event = self.get_current_event()
        enriched_df = build_current_gw_stats(picks_df, gw=current_event)
        enriched_df["expected_basic"] = enriched_df["ep_next"].apply(lambda x: self._safe_float(x, 0.0))
        enriched_df["cost_m"] = enriched_df["now_price"].apply(lambda x: self._safe_float(x, 0.0))
        enriched_df["value_eff"] = enriched_df.apply(
            lambda r: (r["expected_basic"]/r["cost_m"]) if r["cost_m"]>0 else 0.0, axis=1
        )
        team_avg = float(enriched_df["value_eff"].mean())
        sorted_df = enriched_df.sort_values("value_eff", ascending=False)
        players_list = sorted_df[["element","web_name","cost_m","expected_basic","value_eff"]].rename(
            columns={"web_name":"player_name"}).to_dict(orient="records")
        recs = []
        threshold = team_avg * 0.8
        for r in sorted_df.itertuples():
            if getattr(r, "value_eff", 0.0) < threshold:
                recs.append(f"Consider transferring out {getattr(r,'web_name')} (value_eff {getattr(r,'value_eff'):.2f}).")
        return {
            "entry_id": entry_id,
            "team_average_value_efficiency": team_avg,
            "players": players_list,
            "recommendations": recs
        }

    def compute_performance_analysis(self, entry_id: int) -> Dict[str, Any]:
        picks_resp = self.fetch_entry_history(entry_id)
        history = picks_resp.get("current") or []
        if not history:
            return {"entry_id": entry_id, "players": [], "summary": {"under_performers_count": 0, "over_performers_count": 0}, "warning":"No history data."}
        # Here we assume history list contains dicts with 'points_per_game', 'event' etc.
        hist_df = pd.DataFrame(history)
        hist_df["points_per_game"] = hist_df["points_per_game"].apply(lambda x: self._safe_float(x, 0.0))
        hist_df["ep_this"] = hist_df.get("ep_this", 0.0).apply(lambda x: self._safe_float(x, 0.0))
        hist_df["delta"] = hist_df["points_per_game"] - hist_df["ep_this"]
        hist_df["status"] = hist_df["delta"].apply(lambda d: "Under-performing" if d < -1.5 else ("Over-performing" if d > 1.5 else "Normal"))
        players_list = hist_df[["event","points_per_game","ep_this","delta","status"]].rename(
            columns={"event":"gameweek"}).to_dict(orient="records")
        under = int((hist_df["status"] == "Under-performing").sum())
        over  = int((hist_df["status"] == "Over-performing").sum())
        return {
            "entry_id": entry_id,
            "players": players_list,
            "summary": {"under_performers_count": under, "over_performers_count": over}
        }

    def compute_fixture_run(self, entry_id: int, horizon: int = 5) -> Dict[str, Any]:
        picks_resp = self.fetch_entry_picks(entry_id)
        picks_list = picks_resp.get("picks") or []
        if not picks_list:
            return {"entry_id": entry_id, "horizon": horizon, "team_avg_fdr": None, "players": [], "warning":"No picks data."}
        picks_df = pd.DataFrame(picks_list)
        current_event = self.get_current_event()
        future_df = build_future_stats(picks_df, start_gw=current_event+1, horizon=horizon)
        future_df["avg_fdr_nextN"] = future_df["avg_fdr_nextN"].apply(lambda x: float(x) if x is not None else 0.0)
        future_df["fixture_status"] = future_df["avg_fdr_nextN"].apply(
            lambda x: "favourable" if x <= 2.5 else ("tough" if x >= 4.0 else "neutral")
        )
        players_list = future_df[["element","now_price","next_fdr","avg_fdr_nextN","fixture_status"]].rename(
            columns={"now_price":"now_price_m"}).to_dict(orient="records")
        team_avg_fdr = float(future_df["avg_fdr_nextN"].mean())
        return {
            "entry_id": entry_id,
            "horizon": horizon,
            "team_avg_fdr": team_avg_fdr,
            "players": players_list,
            "summary": {
                "favourable_players_count": int((future_df["fixture_status"] == "favourable").sum()),
                "tough_run_players_count": int((future_df["fixture_status"] == "tough").sum())
            }
        }

    def get_current_event(self) -> int:
        data = self._get(f"{self.base_url}/bootstrap-static/")
        events = data.get("events", [])
        current = [e for e in events if e.get("is_current")]
        if current:
            return current[0]["id"]
        nxt = [e for e in events if e.get("is_next")]
        if nxt:
            return nxt[0]["id"]
        finished = [e for e in events if e.get("finished")]
        return finished[-1]["id"] if finished else None

    def get_entry_history(self, entry_id: int) -> Dict[str, Any]:
        return self._get(f"{self.base_url}/entry/{entry_id}/history/")

    def get_entry_picks(self, entry_id: int, event_id: Optional[int] = None) -> Dict[str, Any]:
        if event_id is None:
            event_id = self.get_current_event()
        return self._get(f"{self.base_url}/entry/{entry_id}/event/{event_id}/picks/")

    def get_entry_transfers(self, entry_id: int) -> List[Dict[str, Any]]:
        return self._get(f"{self.base_url}/entry/{entry_id}/transfers/")

    def fetch_element_summaries(self, element_ids, sleep_between: float = 0.35):
        """
        Return {element_id: json} for /element-summary/{id}/ with basic retry & pacing.
        """
        out = {}
        for eid in sorted(set(int(x) for x in element_ids)):
            url = f"{self.base_url}/element-summary/{eid}/"
            for attempt in range(3):
                try:
                    r = requests.get(url, timeout=20)
                    r.raise_for_status()
                    out[eid] = r.json()
                    break
                except Exception as e:
                    if attempt == 2:
                        # final attempt failed
                        out[eid] = {}
                    else:
                        time.sleep(0.6 * (attempt + 1))
            time.sleep(sleep_between)  # be a good citizen
        return out
    
    def _get_bootstrap_data(self):
        """Helper to get bootstrap-static data"""
        return self._get(f"{self.base_url}/bootstrap-static/")
    
    def optimize_transfer(self, entry_id: int, gameweek: Optional[int] = None):
        """
        Suggests optimal 1 free transfer to maximize expected points for next GW
        """
        # Get current gameweek if not provided
        if gameweek is None:
            gameweek = self.get_current_event()
        
        # Get current team picks
        picks_data = self.get_entry_picks(entry_id, gameweek)
        current_team_ids = [pick['element'] for pick in picks_data['picks']]
        
        # Get bootstrap data (all players)
        bootstrap = self._get_bootstrap_data()
        
        # Convert to DataFrame
        df = pd.DataFrame(bootstrap['elements'])
        df = df.set_index(pd.Index(range(len(df))))
        
        # Get team value and bank
        team_value = picks_data['entry_history']['value']
        bank = picks_data['entry_history']['bank']
        total_budget = team_value + bank
        
        # Setup optimization model
        model = LpProblem("FPL_Transfer_Optimizer", LpMaximize)
        
        # Variables
        is_in_squad = LpVariable.dicts("squad", df.index, cat="Binary")
        is_transfer_in = LpVariable.dicts("transfer_in", df.index, cat="Binary")
        
        # Objective: Maximize next GW expected points
        model += lpSum(df.loc[i, 'ep_next'] * is_in_squad[i] for i in df.index)
        
        # Constraints
        # Total squad size = 15
        model += lpSum(is_in_squad[i] for i in df.index) == 15
        
        # Transfer logic
        for i in df.index:
            if df.loc[i, 'id'] not in current_team_ids:
                model += is_transfer_in[i] >= is_in_squad[i]
            else:
                model += is_transfer_in[i] == 0
        
        # Limit to 1 free transfer
        model += lpSum(is_transfer_in[i] for i in df.index) <= 1
        
        # Budget constraint
        model += lpSum(df.loc[i, 'now_cost'] * is_in_squad[i] for i in df.index) <= total_budget
        
        # Position constraints (1=GKP, 2=DEF, 3=MID, 4=FWD)
        model += lpSum(is_in_squad[i] for i in df.index if df.loc[i, 'element_type'] == 1) == 2
        model += lpSum(is_in_squad[i] for i in df.index if df.loc[i, 'element_type'] == 2) == 5
        model += lpSum(is_in_squad[i] for i in df.index if df.loc[i, 'element_type'] == 3) == 5
        model += lpSum(is_in_squad[i] for i in df.index if df.loc[i, 'element_type'] == 4) == 3
        
        # Club constraint: Max 3 players per team
        for team_id in df['team_code'].unique():
            model += lpSum(is_in_squad[i] for i in df.index if df.loc[i, 'team_code'] == team_id) <= 3
        
        # Solve
        status = model.solve()
        
        # Extract results
        transfer_in = []
        for i in df.index:
            if is_transfer_in[i].varValue == 1:
                player = df.loc[i]
                transfer_in.append({
                    "id": int(player['id']),
                    "web_name": player['web_name'],
                    "team": int(player['team']),
                    "position": int(player['element_type']),
                    "cost": player['now_cost'],
                    "ep_next": player['ep_next']
                })
        
        new_squad_ids = [df.loc[i, 'id'] for i in df.index if is_in_squad[i].varValue == 1]
        transfer_out = []
        for old_id in current_team_ids:
            if old_id not in new_squad_ids:
                player = df[df['id'] == old_id].iloc[0]
                transfer_out.append({
                    "id": int(old_id),
                    "web_name": player['web_name'],
                    "team": int(player['team']),
                    "position": int(player['element_type']),
                    "cost": player['now_cost']
                })
        
        return {
            "gameweek": gameweek,
            "optimization_status": "success" if status == 1 else "failed",
            "transfer_in": transfer_in,
            "transfer_out": transfer_out,
            "expected_points_gain": sum(p['ep_next'] for p in transfer_in) if transfer_in else 0
        }
