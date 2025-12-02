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
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Montserrat:wght@400;600;700;800;900&family=Raleway:wght@400;600;700;800&display=swap');
    
    /* Main App Background - Clean with subtle accent */
    .main {
        background-color: #f8f9fa;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* All text default to dark for readability */
    .main * {
        color: #2c3e50;
    }
    
    /* Header Styling */
    .main-header {
        font-size: 5rem;
        font-weight: 900;
        background: linear-gradient(90deg, #37003c, #00ff87, #37003c);
        background-size: 200% auto;
        color: #FFFFFF;
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        padding: 1rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        animation: gradient-shift 3s ease infinite;
        font-family: 'Bebas Neue', cursive;
        letter-spacing: 4px;
        text-transform: uppercase;
    }
    
    @keyframes gradient-shift {
        0% { background-position: 0% center; }
        50% { background-position: 100% center; }
        100% { background-position: 0% center; }
    }
    
    /* Hero Section */
    .hero-banner {
        background: linear-gradient(135deg, #37003c 0%, #00ff87 100%);
        padding: 2.5rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(55, 0, 60, 0.4);
        border: 3px solid #00ff87;
    }
    
    .hero-title {
        color: #FFFFFF;
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
        text-shadow: 3px 3px 10px rgba(0,0,0,0.6);
        font-family: 'Bebas Neue', cursive;
        letter-spacing: 3px;
    }
    
    .hero-subtitle {
        color: #FFFFFF;
        font-size: 1.3rem;
        font-weight: 600;
        text-shadow: 2px 2px 6px rgba(0,0,0,0.6);
        font-family: 'Raleway', sans-serif;
        letter-spacing: 1px;
    }
    
    /* Mobile responsiveness */
    @media screen and (max-width: 768px) {
        .hero-banner {
            padding: 1.5rem 1rem;
        }
        
        .hero-title {
            font-size: 2rem;
            letter-spacing: 2px;
        }
        
        .hero-subtitle {
            font-size: 0.9rem;
            letter-spacing: 0.5px;
        }
    }
    
    @media screen and (max-width: 480px) {
        .hero-banner {
            padding: 1rem 0.5rem;
        }
        
        .hero-title {
            font-size: 1.5rem;
            letter-spacing: 1px;
        }
        
        .hero-subtitle {
            font-size: 0.75rem;
            letter-spacing: 0.3px;
        }
    }
    
    /* Stats Cards */
    .metric-card {
        background: linear-gradient(135deg, #FFFFFF 0%, #f0f2f6 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-left: 5px solid #37003c;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(55, 0, 60, 0.3);
    }
    
    /* Football Field Pattern Background */
    .stApp {
        background-color: #f8f9fa;
        background-image: 
            repeating-linear-gradient(
                90deg,
                transparent,
                transparent 50px,
                rgba(55, 0, 60, 0.02) 50px,
                rgba(55, 0, 60, 0.02) 100px
            ),
            repeating-linear-gradient(
                0deg,
                transparent,
                transparent 50px,
                rgba(55, 0, 60, 0.02) 50px,
                rgba(55, 0, 60, 0.02) 100px
            );
    }
    
    /* Tabs Styling - Football themed */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: linear-gradient(135deg, #37003c 0%, #4a0049 100%);
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3.5rem;
        font-size: 1.1rem;
        font-weight: 700;
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 0 1.5rem;
        transition: all 0.3s;
        border: 2px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"] button {
        color: #FFFFFF !important;
    }
    
    .stTabs [data-baseweb="tab"] p {
        color: #FFFFFF !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(0, 255, 135, 0.2);
        border: 2px solid #00ff87;
        transform: scale(1.05);
    }
    
    .stTabs [data-baseweb="tab"]:hover button,
    .stTabs [data-baseweb="tab"]:hover p {
        color: #00ff87 !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #00ff87 0%, #00cc6a 100%);
        border: 2px solid #37003c;
        box-shadow: 0 4px 12px rgba(0, 255, 135, 0.4);
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] button,
    .stTabs [data-baseweb="tab"][aria-selected="true"] p {
        color: #37003c !important;
    }
    
    /* Team Badge */
    .team-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 8px;
        font-weight: bold;
        color: white;
        margin: 0.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    }
    
    .team-badge:hover {
        transform: scale(1.1);
    }
    
    /* Metric Containers */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        color: #37003c !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-weight: 700;
        color: #495057 !important;
        font-size: 1rem;
    }
    
    /* Headings */
    h1 {
        color: #37003c !important;
        font-family: 'Bebas Neue', cursive !important;
        letter-spacing: 2px;
        font-size: 3rem !important;
    }
    
    h2 {
        color: #37003c !important;
        font-family: 'Raleway', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: 1px;
    }
    
    h3 {
        color: #2c3e50 !important;
        font-family: 'Raleway', sans-serif !important;
        font-weight: 700 !important;
    }
    
    h4, h5, h6 {
        color: #2c3e50 !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
    }
    
    /* Paragraphs and text */
    p, span, div {
        color: #495057;
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Data Tables */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #37003c 0%, #4a0049 100%);
        color: #00ff87 !important;
        font-weight: 700;
        border: 2px solid #00ff87;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #00ff87 0%, #00cc6a 100%);
        color: #37003c !important;
        border: 2px solid #37003c;
        transform: scale(1.05);
        box-shadow: 0 4px 12px rgba(0, 255, 135, 0.4);
    }
    
    /* Selectbox and Inputs */
    .stSelectbox > div > div {
        background-color: #FFFFFF;
        border: 2px solid #37003c;
        border-radius: 8px;
    }
    
    .stSelectbox label {
        color: #2c3e50 !important;
        font-weight: 600;
    }
    
    .stMultiSelect label {
        color: #2c3e50 !important;
        font-weight: 600;
    }
    
    /* Footer */
    .footer-style {
        background: linear-gradient(135deg, #37003c 0%, #4a0049 100%);
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        color: #FFFFFF !important;
        font-weight: 600;
        margin-top: 2rem;
        box-shadow: 0 -4px 16px rgba(0,0,0,0.2);
    }
    
    .footer-style div {
        color: #FFFFFF !important;
    }
    
    .footer-style strong {
        color: #00ff87 !important;
    }
    
    /* Expander Styling */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, rgba(55, 0, 60, 0.1) 0%, rgba(0, 255, 135, 0.1) 100%);
        border-radius: 8px;
        border: 2px solid #37003c;
        font-weight: 700;
        color: #37003c;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, rgba(55, 0, 60, 0.2) 0%, rgba(0, 255, 135, 0.2) 100%);
    }
    
    /* Info/Warning/Success boxes */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid #37003c;
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
TEAM_VIEW = "PLTeam"
TRANSFER_VIEW = "Transfer"
PLAYER_VIEW = "Player"
MANAGER_TEAM_VIEW = "ManagerTeam"
GAMEWEEK_VIEW = "Gameweek"
FIXTURE_VIEW = "Fixture"

# Cache TTL (in seconds)
CACHE_TTL = 3600  # 1 hour

# Plotly Chart Theme Configuration
PLOTLY_THEME = {
    "layout": {
        "paper_bgcolor": "rgba(248, 249, 250, 0.95)",
        "plot_bgcolor": "rgba(255, 255, 255, 0.9)",
        "font": {
            "family": "Montserrat, sans-serif",
            "size": 13,
            "color": "#2c3e50"
        },
        "title": {
            "font": {
                "family": "Raleway, sans-serif",
                "size": 20,
                "color": "#37003c",
                "weight": 700
            }
        },
        "xaxis": {
            "gridcolor": "rgba(55, 0, 60, 0.1)",
            "linecolor": "#37003c",
            "tickfont": {"color": "#2c3e50", "size": 12}
        },
        "yaxis": {
            "gridcolor": "rgba(55, 0, 60, 0.1)",
            "linecolor": "#37003c",
            "tickfont": {"color": "#2c3e50", "size": 12}
        },
        "colorway": ["#37003c", "#00ff87", "#e30613", "#0057b8", "#6cabdd", "#c8102e"],
        "hovermode": "closest"
    }
}

