"""
Consistency Analysis Tab - Performance Consistency and Reliability
"""
import streamlit as st
import pandas as pd
import plotly.express as px


def render(managers_df):
    """Render the Consistency Analysis tab"""
    st.header("Consistency Analysis")
    st.write("Who's the most reliable week-to-week performer?")
    
    # Manager selection at the top (optional - can filter scatter plots)
    selected_managers = st.multiselect(
        "Select Managers to Highlight (optional - leave empty to show all)",
        options=managers_df["manager_name"].tolist(),
        default=[],
        help="Optionally select specific managers to highlight in the analysis"
    )
    
    # Filter dataframe if managers selected
    if selected_managers:
        display_df = managers_df[managers_df["manager_name"].isin(selected_managers)]
    else:
        display_df = managers_df
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Consistency score distribution
        fig = px.scatter(
            display_df,
            x="avg_points_per_week",
            y="points_std_dev",
            size="overall_points",
            color="consistency_score",
            hover_data=["manager_name", "team_name"],
            color_continuous_scale="RdYlGn",
            title="Consistency: Average vs Volatility",
            labels={
                "avg_points_per_week": "Average Points Per Week",
                "points_std_dev": "Points Standard Deviation",
                "consistency_score": "Consistency Score"
            }
        )
        fig.add_annotation(
            text="Lower std dev = More consistent",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=10, color="gray")
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Team value growth
        fig = px.scatter(
            display_df,
            x="total_transfers",
            y="team_value_growth",
            size="overall_points",
            color="consistency_score",
            hover_data=["manager_name", "team_name"],
            color_continuous_scale="RdYlGn",
            title="Transfers vs Team Value Growth",
            labels={
                "total_transfers": "Total Transfers Made",
                "team_value_growth": "Team Value Growth (£m)",
                "consistency_score": "Consistency Score"
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Top performers in different categories
    st.subheader("Category Leaders")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🎯 Most Consistent**")
        top_consistent = managers_df.nlargest(5, "consistency_score")[["manager_name", "consistency_score"]]
        for idx, row in top_consistent.iterrows():
            st.write(f"{row['manager_name']}: {row['consistency_score']:.1f}")
    
    with col2:
        st.markdown("**📈 Best Value Growth**")
        top_growth = managers_df.nlargest(5, "team_value_growth")[["manager_name", "team_value_growth"]]
        for idx, row in top_growth.iterrows():
            st.write(f"{row['manager_name']}: £{row['team_value_growth']:.1f}m")
    
    with col3:
        st.markdown("**⚡ Highest Average PPW**")
        top_avg = managers_df.nlargest(5, "avg_points_per_week")[["manager_name", "avg_points_per_week"]]
        for idx, row in top_avg.iterrows():
            st.write(f"{row['manager_name']}: {row['avg_points_per_week']:.1f}")

