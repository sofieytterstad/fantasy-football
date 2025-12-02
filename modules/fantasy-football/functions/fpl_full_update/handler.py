"""
Comprehensive Fantasy Premier League Data Update Function
Loads all FPL data (teams, players, managers, performance, transfers, betting, fixtures, odds) to CDF data model instances
"""
import os
import time
from datetime import datetime
from collections import defaultdict
from typing import Any

import requests
import numpy as np
from cognite.client import CogniteClient
from cognite.client.data_classes.data_modeling import NodeApply, NodeOrEdgeData

# Try to import OddsFetcher - if not available, will skip odds enrichment
try:
    from odds_fetcher import OddsFetcher
    ODDS_AVAILABLE = True
except ImportError:
    ODDS_AVAILABLE = False
    print("⚠️  OddsFetcher not available - skipping odds enrichment")


class FPLClient:
    """Simple FPL API client"""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    
    def get_bootstrap_static(self):
        """Fetch bootstrap-static data (teams, players, gameweeks)"""
        response = requests.get(f"{self.BASE_URL}/bootstrap-static/")
        response.raise_for_status()
        return response.json()
    
    def get_current_gameweek(self):
        """Get the current gameweek number"""
        data = self.get_bootstrap_static()
        current = next((e for e in data['events'] if e.get('is_current')), None)
        return current['id'] if current else 1
    
    def get_league_standings(self, league_id):
        """Fetch league standings"""
        response = requests.get(f"{self.BASE_URL}/leagues-classic/{league_id}/standings/")
        response.raise_for_status()
        return response.json()
    
    def get_entry_history(self, entry_id):
        """Fetch manager's history"""
        response = requests.get(f"{self.BASE_URL}/entry/{entry_id}/history/")
        response.raise_for_status()
        return response.json()
    
    def get_entry_picks(self, entry_id, gameweek):
        """Fetch manager's picks for a gameweek"""
        response = requests.get(f"{self.BASE_URL}/entry/{entry_id}/event/{gameweek}/picks/")
        response.raise_for_status()
        return response.json()
    
    def get_fixtures(self):
        """Fetch all fixtures"""
        response = requests.get(f"{self.BASE_URL}/fixtures/")
        response.raise_for_status()
        return response.json()


def handle(data: dict[str, Any], client: CogniteClient) -> dict[str, Any]:
    """
    Main handler for comprehensive FPL data update
    
    Args:
        data: Input data (optional league_id override)
        client: CogniteClient instance
    
    Returns:
        Dictionary with status and statistics
    """
    
    SPACE = "fantasy_football"
    VERSION = "1"
    LEAGUE_ID = data.get("league_id") or os.getenv("FPL_LEAGUE_ID", "1097811")
    
    stats = {
        "teams": 0,
        "fixtures": 0,
        "fixtures_with_odds": 0,
        "gameweeks": 0,
        "players": 0,
        "managers": 0,
        "performance_records": 0,
        "manager_teams": 0,
        "player_selections": 0,
        "transfers": 0,
        "team_betting_records": 0,
        "formations_calculated": 0,
        "errors": []
    }
    
    try:
        print(f"Starting FPL data update for league {LEAGUE_ID}")
        fpl_client = FPLClient()
        
        # =====================================================================
        # STEP 1: Fetch bootstrap data
        # =====================================================================
        print("Fetching bootstrap data...")
        bootstrap = fpl_client.get_bootstrap_static()
        teams = bootstrap['teams']
        events = bootstrap['events']
        players = bootstrap['elements']
        current_gw = fpl_client.get_current_gameweek()
        
        print(f"  Teams: {len(teams)}, Gameweeks: {len(events)}, Players: {len(players)}, Current GW: {current_gw}")
        
        # =====================================================================
        # STEP 2: Load Teams
        # =====================================================================
        print("Loading teams...")
        team_nodes = []
        teams_dict = {team['id']: team for team in teams}
        
        for team in teams:
            team_nodes.append(NodeApply(
                space=SPACE,
                external_id=f"team_{team['id']}",
                sources=[
                    NodeOrEdgeData(
                        source={"space": SPACE, "externalId": "PLTeam", "version": VERSION, "type": "view"},
                        properties={
                            "teamId": team['id'],
                            "name": team['name'],
                            "shortName": team['short_name'],
                            "strength": team.get('strength')
                        }
                    )
                ]
            ))
        
        client.data_modeling.instances.apply(nodes=team_nodes, auto_create_direct_relations=True)
        stats["teams"] = len(team_nodes)
        print(f"  ✓ Loaded {len(team_nodes)} teams")
        
        # =====================================================================
        # STEP 2.5: Load Fixtures (with odds if available)
        # =====================================================================
        print("Loading fixtures...")
        try:
            fixtures_raw = fpl_client.get_fixtures()
            print(f"  Fetched {len(fixtures_raw)} fixtures from FPL API")
            
            # Enrich with odds if available
            if ODDS_AVAILABLE:
                api_key = os.getenv("ODDS_API_KEY")
                if api_key:
                    print("  Fetching betting odds...")
                    try:
                        fetcher = OddsFetcher(api_key=api_key, source='odds_api')
                        odds_data = fetcher.fetch_premier_league_odds()
                        
                        if odds_data:
                            print(f"  ✓ Fetched odds for {len(odds_data)} matches")
                            
                            # Add team names to fixtures for matching
                            for fixture in fixtures_raw:
                                home_team_id = fixture.get('team_h')
                                away_team_id = fixture.get('team_a')
                                fixture['team_h_name'] = teams_dict.get(home_team_id, {}).get('name', 'Unknown')
                                fixture['team_a_name'] = teams_dict.get(away_team_id, {}).get('name', 'Unknown')
                            
                            fixtures_raw = fetcher.match_with_fpl_fixtures(odds_data, fixtures_raw)
                            stats["fixtures_with_odds"] = sum(1 for f in fixtures_raw if f.get('home_win_odds'))
                            print(f"  ✓ Matched odds for {stats['fixtures_with_odds']} fixtures")
                        else:
                            print("  ⚠️  No odds data available")
                    except Exception as e:
                        print(f"  ⚠️  Failed to fetch odds: {e}")
                else:
                    print("  ⚠️  No ODDS_API_KEY configured, skipping odds")
            
            # Create fixture nodes
            fixture_nodes = []
            for fixture in fixtures_raw:
                fixture_id = fixture['id']
                gameweek = fixture.get('event')
                
                # Skip fixtures without gameweek (postponed)
                if not gameweek:
                    continue
                
                home_team_id = fixture.get('team_h')
                away_team_id = fixture.get('team_a')
                
                # Parse kickoff time
                kickoff = None
                if fixture.get('kickoff_time'):
                    try:
                        kickoff = datetime.fromisoformat(fixture['kickoff_time'].replace('Z', '+00:00'))
                    except:
                        pass
                
                props = {
                    "fixtureId": fixture_id,
                    "gameweek": {"space": SPACE, "externalId": f"gameweek_{gameweek}"},
                    "homeTeam": {"space": SPACE, "externalId": f"team_{home_team_id}"} if home_team_id else None,
                    "awayTeam": {"space": SPACE, "externalId": f"team_{away_team_id}"} if away_team_id else None,
                    "kickoffTime": kickoff,
                    "homeTeamDifficulty": fixture.get('team_h_difficulty'),
                    "awayTeamDifficulty": fixture.get('team_a_difficulty'),
                    "homeTeamScore": fixture.get('team_h_score'),
                    "awayTeamScore": fixture.get('team_a_score'),
                    "isFinished": fixture.get('finished', False),
                    "started": fixture.get('started', False),
                    "provisionalStartTime": fixture.get('provisional_start_time', False)
                }
                
                # Add odds if available
                if fixture.get('home_win_odds'):
                    props.update({
                        "homeWinOdds": fixture.get('home_win_odds'),
                        "drawOdds": fixture.get('draw_odds'),
                        "awayWinOdds": fixture.get('away_win_odds'),
                        "homeWinProbability": fixture.get('home_win_probability'),
                        "drawProbability": fixture.get('draw_probability'),
                        "awayWinProbability": fixture.get('away_win_probability')
                    })
                
                fixture_nodes.append(NodeApply(
                    space=SPACE,
                    external_id=f"fixture_{fixture_id}",
                    sources=[
                        NodeOrEdgeData(
                            source={"space": SPACE, "externalId": "Fixture", "version": VERSION, "type": "view"},
                            properties=props
                        )
                    ]
                ))
            
            # Load fixtures in batches
            batch_size = 100
            for i in range(0, len(fixture_nodes), batch_size):
                batch = fixture_nodes[i:i + batch_size]
                client.data_modeling.instances.apply(nodes=batch, auto_create_direct_relations=True)
            
            stats["fixtures"] = len(fixture_nodes)
            print(f"  ✓ Loaded {len(fixture_nodes)} fixtures")
            
            # Update team strength and next fixture info
            print("  Updating team strength ratings...")
            for team in teams:
                team_id = team['id']
                # Find next unfinished fixture for this team
                next_fixtures = [f for f in fixtures_raw 
                                if (f.get('team_h') == team_id or f.get('team_a') == team_id) 
                                and not f.get('finished')]
                next_fixture_id = next_fixtures[0]['id'] if next_fixtures else None
                
                # Calculate upcoming fixture difficulty (average of next 3-5 fixtures)
                upcoming_difficulties = []
                for f in next_fixtures[:5]:
                    if f.get('team_h') == team_id:
                        upcoming_difficulties.append(f.get('team_h_difficulty', 3))
                    else:
                        upcoming_difficulties.append(f.get('team_a_difficulty', 3))
                
                avg_difficulty = sum(upcoming_difficulties) / len(upcoming_difficulties) if upcoming_difficulties else None
                
                # Update team node with strength and fixture info
                update_node = NodeApply(
                    space=SPACE,
                    external_id=f"team_{team_id}",
                    sources=[
                        NodeOrEdgeData(
                            source={"space": SPACE, "externalId": "PLTeam", "version": VERSION, "type": "view"},
                            properties={
                                "teamId": team_id,
                                "name": team['name'],
                                "shortName": team['short_name'],
                                "strength": team.get('strength'),
                                "strengthOverallHome": team.get('strength_overall_home'),
                                "strengthOverallAway": team.get('strength_overall_away'),
                                "strengthAttackHome": team.get('strength_attack_home'),
                                "strengthAttackAway": team.get('strength_attack_away'),
                                "strengthDefenceHome": team.get('strength_defence_home'),
                                "strengthDefenceAway": team.get('strength_defence_away'),
                                "upcomingFixtureDifficulty": avg_difficulty,
                                "nextFixture": {"space": SPACE, "externalId": f"fixture_{next_fixture_id}"} if next_fixture_id else None
                            }
                        )
                    ]
                )
                client.data_modeling.instances.apply(nodes=[update_node], auto_create_direct_relations=True)
            
            print(f"  ✓ Updated team strength ratings")
            
        except Exception as e:
            print(f"  ✗ Error loading fixtures: {e}")
            stats["errors"].append(f"Fixtures: {str(e)}")
        
        # =====================================================================
        # STEP 3: Load Gameweeks
        # =====================================================================
        print("Loading gameweeks...")
        gameweek_nodes = []
        
        for event in events:
            deadline = None
            if event.get('deadline_time'):
                try:
                    deadline = datetime.fromisoformat(event['deadline_time'].replace('Z', '+00:00'))
                except:
                    pass
            
            gameweek_nodes.append(NodeApply(
                space=SPACE,
                external_id=f"gameweek_{event['id']}",
                sources=[
                    NodeOrEdgeData(
                        source={"space": SPACE, "externalId": "Gameweek", "version": VERSION, "type": "view"},
                        properties={
                            "gameweekNumber": event['id'],
                            "name": event['name'],
                            "deadlineTime": deadline,
                            "isFinished": event['finished'],
                            "isCurrent": event.get('is_current', False),
                            "averageScore": event.get('average_entry_score'),
                            "highestScore": event.get('highest_score')
                        }
                    )
                ]
            ))
        
        client.data_modeling.instances.apply(nodes=gameweek_nodes, auto_create_direct_relations=True)
        stats["gameweeks"] = len(gameweek_nodes)
        print(f"  ✓ Loaded {len(gameweek_nodes)} gameweeks")
        
        # =====================================================================
        # STEP 4: Load Players
        # =====================================================================
        print("Loading players...")
        player_nodes = []
        position_map = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
        players_by_id = {p['id']: p for p in players}
        
        for player in players:
            player_nodes.append(NodeApply(
                space=SPACE,
                external_id=f"player_{player['id']}",
                sources=[
                    NodeOrEdgeData(
                        source={"space": SPACE, "externalId": "Player", "version": VERSION, "type": "view"},
                        properties={
                            "playerId": player['id'],
                            "webName": player['web_name'],
                            "firstName": player['first_name'],
                            "lastName": player['second_name'],
                            "plTeam": {"space": SPACE, "externalId": f"team_{player['team']}"},
                            "position": position_map.get(player['element_type'], "Unknown"),
                            "currentPrice": player['now_cost'] / 10.0,
                            "totalPoints": player['total_points'],
                            "form": float(player.get('form', 0)) if player.get('form') else 0.0,
                            "selectedByPercent": float(player.get('selected_by_percent', 0)) if player.get('selected_by_percent') else 0.0,
                            "pointsPerGame": float(player.get('points_per_game', 0)) if player.get('points_per_game') else 0.0
                        }
                    )
                ]
            ))
        
        # Load in batches
        batch_size = 100
        for i in range(0, len(player_nodes), batch_size):
            batch = player_nodes[i:i + batch_size]
            client.data_modeling.instances.apply(nodes=batch, auto_create_direct_relations=True)
        
        stats["players"] = len(player_nodes)
        print(f"  ✓ Loaded {len(player_nodes)} players")
        
        # =====================================================================
        # STEP 5: Load Managers & Performance
        # =====================================================================
        print("Loading managers and performance...")
        league_data = fpl_client.get_league_standings(LEAGUE_ID)
        standings = league_data['standings']['results']
        
        manager_nodes = []
        performance_nodes = []
        manager_histories = {}
        
        for manager in standings:
            entry_id = manager['entry']
            
            try:
                history = fpl_client.get_entry_history(entry_id)
                manager_histories[entry_id] = history
                current_gw_data = history.get('current', [])
                
                # Calculate analytics
                weekly_points = [gw['points'] for gw in current_gw_data]
                
                if len(weekly_points) > 1 and np.mean(weekly_points) > 0:
                    points_mean = np.mean(weekly_points)
                    points_std = np.std(weekly_points)
                    coeff_variation = points_std / points_mean
                    consistency_score = max(0, min(100, 100 * (1 - min(coeff_variation, 1))))
                else:
                    consistency_score = 0.0
                    points_mean = float(np.mean(weekly_points)) if weekly_points else 0.0
                    points_std = 0.0
                
                if current_gw_data:
                    starting_value = current_gw_data[0]['value'] / 10.0
                    current_value = current_gw_data[-1]['value'] / 10.0
                    team_value_growth = current_value - starting_value
                    final_team_value = current_value
                else:
                    team_value_growth = 0.0
                    final_team_value = 100.0
                
                total_transfers = sum(gw.get('event_transfers', 0) for gw in current_gw_data)
                
                # Create manager node
                manager_nodes.append(NodeApply(
                    space=SPACE,
                    external_id=f"manager_{entry_id}",
                    sources=[
                        NodeOrEdgeData(
                            source={"space": SPACE, "externalId": "Manager", "version": VERSION, "type": "view"},
                            properties={
                                "entryId": entry_id,
                                "managerName": manager['player_name'],
                                "teamName": manager['entry_name'],
                                "overallPoints": manager['total'],
                                "overallRank": manager.get('rank'),
                                "leagueRank": manager.get('rank'),
                                "teamValue": final_team_value,
                                "consistencyScore": round(consistency_score, 2),
                                "averagePointsPerWeek": round(points_mean, 2),
                                "pointsStdDev": round(points_std, 2),
                                "teamValueGrowth": round(team_value_growth, 2),
                                "totalTransfers": total_transfers,
                            }
                        )
                    ]
                ))
                
                # Create performance records
                for gw_data in current_gw_data:
                    gameweek = gw_data['event']
                    performance_nodes.append(NodeApply(
                        space=SPACE,
                        external_id=f"performance_{entry_id}_gw{gameweek}",
                        sources=[
                            NodeOrEdgeData(
                                source={"space": SPACE, "externalId": "ManagerGameweekPerformance", "version": VERSION, "type": "view"},
                                properties={
                                    "manager": {"space": SPACE, "externalId": f"manager_{entry_id}"},
                                    "gameweek": {"space": SPACE, "externalId": f"gameweek_{gameweek}"},
                                    "points": gw_data['points'],
                                    "totalPoints": gw_data['total_points'],
                                    "rank": gw_data.get('overall_rank'),
                                    "gameweekRank": gw_data.get('rank'),
                                    "transfers": gw_data.get('event_transfers', 0),
                                    "transferCost": gw_data.get('event_transfers_cost', 0),
                                    "bank": gw_data.get('bank', 0) / 10.0,
                                    "teamValue": gw_data.get('value', 0) / 10.0
                                }
                            )
                        ]
                    ))
                
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                stats["errors"].append(f"Manager {entry_id}: {str(e)}")
                continue
        
        client.data_modeling.instances.apply(nodes=manager_nodes, auto_create_direct_relations=True)
        stats["managers"] = len(manager_nodes)
        print(f"  ✓ Loaded {len(manager_nodes)} managers")
        
        # Load performance in batches
        for i in range(0, len(performance_nodes), batch_size):
            batch = performance_nodes[i:i + batch_size]
            client.data_modeling.instances.apply(nodes=batch, auto_create_direct_relations=True)
        
        stats["performance_records"] = len(performance_nodes)
        print(f"  ✓ Loaded {len(performance_nodes)} performance records")
        
        # =====================================================================
        # STEP 6: Load Manager Teams & Player Selections
        # =====================================================================
        print("Loading manager teams and player selections...")
        print("(This may take a while - fetching picks for each manager/gameweek)")
        
        manager_team_nodes = []
        player_selection_nodes = []
        
        for idx, manager in enumerate(standings, 1):
            entry_id = manager['entry']
            manager_name = manager['player_name']
            print(f"  [{idx}/{len(standings)}] {manager_name:<35} ", end="")
            
            try:
                history = manager_histories.get(entry_id, {})
                gameweeks = [gw['event'] for gw in history.get('current', [])]
                selections_count = 0
                
                for gw in gameweeks:
                    try:
                        picks_data = fpl_client.get_entry_picks(entry_id, gw)
                        picks = picks_data.get('picks', [])
                        entry_history = picks_data.get('entry_history', {})
                        
                        # Find captain and vice captain
                        captain_id = None
                        vice_captain_id = None
                        for pick in picks:
                            if pick.get('is_captain'):
                                captain_id = pick['element']
                            if pick.get('is_vice_captain'):
                                vice_captain_id = pick['element']
                        
                        # Create ManagerTeam node
                        manager_team_ext_id = f"managerteam_{entry_id}_gw{gw}"
                        manager_team_nodes.append(NodeApply(
                            space=SPACE,
                            external_id=manager_team_ext_id,
                            sources=[
                                NodeOrEdgeData(
                                    source={"space": SPACE, "externalId": "ManagerTeam", "version": VERSION, "type": "view"},
                                    properties={
                                        "manager": {"space": SPACE, "externalId": f"manager_{entry_id}"},
                                        "gameweek": {"space": SPACE, "externalId": f"gameweek_{gw}"},
                                        "captain": {"space": SPACE, "externalId": f"player_{captain_id}"} if captain_id else None,
                                        "viceCaptain": {"space": SPACE, "externalId": f"player_{vice_captain_id}"} if vice_captain_id else None,
                                        "totalPoints": entry_history.get('points'),
                                        "teamValue": entry_history.get('value', 0) / 10.0 if entry_history.get('value') else None,
                                        "bank": entry_history.get('bank', 0) / 10.0 if entry_history.get('bank') else None,
                                        "activeChip": picks_data.get('active_chip')
                                    }
                                )
                            ]
                        ))
                        
                        # Create PlayerSelection nodes for each of the 15 picks
                        for pick in picks:
                            player_id = pick['element']
                            position = pick['position']
                            multiplier = pick['multiplier']
                            is_captain = pick.get('is_captain', False)
                            is_vice = pick.get('is_vice_captain', False)
                            
                            player_selection_nodes.append(NodeApply(
                                space=SPACE,
                                external_id=f"selection_{entry_id}_gw{gw}_p{player_id}_pos{position}",
                                sources=[
                                    NodeOrEdgeData(
                                        source={"space": SPACE, "externalId": "PlayerSelection", "version": VERSION, "type": "view"},
                                        properties={
                                            "managerTeam": {"space": SPACE, "externalId": manager_team_ext_id},
                                            "player": {"space": SPACE, "externalId": f"player_{player_id}"},
                                            "position": position,
                                            "multiplier": multiplier,
                                            "isCaptain": is_captain,
                                            "isViceCaptain": is_vice,
                                            "pointsScored": None  # Would need player gameweek stats to populate
                                        }
                                    )
                                ]
                            ))
                            selections_count += 1
                        
                        time.sleep(0.3)  # Rate limiting
                        
                    except Exception as e:
                        stats["errors"].append(f"Picks for {entry_id} GW{gw}: {str(e)}")
                        continue
                
                print(f"✓ {len(gameweeks)} teams, {selections_count} selections")
                
            except Exception as e:
                print(f"✗ Error: {e}")
                stats["errors"].append(f"Manager teams {entry_id}: {str(e)}")
                continue
        
        # Load manager teams in batches
        for i in range(0, len(manager_team_nodes), batch_size):
            batch = manager_team_nodes[i:i + batch_size]
            client.data_modeling.instances.apply(nodes=batch, auto_create_direct_relations=True)
        
        stats["manager_teams"] = len(manager_team_nodes)
        print(f"  ✓ Loaded {len(manager_team_nodes)} manager teams")
        
        # Load player selections in batches
        for i in range(0, len(player_selection_nodes), batch_size):
            batch = player_selection_nodes[i:i + batch_size]
            client.data_modeling.instances.apply(nodes=batch, auto_create_direct_relations=True)
        
        stats["player_selections"] = len(player_selection_nodes)
        print(f"  ✓ Loaded {len(player_selection_nodes)} player selections")
        
        # =====================================================================
        # STEP 6.5: Calculate Formations for Manager Teams
        # =====================================================================
        print("Calculating formations for manager teams...")
        
        # Build a lookup of player positions
        player_positions = {f"player_{p['id']}": position_map.get(p['element_type']) for p in players}
        
        # Build formation data from player selections
        formations_data = defaultdict(lambda: {"DEF": 0, "MID": 0, "FWD": 0, "active_chip": None})
        
        for idx, manager in enumerate(standings):
            entry_id = manager['entry']
            
            try:
                history = manager_histories.get(entry_id, {})
                gameweeks = [gw['event'] for gw in history.get('current', [])]
                
                for gw in gameweeks:
                    try:
                        picks_data = fpl_client.get_entry_picks(entry_id, gw)
                        picks = picks_data.get('picks', [])
                        active_chip = picks_data.get('active_chip')
                        
                        # Skip if bench boost is active
                        if active_chip == 'bboost':
                            continue
                        
                        # Count starting 11 by position (position 1-11 are starters)
                        position_counts = {"DEF": 0, "MID": 0, "FWD": 0}
                        
                        for pick in picks:
                            if pick['position'] <= 11:  # Starting 11
                                player_ext_id = f"player_{pick['element']}"
                                pos = player_positions.get(player_ext_id)
                                if pos in position_counts:
                                    position_counts[pos] += 1
                        
                        # Format as formation string (e.g., "4-3-3")
                        formation_str = f"{position_counts['DEF']}-{position_counts['MID']}-{position_counts['FWD']}"
                        
                        # Store for later update
                        manager_team_ext_id = f"managerteam_{entry_id}_gw{gw}"
                        formations_data[manager_team_ext_id] = {
                            "formation": formation_str,
                            "entry_id": entry_id,
                            "gameweek": gw
                        }
                        
                        time.sleep(0.2)  # Rate limiting
                        
                    except Exception as e:
                        continue
                
            except Exception as e:
                continue
        
        # Update manager team nodes with formations
        formation_updates = []
        for ext_id, data in formations_data.items():
            formation_updates.append(NodeApply(
                space=SPACE,
                external_id=ext_id,
                sources=[
                    NodeOrEdgeData(
                        source={"space": SPACE, "externalId": "ManagerTeam", "version": VERSION, "type": "view"},
                        properties={
                            "formation": data["formation"]
                        }
                    )
                ]
            ))
        
        # Apply formation updates in batches
        for i in range(0, len(formation_updates), batch_size):
            batch = formation_updates[i:i + batch_size]
            client.data_modeling.instances.apply(nodes=batch, auto_create_direct_relations=True)
        
        stats["formations_calculated"] = len(formation_updates)
        print(f"  ✓ Calculated formations for {len(formation_updates)} manager teams")
        
        # =====================================================================
        # STEP 7: Load Transfers (simplified - last 5 GWs only)
        # =====================================================================
        print("Analyzing transfers (last 5 gameweeks)...")
        
        player_stats = {p['id']: {'form': float(p.get('form', 0))} for p in players}
        all_transfers = []
        recent_gameweeks = range(max(1, current_gw - 4), current_gw + 1)
        
        for entry_id in [s['entry'] for s in standings]:
            try:
                history = manager_histories.get(entry_id, {})
                gameweeks = [gw['event'] for gw in history.get('current', [])]
                
                picks_by_gw = {}
                for gw in [g for g in gameweeks if g in recent_gameweeks]:
                    try:
                        picks_data = fpl_client.get_entry_picks(entry_id, gw)
                        picks_by_gw[gw] = {
                            'picks': picks_data.get('picks', []),
                            'transfers': picks_data.get('entry_history', {})
                        }
                        time.sleep(0.3)
                    except:
                        continue
                
                sorted_gws = sorted(picks_by_gw.keys())
                for i in range(len(sorted_gws) - 1):
                    prev_gw = sorted_gws[i]
                    curr_gw = sorted_gws[i + 1]
                    
                    prev_squad = {pick['element'] for pick in picks_by_gw[prev_gw]['picks']}
                    curr_squad = {pick['element'] for pick in picks_by_gw[curr_gw]['picks']}
                    
                    players_in = curr_squad - prev_squad
                    players_out = prev_squad - curr_squad
                    
                    if players_in and players_out:
                        transfer_cost = picks_by_gw[curr_gw]['transfers'].get('event_transfers_cost', 0)
                        num_transfers = picks_by_gw[curr_gw]['transfers'].get('event_transfers', 0)
                        cost_per_transfer = transfer_cost / num_transfers if num_transfers > 0 else 0
                        
                        for player_in_id, player_out_id in zip(list(players_in), list(players_out)):
                            player_in = players_by_id.get(player_in_id, {})
                            player_out = players_by_id.get(player_out_id, {})
                            
                            form_in = player_stats.get(player_in_id, {}).get('form', 0)
                            form_out = player_stats.get(player_out_id, {}).get('form', 0)
                            
                            net_benefit = (form_in - form_out) * 3
                            
                            all_transfers.append({
                                'entry_id': entry_id,
                                'gameweek': curr_gw,
                                'player_in_id': player_in_id,
                                'player_out_id': player_out_id,
                                'player_in_price': player_in.get('now_cost', 0) / 10.0,
                                'player_out_price': player_out.get('now_cost', 0) / 10.0,
                                'transfer_cost': int(cost_per_transfer),
                                'net_benefit': int(round(net_benefit)),
                                'was_successful': net_benefit > cost_per_transfer
                            })
                
            except Exception as e:
                stats["errors"].append(f"Transfers for {entry_id}: {str(e)}")
                continue
        
        # Create transfer nodes
        transfer_nodes = []
        for transfer in all_transfers:
            transfer_nodes.append(NodeApply(
                space=SPACE,
                external_id=f"transfer_{transfer['entry_id']}_gw{transfer['gameweek']}_{transfer['player_out_id']}to{transfer['player_in_id']}",
                sources=[
                    NodeOrEdgeData(
                        source={"space": SPACE, "externalId": "Transfer", "version": VERSION, "type": "view"},
                        properties={
                            "manager": {"space": SPACE, "externalId": f"manager_{transfer['entry_id']}"},
                            "gameweek": {"space": SPACE, "externalId": f"gameweek_{transfer['gameweek']}"},
                            "playerIn": {"space": SPACE, "externalId": f"player_{transfer['player_in_id']}"},
                            "playerOut": {"space": SPACE, "externalId": f"player_{transfer['player_out_id']}"},
                            "transferCost": transfer['transfer_cost'],
                            "playerInPrice": transfer['player_in_price'],
                            "playerOutPrice": transfer['player_out_price'],
                            "pointsGainedNext3GW": transfer['net_benefit'],
                            "wasSuccessful": transfer['was_successful'],
                            "netBenefit": transfer['net_benefit']
                        }
                    )
                ]
            ))
        
        for i in range(0, len(transfer_nodes), batch_size):
            batch = transfer_nodes[i:i + batch_size]
            client.data_modeling.instances.apply(nodes=batch, auto_create_direct_relations=True)
        
        stats["transfers"] = len(transfer_nodes)
        print(f"  ✓ Loaded {len(transfer_nodes)} transfers")
        
        print(f"\n✅ Data update complete!")
        print(f"   Teams: {stats['teams']}, Fixtures: {stats['fixtures']} ({stats['fixtures_with_odds']} with odds)")
        print(f"   Gameweeks: {stats['gameweeks']}, Players: {stats['players']}")
        print(f"   Managers: {stats['managers']}, Performance: {stats['performance_records']}")
        print(f"   Manager Teams: {stats['manager_teams']} ({stats['formations_calculated']} with formations)")
        print(f"   Player Selections: {stats['player_selections']}, Transfers: {stats['transfers']}")
        
        return {
            "status": "success",
            "message": "FPL data update completed successfully",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

