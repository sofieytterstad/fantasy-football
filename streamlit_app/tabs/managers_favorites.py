"""
Manager's Favorites Tab - Team Preference and Performance Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render(client, managers_df, teams_dict, 
           fetch_team_betting_data, fetch_players, fetch_player_picks_from_raw,
           fetch_player_gameweek_points, get_team_color, create_team_badge):
    """Render the Manager's Favorites tab"""
    st.header("⭐ Manager's Favorite Teams")
    st.write("Discover which Premier League teams managers favor and how their choices pay off in points!")
    
    # Manager selection at the top - SINGLE SELECTION
    selected_manager = st.selectbox(
        "Select Manager to Analyze",
        options=managers_df["manager_name"].tolist(),
        index=0,
        help="Choose a manager to view their favorite teams"
    )
    
    if not selected_manager:
        st.info("Please select a manager to view their favorite teams")
        return
    
    betting_df = fetch_team_betting_data(client)
    players_dict = fetch_players(client)
    
    if not betting_df.empty and managers_df is not None and not managers_df.empty:
        # Map team IDs to names
        betting_df["team_name"] = betting_df["team_id"].map(teams_dict)
        
        # Map manager IDs to names
        manager_id_to_name = dict(zip(managers_df["external_id"], managers_df["manager_name"]))
        betting_df["manager_name"] = betting_df["manager_id"].map(manager_id_to_name)
        
        # Filter for selected manager (single)
        betting_filtered = betting_df[betting_df["manager_name"] == selected_manager]
        
        if not betting_filtered.empty:
            _render_overview(betting_filtered, selected_manager)
            _render_team_performance(betting_filtered, selected_manager, get_team_color)
            _render_manager_detail(client, managers_df, betting_filtered, players_dict, teams_dict,
                                  selected_manager, fetch_player_picks_from_raw, 
                                  fetch_player_gameweek_points, get_team_color, create_team_badge)
        else:
            st.info(f"No team preference data available for {selected_manager}")
    else:
        st.info("No team preference data available. Run the team analysis in the notebook first.")


def _render_overview(betting_filtered, selected_manager):
    """Render overview metrics"""
    st.subheader(f"📊 {selected_manager}'s Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    total_teams_used = betting_filtered["team_name"].nunique()
    total_players_used = betting_filtered["total_players_used"].sum()
    total_points_generated = betting_filtered["total_points"].sum()
    avg_points_per_team = betting_filtered.groupby("team_name")["total_points"].sum().mean()
    
    with col1:
        st.metric("Teams Used", f"{total_teams_used}", 
                 help="Number of different PL teams with players selected")
    
    with col2:
        st.metric("Total Player Selections", f"{int(total_players_used)}", 
                 help="Total times players were picked (across all gameweeks)")
    
    with col3:
        st.metric("Total Points Generated", f"{int(total_points_generated):,}", 
                 help="Total points from all team selections")
    
    with col4:
        st.metric("Avg Points per Team", f"{avg_points_per_team:.0f}", 
                 help="Average points generated per team")
    
    st.markdown("---")


def _render_team_performance(betting_filtered, selected_manager, get_team_color):
    """Render team performance analysis"""
    st.subheader(f"🎯 {selected_manager}'s Team Performance: Most Picked vs Most Valuable")
    
    team_summary = betting_filtered.groupby("team_name").agg({
        "total_players_used": "sum",
        "total_points": "sum",
        "avg_points_per_player": "mean",
        "success_rate": "mean"
    }).reset_index()
    
    # Calculate points per selection with safe division
    team_summary["points_per_selection"] = team_summary.apply(
        lambda row: round(row["total_points"] / row["total_players_used"], 2) 
        if row["total_players_used"] > 0 else 0,
        axis=1
    )
    
    # Add team colors
    team_summary["color"] = team_summary["team_name"].apply(get_team_color)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Most Picked Teams**")
        most_picked = team_summary.nlargest(10, "total_players_used")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=most_picked["team_name"],
            y=most_picked["total_players_used"],
            marker_color=most_picked["color"],
            text=most_picked["total_players_used"],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Players Used: %{y}<br>Total Points: %{customdata}<extra></extra>',
            customdata=most_picked["total_points"]
        ))
        fig.update_layout(
            title="Teams by Number of Player Selections",
            xaxis_title="Team",
            yaxis_title="Total Player Selections",
            xaxis_tickangle=-45,
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**Most Valuable Teams (Points per Selection)**")
        most_valuable = team_summary.nlargest(10, "points_per_selection")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=most_valuable["team_name"],
            y=most_valuable["points_per_selection"],
            marker_color=most_valuable["color"],
            text=most_valuable["points_per_selection"].round(1),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Points/Selection: %{y:.2f}<br>Total Points: %{customdata}<extra></extra>',
            customdata=most_valuable["total_points"]
        ))
        fig.update_layout(
            title="Teams by Points per Player Selection",
            xaxis_title="Team",
            yaxis_title="Points per Selection",
            xaxis_tickangle=-45,
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Value analysis insights
    _render_value_insights(team_summary)
    
    st.markdown("---")


def _render_value_insights(team_summary):
    """Render value analysis insights"""
    st.markdown("**💡 Insight: Are the most picked teams the most valuable?**")
    
    top_5_picked = set(team_summary.nlargest(5, "total_players_used")["team_name"])
    top_5_valuable = set(team_summary.nlargest(5, "points_per_selection")["team_name"])
    overlap = top_5_picked.intersection(top_5_valuable)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**{len(overlap)}/5** top picked teams are also in top 5 most valuable")
    with col2:
        undervalued = top_5_valuable - top_5_picked
        if undervalued:
            st.success(f"**Underutilized gems:** {', '.join(undervalued)}")
        else:
            st.success("**All valuable teams are being picked!**")
    with col3:
        overvalued = top_5_picked - top_5_valuable
        if overvalued:
            st.warning(f"**Over-picked but lower value:** {', '.join(overvalued)}")


def _render_manager_detail(client, managers_df, betting_filtered, players_dict, teams_dict,
                           selected_manager, fetch_player_picks_from_raw, 
                           fetch_player_gameweek_points, get_team_color, create_team_badge):
    """Render individual manager detail view
    
    Note: Player-level detail requires FPL data ingestion function to be run.
    For now, showing aggregated team statistics.
    """
    st.subheader(f"👤 {selected_manager}'s Team Preferences")
    
    manager_data = betting_filtered[betting_filtered["manager_name"] == selected_manager]
    
    if not manager_data.empty:
        manager_data = manager_data.sort_values("total_points", ascending=False)
        
        # Display teams with top player
        st.markdown(f"**{selected_manager}'s Team Performance - Top Player per Team:**")
        
        # Get top player from each team
        with st.spinner("Loading top players..."):
            picks_df = fetch_player_picks_from_raw(client)
            points_df = fetch_player_gameweek_points(client)
            top_players_by_team = {}
            
            if not picks_df.empty and not points_df.empty and players_dict:
                manager_entry_id = managers_df[managers_df["manager_name"] == selected_manager].iloc[0]["entry_id"]
                manager_picks = picks_df[picks_df["manager_entry_id"] == manager_entry_id]
                
                if not manager_picks.empty:
                    # Merge picks with points data
                    manager_picks_with_points = manager_picks.merge(
                        points_df, 
                        on=["player_id", "gameweek"], 
                        how="left"
                    )
                    
                    # Calculate adjusted points
                    manager_picks_with_points["player_key"] = "player_" + manager_picks_with_points["player_id"].astype(str)
                    manager_picks_with_points["adjusted_points"] = manager_picks_with_points["total_points"] * manager_picks_with_points["multiplier"]
                    
                    # Group by player and sum points
                    player_totals = manager_picks_with_points.groupby("player_key")["adjusted_points"].sum().to_dict()
                    
                    # Find top player per team
                    for player_key, total_points in player_totals.items():
                        if player_key in players_dict:
                            player_info = players_dict[player_key]
                            team_id = player_info.get("team_id", "")
                            
                            if team_id in teams_dict:
                                team_name = teams_dict[team_id]
                                player_name = player_info["name"]
                                
                                if team_name not in top_players_by_team or total_points > top_players_by_team[team_name]["points"]:
                                    top_players_by_team[team_name] = {
                                        "name": player_name,
                                        "points": total_points
                                    }
        
        # Display teams with their top player
        for idx, (_, row) in enumerate(manager_data.head(10).iterrows()):
            team_name = row['team_name']
            team_color = get_team_color(team_name)
            
            # Create a card-style display
            st.markdown(f"### {idx+1}. {team_name}")
            
            # Show top player prominently if available
            if team_name in top_players_by_team:
                top_player = top_players_by_team[team_name]
                st.markdown(f"**⭐ Top Player:** {top_player['name']} - **{top_player['points']:.0f} points**")
            else:
                st.caption("_No player data available_")
            
            # Show metrics in columns
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Points", int(row["total_points"]))
            with col2:
                st.metric("Players Used", int(row["total_players_used"]))
            with col3:
                st.metric("Avg Pts/Player", f"{row['avg_points_per_player']:.1f}")
            
            st.markdown("---")
        
        st.markdown("---")
        st.markdown("**Detailed Stats:**")
        
        # Display stats table
        display_data = manager_data[["team_name", "total_players_used", "total_points", 
                                    "avg_points_per_player", "success_rate"]].copy()
        display_data.columns = ["Team", "Players Used", "Total Points", "Avg Pts/Player", "Success Rate %"]
        
        st.dataframe(
            display_data.style.format({
                "Total Points": "{:.0f}",
                "Avg Pts/Player": "{:.2f}",
                "Success Rate %": "{:.1f}"
            }),
            use_container_width=True,
            height=400
        )
        
        # Pie chart
        st.markdown("**Points Distribution by Team:**")
        fig = go.Figure(data=[go.Pie(
            labels=manager_data["team_name"],
            values=manager_data["total_points"],
            marker=dict(colors=[get_team_color(team) for team in manager_data["team_name"]]),
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Points: %{value}<br>Percentage: %{percent}<extra></extra>'
        )])
        fig.update_layout(
            title=f"Where {selected_manager}'s Points Come From",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")

