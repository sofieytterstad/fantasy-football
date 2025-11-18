"""
Main Streamlit Application Entry Point
"""
import streamlit as st
import pandas as pd

from .config import CUSTOM_CSS
from .utils import (
    get_cdf_client, fetch_managers, fetch_performance_data,
    fetch_team_betting_data, fetch_teams, fetch_transfer_data,
    fetch_players, fetch_player_picks_from_raw, fetch_player_gameweek_points,
    get_team_color, create_team_badge
)
from .tabs import (
    leaderboard, performance_trends, transfer_analysis,
    managers_favorites, consistency_analysis
)


def main():
    """Main application function"""
    # Page config
    st.set_page_config(
        page_title="Fantasy Football Analytics",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Main header
    st.markdown('<h1 class="main-header">Let\'s play fantaSIUUUU!</h1>', unsafe_allow_html=True)
    
    # Initialize client
    try:
        client = get_cdf_client()
    except Exception as e:
        st.error(f"Failed to connect to CDF: {e}")
        st.info("Please check your .env file and credentials")
        return
    
    # Fetch data
    with st.spinner("Loading data from CDF..."):
        managers_df = fetch_managers(client)
        teams_dict = fetch_teams(client)
    
    if managers_df.empty:
        st.warning("No manager data found. Please run the notebook to load data first.")
        return
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Leaderboard", 
        "📈 Performance Trends", 
        "🔄 Transfer Analysis",
        "⭐ Manager's Favorites", 
        "💎 Consistency Analysis"
    ])
    
    # Render tabs
    with tab1:
        leaderboard.render(managers_df)
    
    with tab2:
        performance_trends.render(
            client, managers_df, fetch_performance_data
        )
    
    with tab3:
        transfer_analysis.render(
            client, managers_df, fetch_transfer_data, fetch_players
        )
    
    with tab4:
        managers_favorites.render(
            client, managers_df, teams_dict,
            fetch_team_betting_data, fetch_players, fetch_player_picks_from_raw,
            fetch_player_gameweek_points, get_team_color, create_team_badge
        )
    
    with tab5:
        consistency_analysis.render(managers_df)
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"**Data from CDF Project:** {client.config.project} | "
        f"**Space:** fantasy_football | "
        f"**Last refreshed:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
    )


if __name__ == "__main__":
    main()

