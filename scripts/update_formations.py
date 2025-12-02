"""
Calculate and update formations for existing ManagerTeam nodes

This script calculates formations from PlayerSelection data and updates
the ManagerTeam nodes with the formation field.
"""
import os
import sys
from collections import defaultdict
from dotenv import load_dotenv
from cognite.client import CogniteClient
from cognite.client.config import ClientConfig
from cognite.client.credentials import OAuthClientCredentials
from cognite.client.data_classes.data_modeling import NodeApply, NodeOrEdgeData
from cognite.client.data_classes.data_modeling.ids import ViewId

load_dotenv()

SPACE = "fantasy_football"
VERSION = "1"


def get_cdf_client():
    """Initialize CDF client"""
    cluster = os.getenv("CDF_CLUSTER", "bluefield")
    project = os.getenv("CDF_PROJECT", "sofie-prod")
    base_url = os.getenv("CDF_BASE_URL", f"https://{cluster}.cognitedata.com")
    token_url = os.getenv("CDF_TOKEN_URL")
    client_id = os.getenv("CDF_CLIENT_ID")
    client_secret = os.getenv("CDF_CLIENT_SECRET")
    
    creds = OAuthClientCredentials(
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        scopes=[f"{base_url}/.default"],
    )
    
    cnf = ClientConfig(
        client_name="fpl-formation-updater",
        project=project,
        credentials=creds,
        base_url=base_url,
    )
    
    return CogniteClient(cnf)


def fetch_players(client):
    """Fetch all players with their positions"""
    print("Fetching players...")
    player_view = ViewId(space=SPACE, external_id="Player", version=VERSION)
    
    try:
        nodes = client.data_modeling.instances.list(
            instance_type="node",
            sources=[player_view],
            limit=1000
        )
        
        players_dict = {}
        for node in nodes:
            if hasattr(node, 'properties'):
                props_dict = node.properties.dump() if hasattr(node.properties, 'dump') else node.properties
                props = props_dict.get(SPACE, {}).get(f"Player/{VERSION}", {})
                
                if props:
                    players_dict[node.external_id] = {
                        'position': props.get('position', 'UNK'),
                        'name': props.get('webName', 'Unknown')
                    }
        
        print(f"✓ Fetched {len(players_dict)} players")
        return players_dict
    except Exception as e:
        print(f"✗ Error fetching players: {e}")
        return {}


def fetch_player_selections(client):
    """Fetch all player selections"""
    print("Fetching player selections...")
    selection_view = ViewId(space=SPACE, external_id="PlayerSelection", version=VERSION)
    
    try:
        nodes = client.data_modeling.instances.list(
            instance_type="node",
            sources=[selection_view],
            limit=10000
        )
        
        selections_by_team = defaultdict(list)
        for node in nodes:
            if hasattr(node, 'properties'):
                props_dict = node.properties.dump() if hasattr(node.properties, 'dump') else node.properties
                props = props_dict.get(SPACE, {}).get(f"PlayerSelection/{VERSION}", {})
                
                if props:
                    manager_team = props.get('managerTeam', {}).get('externalId', '')
                    player = props.get('player', {}).get('externalId', '')
                    multiplier = props.get('multiplier', 0)
                    
                    if manager_team and player:
                        selections_by_team[manager_team].append({
                            'player_id': player,
                            'multiplier': multiplier
                        })
        
        print(f"✓ Fetched selections for {len(selections_by_team)} manager teams")
        return selections_by_team
    except Exception as e:
        print(f"✗ Error fetching player selections: {e}")
        return {}


def calculate_formation(selections, players_dict):
    """
    Calculate formation from player selections
    
    Returns formation as "DEF-MID-FWD" (e.g., "4-3-3")
    """
    # Filter for starting XI (multiplier > 0)
    starting_xi = [s for s in selections if s['multiplier'] > 0]
    
    # Count by position
    position_counts = {'GK': 0, 'DEF': 0, 'MID': 0, 'FWD': 0}
    
    for selection in starting_xi:
        player_data = players_dict.get(selection['player_id'], {})
        position = player_data.get('position', 'UNK')
        
        if position in position_counts:
            position_counts[position] += 1
    
    # Return as DEF-MID-FWD (standard FPL format)
    formation = f"{position_counts['DEF']}-{position_counts['MID']}-{position_counts['FWD']}"
    
    # Validate (should have 1 GK and 10 outfield = 11 total starters)
    total_starters = len(starting_xi)
    if total_starters != 11:
        return None  # Invalid formation
    
    if position_counts['GK'] != 1:
        return None  # Must have 1 GK
    
    return formation


def fetch_manager_teams(client):
    """Fetch all manager teams with their active chip info"""
    print("Fetching manager teams...")
    manager_team_view = ViewId(space=SPACE, external_id="ManagerTeam", version=VERSION)
    
    try:
        nodes = client.data_modeling.instances.list(
            instance_type="node",
            sources=[manager_team_view],
            limit=5000
        )
        
        manager_teams = []
        for node in nodes:
            props_dict = node.properties.dump() if hasattr(node.properties, 'dump') else node.properties
            props = props_dict.get(SPACE, {}).get(f"ManagerTeam/{VERSION}", {})
            
            active_chip = props.get('activeChip', '')
            
            manager_teams.append({
                'external_id': node.external_id,
                'active_chip': active_chip
            })
        
        print(f"✓ Fetched {len(manager_teams)} manager teams")
        return manager_teams
    except Exception as e:
        print(f"✗ Error fetching manager teams: {e}")
        return []


def update_formations(client, manager_teams, selections_by_team, players_dict):
    """Update formation field for all manager teams"""
    print(f"\nCalculating and updating formations for {len(manager_teams)} teams...")
    
    nodes = []
    formations_calculated = 0
    invalid_formations = 0
    bench_boost_skipped = 0
    
    for team_data in manager_teams:
        team_id = team_data['external_id']
        active_chip = team_data['active_chip']
        
        # Skip formation calculation for bench boost (chip value is "bboost")
        if active_chip and active_chip.lower() in ['bboost', 'bench boost', 'benchboost']:
            # Set formation to None/empty for bench boost gameweeks
            node = NodeApply(
                space=SPACE,
                external_id=team_id,
                sources=[
                    NodeOrEdgeData(
                        source={"space": SPACE, "externalId": "ManagerTeam", "version": VERSION, "type": "view"},
                        properties={
                            "formation": None  # No formation when bench boost is used
                        }
                    )
                ]
            )
            nodes.append(node)
            bench_boost_skipped += 1
            continue
        
        selections = selections_by_team.get(team_id, [])
        
        if not selections:
            continue
        
        formation = calculate_formation(selections, players_dict)
        
        if formation:
            node = NodeApply(
                space=SPACE,
                external_id=team_id,
                sources=[
                    NodeOrEdgeData(
                        source={"space": SPACE, "externalId": "ManagerTeam", "version": VERSION, "type": "view"},
                        properties={
                            "formation": formation
                        }
                    )
                ]
            )
            nodes.append(node)
            formations_calculated += 1
        else:
            invalid_formations += 1
    
    # Update in batches
    batch_size = 100
    total_updated = 0
    
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i + batch_size]
        try:
            result = client.data_modeling.instances.apply(batch)
            total_updated += len(batch)
            print(f"  ✓ Updated batch {i//batch_size + 1}/{(len(nodes)-1)//batch_size + 1} ({len(batch)} teams)")
        except Exception as e:
            print(f"  ✗ Error updating batch: {e}")
    
    print(f"\n✓ Successfully updated {total_updated} manager teams")
    print(f"  - Formations calculated: {formations_calculated}")
    print(f"  - Bench boost weeks (no formation): {bench_boost_skipped}")
    if invalid_formations > 0:
        print(f"  ⚠ Skipped {invalid_formations} teams with invalid/incomplete formations")
    
    return total_updated, invalid_formations, bench_boost_skipped


def main():
    """Main execution"""
    print("=" * 60)
    print("Formation Updater for ManagerTeam nodes")
    print("=" * 60)
    
    # Initialize client
    try:
        client = get_cdf_client()
        print(f"✓ Connected to CDF project: {client.config.project}\n")
    except Exception as e:
        print(f"✗ Failed to connect to CDF: {e}")
        return 1
    
    # Fetch required data
    players_dict = fetch_players(client)
    if not players_dict:
        print("✗ Failed to fetch players. Aborting.")
        return 1
    
    selections_by_team = fetch_player_selections(client)
    if not selections_by_team:
        print("✗ Failed to fetch player selections. Aborting.")
        return 1
    
    manager_teams = fetch_manager_teams(client)
    if not manager_teams:
        print("✗ Failed to fetch manager teams. Aborting.")
        return 1
    
    # Calculate and update formations
    updated, invalid, bench_boost = update_formations(client, manager_teams, selections_by_team, players_dict)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Manager teams processed: {len(manager_teams)}")
    print(f"Formations calculated: {updated - bench_boost}")
    print(f"Bench boost weeks (no formation): {bench_boost}")
    print(f"Invalid/incomplete: {invalid}")
    print("=" * 60)
    print("✓ Done!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

