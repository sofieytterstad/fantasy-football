"""
Load Fixture data from FPL API into CDF

This script fetches Premier League fixtures from the FPL API and creates
Fixture nodes in CDF with difficulty ratings and optional betting odds.
"""
import os
import sys
import requests
from dotenv import load_dotenv
from cognite.client import CogniteClient
from cognite.client.config import ClientConfig
from cognite.client.credentials import OAuthClientCredentials
from cognite.client.data_classes.data_modeling import NodeApply, NodeOrEdgeData

# Add parent directory to path to import odds_fetcher
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.odds_fetcher import OddsFetcher

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
        client_name="fpl-fixture-loader",
        project=project,
        credentials=creds,
        base_url=base_url,
    )
    
    return CogniteClient(cnf)


def fetch_fpl_fixtures():
    """Fetch fixtures from FPL API"""
    print("Fetching fixtures from FPL API...")
    url = "https://fantasy.premierleague.com/api/fixtures/"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        fixtures = response.json()
        print(f"✓ Fetched {len(fixtures)} fixtures")
        return fixtures
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching fixtures: {e}")
        return []


def fetch_fpl_teams():
    """Fetch team data to map team IDs to names"""
    print("Fetching team data from FPL API...")
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        teams = {team['id']: team for team in data['teams']}
        print(f"✓ Fetched {len(teams)} teams")
        return teams
    except requests.exceptions.RequestException as e:
        print(f"✗ Error fetching teams: {e}")
        return {}


def enrich_with_odds(fixtures, teams_dict, use_odds=False):
    """Optionally enrich fixtures with betting odds"""
    if not use_odds:
        print("Skipping odds enrichment (use --with-odds to enable)")
        return fixtures
    
    api_key = os.getenv("ODDS_API_KEY")
    odds_source = os.getenv("ODDS_API_SOURCE", "mock")
    
    if not api_key and odds_source != "mock":
        print("⚠ No ODDS_API_KEY found, using mock data")
        odds_source = "mock"
    
    print(f"Fetching odds from {odds_source}...")
    fetcher = OddsFetcher(api_key=api_key, source=odds_source)
    odds_data = fetcher.fetch_premier_league_odds()
    
    if odds_data:
        print(f"✓ Fetched odds for {len(odds_data)} matches")
        
        # Add team names to fixtures for matching
        for fixture in fixtures:
            home_team_id = fixture.get('team_h')
            away_team_id = fixture.get('team_a')
            fixture['team_h_name'] = teams_dict.get(home_team_id, {}).get('name', 'Unknown')
            fixture['team_a_name'] = teams_dict.get(away_team_id, {}).get('name', 'Unknown')
        
        enriched = fetcher.match_with_fpl_fixtures(odds_data, fixtures)
        print(f"✓ Matched odds for {sum(1 for f in enriched if f.get('home_win_odds'))} fixtures")
        return enriched
    else:
        print("⚠ No odds data fetched, proceeding without odds")
        return fixtures


def create_fixture_nodes(client, fixtures, teams_dict):
    """Create Fixture nodes in CDF"""
    print(f"\nCreating {len(fixtures)} fixture nodes in CDF...")
    
    nodes = []
    for fixture in fixtures:
        fixture_id = fixture['id']
        gameweek = fixture.get('event')
        
        # Skip fixtures without gameweek (may be postponed)
        if not gameweek:
            continue
        
        # Get team names
        home_team_id = fixture.get('team_h')
        away_team_id = fixture.get('team_a')
        home_team_name = teams_dict.get(home_team_id, {}).get('name', 'Unknown')
        away_team_name = teams_dict.get(away_team_id, {}).get('name', 'Unknown')
        
        node = NodeApply(
            space=SPACE,
            external_id=f"fixture_{fixture_id}",
            sources=[
                NodeOrEdgeData(
                    source={"space": SPACE, "externalId": "Fixture", "version": VERSION, "type": "view"},
                    properties={
                        "fixtureId": fixture_id,
                        "gameweek": {"space": SPACE, "externalId": f"gameweek_{gameweek}"},
                        "homeTeam": {"space": SPACE, "externalId": f"team_{home_team_id}"},
                        "awayTeam": {"space": SPACE, "externalId": f"team_{away_team_id}"},
                        "kickoffTime": fixture.get('kickoff_time'),
                        "homeTeamDifficulty": fixture.get('team_h_difficulty'),
                        "awayTeamDifficulty": fixture.get('team_a_difficulty'),
                        "homeTeamScore": fixture.get('team_h_score'),
                        "awayTeamScore": fixture.get('team_a_score'),
                        "isFinished": fixture.get('finished', False),
                        "started": fixture.get('started', False),
                        "provisionalStartTime": fixture.get('provisional_start_time', False),
                        # Odds data (if available)
                        "homeWinOdds": fixture.get('home_win_odds'),
                        "drawOdds": fixture.get('draw_odds'),
                        "awayWinOdds": fixture.get('away_win_odds'),
                        "homeWinProbability": fixture.get('home_win_probability'),
                        "drawProbability": fixture.get('draw_probability'),
                        "awayWinProbability": fixture.get('away_win_probability'),
                    }
                )
            ]
        )
        nodes.append(node)
    
    # Apply nodes in batches
    batch_size = 100
    total_created = 0
    
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i + batch_size]
        try:
            result = client.data_modeling.instances.apply(batch)
            total_created += len(batch)
            print(f"  ✓ Created batch {i//batch_size + 1}/{(len(nodes)-1)//batch_size + 1} ({len(batch)} fixtures)")
        except Exception as e:
            print(f"  ✗ Error creating batch: {e}")
    
    print(f"\n✓ Successfully created {total_created} fixture nodes")
    return total_created


def update_team_strength(client, teams_dict):
    """Update PLTeam nodes with strength ratings from FPL"""
    print("\nUpdating team strength ratings...")
    
    nodes = []
    for team_id, team_data in teams_dict.items():
        node = NodeApply(
            space=SPACE,
            external_id=f"team_{team_id}",
            sources=[
                NodeOrEdgeData(
                    source={"space": SPACE, "externalId": "PLTeam", "version": VERSION, "type": "view"},
                    properties={
                        "strengthOverallHome": team_data.get('strength_overall_home'),
                        "strengthOverallAway": team_data.get('strength_overall_away'),
                        "strengthAttackHome": team_data.get('strength_attack_home'),
                        "strengthAttackAway": team_data.get('strength_attack_away'),
                        "strengthDefenceHome": team_data.get('strength_defence_home'),
                        "strengthDefenceAway": team_data.get('strength_defence_away'),
                    }
                )
            ]
        )
        nodes.append(node)
    
    try:
        result = client.data_modeling.instances.apply(nodes)
        print(f"✓ Updated {len(nodes)} team strength ratings")
        return len(nodes)
    except Exception as e:
        print(f"✗ Error updating teams: {e}")
        return 0


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load fixtures into CDF')
    parser.add_argument('--with-odds', action='store_true', help='Fetch and include betting odds')
    parser.add_argument('--update-teams', action='store_true', help='Update team strength ratings')
    args = parser.parse_args()
    
    print("=" * 60)
    print("FPL Fixture Loader")
    print("=" * 60)
    
    # Initialize client
    try:
        client = get_cdf_client()
        print(f"✓ Connected to CDF project: {client.config.project}\n")
    except Exception as e:
        print(f"✗ Failed to connect to CDF: {e}")
        return 1
    
    # Fetch data
    teams_dict = fetch_fpl_teams()
    if not teams_dict:
        print("✗ Failed to fetch teams. Aborting.")
        return 1
    
    fixtures = fetch_fpl_fixtures()
    if not fixtures:
        print("✗ Failed to fetch fixtures. Aborting.")
        return 1
    
    # Enrich with odds if requested
    fixtures = enrich_with_odds(fixtures, teams_dict, use_odds=args.with_odds)
    
    # Create fixture nodes
    fixtures_created = create_fixture_nodes(client, fixtures, teams_dict)
    
    # Update team strengths if requested
    teams_updated = 0
    if args.update_teams:
        teams_updated = update_team_strength(client, teams_dict)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Fixtures created: {fixtures_created}")
    if args.update_teams:
        print(f"Teams updated: {teams_updated}")
    print("=" * 60)
    print("✓ Done!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

