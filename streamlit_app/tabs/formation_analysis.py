"""
Formation Analysis Tab - Analyze formation strategies and profitability
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from ..utils import apply_plotly_theme


def calculate_formation(player_positions, multipliers):
    """
    Calculate formation from player positions (1-15)
    Positions 1-11 are starting XI, 12-15 are bench
    Multiplier 0 means benched
    Returns formation as string like "4-4-2"
    """
    # Filter for starting players (multiplier > 0 or position <= 11)
    starting_positions = []
    
    for pos, mult in zip(player_positions, multipliers):
        if mult > 0:  # Not benched
            starting_positions.append(pos)
    
    # Count by FPL position ranges
    # Position 1 = GK, 2-6 = DEF, 7-10 = MID, 11-14 = FWD (approximately)
    # We'll infer from position numbers
    defenders = len([p for p in starting_positions if 2 <= p <= 6])
    midfielders = len([p for p in starting_positions if 7 <= p <= 10])
    forwards = len([p for p in starting_positions if 11 <= p <= 15])
    
    # Standard formations should have 11 starters (1 GK + 10 outfield)
    # Return as DEF-MID-FWD
    return f"{defenders}-{midfielders}-{forwards}"


def render(client, managers_df, fetch_manager_teams, fetch_players, fetch_player_picks_from_raw=None):
    """Render the Formation Analysis tab"""
    st.header("⚽ Formation Analysis")
    st.write("Discover which formations are most profitable and how managers use different tactical setups")
    
    # Fetch data
    with st.spinner("Loading formation data..."):
        manager_teams_df = fetch_manager_teams(client)
    
    if manager_teams_df.empty:
        st.warning("⚠️ No manager team data found.")
        return
    
    # Filter out teams without formations (bench boost weeks)
    teams_with_formation = manager_teams_df[manager_teams_df['formation'].notna()].copy()
    
    if teams_with_formation.empty:
        st.warning("⚠️ No formation data found. Run scripts/update_formations.py to calculate formations.")
        st.info("""
        **To populate formation data:**
        ```bash
        source .venv/bin/activate
        python scripts/update_formations.py
        ```
        """)
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_teams = len(teams_with_formation)
        st.metric(
            "Total Teams Analyzed",
            total_teams,
            help="Manager teams with formation data (excludes bench boost weeks)"
        )
    
    with col2:
        unique_formations = teams_with_formation['formation'].nunique()
        st.metric(
            "Unique Formations",
            unique_formations,
            help="Number of different formations used"
        )
    
    with col3:
        most_popular = teams_with_formation['formation'].mode()[0] if len(teams_with_formation) > 0 else "N/A"
        st.metric(
            "Most Popular",
            most_popular,
            help="Most commonly used formation"
        )
    
    with col4:
        bench_boost_weeks = len(manager_teams_df[manager_teams_df['active_chip'] == 'bboost'])
        st.metric(
            "Bench Boost Weeks",
            bench_boost_weeks,
            help="Weeks where formation doesn't apply"
        )
    
    # Formation Performance Analysis
    st.subheader("Formation Performance")
    
    # Calculate formation statistics
    formation_stats = teams_with_formation.groupby('formation').agg({
        'total_points': ['mean', 'count', 'sum'],
    }).round(2)
    
    formation_stats.columns = ['Avg Points', 'Usage Count', 'Total Points']
    formation_stats['Usage %'] = (formation_stats['Usage Count'] / len(teams_with_formation) * 100).round(1)
    formation_stats = formation_stats.sort_values('Avg Points', ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Formation performance chart
        fig = go.Figure()
        
        # Add bars for average points
        fig.add_trace(go.Bar(
            x=formation_stats.index,
            y=formation_stats['Avg Points'],
            name='Avg Points',
            marker_color='rgba(55, 0, 60, 0.8)',
            text=formation_stats['Avg Points'].apply(lambda x: f'{x:.1f}'),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Avg Points: %{y:.1f}<br>Used: %{customdata} times<extra></extra>',
            customdata=formation_stats['Usage Count']
        ))
        
        fig.update_layout(
            title='Average Points by Formation',
            xaxis_title='Formation',
            yaxis_title='Average Points',
            height=400,
            showlegend=False
        )
        
        apply_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Formation usage pie chart
        fig = go.Figure(data=[go.Pie(
            labels=formation_stats.index,
            values=formation_stats['Usage Count'],
            hole=0.4,
            marker=dict(colors=px.colors.sequential.Viridis),
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Used: %{value} times<br>%{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title='Formation Usage Distribution',
            height=400,
            showlegend=False
        )
        
        apply_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed statistics table
    st.subheader("Formation Statistics")
    
    display_stats = formation_stats[['Avg Points', 'Usage Count', 'Usage %', 'Total Points']].copy()
    
    st.dataframe(
        display_stats.style.format({
            'Avg Points': '{:.1f}',
            'Usage Count': '{:.0f}',
            'Usage %': '{:.1f}%',
            'Total Points': '{:.0f}'
        }).background_gradient(subset=['Avg Points'], cmap='RdYlGn'),
        use_container_width=True
    )
    
    # Formation trends over time
    st.subheader("Formation Trends Over Gameweeks")
    
    # Calculate formation usage by gameweek
    formation_by_gw = teams_with_formation.groupby(['gameweek', 'formation']).size().reset_index(name='count')
    
    # Get top 5 formations
    top_formations = formation_stats.head(5).index.tolist()
    formation_by_gw_filtered = formation_by_gw[formation_by_gw['formation'].isin(top_formations)]
    
    fig = go.Figure()
    
    for formation in top_formations:
        data = formation_by_gw_filtered[formation_by_gw_filtered['formation'] == formation]
        fig.add_trace(go.Scatter(
            x=data['gameweek'],
            y=data['count'],
            mode='lines+markers',
            name=formation,
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate=f'<b>{formation}</b><br>GW %{{x}}<br>Used: %{{y}} times<extra></extra>'
        ))
    
    fig.update_layout(
        title='Top 5 Formations Usage Over Time',
        xaxis_title='Gameweek',
        yaxis_title='Number of Teams',
        height=400,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(dtick=1)
    
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    # Best formations by points range
    st.subheader("Formation Profitability Analysis")
    
    # Categorize points into ranges
    teams_with_formation['points_category'] = pd.cut(
        teams_with_formation['total_points'],
        bins=[0, 40, 60, 80, 200],
        labels=['Low (0-40)', 'Medium (40-60)', 'Good (60-80)', 'Excellent (80+)']
    )
    
    formation_by_performance = teams_with_formation.groupby(['points_category', 'formation']).size().reset_index(name='count')
    formation_by_performance = formation_by_performance[formation_by_performance['formation'].isin(top_formations)]
    
    fig = go.Figure()
    
    for formation in top_formations:
        data = formation_by_performance[formation_by_performance['formation'] == formation]
        fig.add_trace(go.Bar(
            name=formation,
            x=data['points_category'],
            y=data['count'],
            hovertemplate=f'<b>{formation}</b><br>%{{x}}<br>Count: %{{y}}<extra></extra>'
        ))
    
    fig.update_layout(
        title='Which Formations Lead to High Scores?',
        xaxis_title='Points Category',
        yaxis_title='Number of Teams',
        barmode='group',
        height=400,
        legend=dict(title='Formation')
    )
    
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    # Manager Formation Preferences
    st.subheader("👥 Manager Formation Preferences")
    st.write("See each manager's favorite formations and how profitable their choices have been")
    
    # Calculate favorite formation and profitability for each manager
    manager_formation_stats = []
    
    for manager_id in teams_with_formation['manager_id'].unique():
        manager_teams = teams_with_formation[teams_with_formation['manager_id'] == manager_id]
        
        if len(manager_teams) == 0:
            continue
        
        # Extract numeric entry_id from manager_id (format: "manager_123456")
        entry_id = manager_id.replace("manager_", "") if isinstance(manager_id, str) else manager_id
        try:
            entry_id = int(entry_id)
        except:
            entry_id = None
        
        # Get manager name from managers_df
        if entry_id:
            manager_info = managers_df[managers_df['entry_id'] == entry_id]
            manager_name = manager_info['manager_name'].iloc[0] if not manager_info.empty else f"Manager {entry_id}"
            overall_points = manager_info['overall_points'].iloc[0] if not manager_info.empty else 0
        else:
            manager_name = f"Manager {manager_id}"
            overall_points = 0
        
        # Calculate formation usage
        formation_counts = manager_teams['formation'].value_counts()
        favorite_formation = formation_counts.index[0] if len(formation_counts) > 0 else "N/A"
        favorite_usage = (formation_counts.iloc[0] / len(manager_teams) * 100) if len(formation_counts) > 0 else 0
        
        # Calculate average points by formation for this manager
        avg_points_by_formation = manager_teams.groupby('formation')['total_points'].mean()
        best_formation = avg_points_by_formation.idxmax() if len(avg_points_by_formation) > 0 else "N/A"
        best_avg_points = avg_points_by_formation.max() if len(avg_points_by_formation) > 0 else 0
        
        # Average points overall
        avg_points = manager_teams['total_points'].mean()
        
        manager_formation_stats.append({
            'manager_name': manager_name,
            'manager_id': manager_id,
            'entry_id': entry_id if entry_id else manager_id,
            'overall_points': overall_points,
            'favorite_formation': favorite_formation,
            'favorite_usage_pct': favorite_usage,
            'best_formation': best_formation,
            'best_avg_points': best_avg_points,
            'avg_points_overall': avg_points,
            'formations_used': len(formation_counts)
        })
    
    if manager_formation_stats:
        manager_form_df = pd.DataFrame(manager_formation_stats).sort_values('overall_points', ascending=False)
        
        # Top 5 and Bottom 5 managers
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏆 Top 5 Managers' Formations")
            top_5 = manager_form_df.head(5)
            
            # Count formation usage in top 5
            top_5_formations = teams_with_formation[
                teams_with_formation['manager_id'].isin(top_5['manager_id'])
            ]['formation'].value_counts().head(5)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=top_5_formations.index,
                y=top_5_formations.values,
                marker=dict(
                    color=top_5_formations.values,
                    colorscale='Greens',
                    showscale=True,
                    colorbar=dict(title="Usage")
                ),
                text=top_5_formations.values,
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Used: %{y} times by top 5<extra></extra>'
            ))
            
            fig.update_layout(
                title='Most Used Formations by Top 5 Managers',
                xaxis_title='Formation',
                yaxis_title='Times Used',
                height=350,
                showlegend=False
            )
            
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show top 5 details
            st.markdown("**Top 5 Managers:**")
            for _, manager in top_5.iterrows():
                st.write(f"**{manager['manager_name']}** ({manager['overall_points']} pts)")
                st.write(f"  • Favorite: {manager['favorite_formation']} ({manager['favorite_usage_pct']:.0f}% of time)")
                st.write(f"  • Best: {manager['best_formation']} ({manager['best_avg_points']:.1f} avg pts)")
        
        with col2:
            st.markdown("### 🔴 Bottom 5 Managers' Formations")
            bottom_5 = manager_form_df.tail(5)
            
            # Count formation usage in bottom 5
            bottom_5_formations = teams_with_formation[
                teams_with_formation['manager_id'].isin(bottom_5['manager_id'])
            ]['formation'].value_counts().head(5)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=bottom_5_formations.index,
                y=bottom_5_formations.values,
                marker=dict(
                    color=bottom_5_formations.values,
                    colorscale='Reds',
                    showscale=True,
                    colorbar=dict(title="Usage")
                ),
                text=bottom_5_formations.values,
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Used: %{y} times by bottom 5<extra></extra>'
            ))
            
            fig.update_layout(
                title='Most Used Formations by Bottom 5 Managers',
                xaxis_title='Formation',
                yaxis_title='Times Used',
                height=350,
                showlegend=False
            )
            
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show bottom 5 details
            st.markdown("**Bottom 5 Managers:**")
            for _, manager in bottom_5.iterrows():
                st.write(f"**{manager['manager_name']}** ({manager['overall_points']} pts)")
                st.write(f"  • Favorite: {manager['favorite_formation']} ({manager['favorite_usage_pct']:.0f}% of time)")
                st.write(f"  • Best: {manager['best_formation']} ({manager['best_avg_points']:.1f} avg pts)")
        
        # All managers formation table
        st.markdown("### 📊 All Managers Formation Analysis")
        
        display_manager_form = manager_form_df[[
            'manager_name', 'overall_points', 'favorite_formation', 
            'favorite_usage_pct', 'best_formation', 'best_avg_points', 
            'avg_points_overall', 'formations_used'
        ]].copy()
        
        display_manager_form.columns = [
            'Manager', 'Total Points', 'Favorite Formation', 
            'Usage %', 'Best Formation', 'Best Avg', 
            'Overall Avg', 'Formations Used'
        ]
        
        st.dataframe(
            display_manager_form.style.format({
                'Total Points': '{:.0f}',
                'Usage %': '{:.0f}%',
                'Best Avg': '{:.1f}',
                'Overall Avg': '{:.1f}',
                'Formations Used': '{:.0f}'
            }).background_gradient(subset=['Total Points'], cmap='RdYlGn')
            .background_gradient(subset=['Best Avg'], cmap='Blues'),
            use_container_width=True,
            height=400
        )
    
    # Captain Position Analysis
    st.subheader("👑 Captain Position Analysis")
    st.write("Is it better to captain a Midfielder or a Forward? Let's find out!")
    
    if fetch_player_picks_from_raw:
        with st.spinner("Analyzing captain choices..."):
            try:
                picks_df = fetch_player_picks_from_raw(client)
                players_dict = fetch_players(client)
                
                if not picks_df.empty and players_dict:
                    # Filter for captain picks only
                    captain_picks = picks_df[picks_df['is_captain'] == True].copy()
                    
                    if not captain_picks.empty:
                        # Map player positions
                        captain_picks['player_position'] = captain_picks['player_id'].apply(
                            lambda x: players_dict.get(f"player_{x}", {}).get('position', 'Unknown')
                        )
                        
                        # Calculate captain statistics by position
                        captain_stats = captain_picks.groupby('player_position').agg({
                            'multiplier': 'count',  # Number of times position was captained
                        }).reset_index()
                        
                        captain_stats.columns = ['Position', 'Times Captained']
                        captain_stats['Percentage'] = (captain_stats['Times Captained'] / captain_stats['Times Captained'].sum() * 100).round(1)
                        captain_stats = captain_stats.sort_values('Times Captained', ascending=False)
                        
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Captain choice distribution
                            fig = go.Figure()
                            
                            colors = {'FWD': '#e74c3c', 'MID': '#3498db', 'DEF': '#2ecc71', 'GK': '#95a5a6'}
                            
                            fig.add_trace(go.Bar(
                                x=captain_stats['Position'],
                                y=captain_stats['Times Captained'],
                                marker=dict(
                                    color=[colors.get(pos, '#95a5a6') for pos in captain_stats['Position']]
                                ),
                                text=captain_stats['Percentage'].apply(lambda x: f'{x:.1f}%'),
                                textposition='outside',
                                hovertemplate='<b>%{x}</b><br>Captained: %{y} times<br>%{text} of all captains<extra></extra>'
                            ))
                            
                            fig.update_layout(
                                title='Captain Choices by Position',
                                xaxis_title='Player Position',
                                yaxis_title='Times Captained',
                                height=400,
                                showlegend=False
                            )
                            
                            apply_plotly_theme(fig)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.markdown("### 📈 Captain Statistics")
                            
                            if not captain_stats.empty:
                                most_popular = captain_stats.iloc[0]
                                st.metric(
                                    "Most Popular",
                                    most_popular['Position'],
                                    f"{most_popular['Percentage']:.1f}% of captains"
                                )
                                
                                st.markdown("---")
                                
                                st.markdown("**Breakdown:**")
                                for _, row in captain_stats.iterrows():
                                    st.write(f"**{row['Position']}:** {row['Times Captained']} ({row['Percentage']:.1f}%)")
                        
                        # Captain success by position (if we have points data)
                        st.markdown("### 💡 Captain Insights")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            mid_captains = captain_stats[captain_stats['Position'] == 'MID']['Times Captained'].sum()
                            fwd_captains = captain_stats[captain_stats['Position'] == 'FWD']['Times Captained'].sum()
                            
                            if mid_captains > fwd_captains:
                                pct_more = ((mid_captains / fwd_captains - 1) * 100) if fwd_captains > 0 else 100
                                st.success(f"**Midfielders** are captained {pct_more:.0f}% more often than forwards")
                            else:
                                pct_more = ((fwd_captains / mid_captains - 1) * 100) if mid_captains > 0 else 100
                                st.info(f"**Forwards** are captained {pct_more:.0f}% more often than midfielders")
                        
                        with col2:
                            def_captains = captain_stats[captain_stats['Position'] == 'DEF']['Times Captained'].sum()
                            if def_captains > 0:
                                def_pct = (def_captains / captain_stats['Times Captained'].sum() * 100)
                                st.warning(f"**{def_pct:.1f}%** of captains were defenders - risky but can pay off!")
                            else:
                                st.info("No defenders were captained (typical)")
                        
                        with col3:
                            # Check captain diversity
                            unique_captains = captain_picks['player_id'].nunique()
                            total_captain_picks = len(captain_picks)
                            diversity_score = (unique_captains / total_captain_picks * 100) if total_captain_picks > 0 else 0
                            
                            st.metric(
                                "Captain Diversity",
                                f"{unique_captains} players",
                                f"{diversity_score:.1f}% unique"
                            )
                        
                        # Top captained players by position
                        st.markdown("### 🌟 Most Captained Players by Position")
                        
                        top_captains_by_pos = []
                        for pos in ['FWD', 'MID', 'DEF']:
                            pos_captains = captain_picks[captain_picks['player_position'] == pos]
                            if not pos_captains.empty:
                                player_counts = pos_captains['player_id'].value_counts().head(3)
                                for player_id, count in player_counts.items():
                                    player_info = players_dict.get(f"player_{player_id}", {})
                                    top_captains_by_pos.append({
                                        'Position': pos,
                                        'Player': player_info.get('web_name', f'Player {player_id}'),
                                        'Team': player_info.get('team_name', 'Unknown'),
                                        'Times Captained': count,
                                        'Percentage': (count / len(captain_picks) * 100)
                                    })
                        
                        if top_captains_by_pos:
                            top_captains_df = pd.DataFrame(top_captains_by_pos)
                            
                            # Pivot for better display
                            col1, col2, col3 = st.columns(3)
                            
                            for idx, (col, pos) in enumerate(zip([col1, col2, col3], ['FWD', 'MID', 'DEF'])):
                                with col:
                                    pos_data = top_captains_df[top_captains_df['Position'] == pos]
                                    if not pos_data.empty:
                                        pos_emoji = {'FWD': '⚽', 'MID': '🎯', 'DEF': '🛡️'}
                                        st.markdown(f"**{pos_emoji.get(pos, '')} {pos}**")
                                        for _, player in pos_data.iterrows():
                                            st.write(f"{player['Player']} ({player['Team']})")
                                            st.caption(f"{player['Times Captained']} times • {player['Percentage']:.1f}%")
                    else:
                        st.info("No captain data available")
                else:
                    st.info("Player picks data not available for captain analysis")
            except Exception as e:
                st.warning(f"Captain analysis unavailable: {e}")
                st.info("This feature requires player picks data. Ensure data is loaded correctly.")
    else:
        st.info("Captain analysis requires additional data loading. Feature coming soon!")

