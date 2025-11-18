"""
Leaderboard Tab - League Rankings and Statistics
"""
import streamlit as st
import pandas as pd
import plotly.express as px


def render(managers_df):
    """Render the Leaderboard tab"""
    st.header("League Leaderboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Managers",
            len(managers_df),
            help="Number of managers in your league"
        )
    
    with col2:
        st.metric(
            "Highest Points",
            f"{managers_df['overall_points'].max():,.0f}",
            help="Highest total points"
        )
    
    with col3:
        st.metric(
            "Most Consistent",
            managers_df.loc[managers_df['consistency_score'].idxmax(), 'manager_name'],
            f"{managers_df['consistency_score'].max():.1f} score"
        )
    
    with col4:
        st.metric(
            "Best Value Growth",
            managers_df.loc[managers_df['team_value_growth'].idxmax(), 'manager_name'],
            f"£{managers_df['team_value_growth'].max():.1f}m"
        )
    
    # Main leaderboard table
    st.subheader("Rankings")
    display_df = managers_df.sort_values("overall_points", ascending=False)[
        ["league_rank", "manager_name", "team_name", "overall_points", 
         "team_value", "consistency_score", "avg_points_per_week", "total_transfers"]
    ].copy()
    
    display_df.columns = ["Rank", "Manager", "Team", "Points", "Value (£m)", 
                          "Consistency", "Avg PPW", "Transfers"]
    
    st.dataframe(
        display_df.style.format({
            "Points": "{:,.0f}",
            "Value (£m)": "£{:.1f}m",
            "Consistency": "{:.1f}",
            "Avg PPW": "{:.1f}",
            "Transfers": "{:.0f}"
        }),
        use_container_width=True,
        height=400
    )
    
    # Points distribution
    st.subheader("Points Distribution")
    fig = px.bar(
        managers_df.sort_values("overall_points", ascending=False),
        x="manager_name",
        y="overall_points",
        color="consistency_score",
        color_continuous_scale="RdYlGn",
        labels={"overall_points": "Total Points", "manager_name": "Manager", 
               "consistency_score": "Consistency Score"},
        title="Total Points by Manager (colored by consistency)"
    )
    fig.update_layout(xaxis_tickangle=-45, height=500)
    st.plotly_chart(fig, use_container_width=True)

