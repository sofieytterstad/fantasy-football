"""
Leaderboard Tab - League Rankings and Statistics
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render(client, managers_df, fetch_current_gameweek, fetch_manager_teams,
           fetch_performance_data, fetch_players, fetch_player_gameweek_points):
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
    
    # Gameweek insights section
    st.markdown("---")
    _render_gameweek_insights(
        client, managers_df, fetch_current_gameweek, fetch_manager_teams,
        fetch_performance_data, fetch_players, fetch_player_gameweek_points
    )


def _render_gameweek_insights(client, managers_df, fetch_current_gameweek, 
                              fetch_manager_teams, fetch_performance_data,
                              fetch_players, fetch_player_gameweek_points):
    """Render gameweek-specific insights"""
    st.subheader("📅 This Gameweek's Highlights")
    
    # Get current gameweek
    current_gw = fetch_current_gameweek(client)
    
    if not current_gw:
        st.info("No gameweek data available yet.")
        return
    
    gw_number = current_gw["gameweek_number"]
    st.markdown(f"**Gameweek {gw_number}** - {current_gw['name']}")
    
    # Fetch all performance data for this gameweek
    all_performance = []
    with st.spinner("Loading gameweek data..."):
        for _, manager_row in managers_df.iterrows():
            try:
                perf_df = fetch_performance_data(client, manager_row["external_id"])
                if not perf_df.empty:
                    gw_perf = perf_df[perf_df["gameweek"] == gw_number]
                    if not gw_perf.empty:
                        perf_data = gw_perf.iloc[0].to_dict()
                        perf_data["manager_name"] = manager_row["manager_name"]
                        perf_data["manager_id"] = manager_row["external_id"]
                        all_performance.append(perf_data)
            except Exception:
                continue
    
    if not all_performance:
        st.info(f"No performance data available for Gameweek {gw_number}")
        return
    
    perf_df = pd.DataFrame(all_performance)
    
    # Fetch manager teams for captain and chip info
    manager_teams_df = fetch_manager_teams(client, gw_number)
    
    # Render insights
    col1, col2 = st.columns(2)
    
    with col1:
        _render_winner_loser(perf_df)
    
    with col2:
        _render_captain_decisions(client, perf_df, manager_teams_df, 
                                  fetch_players, fetch_player_gameweek_points, gw_number)
    
    # Chip usage in a separate row
    st.markdown("---")
    _render_chip_usage(client, perf_df, manager_teams_df, 
                      fetch_players, fetch_player_gameweek_points, gw_number)


def _render_winner_loser(perf_df):
    """Render gameweek winner and loser"""
    st.markdown("### 🏆 Winner & Loser")
    
    # Winner
    winner = perf_df.loc[perf_df["points"].idxmax()]
    st.markdown("#### 🥇 Gameweek Winner")
    st.success(f"**{winner['manager_name']}** scored **{int(winner['points'])} points**")
    
    st.markdown("")
    
    # Loser
    loser = perf_df.loc[perf_df["points"].idxmin()]
    st.markdown("#### 😢 Gameweek Loser")
    st.error(f"**{loser['manager_name']}** scored **{int(loser['points'])} points**")


def _render_captain_decisions(client, perf_df, manager_teams_df, 
                              fetch_players, fetch_player_gameweek_points, gw_number):
    """Render best and worst captain decisions"""
    st.markdown("### ⭐ Captain Decisions")
    
    if manager_teams_df.empty:
        st.info("Captain data not available")
        return
    
    # Merge performance with manager teams
    merged = perf_df.merge(
        manager_teams_df, 
        left_on="manager_id", 
        right_on="manager_id",
        how="left"
    )
    
    # Fetch players and their gameweek points
    players_dict = fetch_players(client)
    player_gw_points = fetch_player_gameweek_points(client)
    
    if player_gw_points.empty:
        st.info("Player gameweek points not available")
        return
    
    # Filter for this gameweek
    gw_points = player_gw_points[player_gw_points["gameweek"] == gw_number]
    
    # Calculate captain points for each manager
    captain_data = []
    for _, row in merged.iterrows():
        captain_id = row.get("captain_id", "")
        if captain_id and captain_id in players_dict:
            # Get captain's player_id (strip "player_" prefix)
            player_id = int(captain_id.replace("player_", "")) if captain_id.startswith("player_") else 0
            
            # Get captain's points this gameweek
            captain_points_row = gw_points[gw_points["player_id"] == player_id]
            if not captain_points_row.empty:
                captain_points = captain_points_row.iloc[0]["total_points"]
                captain_name = players_dict[captain_id]["name"]
                
                captain_data.append({
                    "manager_name": row["manager_name"],
                    "captain_name": captain_name,
                    "captain_points": captain_points,
                    "captain_doubled_points": captain_points * 2  # Captain gets 2x
                })
    
    if captain_data:
        captain_df = pd.DataFrame(captain_data)
        
        # Best captain
        best = captain_df.loc[captain_df["captain_doubled_points"].idxmax()]
        st.markdown("#### ⭐ Best Captain Choice")
        st.success(
            f"**{best['manager_name']}** captained **{best['captain_name']}** "
            f"who scored **{int(best['captain_points'])} points** "
            f"(**{int(best['captain_doubled_points'])} with armband**)"
        )
        
        st.markdown("")
        
        # Worst captain(s) - show all if there are ties
        min_points = captain_df["captain_doubled_points"].min()
        worst_captains = captain_df[captain_df["captain_doubled_points"] == min_points]
        
        st.markdown("#### 💔 Worst Captain Choice")
        
        if len(worst_captains) == 1:
            worst = worst_captains.iloc[0]
            st.error(
                f"**{worst['manager_name']}** captained **{worst['captain_name']}** "
                f"who scored **{int(worst['captain_points'])} points** "
                f"(**{int(worst['captain_doubled_points'])} with armband**)"
            )
        else:
            # Multiple managers made equally bad captain choices
            st.error(f"**{len(worst_captains)} managers** tied for worst captain choice:")
            for idx, worst in worst_captains.iterrows():
                st.markdown(
                    f"- **{worst['manager_name']}** captained **{worst['captain_name']}** "
                    f"who scored **{int(worst['captain_points'])} points** "
                    f"(**{int(worst['captain_doubled_points'])} with armband**)"
                )
    else:
        st.info("Captain performance data not available")


def _render_chip_usage(client, perf_df, manager_teams_df, 
                       fetch_players, fetch_player_gameweek_points, gw_number):
    """Render chip usage separated by type"""
    st.markdown("### 🎴 Chip Usage This Gameweek")
    
    if manager_teams_df.empty:
        st.info("No chip data available")
        return
    
    # Merge performance with chips
    merged = perf_df.merge(
        manager_teams_df, 
        left_on="manager_id", 
        right_on="manager_id",
        how="left"
    )
    
    # Filter for managers who used chips
    chip_users = merged[merged["active_chip"].notna() & (merged["active_chip"] != "")]
    
    if chip_users.empty:
        st.info("No chips were used this gameweek")
        return
    
    # Get unique chip types used
    chip_types = chip_users["active_chip"].unique()
    
    # Fetch players and gameweek points for Triple Captain calculations
    players_dict = fetch_players(client)
    player_gw_points = fetch_player_gameweek_points(client)
    
    # Render each chip type separately
    for chip_type in sorted(chip_types):
        chip_type_users = chip_users[chip_users["active_chip"] == chip_type]
        _render_chip_type_section(
            chip_type, chip_type_users, 
            players_dict, player_gw_points, gw_number
        )


def _render_chip_type_section(chip_type, chip_users_df, 
                              players_dict, player_gw_points, gw_number):
    """Render a section for a specific chip type"""
    # Get chip emoji and display name
    chip_display_names = {
        "3xc": "⚡ Triple Captain",
        "freehit": "🆓 Free Hit",
        "bboost": "💺 Bench Boost",
        "wildcard": "🃏 Wildcard"
    }
    
    display_name = chip_display_names.get(chip_type, f"🎴 {chip_type.upper()}")
    
    st.markdown(f"#### {display_name}")
    
    # For Triple Captain, we need to show captain points specifically
    # For other chips, show total team points
    if chip_type == "3xc":
        _render_triple_captain_usage(chip_users_df, players_dict, player_gw_points, gw_number)
    else:
        _render_other_chip_usage(chip_users_df, chip_type)
    
    st.markdown("---")


def _render_triple_captain_usage(chip_users_df, players_dict, player_gw_points, gw_number):
    """Render Triple Captain chip usage with captain-specific points"""
    import streamlit as st
    import pandas as pd
    
    st.markdown(f"**{len(chip_users_df)} manager(s) used Triple Captain**")
    
    # Calculate captain points for each Triple Captain user
    if player_gw_points.empty or not players_dict:
        st.info("Captain points data not available")
        return
    
    gw_points = player_gw_points[player_gw_points["gameweek"] == gw_number]
    
    triple_cap_data = []
    for _, row in chip_users_df.iterrows():
        captain_id = row.get("captain_id", "")
        if captain_id and captain_id in players_dict:
            # Get captain's player_id
            player_id = int(captain_id.replace("player_", "")) if captain_id.startswith("player_") else 0
            
            # Get captain's points this gameweek
            captain_points_row = gw_points[gw_points["player_id"] == player_id]
            if not captain_points_row.empty:
                captain_base_points = captain_points_row.iloc[0]["total_points"]
                captain_name = players_dict[captain_id]["name"]
                
                triple_cap_data.append({
                    "manager_name": row["manager_name"],
                    "captain_name": captain_name,
                    "captain_base_points": captain_base_points,
                    "captain_triple_points": captain_base_points * 3,
                    "total_team_points": row["points"]
                })
    
    if not triple_cap_data:
        st.info("Captain points data not available for Triple Captain users")
        return
    
    # Create detailed table
    triple_cap_df = pd.DataFrame(triple_cap_data)
    triple_cap_df = triple_cap_df.sort_values("captain_triple_points", ascending=False).reset_index(drop=True)
    triple_cap_df.index = triple_cap_df.index + 1
    
    display_df = triple_cap_df[["manager_name", "captain_name", "captain_base_points", "captain_triple_points"]].copy()
    display_df.columns = ["Manager", "Captain", "Captain Base Pts", "Captain 3xC Pts"]
    display_df.insert(0, "Rank", display_df.index)
    
    # Highlight top performer
    def highlight_top(row):
        if row.name == 0:
            return ['background-color: #FFD700'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(
        display_df.style.format({
            "Captain Base Pts": "{:.0f}",
            "Captain 3xC Pts": "{:.0f}"
        }).apply(highlight_top, axis=1),
        use_container_width=True,
        hide_index=True,
        height=min(300, len(display_df) * 35 + 38)
    )
    
    # Show stats
    avg_captain_pts = triple_cap_df["captain_triple_points"].mean()
    max_captain_pts = triple_cap_df["captain_triple_points"].max()
    min_captain_pts = triple_cap_df["captain_triple_points"].min()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Avg Captain Pts", f"{avg_captain_pts:.1f}")
    with col2:
        st.metric("Best Captain", f"{int(max_captain_pts)} pts")
    with col3:
        st.metric("Worst Captain", f"{int(min_captain_pts)} pts")
    
    # Show best and worst if more than one user
    if len(triple_cap_df) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            best = triple_cap_df.loc[triple_cap_df["captain_triple_points"].idxmax()]
            st.success(
                f"🏅 **Best**: {best['manager_name']} - "
                f"{best['captain_name']} ({int(best['captain_base_points'])} × 3 = {int(best['captain_triple_points'])} pts)"
            )
        
        with col2:
            worst = triple_cap_df.loc[triple_cap_df["captain_triple_points"].idxmin()]
            st.warning(
                f"😬 **Worst**: {worst['manager_name']} - "
                f"{worst['captain_name']} ({int(worst['captain_base_points'])} × 3 = {int(worst['captain_triple_points'])} pts)"
            )
    elif len(triple_cap_df) == 1:
        user = triple_cap_df.iloc[0]
        st.info(
            f"👤 **{user['manager_name']}** captained **{user['captain_name']}** "
            f"({int(user['captain_base_points'])} × 3 = {int(user['captain_triple_points'])} pts)"
        )


def _render_other_chip_usage(chip_users_df, chip_type):
    """Render other chip usage (Free Hit, Bench Boost, Wildcard)"""
    import streamlit as st
    
    st.markdown(f"**{len(chip_users_df)} manager(s) used this chip**")
    
    # Create detailed ranking
    chip_detail = chip_users_df[["manager_name", "points"]].copy()
    chip_detail = chip_detail.sort_values("points", ascending=False).reset_index(drop=True)
    chip_detail.index = chip_detail.index + 1
    chip_detail.columns = ["Manager", "Points Scored"]
    chip_detail.insert(0, "Rank", chip_detail.index)
    
    # Highlight top performer
    def highlight_top(row):
        if row.name == 0:
            return ['background-color: #FFD700'] * len(row)
        else:
            return [''] * len(row)
    
    st.dataframe(
        chip_detail.style.format({
            "Points Scored": "{:.0f}"
        }).apply(highlight_top, axis=1),
        use_container_width=True,
        hide_index=True,
        height=min(300, len(chip_detail) * 35 + 38)
    )
    
    # Show stats
    avg_points = chip_users_df["points"].mean()
    max_points = chip_users_df["points"].max()
    min_points = chip_users_df["points"].min()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average", f"{avg_points:.1f} pts")
    with col2:
        st.metric("Highest", f"{int(max_points)} pts")
    with col3:
        st.metric("Lowest", f"{int(min_points)} pts")
    
    # Show best and worst if more than one user
    if len(chip_users_df) > 1:
        col1, col2 = st.columns(2)
        
        with col1:
            best = chip_users_df.loc[chip_users_df["points"].idxmax()]
            st.success(
                f"🏅 **Best**: {best['manager_name']} - {int(best['points'])} pts"
            )
        
        with col2:
            worst = chip_users_df.loc[chip_users_df["points"].idxmin()]
            st.warning(
                f"😬 **Worst**: {worst['manager_name']} - {int(worst['points'])} pts"
            )

