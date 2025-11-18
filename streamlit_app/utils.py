"""
Utility functions for Fantasy Football Dashboard
"""
import streamlit as st
import pandas as pd
from cognite.client import CogniteClient
from cognite.client.config import ClientConfig
from cognite.client.credentials import OAuthClientCredentials
from cognite.client.data_classes.data_modeling.ids import ViewId
import os
from dotenv import load_dotenv

from .config import (
    PREMIER_LEAGUE_COLORS, SPACE, VERSION,
    MANAGER_VIEW, GAMEWEEK_PERF_VIEW, TEAM_BETTING_VIEW,
    TEAM_VIEW, TRANSFER_VIEW, PLAYER_VIEW, CACHE_TTL
)

# Load environment variables
load_dotenv()


@st.cache_resource
def get_cdf_client():
    """Initialize and return CDF client"""
    # Try Streamlit secrets first (for cloud deployment), then fall back to env vars (for local)
    try:
        cluster = st.secrets.get("CDF_CLUSTER", os.getenv("CDF_CLUSTER", "bluefield"))
        project = st.secrets.get("CDF_PROJECT", os.getenv("CDF_PROJECT", "sofie-prod"))
        base_url = st.secrets.get("CDF_BASE_URL", os.getenv("CDF_BASE_URL", f"https://{cluster}.cognitedata.com"))
        token_url = st.secrets.get("CDF_TOKEN_URL", os.getenv("CDF_TOKEN_URL"))
        client_id = st.secrets.get("CDF_CLIENT_ID", os.getenv("CDF_CLIENT_ID"))
        client_secret = st.secrets.get("CDF_CLIENT_SECRET", os.getenv("CDF_CLIENT_SECRET"))
    except Exception:
        # Fallback to environment variables only
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
        client_name="fpl-streamlit-app",
        project=project,
        credentials=creds,
        base_url=base_url,
    )
    
    return CogniteClient(cnf)


@st.cache_data(ttl=CACHE_TTL)
def fetch_managers(_client):
    """Fetch all managers from CDF"""
    try:
        manager_view = ViewId(space=SPACE, external_id=MANAGER_VIEW, version=VERSION)
        nodes = _client.data_modeling.instances.list(
            instance_type="node",
            sources=[manager_view],
            limit=100
        )
        
        managers = []
        for node in nodes:
            if not node.external_id.startswith("manager_"):
                continue
                
            if hasattr(node, 'properties') and node.properties is not None:
                try:
                    if hasattr(node.properties, 'dump'):
                        props_dict = node.properties.dump()
                    else:
                        props_dict = node.properties
                    
                    if isinstance(props_dict, dict):
                        props = props_dict.get(SPACE, {})
                        if isinstance(props, dict):
                            props = props.get(f"{MANAGER_VIEW}/{VERSION}", {})
                    else:
                        props = {}
                except Exception:
                    props = {}
                
                if props and isinstance(props, dict):
                    managers.append({
                        "external_id": node.external_id,
                        "entry_id": props.get("entryId"),
                        "manager_name": props.get("managerName", "Unknown"),
                        "team_name": props.get("teamName", ""),
                        "overall_points": props.get("overallPoints", 0),
                        "overall_rank": props.get("overallRank", 0),
                        "league_rank": props.get("leagueRank", 0),
                        "team_value": props.get("teamValue", 0),
                        "consistency_score": props.get("consistencyScore", 0),
                        "avg_points_per_week": props.get("averagePointsPerWeek", 0),
                        "points_std_dev": props.get("pointsStdDev", 0),
                        "team_value_growth": props.get("teamValueGrowth", 0),
                        "total_transfers": props.get("totalTransfers", 0)
                    })
        
        return pd.DataFrame(managers)
    except Exception as e:
        st.error(f"Error fetching managers: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_performance_data(_client, manager_external_id):
    """Fetch gameweek performance for a manager"""
    try:
        perf_view = ViewId(space=SPACE, external_id=GAMEWEEK_PERF_VIEW, version=VERSION)
        nodes = _client.data_modeling.instances.list(
            instance_type="node",
            sources=[perf_view],
            limit=1000
        )
        
        performance = []
        for node in nodes:
            if not node.external_id.startswith(f"performance_{manager_external_id.split('_')[1]}_"):
                continue
                
            if hasattr(node, 'properties') and node.properties is not None:
                try:
                    if hasattr(node.properties, 'dump'):
                        props_dict = node.properties.dump()
                    else:
                        props_dict = node.properties
                    
                    if isinstance(props_dict, dict):
                        props = props_dict.get(SPACE, {})
                        if isinstance(props, dict):
                            props = props.get(f"{GAMEWEEK_PERF_VIEW}/{VERSION}", {})
                    else:
                        props = {}
                except Exception:
                    props = {}
                
                if props and isinstance(props, dict):
                    gw_num = node.external_id.split("_gw")[-1]
                    performance.append({
                        "gameweek": int(gw_num) if gw_num.isdigit() else 0,
                        "points": props.get("points", 0),
                        "total_points": props.get("totalPoints", 0),
                        "rank": props.get("overallRank", 0),
                        "transfers": props.get("transfers", 0),
                        "transfer_cost": props.get("transferCost", 0)
                    })
        
        df = pd.DataFrame(performance)
        if not df.empty:
            df = df.sort_values("gameweek")
        return df
    except Exception as e:
        st.error(f"Error fetching performance data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_team_betting_data(_client):
    """Fetch team betting patterns"""
    try:
        betting_view = ViewId(space=SPACE, external_id=TEAM_BETTING_VIEW, version=VERSION)
        nodes = _client.data_modeling.instances.list(
            instance_type="node",
            sources=[betting_view],
            limit=1000
        )
        
        betting_data = []
        for node in nodes:
            if not node.external_id.startswith("betting_"):
                continue
                
            if hasattr(node, 'properties') and node.properties is not None:
                try:
                    if hasattr(node.properties, 'dump'):
                        props_dict = node.properties.dump()
                    else:
                        props_dict = node.properties
                    
                    if isinstance(props_dict, dict):
                        props = props_dict.get(SPACE, {})
                        if isinstance(props, dict):
                            props = props.get(f"{TEAM_BETTING_VIEW}/{VERSION}", {})
                    else:
                        props = {}
                except Exception:
                    props = {}
                
                if props and isinstance(props, dict):
                    manager_id = props.get("manager", {}).get("externalId", "")
                    team_id = props.get("team", {}).get("externalId", "")
                    
                    betting_data.append({
                        "manager_id": manager_id,
                        "team_id": team_id,
                        "total_players_used": props.get("totalPlayersUsed", 0),
                        "total_points": props.get("totalPoints", 0),
                        "avg_points_per_player": props.get("averagePointsPerPlayer", 0),
                        "success_rate": props.get("successRate", 0)
                    })
        
        return pd.DataFrame(betting_data)
    except Exception as e:
        st.error(f"Error fetching team betting data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_teams(_client):
    """Fetch Premier League teams"""
    try:
        team_view = ViewId(space=SPACE, external_id=TEAM_VIEW, version=VERSION)
        nodes = _client.data_modeling.instances.list(
            instance_type="node",
            sources=[team_view],
            limit=100
        )
        
        teams = {}
        for node in nodes:
            if not node.external_id.startswith("team_"):
                continue
                
            if hasattr(node, 'properties') and node.properties is not None:
                try:
                    if hasattr(node.properties, 'dump'):
                        props_dict = node.properties.dump()
                    else:
                        props_dict = node.properties
                    
                    if isinstance(props_dict, dict):
                        props = props_dict.get(SPACE, {})
                        if isinstance(props, dict):
                            props = props.get(f"{TEAM_VIEW}/{VERSION}", {})
                    else:
                        props = {}
                except Exception:
                    props = {}
                
                if props and isinstance(props, dict):
                    teams[node.external_id] = props.get("name", "Unknown Team")
        
        return teams
    except Exception as e:
        st.error(f"Error fetching teams: {e}")
        return {}


@st.cache_data(ttl=CACHE_TTL)
def fetch_transfer_data(_client):
    """Fetch transfer data with success metrics"""
    try:
        transfer_view = ViewId(space=SPACE, external_id=TRANSFER_VIEW, version=VERSION)
        nodes = _client.data_modeling.instances.list(
            instance_type="node",
            sources=[transfer_view],
            limit=2000
        )
        
        transfers = []
        for node in nodes:
            if hasattr(node, 'properties'):
                props_dict = node.properties.dump() if hasattr(node.properties, 'dump') else node.properties
                props = props_dict.get(SPACE, {}).get(f"{TRANSFER_VIEW}/{VERSION}", {})
                if props:
                    manager_id = props.get("manager", {}).get("externalId", "")
                    gameweek_id = props.get("gameweek", {}).get("externalId", "")
                    player_in_id = props.get("playerIn", {}).get("externalId", "")
                    player_out_id = props.get("playerOut", {}).get("externalId", "")
                    
                    gw_num = gameweek_id.split("_")[-1] if gameweek_id else "0"
                    
                    transfers.append({
                        "external_id": node.external_id,
                        "manager_id": manager_id,
                        "gameweek": int(gw_num) if gw_num.isdigit() else 0,
                        "player_in_id": player_in_id,
                        "player_out_id": player_out_id,
                        "transfer_cost": props.get("transferCost", 0),
                        "player_in_price": props.get("playerInPrice", 0),
                        "player_out_price": props.get("playerOutPrice", 0),
                        "points_gained_next_3gw": props.get("pointsGainedNext3GW", 0),
                        "was_successful": props.get("wasSuccessful", False),
                        "net_benefit": props.get("netBenefit", 0)
                    })
        
        return pd.DataFrame(transfers)
    except Exception as e:
        st.error(f"Error fetching transfer data: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_players(_client):
    """Fetch player data"""
    try:
        player_view = ViewId(space=SPACE, external_id=PLAYER_VIEW, version=VERSION)
        nodes = _client.data_modeling.instances.list(
            instance_type="node",
            sources=[player_view],
            limit=1000
        )
        
        players = {}
        for node in nodes:
            if hasattr(node, 'properties'):
                props_dict = node.properties.dump() if hasattr(node.properties, 'dump') else node.properties
                props = props_dict.get(SPACE, {}).get(f"{PLAYER_VIEW}/{VERSION}", {})
                if props:
                    players[node.external_id] = {
                        "name": props.get("webName", "Unknown"),
                        "full_name": props.get("fullName", ""),
                        "team_id": props.get("team", {}).get("externalId", ""),
                        "position": props.get("elementType", "")
                    }
        
        return players
    except Exception as e:
        st.error(f"Error fetching players: {e}")
        return {}


@st.cache_data(ttl=CACHE_TTL)
def fetch_player_picks_from_raw(_client):
    """Fetch raw player picks data to see which players were actually used"""
    try:
        rows = _client.raw.rows.list(db_name="fantasy_football", table_name="fpl_manager_picks", limit=5000)
        
        picks_data = []
        parse_errors = 0
        
        for row in rows:
            cols = row.columns
            picks_json_str = cols.get("picks_json", "[]")
            
            try:
                import json
                import ast
                
                # Try to parse as proper JSON first
                try:
                    picks_list = json.loads(picks_json_str)
                except:
                    # Fall back to ast.literal_eval for Python string format
                    picks_list = ast.literal_eval(picks_json_str)
                
                for pick in picks_list:
                    picks_data.append({
                        "manager_entry_id": cols.get("entry_id"),
                        "gameweek": cols.get("gameweek"),
                        "player_id": pick.get("element"),
                        "multiplier": pick.get("multiplier", 1)
                    })
            except Exception as e:
                parse_errors += 1
                continue
        
        if parse_errors > 0:
            st.warning(f"⚠️ Failed to parse {parse_errors} pick records")
        
        return pd.DataFrame(picks_data) if picks_data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching player picks: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL)
def fetch_player_gameweek_points(_client):
    """Fetch player points by gameweek from raw data"""
    try:
        rows = _client.raw.rows.list(db_name="fantasy_football", table_name="fpl_player_gameweek", limit=10000)
        
        player_points = []
        for row in rows:
            cols = row.columns
            player_points.append({
                "player_id": cols.get("player_id"),
                "gameweek": cols.get("gameweek"),
                "total_points": cols.get("total_points", 0),
                "minutes": cols.get("minutes", 0),
                "goals_scored": cols.get("goals_scored", 0),
                "assists": cols.get("assists", 0)
            })
        
        return pd.DataFrame(player_points)
    except Exception as e:
        st.error(f"Error fetching player gameweek points: {e}")
        return pd.DataFrame()


def get_team_color(team_name):
    """Get the primary color for a Premier League team"""
    colors = PREMIER_LEAGUE_COLORS.get(team_name, {"primary": "#38003c", "secondary": "#FFFFFF"})
    return colors["primary"]


def create_team_badge(team_name, team_color):
    """Create a colored badge HTML for a team"""
    text_color = "#FFFFFF" if team_name != "Fulham" else "#000000"
    return f'<span class="team-badge" style="background-color: {team_color}; color: {text_color};">{team_name}</span>'

