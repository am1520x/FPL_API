import requests
from typing import Dict, List, Optional, Any
import pandas as pd
from app.core.config import settings

BASE_URL = "https://fantasy.premierleague.com/api"


class LeagueService:
    """Service for fetching and analyzing FPL league data."""
    
    @staticmethod
    def get_league_standings(league_id: int) -> Optional[Dict[str, Any]]:
        """Fetch league standings."""
        url = f"{BASE_URL}/leagues-classic/{league_id}/standings/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching league standings: {e}")
            return None
    
    @staticmethod
    def get_manager_history(manager_id: int) -> Optional[Dict[str, Any]]:
        """Fetch manager's history data."""
        url = f"{BASE_URL}/entry/{manager_id}/history/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching manager {manager_id} history: {e}")
            return None
    
    @staticmethod
    def get_manager_picks(manager_id: int, gameweek: int) -> Optional[Dict[str, Any]]:
        """Fetch manager's picks for a specific gameweek."""
        url = f"{BASE_URL}/entry/{manager_id}/event/{gameweek}/picks/"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching picks for manager {manager_id}, GW {gameweek}: {e}")
            return None
    
    @staticmethod
    def collect_all_managers_data(league_id: int, current_gameweek: int) -> Dict[int, Dict[str, Any]]:
        """Collect historical data for all managers in a league."""
        standings = LeagueService.get_league_standings(league_id)
        if not standings or 'standings' not in standings or 'results' not in standings['standings']:
            return {}
        
        manager_ids = [manager['entry'] for manager in standings['standings']['results']]
        all_managers_data = {}
        
        for manager_id in manager_ids:
            manager_history = LeagueService.get_manager_history(manager_id)
            
            if manager_history:
                all_managers_data[manager_id] = {
                    'history': manager_history,
                    'picks_by_gameweek': {}
                }
                
                # Fetch picks for each gameweek
                for gw in range(1, current_gameweek + 1):
                    gw_picks = LeagueService.get_manager_picks(manager_id, gw)
                    if gw_picks:
                        all_managers_data[manager_id]['picks_by_gameweek'][gw] = gw_picks
        
        return all_managers_data
    
    @staticmethod
    def get_top_bottom_performers(league_id: int, current_gameweek: int) -> List[Dict[str, Any]]:
        """Analyze top and bottom performers per gameweek."""
        all_managers_data = LeagueService.collect_all_managers_data(league_id, current_gameweek)
        
        # Build time series data
        managers_time_series_data = []
        for manager_id, manager_data in all_managers_data.items():
            if 'history' in manager_data and 'current' in manager_data['history']:
                for gw_entry in manager_data['history']['current']:
                    managers_time_series_data.append({
                        'manager_id': manager_id,
                        'gameweek': gw_entry['event'],
                        'total_points': gw_entry['total_points'],
                        'overall_rank': gw_entry['overall_rank']
                    })
        
        if not managers_time_series_data:
            return []
        
        df = pd.DataFrame(managers_time_series_data)
        top_bottom_per_gw = []
        
        for gw in df['gameweek'].unique():
            gameweek_df = df[df['gameweek'] == gw]
            max_points = gameweek_df['total_points'].max()
            min_points = gameweek_df['total_points'].min()
            
            top_bottom_per_gw.append({
                'gameweek': int(gw),
                'top_manager_ids': gameweek_df[gameweek_df['total_points'] == max_points]['manager_id'].tolist(),
                'bottom_manager_ids': gameweek_df[gameweek_df['total_points'] == min_points]['manager_id'].tolist(),
                'max_points': int(max_points),
                'min_points': int(min_points)
            })
        
        return top_bottom_per_gw
    
    @staticmethod
    def calculate_streaks(league_id: int, current_gameweek: int) -> Dict[str, Any]:
        """Calculate top and bottom streaks for managers."""
        standings = LeagueService.get_league_standings(league_id)
        if not standings:
            return {}
        
        standings_results = standings['standings']['results']
        top_bottom_data = LeagueService.get_top_bottom_performers(league_id, current_gameweek)
        
        manager_top_weeks = {}
        manager_bottom_weeks = {}
        manager_top_streaks = {}
        manager_bottom_streaks = {}
        current_top_streaks = {}
        current_bottom_streaks = {}
        prev_top_managers = set()
        prev_bottom_managers = set()
        
        sorted_data = sorted(top_bottom_data, key=lambda x: x['gameweek'])
        
        for entry in sorted_data:
            current_gw_top_managers = set(entry['top_manager_ids'])
            current_gw_bottom_managers = set(entry['bottom_manager_ids'])
            
            # Top managers
            for manager_id in current_gw_top_managers:
                manager_top_weeks[manager_id] = manager_top_weeks.get(manager_id, 0) + 1
                if manager_id in prev_top_managers:
                    current_top_streaks[manager_id] = current_top_streaks.get(manager_id, 0) + 1
                else:
                    current_top_streaks[manager_id] = 1
                manager_top_streaks[manager_id] = max(manager_top_streaks.get(manager_id, 0), current_top_streaks[manager_id])
            
            for manager_id in list(current_top_streaks.keys()):
                if manager_id not in current_gw_top_managers:
                    current_top_streaks[manager_id] = 0
            
            # Bottom managers
            for manager_id in current_gw_bottom_managers:
                manager_bottom_weeks[manager_id] = manager_bottom_weeks.get(manager_id, 0) + 1
                if manager_id in prev_bottom_managers:
                    current_bottom_streaks[manager_id] = current_bottom_streaks.get(manager_id, 0) + 1
                else:
                    current_bottom_streaks[manager_id] = 1
                manager_bottom_streaks[manager_id] = max(manager_bottom_streaks.get(manager_id, 0), current_bottom_streaks[manager_id])
            
            for manager_id in list(current_bottom_streaks.keys()):
                if manager_id not in current_gw_bottom_managers:
                    current_bottom_streaks[manager_id] = 0
            
            prev_top_managers = current_gw_top_managers
            prev_bottom_managers = current_gw_bottom_managers
        
        def get_manager_name(manager_id):
            return next((m['player_name'] for m in standings_results if m['entry'] == manager_id), f"Manager {manager_id}")
        
        return {
            'top_weeks': [{'manager_id': mid, 'manager_name': get_manager_name(mid), 'weeks': weeks} 
                         for mid, weeks in sorted(manager_top_weeks.items(), key=lambda x: x[1], reverse=True)],
            'top_streaks': [{'manager_id': mid, 'manager_name': get_manager_name(mid), 'streak': streak} 
                           for mid, streak in sorted(manager_top_streaks.items(), key=lambda x: x[1], reverse=True)],
            'bottom_weeks': [{'manager_id': mid, 'manager_name': get_manager_name(mid), 'weeks': weeks} 
                            for mid, weeks in sorted(manager_bottom_weeks.items(), key=lambda x: x[1], reverse=True)],
            'bottom_streaks': [{'manager_id': mid, 'manager_name': get_manager_name(mid), 'streak': streak} 
                              for mid, streak in sorted(manager_bottom_streaks.items(), key=lambda x: x[1], reverse=True)]
        }
    
    @staticmethod
    def get_bench_points_analysis(league_id: int, current_gameweek: int) -> List[Dict[str, Any]]:
        """Analyze total bench points per manager."""
        standings = LeagueService.get_league_standings(league_id)
        if not standings:
            return []
        
        standings_results = standings['standings']['results']
        all_managers_data = LeagueService.collect_all_managers_data(league_id, current_gameweek)
        
        manager_performance_data = []
        for manager_id, manager_data in all_managers_data.items():
            if 'picks_by_gameweek' in manager_data:
                for gw, gw_picks in manager_data['picks_by_gameweek'].items():
                    entry_history = gw_picks.get('entry_history', {})
                    manager_performance_data.append({
                        'manager_id': manager_id,
                        'gameweek': gw,
                        'bench_points': entry_history.get('points_on_bench', 0)
                    })
        
        if not manager_performance_data:
            return []
        
        df = pd.DataFrame(manager_performance_data)
        total_bench = df.groupby('manager_id')['bench_points'].sum().reset_index()
        total_bench = total_bench.sort_values(by='bench_points', ascending=False)
        
        def get_manager_name(manager_id):
            return next((m['player_name'] for m in standings_results if m['entry'] == manager_id), f"Manager {manager_id}")
        
        return [
            {
                'manager_id': int(row['manager_id']),
                'manager_name': get_manager_name(row['manager_id']),
                'total_bench_points': int(row['bench_points'])
            }
            for _, row in total_bench.iterrows()
        ]
    
    @staticmethod
    def get_squad_value_analysis(league_id: int, current_gameweek: int) -> List[Dict[str, Any]]:
        """Analyze squad values per manager."""
        standings = LeagueService.get_league_standings(league_id)
        if not standings:
            return []
        
        standings_results = standings['standings']['results']
        all_managers_data = LeagueService.collect_all_managers_data(league_id, current_gameweek)
        
        manager_performance_data = []
        for manager_id, manager_data in all_managers_data.items():
            if 'picks_by_gameweek' in manager_data:
                for gw, gw_picks in manager_data['picks_by_gameweek'].items():
                    entry_history = gw_picks.get('entry_history', {})
                    value = entry_history.get('value', 0)
                    bank = entry_history.get('bank', 0)
                    manager_performance_data.append({
                        'manager_id': manager_id,
                        'gameweek': gw,
                        'total_squad_value': value + bank
                    })
        
        if not manager_performance_data:
            return []
        
        df = pd.DataFrame(manager_performance_data)
        squad_value_analysis = df.groupby('manager_id')['total_squad_value'].agg(['mean', 'max']).reset_index()
        squad_value_analysis = squad_value_analysis.sort_values(by='mean', ascending=False)
        
        def get_manager_name(manager_id):
            return next((m['player_name'] for m in standings_results if m['entry'] == manager_id), f"Manager {manager_id}")
        
        return [
            {
                'manager_id': int(row['manager_id']),
                'manager_name': get_manager_name(row['manager_id']),
                'average_squad_value': float(row['mean']) / 10,  # Convert to millions
                'peak_squad_value': float(row['max']) / 10
            }
            for _, row in squad_value_analysis.iterrows()
        ]
    
    @staticmethod
    def get_transfers_analysis(league_id: int, current_gameweek: int) -> List[Dict[str, Any]]:
        """Analyze total transfers per manager."""
        standings = LeagueService.get_league_standings(league_id)
        if not standings:
            return []
        
        standings_results = standings['standings']['results']
        all_managers_data = LeagueService.collect_all_managers_data(league_id, current_gameweek)
        
        manager_performance_data = []
        for manager_id, manager_data in all_managers_data.items():
            if 'picks_by_gameweek' in manager_data:
                for gw, gw_picks in manager_data['picks_by_gameweek'].items():
                    entry_history = gw_picks.get('entry_history', {})
                    manager_performance_data.append({
                        'manager_id': manager_id,
                        'gameweek': gw,
                        'transfers': entry_history.get('event_transfers', 0)
                    })
        
        if not manager_performance_data:
            return []
        
        df = pd.DataFrame(manager_performance_data)
        total_transfers = df.groupby('manager_id')['transfers'].sum().reset_index()
        total_transfers = total_transfers.sort_values(by='transfers', ascending=False)
        
        def get_manager_name(manager_id):
            return next((m['player_name'] for m in standings_results if m['entry'] == manager_id), f"Manager {manager_id}")
        
        return [
            {
                'manager_id': int(row['manager_id']),
                'manager_name': get_manager_name(row['manager_id']),
                'total_transfers': int(row['transfers'])
            }
            for _, row in total_transfers.iterrows()
        ]