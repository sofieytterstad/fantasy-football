"""
Configuration and Constants for Fantasy Football Dashboard
"""

# Premier League Team Colors (official colors)
PREMIER_LEAGUE_COLORS = {
    "Arsenal": {"primary": "#EF0107", "secondary": "#FFFFFF"},
    "Aston Villa": {"primary": "#670E36", "secondary": "#95BFE5"},
    "Bournemouth": {"primary": "#DA291C", "secondary": "#000000"},
    "Brentford": {"primary": "#E30613", "secondary": "#FBB800"},
    "Brighton": {"primary": "#0057B8", "secondary": "#FFCD00"},
    "Chelsea": {"primary": "#034694", "secondary": "#FFFFFF"},
    "Crystal Palace": {"primary": "#1B458F", "secondary": "#C4122E"},
    "Everton": {"primary": "#003399", "secondary": "#FFFFFF"},
    "Fulham": {"primary": "#FFFFFF", "secondary": "#CC0000"},
    "Liverpool": {"primary": "#C8102E", "secondary": "#00B2A9"},
    "Man City": {"primary": "#6CABDD", "secondary": "#1C2C5B"},
    "Man Utd": {"primary": "#DA291C", "secondary": "#FBE122"},
    "Newcastle": {"primary": "#241F20", "secondary": "#FFFFFF"},
    "Nott'm Forest": {"primary": "#DD0000", "secondary": "#FFFFFF"},
    "Spurs": {"primary": "#132257", "secondary": "#FFFFFF"},
    "West Ham": {"primary": "#7A263A", "secondary": "#1BB1E7"},
    "Wolves": {"primary": "#FDB913", "secondary": "#231F20"},
    "Leicester": {"primary": "#003090", "secondary": "#FDBE11"},
    "Leeds": {"primary": "#FFCD00", "secondary": "#1D428A"},
    "Southampton": {"primary": "#D71920", "secondary": "#130C0E"},
    "Ipswich": {"primary": "#0033A0", "secondary": "#FFFFFF"},
    "Luton": {"primary": "#F78F1E", "secondary": "#002D62"}
}

# Custom CSS
CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 3rem;
        color: #37003c;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        font-size: 1.1rem;
    }
    .team-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 0.3rem;
        font-weight: bold;
        color: white;
        margin: 0.2rem;
    }
</style>
"""

# CDF Configuration
SPACE = "fantasy_football"
VERSION = "1"

# Data model external IDs
MANAGER_VIEW = "Manager"
GAMEWEEK_PERF_VIEW = "ManagerGameweekPerformance"
TEAM_BETTING_VIEW = "ManagerTeamBetting"
TEAM_VIEW = "Team"
TRANSFER_VIEW = "Transfer"
PLAYER_VIEW = "Player"

# Cache TTL (in seconds)
CACHE_TTL = 3600  # 1 hour

