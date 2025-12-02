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
    fetch_current_gameweek, fetch_manager_teams, fetch_fixtures,
    get_team_color, create_team_badge
)
from .tabs import (
    leaderboard, performance_trends, transfer_analysis,
    managers_favorites, fun_facts, formation_analysis, fixture_odds_analysis
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
    
    # Hero Banner
    st.markdown("""
        <div class="hero-banner">
            <div class="hero-title">⚽ Let's play fantaSIUUUU! ⚽</div>
            <div class="hero-subtitle">🏆 Your Ultimate Fantasy Football Analytics Dashboard 🏆</div>
        </div>
    """, unsafe_allow_html=True)
    
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
    
    # Quick Stats Banner
    st.markdown("### 📊 League Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("👥 Managers", len(managers_df), help="Total managers in the league")
    
    with col2:
        avg_points = int(managers_df["overall_points"].mean())
        st.metric("🎯 Avg Points", f"{avg_points:,}", help="Average points across all managers")
    
    with col3:
        top_scorer = int(managers_df["overall_points"].max())
        st.metric("🏆 Top Score", f"{top_scorer:,}", help="Highest scoring manager")
    
    with col4:
        avg_value = managers_df["team_value"].mean()
        st.metric("💰 Avg Value", f"£{avg_value:.1f}m", help="Average team value")
    
    with col5:
        total_transfers = int(managers_df["total_transfers"].sum())
        st.metric("🔄 Total Transfers", f"{total_transfers:,}", help="All transfers made in the league")
    
    st.markdown("---")
    
    # Welcome message
    with st.expander("ℹ️ **How to Use This Dashboard**", expanded=False):
        st.markdown("""
        **Welcome to your Fantasy Football Analytics Hub!** 🎉
        
        Navigate through the tabs to explore different aspects of your league:
        
        - **📊 Leaderboard** - See current standings and manager rankings
        - **📈 Performance Trends** - Track performance over time with beautiful charts
        - **🔄 Transfer Analysis** - Analyze transfer strategies and patterns
        - **⭐ Manager's Favorites** - Discover which Premier League teams managers favor
        - **⚽ Formation Analysis** - Compare formation strategies and their profitability
        - **🎯 Fixture & Odds** - Identify profitable teams based on fixtures and performance
        - **🎉 Fun Facts** - Interesting stats and category leaders
        
        **Tip:** Hover over charts and metrics for more details! 💡
        """)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Leaderboard", 
        "📈 Performance Trends", 
        "🔄 Transfer Analysis",
        "⭐ Manager's Favorites",
        "⚽ Formation Analysis",
        "🎯 Fixture & Odds",
        "🎉 Fun Facts"
    ])
    
    # Render tabs
    with tab1:
        leaderboard.render(
            client, managers_df, 
            fetch_current_gameweek, fetch_manager_teams,
            fetch_performance_data, fetch_players, fetch_player_gameweek_points
        )
    
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
        formation_analysis.render(
            client, managers_df, fetch_manager_teams, fetch_players, fetch_player_picks_from_raw
        )
    
    with tab6:
        fixture_odds_analysis.render(
            client, managers_df, fetch_teams,
            fetch_players, fetch_team_betting_data, fetch_fixtures
        )
    
    with tab7:
        fun_facts.render(managers_df)
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
        <div class="footer-style">
            <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">⚽ Fantasy Football Analytics ⚽</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">
                📊 <strong>Data Source:</strong> {client.config.project} | 
                🌐 <strong>Space:</strong> fantasy_football | 
                🕐 <strong>Last Updated:</strong> {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
            </div>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

