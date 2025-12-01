"""
Performance Trends Tab - Weekly Performance Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ..utils import apply_plotly_theme


def render(client, managers_df, fetch_performance_data):
    """Render the Performance Trends tab"""
    st.header("Weekly Performance Trends")
    
    try:
        # Manager selection at the top
        selected_managers = st.multiselect(
            "Select Managers to Compare",
            options=managers_df["manager_name"].tolist(),
            default=managers_df["manager_name"].tolist()[:5] if len(managers_df) >= 5 else managers_df["manager_name"].tolist(),
            help="Choose one or more managers to view their performance trends",
            key="performance_trends_managers"
        )
        
        if not selected_managers:
            st.info("Please select at least one manager to view their performance")
        else:
            # Fetch performance data for ALL managers (for accurate league ranking)
            all_league_performance = []
            selected_performance = []
            
            with st.spinner("Loading performance data..."):
                for idx, row in managers_df.iterrows():
                    manager_name = row["manager_name"]
                    try:
                        perf_df = fetch_performance_data(client, row["external_id"])
                        if not perf_df.empty:
                            perf_df["manager"] = manager_name
                            all_league_performance.append(perf_df)
                            
                            # Also collect selected managers separately for display
                            if manager_name in selected_managers:
                                selected_performance.append(perf_df)
                    except Exception as e:
                        if manager_name in selected_managers:
                            st.error(f"Error loading data for {manager_name}: {e}")
            
            if selected_performance:
                combined_df = pd.concat(selected_performance, ignore_index=True)
                full_league_df = pd.concat(all_league_performance, ignore_index=True) if all_league_performance else combined_df
                
                # Calculate additional metrics
                combined_df = _calculate_metrics(combined_df)
                
                # Create tabs for different views
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📊 Gameweek Points", 
                    "📈 Cumulative Progress", 
                    "🔄 Transfer Impact",
                    "📉 Rank Movement"
                ])
                
                with tab1:
                    _render_gameweek_points(combined_df)
                
                with tab2:
                    _render_cumulative_view(combined_df)
                
                with tab3:
                    _render_transfer_analysis(combined_df)
                
                with tab4:
                    _render_rank_movement(combined_df, full_league_df)
            else:
                st.info("No performance data available for selected managers")
    
    except Exception as e:
        st.error(f"Error rendering Performance Trends: {e}")
        import traceback
        st.code(traceback.format_exc())


def _calculate_metrics(df):
    """Calculate additional metrics for analysis"""
    df = df.copy()
    
    # Calculate rolling averages per manager
    for manager in df["manager"].unique():
        mask = df["manager"] == manager
        df.loc[mask, "points_ma3"] = df.loc[mask, "points"].rolling(window=3, min_periods=1).mean()
        df.loc[mask, "points_ma5"] = df.loc[mask, "points"].rolling(window=5, min_periods=1).mean()
    
    # Calculate net points (after transfer cost)
    df["net_points"] = df["points"] - df.get("transfer_cost", 0)
    
    return df


def _render_gameweek_points(combined_df):
    """Render clean gameweek points comparison"""
    st.subheader("Points Per Gameweek")
    
    # View options
    col1, col2 = st.columns([3, 1])
    with col2:
        show_avg = st.checkbox("Show 3-week moving average", value=False, key="show_avg_gw")
    
    # Create the main points chart
    fig = go.Figure()
    
    colors = px.colors.qualitative.Plotly
    managers = combined_df["manager"].unique()
    
    for idx, manager in enumerate(managers):
        manager_data = combined_df[combined_df["manager"] == manager].sort_values("gameweek")
        color = colors[idx % len(colors)]
        
        # Add main points line
        fig.add_trace(go.Scatter(
            x=manager_data["gameweek"],
            y=manager_data["points"],
            name=manager,
            mode="lines+markers",
            line=dict(color=color, width=2.5),
            marker=dict(size=8),
            hovertemplate="<b>%{fullData.name}</b><br>" +
                          "Gameweek: %{x}<br>" +
                          "Points: %{y}<br>" +
                          "<extra></extra>"
        ))
        
        # Add moving average if selected
        if show_avg and "points_ma3" in manager_data.columns:
            fig.add_trace(go.Scatter(
                x=manager_data["gameweek"],
                y=manager_data["points_ma3"],
                name=f"{manager} (3-wk avg)",
                mode="lines",
                line=dict(color=color, width=1.5, dash="dash"),
                opacity=0.5,
                hovertemplate="<b>%{fullData.name}</b><br>" +
                              "Gameweek: %{x}<br>" +
                              "3-wk avg: %{y:.1f}<br>" +
                              "<extra></extra>"
            ))
    
    fig.update_layout(
        title="Points Per Gameweek",
        height=500,
        xaxis_title="Gameweek",
        yaxis_title="Points",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    # Summary stats
    st.subheader("Gameweek Statistics")
    cols = st.columns(len(managers))
    for idx, manager in enumerate(managers):
        with cols[idx]:
            manager_data = combined_df[combined_df["manager"] == manager]
            st.metric(
                label=manager,
                value=f"{manager_data['points'].mean():.1f}",
                delta=f"±{manager_data['points'].std():.1f}",
                help=f"Average points per gameweek ± standard deviation"
            )


def _render_cumulative_view(combined_df):
    """Render cumulative points progression"""
    st.subheader("Cumulative Points Over Season")
    
    # Cumulative points chart
    fig = px.line(
        combined_df.sort_values(["manager", "gameweek"]),
        x="gameweek",
        y="total_points",
        color="manager",
        markers=True,
        title="Cumulative Points Over Season",
        labels={"total_points": "Total Points", "gameweek": "Gameweek"}
    )
    
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8)
    )
    
    fig.update_layout(
        height=500,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    # Points gaps
    st.subheader("Current Standings")
    latest_gw = combined_df["gameweek"].max()
    latest_standings = combined_df[combined_df["gameweek"] == latest_gw].sort_values("total_points", ascending=False)
    
    if not latest_standings.empty:
        leader_points = latest_standings.iloc[0]["total_points"]
        standings_data = []
        
        for idx, row in latest_standings.iterrows():
            gap = row["total_points"] - leader_points
            standings_data.append({
                "Position": len(standings_data) + 1,
                "Manager": row["manager"],
                "Total Points": int(row["total_points"]),
                "Gap to Leader": f"{gap:+d}" if gap != 0 else "—"
            })
        
        st.dataframe(
            pd.DataFrame(standings_data),
            use_container_width=True,
            hide_index=True
        )


def _render_transfer_analysis(combined_df):
    """Render transfer impact analysis"""
    st.subheader("Transfer Activity & Impact")
    
    # Create two columns for different views
    col1, col2 = st.columns(2)
    
    with col1:
        # Transfer frequency
        st.markdown("#### Transfer Frequency")
        transfer_summary = combined_df.groupby("manager").agg({
            "transfers": ["sum", "mean"],
            "transfer_cost": "sum"
        }).round(2)
        transfer_summary.columns = ["Total Transfers", "Avg per GW", "Total Cost"]
        st.dataframe(transfer_summary, use_container_width=True)
    
    with col2:
        # Points efficiency
        st.markdown("#### Transfer Efficiency")
        efficiency = combined_df.groupby("manager").agg({
            "points": "sum",
            "transfer_cost": "sum"
        })
        efficiency["Net Points"] = efficiency["points"] - efficiency["transfer_cost"]
        efficiency["Cost %"] = (efficiency["transfer_cost"] / efficiency["points"] * 100).round(2)
        efficiency = efficiency[["Net Points", "Cost %"]].sort_values("Net Points", ascending=False)
        st.dataframe(efficiency, use_container_width=True)
    
    # Transfer timeline - Clean scatter plot
    st.markdown("#### Transfer Activity Over Time")
    
    # Filter to only show gameweeks where transfers were made
    transfer_data = combined_df[combined_df["transfers"] > 0].copy()
    
    if not transfer_data.empty:
        # Create scatter plot with sized markers
        fig = go.Figure()
        
        colors = px.colors.qualitative.Plotly
        managers = sorted(combined_df["manager"].unique())
        
        for idx, manager in enumerate(managers):
            manager_transfers = transfer_data[transfer_data["manager"] == manager]
            
            if not manager_transfers.empty:
                color = colors[idx % len(colors)]
                
                # Create marker sizes based on number of transfers
                marker_sizes = manager_transfers["transfers"] * 15 + 10
                
                fig.add_trace(go.Scatter(
                    x=manager_transfers["gameweek"],
                    y=[manager] * len(manager_transfers),
                    name=manager,
                    mode="markers+text",
                    marker=dict(
                        size=marker_sizes,
                        color=color,
                        line=dict(color="white", width=2),
                        opacity=0.8
                    ),
                    text=manager_transfers["transfers"].astype(str),
                    textposition="middle center",
                    textfont=dict(color="white", size=10, family="Arial Black"),
                    hovertemplate="<b>%{fullData.name}</b><br>" +
                                  "Gameweek: %{x}<br>" +
                                  "Transfers: %{text}<br>" +
                                  "<extra></extra>",
                    showlegend=False
                ))
        
        fig.update_layout(
            title="",
            height=max(250, len(managers) * 60),
            xaxis_title="Gameweek",
            yaxis_title="",
            xaxis=dict(
                tickmode="linear",
                tick0=combined_df["gameweek"].min(),
                dtick=1
            ),
            yaxis=dict(
                categoryorder="array",
                categoryarray=list(reversed(managers))  # Reverse to match legend order
            ),
            hovermode="closest",
            plot_bgcolor="rgba(240,240,240,0.3)",
            showlegend=False
        )
        
        apply_plotly_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("💡 Larger circles = more transfers. Numbers show exact transfer count.")
    else:
        st.info("No transfers made in the selected gameweeks")


def _render_rank_movement(combined_df, full_league_df):
    """Render rank movement over time"""
    st.subheader("League Rank Progression")
    
    # Calculate league rank based on ALL managers in the league
    full_league_with_rank = full_league_df.copy()
    
    # For each gameweek, rank ALL managers by total_points
    full_league_with_rank['league_rank'] = full_league_with_rank.groupby('gameweek')['total_points'].rank(
        ascending=False, method='min'
    ).astype(int)
    
    # Get total number of managers for context
    total_managers = full_league_with_rank['manager'].nunique()
    
    st.caption(f"League positions out of {total_managers} managers")
    
    # Filter to only show selected managers
    selected_managers = combined_df['manager'].unique()
    df_with_rank = full_league_with_rank[full_league_with_rank['manager'].isin(selected_managers)].copy()
    
    # Create the rank progression chart
    fig = px.line(
        df_with_rank.sort_values(["manager", "gameweek"]),
        x="gameweek",
        y="league_rank",
        color="manager",
        markers=True,
        title="League Rank Progression",
        labels={"league_rank": "League Position", "gameweek": "Gameweek"}
    )
    
    fig.update_traces(
        line=dict(width=3),
        marker=dict(size=8)
    )
    
    # Invert y-axis so rank 1 is at the top
    fig.update_yaxes(autorange="reversed")
    
    fig.update_layout(
        height=500,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    apply_plotly_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    # Rank changes
    st.subheader("Position Changes")
    rank_changes = []
    
    for manager in df_with_rank["manager"].unique():
        manager_data = df_with_rank[df_with_rank["manager"] == manager].sort_values("gameweek")
        if len(manager_data) >= 2:
            first_rank = manager_data.iloc[0]["league_rank"]
            last_rank = manager_data.iloc[-1]["league_rank"]
            change = first_rank - last_rank  # Positive = improved (moved up)
            
            # Find biggest single gameweek change
            manager_data = manager_data.copy()
            manager_data["rank_change"] = manager_data["league_rank"].diff() * -1
            biggest_jump_idx = manager_data["rank_change"].abs().idxmax()
            
            if pd.notna(biggest_jump_idx):
                biggest_jump = manager_data.loc[biggest_jump_idx]
                best_jump_val = biggest_jump['rank_change']
                best_jump_gw = int(biggest_jump['gameweek'])
            else:
                best_jump_val = 0
                best_jump_gw = "N/A"
            
            rank_changes.append({
                "Manager": manager,
                "Overall Change": f"{change:+d}" if change != 0 else "—",
                "Current Position": f"{int(last_rank)}/{total_managers}",
                "Best Jump": f"{best_jump_val:+.0f}" if pd.notna(best_jump_val) and best_jump_val != 0 else "—",
                "Best Jump GW": best_jump_gw if best_jump_val != 0 else "—"
            })
    
    if rank_changes:
        st.dataframe(
            pd.DataFrame(rank_changes).sort_values("Current Position"),
            use_container_width=True,
            hide_index=True
        )

