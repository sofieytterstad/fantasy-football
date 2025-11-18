"""
Performance Trends Tab - Weekly Performance Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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
            # Fetch performance data for selected managers
            all_performance = []
            with st.spinner("Loading performance data..."):
                for manager_name in selected_managers:
                    try:
                        manager_row = managers_df[managers_df["manager_name"] == manager_name].iloc[0]
                        perf_df = fetch_performance_data(client, manager_row["external_id"])
                        if not perf_df.empty:
                            perf_df["manager"] = manager_name
                            all_performance.append(perf_df)
                    except Exception as e:
                        st.error(f"Error loading data for {manager_name}: {e}")
            
            if all_performance:
                combined_df = pd.concat(all_performance, ignore_index=True)
                
                # Enhanced visualization: Points with transfer markers
                st.subheader("📈 Points & Transfer Impact")
                _render_points_with_transfers(combined_df, selected_managers)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Cumulative points
                    fig = px.line(
                        combined_df,
                        x="gameweek",
                        y="total_points",
                        color="manager",
                        markers=True,
                        title="Cumulative Points",
                        labels={"total_points": "Total Points", "gameweek": "Gameweek"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Transfer activity
                    fig = px.bar(
                        combined_df,
                        x="gameweek",
                        y="transfers",
                        color="manager",
                        barmode="group",
                        title="Transfer Activity",
                        labels={"transfers": "Transfers Made", "gameweek": "Gameweek"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No performance data available for selected managers")
    
    except Exception as e:
        st.error(f"Error rendering Performance Trends: {e}")
        import traceback
        st.code(traceback.format_exc())


def _render_points_with_transfers(combined_df, selected_managers):
    """Render points per gameweek with transfer indicators"""
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Color palette for managers
    colors = px.colors.qualitative.Plotly
    
    for idx, manager in enumerate(selected_managers):
        manager_data = combined_df[combined_df["manager"] == manager].sort_values("gameweek")
        color = colors[idx % len(colors)]
        
        # Add points line
        fig.add_trace(
            go.Scatter(
                x=manager_data["gameweek"],
                y=manager_data["points"],
                name=f"{manager} - Points",
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=6),
                hovertemplate="<b>%{fullData.name}</b><br>" +
                              "GW %{x}<br>" +
                              "Points: %{y}<br>" +
                              "<extra></extra>"
            ),
            secondary_y=False
        )
        
        # Add transfer markers (show only gameweeks with transfers)
        transfer_data = manager_data[manager_data["transfers"] > 0].copy()
        if not transfer_data.empty:
            # Create marker sizes based on number of transfers
            transfer_data["marker_size"] = transfer_data["transfers"] * 8 + 10
            
            fig.add_trace(
                go.Scatter(
                    x=transfer_data["gameweek"],
                    y=transfer_data["points"],
                    name=f"{manager} - Transfers",
                    mode="markers",
                    marker=dict(
                        size=transfer_data["marker_size"],
                        color=color,
                        symbol="diamond",
                        line=dict(color="white", width=2)
                    ),
                    hovertemplate="<b>%{fullData.name}</b><br>" +
                                  "GW %{x}<br>" +
                                  "Points: %{y}<br>" +
                                  "Transfers: %{customdata[0]}<br>" +
                                  "Cost: %{customdata[1]} pts<br>" +
                                  "<extra></extra>",
                    customdata=transfer_data[["transfers", "transfer_cost"]].values,
                    showlegend=True
                ),
                secondary_y=False
            )
    
    # Update layout
    fig.update_layout(
        title="Points Per Gameweek with Transfer Activity",
        xaxis_title="Gameweek",
        height=600,
        hovermode="x unified",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="right",
            x=1.15
        )
    )
    
    # Set y-axes titles
    fig.update_yaxes(title_text="Points", secondary_y=False)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add explanation
    st.info("""
    💎 **Diamond markers** indicate gameweeks where transfers were made. 
    Larger diamonds = more transfers. Hover to see transfer details and points impact.
    """)

