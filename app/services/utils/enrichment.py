# app/services/utils/enrichment.py
import time
import requests
import pandas as pd
from typing import Iterable, Dict, Any, Tuple
from urllib.parse import urljoin

FPL_BASE = "https://fantasy.premierleague.com/api/"

def _session_with_retries(total: int = 3, backoff: float = 0.5) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "FPL-Coach/1.0 (+education)",
        "Accept": "application/json, text/plain, */*",
    })
    s._retries = total
    s._backoff = backoff
    return s

def _get_json(session: requests.Session, path: str) -> Any:
    url = urljoin(FPL_BASE, path)
    for i in range(getattr(session, "_retries", 3)):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if i == getattr(session, "_retries", 3) - 1:
                raise RuntimeError(f"Failed to GET {url}: {e}")
            time.sleep(getattr(session, "_backoff", 0.5) * (2 ** i))
    # Fallback
    raise RuntimeError(f"Unreachable code for GET {url}")

def get_bootstrap(session: requests.Session = None) -> Dict[str, Any]:
    session = session or _session_with_retries()
    return _get_json(session, "bootstrap-static/")

def bootstrap_frames(session: requests.Session = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    session = session or _session_with_retries()
    data = get_bootstrap(session)
    elements = pd.DataFrame(data.get("elements", []))
    teams    = pd.DataFrame(data.get("teams", []))
    types    = pd.DataFrame(data.get("element_types", []))
    if elements.empty or teams.empty or types.empty:
        raise RuntimeError("Bootstrap data missing or empty.")
    return elements, teams, types

def get_element_summaries(
    element_ids: Iterable[int],
    session: requests.Session = None,
    sleep_between: float = 0.35
) -> Dict[int, Dict[str, Any]]:
    session = session or _session_with_retries()
    out: Dict[int, Dict[str, Any]] = {}
    for eid in sorted(set(int(x) for x in element_ids)):
        try:
            js = _get_json(session, f"element-summary/{eid}/")
            out[eid] = js
        except Exception as e:
            # Log / handle missing summary
            out[eid] = {}
        time.sleep(sleep_between)
    return out

def get_fixtures_for_events(
    events: Iterable[int],
    session: requests.Session = None
) -> pd.DataFrame:
    session = session or _session_with_retries()
    frames = []
    for ev in sorted(set(int(e) for e in events)):
        try:
            js = _get_json(session, f"fixtures/?event={ev}")
            frames.append(pd.DataFrame(js))
        except Exception:
            # skip if one event fails
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def _make_lookup_tables(session: requests.Session = None) -> Tuple[pd.DataFrame, Dict[int,str], Dict[int,str], Dict[int,str]]:
    session = session or _session_with_retries()
    elements, teams, types = bootstrap_frames(session)
    team_lookup  = teams.set_index("id")["name"].to_dict()
    team_short   = teams.set_index("id")["short_name"].to_dict()
    pos_lookup   = types.set_index("id")["singular_name_short"].to_dict()
    el_basic     = elements[[
        "id","team","element_type","web_name","first_name","second_name",
        "now_cost","cost_change_event","cost_change_start",
        "ep_next","ep_this","form","ict_index","points_per_game",
        "selected_by_percent","status"
    ]].rename(columns={"id":"element"})
    el_basic["now_price"] = el_basic["now_cost"] / 10.0
    # Ensure numeric types where possible
    el_basic["ep_next"] = pd.to_numeric(el_basic["ep_next"], errors="coerce").fillna(0.0)
    el_basic["ep_this"] = pd.to_numeric(el_basic["ep_this"], errors="coerce").fillna(0.0)
    el_basic["points_per_game"] = pd.to_numeric(el_basic["points_per_game"], errors="coerce").fillna(0.0)
    el_basic["form"] = pd.to_numeric(el_basic["form"], errors="coerce").fillna(0.0)
    el_basic["selected_by_percent"] = pd.to_numeric(el_basic["selected_by_percent"], errors="coerce").fillna(0.0)
    return el_basic, team_lookup, team_short, pos_lookup

# def build_current_gw_stats(
#     picks_df: pd.DataFrame, gw: int,
#     session: requests.Session = None
# ) -> pd.DataFrame:
#     session = session or _session_with_retries()
#     el_basic, team_lookup, team_short, pos_lookup = _make_lookup_tables(session)
#     element_ids = picks_df["element"].astype(int).tolist() if "element" in picks_df.columns else []
#     summaries = get_element_summaries(element_ids, session=session)
#     rows = []
#     for eid in element_ids:
#         js = summaries.get(eid, {})
#         hist = pd.DataFrame(js.get("history", []))
#         if hist.empty:
#             rows.append(pd.DataFrame([{"element": eid, "round": gw, "minutes": 0, "total_points": 0}]))
#         else:
#             row = hist.loc[hist["round"] == gw]
#             if row.empty:
#                 rows.append(pd.DataFrame([{"element": eid, "round": gw, "minutes": 0, "total_points": 0}]))
#             else:
#                 row = row.copy()
#                 row["element"] = eid
#                 rows.append(row)
#     gw_stats = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["element","round"])
#     keep_cols = {
#         "element": "element",
#         "round": "gw",
#         "minutes": "minutes",
#         "total_points": "points",
#         "bonus": "bonus",
#         "bps": "bps",
#         "ict_index": "ict_index_gw",
#         "goals_scored": "gs",
#         "assists": "a",
#         "clean_sheets": "cs",
#         "goals_conceded": "gc",
#         "saves": "saves",
#         "expected_goals": "xg",
#         "expected_assists": "xa",
#         "expected_goal_involvements": "xgi",
#         "expected_goals_conceded": "xgc",
#         "was_home": "was_home",
#         "kickoff_time": "kickoff_time",
#         "opponent_team": "opp_team_id",
#     }
#     # Only keep columns that exist
#     renamed = {c:keep_cols[c] for c in keep_cols if c in gw_stats.columns}
#     if renamed:
#         gw_stats = gw_stats[list(renamed.keys())].rename(columns=renamed)
#     else:
#         gw_stats = pd.DataFrame(columns=list(renamed.values()))
#     gw_stats["opponent"] = gw_stats["opp_team_id"].map(team_lookup) if "opp_team_id" in gw_stats.columns else None
#     out = picks_df.merge(el_basic, on="element", how="left").merge(gw_stats, on="element", how="left")
#     #out["team_name"]  = out["team"].map(team_lookup).fillna(out.get("team_name", None))
#     #out["team_short"] = out["team"].map(team_short).fillna(out.get("team_short", None))
#     # after you compute `out`
#     # Safely prefer mapped values, fall back to any existing column if present
#     mapped_team_name  = out["team"].map(team_lookup)  if "team" in out.columns else pd.Series(index=out.index, dtype="object")
#     mapped_team_short = out["team"].map(team_short)   if "team" in out.columns else pd.Series(index=out.index, dtype="object")

#     if "team_name" in out.columns:
#         out["team_name"] = mapped_team_name.combine_first(out["team_name"])
#     else:
#         out["team_name"] = mapped_team_name

#     if "team_short" in out.columns:
#         out["team_short"] = mapped_team_short.combine_first(out["team_short"])
#     else:
#         out["team_short"] = mapped_team_short
#     ##
#     out["position"]   = out["element_type"].map(pos_lookup) if "element_type" in out.columns else None
#     out["home_away"]  = out["was_home"].map({True:"H", False:"A"}) if "was_home" in out.columns else None
#     out = el_basic[["element","now_price"]].merge(out, on="element", how="right")
#     return out

def build_current_gw_stats(
    picks_df: pd.DataFrame, gw: int,
    session: requests.Session = None
) -> pd.DataFrame:
    session = session or _session_with_retries()
    el_basic, team_lookup, team_short, pos_lookup = _make_lookup_tables(session)

    # Ensure we have element ids
    if "element" not in picks_df.columns or picks_df.empty:
        # return a consistent empty frame with expected columns
        cols = ["element","web_name","team","team_name","team_short","element_type","position",
                "now_price","gw","minutes","points","xg","xa","xgi","xgc",
                "opp_team_id","opponent","home_away","bonus","bps","ict_index_gw"]
        return pd.DataFrame(columns=cols)

    element_ids = picks_df["element"].astype(int).tolist()
    summaries = get_element_summaries(element_ids, session=session)

    rows = []
    for eid in element_ids:
        js = summaries.get(eid, {})
        hist = pd.DataFrame(js.get("history", []))
        if hist.empty:
            rows.append(pd.DataFrame([{"element": eid, "round": gw, "minutes": 0, "total_points": 0}]))
        else:
            row = hist.loc[hist["round"] == gw]
            if row.empty:
                rows.append(pd.DataFrame([{"element": eid, "round": gw, "minutes": 0, "total_points": 0}]))
            else:
                row = row.copy()
                row["element"] = eid
                rows.append(row)

    gw_stats = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["element","round"])
    keep_cols = {
        "element": "element",
        "round": "gw",
        "minutes": "minutes",
        "total_points": "points",
        "bonus": "bonus",
        "bps": "bps",
        "ict_index": "ict_index_gw",
        "goals_scored": "gs",
        "assists": "a",
        "clean_sheets": "cs",
        "goals_conceded": "gc",
        "saves": "saves",
        "expected_goals": "xg",
        "expected_assists": "xa",
        "expected_goal_involvements": "xgi",
        "expected_goals_conceded": "xgc",
        "was_home": "was_home",
        "kickoff_time": "kickoff_time",
        "opponent_team": "opp_team_id",
    }
    renamed = {c: keep_cols[c] for c in keep_cols if c in gw_stats.columns}
    if renamed:
        gw_stats = gw_stats[list(renamed.keys())].rename(columns=renamed)
    else:
        gw_stats = pd.DataFrame(columns=list(keep_cols.values()))

    # opponent label if present
    if "opp_team_id" in gw_stats.columns:
        gw_stats["opponent"] = gw_stats["opp_team_id"].map(team_lookup)

    # Merge: picks → basic element meta → gw stats
    out = picks_df.merge(el_basic, on="element", how="left").merge(gw_stats, on="element", how="left")

    # Safe combine for team name/short
    mapped_team_name  = out["team"].map(team_lookup)  if "team" in out.columns else pd.Series(index=out.index, dtype="object")
    mapped_team_short = out["team"].map(team_short)   if "team" in out.columns else pd.Series(index=out.index, dtype="object")

    if "team_name" in out.columns:
        out["team_name"] = mapped_team_name.combine_first(out["team_name"])
    else:
        out["team_name"] = mapped_team_name

    if "team_short" in out.columns:
        out["team_short"] = mapped_team_short.combine_first(out["team_short"])
    else:
        out["team_short"] = mapped_team_short

    # Position label
    if "element_type" in out.columns:
        out["position"] = out["element_type"].map(pos_lookup)
    else:
        out["position"] = pd.Series(index=out.index, dtype="object")

    # Home/away
    if "was_home" in out.columns:
        out["home_away"] = out["was_home"].map({True: "H", False: "A"})
    else:
        out["home_away"] = pd.Series(index=out.index, dtype="object")

    # Ensure now_price is present (from el_basic) and keep it authoritative
    out = el_basic[["element", "now_price"]].merge(out, on="element", how="right")

    return out


def build_future_stats(
    picks_df: pd.DataFrame,
    start_gw: int,
    horizon: int = 5,
    session: requests.Session = None
) -> pd.DataFrame:
    session = session or _session_with_retries()
    el_basic, team_lookup, team_short, pos_lookup = _make_lookup_tables(session)
    base = (picks_df[["element"]].drop_duplicates()
            .merge(el_basic[["element","team","now_price"]], on="element", how="left"))
    base["team"] = base["team"].astype(int)
    events = list(range(start_gw, start_gw + max(0, horizon)))
    fx = get_fixtures_for_events(events, session=session)
    if fx.empty:
        base["next_opponents"]   = [[] for _ in range(len(base))]
        base["next_is_home"]     = [[] for _ in range(len(base))]
        base["next_fdr"]         = [[] for _ in range(len(base))]
        base["avg_fdr_nextN"]    = 0.0
        base["sum_fdr_nextN"]    = 0
        return base
    fx_small = fx[["event","id","team_h","team_a","team_h_difficulty","team_a_difficulty"]].copy()
    # build mapping for each team
    bundle: Dict[int, Dict[str, Any]] = {}
    for t in base["team"].unique():
        sub = fx_small[(fx_small["team_h"] == t) | (fx_small["team_a"] == t)].sort_values(["event","id"])
        opps, homes, fdrs = [], [], []
        for _, r in sub.iterrows():
            if r["team_h"] == t:
                opps.append(team_short.get(int(r["team_a"]), f"T{r['team_a']}"))
                homes.append(True)
                fdrs.append(int(r["team_h_difficulty"]))
            else:
                opps.append(team_short.get(int(r["team_h"]), f"T{r['team_h']}"))
                homes.append(False)
                fdrs.append(int(r["team_a_difficulty"]))
            if len(opps) >= horizon:
                break
        bundle[int(t)] = {
            "next_opponents": opps,
            "next_is_home": homes,
            "next_fdr": fdrs,
            "avg_fdr_nextN": float(pd.Series(fdrs).mean()) if fdrs else None,
            "sum_fdr_nextN": int(pd.Series(fdrs).sum()) if fdrs else None
        }
    # map to players
    base["next_opponents"] = base["team"].map(lambda t: bundle.get(int(t), {}).get("next_opponents", []))
    base["next_is_home"]   = base["team"].map(lambda t: bundle.get(int(t), {}).get("next_is_home", []))
    base["next_fdr"]       = base["team"].map(lambda t: bundle.get(int(t), {}).get("next_fdr", []))
    base["avg_fdr_nextN"]  = base["team"].map(lambda t: bundle.get(int(t), {}).get("avg_fdr_nextN", 0.0))
    base["sum_fdr_nextN"]  = base["team"].map(lambda t: bundle.get(int(t), {}).get("sum_fdr_nextN", 0))
    return base
