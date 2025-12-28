# app/services/insights_service.py
from typing import List, Dict, Any
import pandas as pd
from dataclasses import dataclass

@dataclass
class Insight:
    title: str
    items: List[str]

class InsightsService:
    def __init__(self, fpl_entry_service, bootstrap_cache):
        """
        fpl_entry_service: the service you already created (FPLEntryService)
        bootstrap_cache: a cached lookup of player / team meta (you may implement)
        """
        self.fpl_entry_service = fpl_entry_service
        self.bootstrap = bootstrap_cache

    def _fetch_recent_histories(
        self, element_ids: List[int], get_element_summaries_fn, last_n=5
    ) -> Dict[int, pd.DataFrame]:
        summaries = get_element_summaries_fn(element_ids)
        out: Dict[int, pd.DataFrame] = {}
        for eid, js in summaries.items():
            hist = pd.DataFrame(js.get("history", []))
            if not hist.empty:
                hist = hist.sort_values("round", ascending=False).head(last_n)
            out[eid] = hist
        return out

    def generate_insights(
        self,
        enriched_df: pd.DataFrame,
        future_df: pd.DataFrame,
        gw: int,
        get_element_summaries_fn,
        bench_haul_threshold: int = 4,
        low_points_threshold: int = 2,
        low_points_streak_len: int = 2,
        horizon: int = 5,
    ) -> List[Insight]:
        """ 
        Returns a list of Insight objects with human-readable bullet points. 
        """ 
        name_col = "web_name"  if "web_name" in enriched_df.columns else ( "player_name" if "player_name" in enriched_df.columns else "second_name") 
        # 4.1 Bench hauls 
        bench = enriched_df[enriched_df["multiplier"] == 0] 
        bench_hauls = bench[(bench["points"] >= bench_haul_threshold)] 
        bench_items = [ 
            f"{row[name_col]} ({row.get('team_short','')}) scored {int(row['points'])} on the bench." 
            for _, row in bench_hauls.iterrows() 
            ] 
        # 4.2 Low-points streaks using recent history 
        starts = enriched_df["element"].unique().tolist() 
        recent = self._fetch_recent_histories(starts, get_element_summaries_fn, last_n=max(3, low_points_streak_len+1)) 
        cold_items = [] 
        for eid, hist in recent.items(): 
            if hist.empty: 
                continue 
            pts = (hist.sort_values("round")["total_points"].tolist()) # ascending order 
            # Find longest current streak of <= threshold 
            streak = 0 
            for p in reversed(pts): 
                if p <= low_points_threshold: 
                    streak += 1 
                else: 
                    break 
            if streak >= low_points_streak_len:
                row = enriched_df.loc[enriched_df["element"] == eid].iloc[0] 
                cold_items.append(f"{row[name_col]} ({row.get('team_short','')}) ≤{low_points_threshold} pts in {streak} consecutive GWs.") 
        # 4.3 Fixture runs by FDR (use future_df computed earlier) 
        fut = future_df.copy() 
        fut["avg_fdr"] = fut["avg_fdr_nextN"] 
        # Easiest/hardest (lower is easier) 
        easiest = fut.nsmallest(3, "avg_fdr").merge(enriched_df[[ "element", name_col, "team_short"]], on="element", how="left") 
        hardest = fut.nlargest(3, "avg_fdr").merge(enriched_df[[ "element", name_col, "team_short"]], on="element", how="left") 
        easy_items = [f"{r[name_col]} ({r.get('team_short','')}) has easy run: avg FDR {r['avg_fdr']:.2f} over next {horizon}." for _, r in easiest.iterrows() if pd.notna(r["avg_fdr"])] 
        hard_items = [f"{r[name_col]} ({r.get('team_short','')}) has tough run: avg FDR {r['avg_fdr']:.2f} over next {horizon}." for _, r in hardest.iterrows() if pd.notna(r["avg_fdr"])] 
        
        # 4.4 Rotation risk (mins <45 in 2 of last 3) 
        rot_items = [] 
        for eid, hist in recent.items(): 
            if hist.empty: 
                continue 
            last3 = hist.sort_values("round", ascending=False).head(3) 
            low_min = (last3["minutes"] < 45).sum() 
            if low_min >= 2: 
                row = enriched_df.loc[enriched_df["element"] == eid].iloc[0] 
                rot_items.append(f"{row[name_col]} rotation risk: <45 mins in {low_min}/last 3.") 
        
        # 4.5 Differentials with good run (selected_by% ≤ 10 and avg_fdr <= 3) 
        cand = (enriched_df.merge(fut[["element","avg_fdr"]], on="element", how="left") .copy()) 
        cand["sel"] = pd.to_numeric(cand.get("selected_by_percent", 0), errors="coerce") 
        diff = cand[(cand["sel"] <= 10) & (cand["avg_fdr"].fillna(5) <= 3.0)] 
        diff_items = [f"{r[name_col]} ({r.get('team_short','')}) is a differential ({r['sel']:.1f}% TSB) with good fixtures (avg FDR {r['avg_fdr']:.2f})." for _, r in diff.iterrows()] 
        insights = [ 
            Insight("Bench hauls (≥4 pts)", bench_items), 
            Insight("Cold streaks (≤2 pts, ≥2 GWs in a row)", cold_items), 
            Insight("Easiest upcoming runs", easy_items), 
            Insight("Toughest upcoming runs", hard_items), 
            Insight("Rotation risk (mins <45 in 2/3)", rot_items), 
            Insight("Differentials with good fixtures", diff_items), 
            ] 
        return insights
