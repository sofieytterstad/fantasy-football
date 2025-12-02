"""
Fixture & Odds Analysis Tab - Analyze team performance based on fixture difficulty and odds
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from ..utils import apply_plotly_theme


def render(client, managers_df, fetch_teams, fetch_players, fetch_team_betting_data, fetch_fixtures):
    """Render the Fixture & Odds Analysis tab"""
    st.header("🎯 Fixture & Odds Analysis")
    st.write("Identify which teams to target based on fixture difficulty, odds, and historical performance")
    
    # Fetch data
    with st.spinner("Loading fixture analysis data..."):
        teams_dict = fetch_teams(client)
        players_dict = fetch_players(client)
        betting_df = fetch_team_betting_data(client)
        fixtures_df = fetch_fixtures(client)
    
    if fixtures_df.empty:
        st.warning("⚠️ No fixture data found. Run scripts/load_fixtures.py to load fixture data.")
        st.code("python scripts/load_fixtures.py --update-teams")
        return
    
    # Map team IDs to names
    fixtures_df['home_team_name'] = fixtures_df['home_team_id'].map(teams_dict)
    fixtures_df['away_team_name'] = fixtures_df['away_team_id'].map(teams_dict)
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        upcoming_fixtures = fixtures_df[~fixtures_df['is_finished']]
        st.metric(
            "Upcoming Fixtures",
            len(upcoming_fixtures),
            help="Matches yet to be played"
        )
    
    with col2:
        with_odds = fixtures_df[fixtures_df['home_win_odds'].notna()]
        st.metric(
            "Fixtures with Odds",
            len(with_odds),
            f"{len(with_odds)/len(fixtures_df)*100:.0f}%" if len(fixtures_df) > 0 else "0%"
        )
    
    with col3:
        if not fixtures_df.empty:
            avg_home_diff = fixtures_df['home_team_difficulty'].mean()
            st.metric(
                "Avg Home Difficulty",
                f"{avg_home_diff:.1f}",
                help="Average FPL difficulty rating for home teams (1-5)"
            )
    
    with col4:
        if not fixtures_df.empty:
            avg_away_diff = fixtures_df['away_team_difficulty'].mean()
            st.metric(
                "Avg Away Difficulty",
                f"{avg_away_diff:.1f}",
                help="Average FPL difficulty rating for away teams (1-5)"
            )
    
    # Upcoming fixtures with difficulty
    st.subheader("Upcoming Fixtures")
    
    upcoming_df = fixtures_df[~fixtures_df['is_finished']].sort_values('gameweek').head(20)
    
    if not upcoming_df.empty:
        display_upcoming = upcoming_df[[
            'gameweek', 'home_team_name', 'away_team_name',
            'home_team_difficulty', 'away_team_difficulty',
            'home_win_odds', 'draw_odds', 'away_win_odds'
        ]].copy()
        
        display_upcoming.columns = [
            'GW', 'Home Team', 'Away Team', 'Home Diff', 'Away Diff',
            'Home Odds', 'Draw Odds', 'Away Odds'
        ]
        
        st.dataframe(
            display_upcoming.style.format({
                'Home Diff': '{:.0f}',
                'Away Diff': '{:.0f}',
                'Home Odds': lambda x: f'{x:.2f}' if pd.notna(x) else '-',
                'Draw Odds': lambda x: f'{x:.2f}' if pd.notna(x) else '-',
                'Away Odds': lambda x: f'{x:.2f}' if pd.notna(x) else '-'
            }).background_gradient(subset=['Home Diff', 'Away Diff'], cmap='RdYlGn_r'),
            use_container_width=True,
            height=400
        )
    else:
        st.info("All fixtures have been played!")
    
    # Team betting data analysis (if available)
    if not betting_df.empty:
        # Map team IDs to names
        betting_df['team_name'] = betting_df['team_id'].map(teams_dict)
        betting_df = betting_df[betting_df['team_name'].notna()]
    
    # Calculate fixture difficulty by team
    st.subheader("Fixture Difficulty by Team")
    
    # Calculate upcoming difficulty for each team
    upcoming_fixtures = fixtures_df[~fixtures_df['is_finished']].copy()
    
    if not upcoming_fixtures.empty:
        # Get next 5 fixtures for each team
        team_difficulty = []
        
        for team_id, team_name in teams_dict.items():
            home_fixtures = upcoming_fixtures[upcoming_fixtures['home_team_id'] == team_id].head(5)
            away_fixtures = upcoming_fixtures[upcoming_fixtures['away_team_id'] == team_id].head(5)
            
            home_diff = home_fixtures['home_team_difficulty'].mean() if not home_fixtures.empty else 0
            away_diff = away_fixtures['away_team_difficulty'].mean() if not away_fixtures.empty else 0
            
            total_fixtures = len(home_fixtures) + len(away_fixtures)
            avg_diff = (home_diff * len(home_fixtures) + away_diff * len(away_fixtures)) / total_fixtures if total_fixtures > 0 else 0
            
            if total_fixtures > 0:
                team_difficulty.append({
                    'team_name': team_name,
                    'avg_difficulty': avg_diff,
                    'next_5_fixtures': total_fixtures
                })
        
        difficulty_df = pd.DataFrame(team_difficulty).sort_values('avg_difficulty')
        
        # Show teams with easiest fixtures
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Easiest Fixtures (Target These Teams)")
            easy_fixtures = difficulty_df.head(10)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=easy_fixtures['team_name'],
                x=easy_fixtures['avg_difficulty'],
                orientation='h',
                marker=dict(
                    color=easy_fixtures['avg_difficulty'],
                    colorscale='RdYlGn_r',  # Red for hard, green for easy
                    showscale=True,
                    colorbar=dict(title="Difficulty")
                ),
                text=easy_fixtures['avg_difficulty'].apply(lambda x: f'{x:.2f}'),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Avg Difficulty: %{x:.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                title='Teams with Easiest Upcoming Fixtures',
                xaxis_title='Average Difficulty (next 5 games)',
                yaxis_title='',
                height=450,
                showlegend=False,
                xaxis=dict(range=[0, 5])
            )
            
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 🔴 Hardest Fixtures (Avoid These Teams)")
            hard_fixtures = difficulty_df.tail(10).sort_values('avg_difficulty', ascending=False)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=hard_fixtures['team_name'],
                x=hard_fixtures['avg_difficulty'],
                orientation='h',
                marker=dict(
                    color=hard_fixtures['avg_difficulty'],
                    colorscale='RdYlGn_r',
                    showscale=True,
                    colorbar=dict(title="Difficulty")
                ),
                text=hard_fixtures['avg_difficulty'].apply(lambda x: f'{x:.2f}'),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Avg Difficulty: %{x:.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                title='Teams with Hardest Upcoming Fixtures',
                xaxis_title='Average Difficulty (next 5 games)',
                yaxis_title='',
                height=450,
                showlegend=False,
                xaxis=dict(range=[0, 5])
            )
            
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
    
    # Players to Target (from teams with easy fixtures)
    st.subheader("⭐ Players to Target")
    st.write("Top performing players from teams with easy upcoming fixtures")
    
    # Get players from easy fixture teams
    if not difficulty_df.empty and players_dict:
        # Get top 5 easiest teams
        easy_teams = difficulty_df.head(5)['team_name'].tolist()
        
        # Get players from these teams
        players_list = []
        for player_id, player_info in players_dict.items():
            if player_info.get('team_name') in easy_teams:
                players_list.append({
                    'name': player_info.get('web_name', 'Unknown'),
                    'team': player_info.get('team_name', 'Unknown'),
                    'position': player_info.get('position', 'Unknown'),
                    'price': player_info.get('current_price', 0),
                    'total_points': player_info.get('total_points', 0),
                    'form': player_info.get('form', 0),
                    'selected_by': player_info.get('selected_by_percent', 0),
                    'ppg': player_info.get('points_per_game', 0)
                })
        
        if players_list:
            players_target_df = pd.DataFrame(players_list)
            # Filter for players with decent form and points
            players_target_df = players_target_df[
                (players_target_df['form'] > 0) & 
                (players_target_df['total_points'] > 20)
            ].sort_values('form', ascending=False).head(20)
            
            # Create visualization by position
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🎯 Top Targets by Form")
                
                fig = go.Figure()
                
                colors = {'FWD': '#e74c3c', 'MID': '#3498db', 'DEF': '#2ecc71', 'GK': '#f39c12'}
                
                for pos in ['FWD', 'MID', 'DEF']:
                    pos_players = players_target_df[players_target_df['position'] == pos].head(5)
                    if not pos_players.empty:
                        fig.add_trace(go.Bar(
                            name=pos,
                            y=pos_players['name'],
                            x=pos_players['form'],
                            orientation='h',
                            marker=dict(color=colors.get(pos, '#95a5a6')),
                            text=pos_players['price'].apply(lambda x: f'£{x:.1f}m'),
                            textposition='outside',
                            hovertemplate='<b>%{y}</b><br>Form: %{x:.1f}<br>Price: £%{customdata[0]:.1f}m<br>Owned: %{customdata[1]:.1f}%<extra></extra>',
                            customdata=pos_players[['price', 'selected_by']].values
                        ))
                
                fig.update_layout(
                    title='Players in Form from Easy Fixture Teams',
                    xaxis_title='Current Form',
                    yaxis_title='',
                    height=500,
                    barmode='stack',
                    showlegend=True,
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
                
                apply_plotly_theme(fig)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 💎 Best Value Picks")
                
                # Calculate value score (form / price)
                players_target_df['value_score'] = players_target_df['form'] / players_target_df['price']
                best_value = players_target_df.nlargest(10, 'value_score')
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=best_value['price'],
                    y=best_value['form'],
                    mode='markers+text',
                    marker=dict(
                        size=best_value['total_points'] / 5,
                        color=best_value['selected_by'],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="Owned<br>%"),
                        line=dict(width=1, color='white')
                    ),
                    text=best_value['name'],
                    textposition='top center',
                    textfont=dict(size=9),
                    hovertemplate='<b>%{text}</b><br>Price: £%{x:.1f}m<br>Form: %{y:.1f}<br>Owned: %{marker.color:.1f}%<br>Total Pts: %{customdata}<extra></extra>',
                    customdata=best_value['total_points']
                ))
                
                fig.update_layout(
                    title='Price vs Form (Good Fixture Teams)',
                    xaxis_title='Price (£m)',
                    yaxis_title='Form',
                    height=500,
                    hovermode='closest'
                )
                
                apply_plotly_theme(fig)
                st.plotly_chart(fig, use_container_width=True)
            
            # Table of top picks
            st.markdown("### 📋 Detailed Player List")
            display_target = players_target_df.head(15)[['name', 'team', 'position', 'price', 'form', 'total_points', 'selected_by']].copy()
            display_target.columns = ['Player', 'Team', 'Pos', 'Price', 'Form', 'Total Pts', 'Owned %']
            
            st.dataframe(
                display_target.style.format({
                    'Price': '£{:.1f}m',
                    'Form': '{:.1f}',
                    'Total Pts': '{:.0f}',
                    'Owned %': '{:.1f}%'
                }).background_gradient(subset=['Form'], cmap='Greens')
                .background_gradient(subset=['Price'], cmap='RdYlGn_r'),
                use_container_width=True,
                height=400
            )
        else:
            st.info("Player data not available for easy fixture teams")
    
    # Captain Picks
    st.subheader("👑 Captain Picks")
    st.write("Best captain options for upcoming gameweeks based on fixtures and form")
    
    if not difficulty_df.empty and players_dict:
        # Get teams with easiest next fixture
        easiest_next = difficulty_df.head(10)
        
        # Get high-scoring players from these teams
        captain_candidates = []
        for player_id, player_info in players_dict.items():
            if player_info.get('team_name') in easiest_next['team_name'].values:
                total_pts = player_info.get('total_points', 0)
                if total_pts > 50:  # Only consider players with decent total points
                    captain_candidates.append({
                        'name': player_info.get('web_name', 'Unknown'),
                        'team': player_info.get('team_name', 'Unknown'),
                        'position': player_info.get('position', 'Unknown'),
                        'total_points': total_pts,
                        'form': player_info.get('form', 0),
                        'selected_by': player_info.get('selected_by_percent', 0),
                        'ppg': player_info.get('points_per_game', 0),
                        'price': player_info.get('current_price', 0)
                    })
        
        if captain_candidates:
            captain_df = pd.DataFrame(captain_candidates).sort_values('form', ascending=False).head(10)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = go.Figure()
                
                # Calculate captain score (form * ppg)
                captain_df['captain_score'] = captain_df['form'] * captain_df['ppg']
                captain_df = captain_df.sort_values('captain_score', ascending=True)
                
                fig.add_trace(go.Bar(
                    y=captain_df['name'],
                    x=captain_df['captain_score'],
                    orientation='h',
                    marker=dict(
                        color=captain_df['captain_score'],
                        colorscale='YlOrRd',
                        showscale=True,
                        colorbar=dict(title="Captain<br>Score")
                    ),
                    text=captain_df['team'],
                    textposition='inside',
                    hovertemplate='<b>%{y}</b> (%{text})<br>Captain Score: %{x:.1f}<br>Form: %{customdata[0]:.1f}<br>PPG: %{customdata[1]:.1f}<br>Owned: %{customdata[2]:.1f}%<extra></extra>',
                    customdata=captain_df[['form', 'ppg', 'selected_by']].values
                ))
                
                fig.update_layout(
                    title='Best Captain Options (Easy Fixtures)',
                    xaxis_title='Captain Score (Form × PPG)',
                    yaxis_title='',
                    height=450,
                    showlegend=False
                )
                
                apply_plotly_theme(fig)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 💡 Captain Tips")
                if not captain_df.empty:
                    top_captain = captain_df.iloc[-1]
                    st.success(f"**Top Pick:** {top_captain['name']}")
                    st.write(f"🔹 Team: {top_captain['team']}")
                    st.write(f"🔹 Form: {top_captain['form']:.1f}")
                    st.write(f"🔹 PPG: {top_captain['ppg']:.1f}")
                    st.write(f"🔹 Owned: {top_captain['selected_by']:.1f}%")
                    
                    st.markdown("---")
                    st.markdown("**Differential Pick:**")
                    diff_captain = captain_df[captain_df['selected_by'] < 15].iloc[-1] if not captain_df[captain_df['selected_by'] < 15].empty else captain_df.iloc[-2]
                    st.info(f"{diff_captain['name']} ({diff_captain['selected_by']:.1f}% owned)")
        else:
            st.info("No captain candidates found")
    
    # Fixture Swing Analysis
    st.subheader("📈 Fixture Swing")
    st.write("Teams whose fixture difficulty changes dramatically in upcoming weeks")
    
    if not upcoming_fixtures.empty:
        swing_data = []
        
        for team_id, team_name in teams_dict.items():
            team_fixtures = upcoming_fixtures[
                (upcoming_fixtures['home_team_id'] == team_id) | 
                (upcoming_fixtures['away_team_id'] == team_id)
            ].sort_values('gameweek').head(10)
            
            if len(team_fixtures) >= 6:
                # Calculate difficulty for next 3 and then 3 after
                next_3_difficulties = []
                after_3_difficulties = []
                
                for idx, fix in enumerate(team_fixtures.iterrows()):
                    fix_data = fix[1]
                    if fix_data['home_team_id'] == team_id:
                        diff = fix_data['home_team_difficulty']
                    else:
                        diff = fix_data['away_team_difficulty']
                    
                    if idx < 3:
                        next_3_difficulties.append(diff)
                    elif idx < 6:
                        after_3_difficulties.append(diff)
                
                if next_3_difficulties and after_3_difficulties:
                    avg_next_3 = sum(next_3_difficulties) / len(next_3_difficulties)
                    avg_after_3 = sum(after_3_difficulties) / len(after_3_difficulties)
                    swing = avg_after_3 - avg_next_3
                    
                    swing_data.append({
                        'team': team_name,
                        'next_3_diff': avg_next_3,
                        'after_3_diff': avg_after_3,
                        'swing': swing
                    })
        
        if swing_data:
            swing_df = pd.DataFrame(swing_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📉 Fixtures Getting Easier (Buy Now!)")
                improving = swing_df[swing_df['swing'] < -0.5].sort_values('swing').head(8)
                
                if not improving.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        y=improving['team'],
                        x=abs(improving['swing']),
                        orientation='h',
                        marker=dict(color='#2ecc71'),
                        text=improving.apply(lambda x: f"{x['next_3_diff']:.1f} → {x['after_3_diff']:.1f}", axis=1),
                        textposition='outside',
                        hovertemplate='<b>%{y}</b><br>Improvement: %{x:.2f}<br>Next 3 GW: %{customdata[0]:.1f}<br>After 3 GW: %{customdata[1]:.1f}<extra></extra>',
                        customdata=improving[['next_3_diff', 'after_3_diff']].values
                    ))
                    
                    fig.update_layout(
                        title='Teams with Improving Fixtures',
                        xaxis_title='Difficulty Improvement',
                        yaxis_title='',
                        height=400,
                        showlegend=False
                    )
                    
                    apply_plotly_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No teams have significantly improving fixtures")
            
            with col2:
                st.markdown("### 📈 Fixtures Getting Harder (Sell Soon!)")
                worsening = swing_df[swing_df['swing'] > 0.5].sort_values('swing', ascending=False).head(8)
                
                if not worsening.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        y=worsening['team'],
                        x=worsening['swing'],
                        orientation='h',
                        marker=dict(color='#e74c3c'),
                        text=worsening.apply(lambda x: f"{x['next_3_diff']:.1f} → {x['after_3_diff']:.1f}", axis=1),
                        textposition='outside',
                        hovertemplate='<b>%{y}</b><br>Difficulty Increase: %{x:.2f}<br>Next 3 GW: %{customdata[0]:.1f}<br>After 3 GW: %{customdata[1]:.1f}<extra></extra>',
                        customdata=worsening[['next_3_diff', 'after_3_diff']].values
                    ))
                    
                    fig.update_layout(
                        title='Teams with Worsening Fixtures',
                        xaxis_title='Difficulty Increase',
                        yaxis_title='',
                        height=400,
                        showlegend=False
                    )
                    
                    apply_plotly_theme(fig)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No teams have significantly worsening fixtures")
    
    # Differential Picks
    st.subheader("💎 Differential Picks")
    st.write("Less owned players (<15%) from teams with good fixtures")
    
    if not difficulty_df.empty and players_dict:
        easy_teams = difficulty_df.head(10)['team_name'].tolist()
        
        differentials = []
        for player_id, player_info in players_dict.items():
            owned = player_info.get('selected_by_percent', 0)
            if player_info.get('team_name') in easy_teams and owned < 15 and owned > 0:
                form = player_info.get('form', 0)
                if form > 3:  # Only good form players
                    differentials.append({
                        'name': player_info.get('web_name', 'Unknown'),
                        'team': player_info.get('team_name', 'Unknown'),
                        'position': player_info.get('position', 'Unknown'),
                        'price': player_info.get('current_price', 0),
                        'form': form,
                        'owned': owned,
                        'total_points': player_info.get('total_points', 0),
                        'ppg': player_info.get('points_per_game', 0)
                    })
        
        if differentials:
            diff_df = pd.DataFrame(differentials).sort_values('form', ascending=False).head(15)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = go.Figure()
                
                colors = {'FWD': '#e74c3c', 'MID': '#3498db', 'DEF': '#2ecc71', 'GK': '#f39c12'}
                
                for pos in ['FWD', 'MID', 'DEF']:
                    pos_diff = diff_df[diff_df['position'] == pos]
                    if not pos_diff.empty:
                        fig.add_trace(go.Scatter(
                            x=pos_diff['owned'],
                            y=pos_diff['form'],
                            mode='markers+text',
                            name=pos,
                            marker=dict(
                                size=pos_diff['ppg'] * 8,
                                color=colors.get(pos, '#95a5a6'),
                                line=dict(width=1, color='white'),
                                opacity=0.8
                            ),
                            text=pos_diff['name'],
                            textposition='top center',
                            textfont=dict(size=9),
                            hovertemplate='<b>%{text}</b><br>Owned: %{x:.1f}%<br>Form: %{y:.1f}<br>Price: £%{customdata[0]:.1f}m<br>PPG: %{customdata[1]:.1f}<extra></extra>',
                            customdata=pos_diff[['price', 'ppg']].values
                        ))
                
                fig.update_layout(
                    title='Differential Players: Ownership vs Form',
                    xaxis_title='Ownership (%)',
                    yaxis_title='Form',
                    height=450,
                    showlegend=True,
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                )
                
                apply_plotly_theme(fig)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### 🎯 Top Differentials")
                for idx, player in diff_df.head(5).iterrows():
                    with st.container():
                        st.markdown(f"**{player['name']}** ({player['position']})")
                        st.write(f"🔹 {player['team']} • £{player['price']:.1f}m")
                        st.write(f"📊 Form: {player['form']:.1f} • Owned: {player['owned']:.1f}%")
                        st.markdown("---")
        else:
            st.info("No differential picks found with current criteria")

