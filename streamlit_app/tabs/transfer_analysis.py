"""
Transfer Analysis Tab - Transfer Success and ROI Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ..utils import apply_plotly_theme


def render(client, managers_df, fetch_transfer_data, fetch_players):
    """Render the Transfer Analysis tab"""
    st.header("Transfer Success Analysis")
    st.write("Analyzing transfer decisions: Did they pay off?")
    
    # Manager selection at the top - SINGLE SELECT
    selected_manager = st.selectbox(
        "Select Manager to Analyze",
        options=managers_df["manager_name"].tolist(),
        help="Choose a manager to view their transfer success"
    )
    
    if not selected_manager:
        st.info("Please select a manager to view transfer analysis")
        return
    
    transfer_df = fetch_transfer_data(client)
    players_dict = fetch_players(client)
    
    if not transfer_df.empty and managers_df is not None and not managers_df.empty:
        # Map manager IDs to names
        manager_id_to_name = dict(zip(managers_df["external_id"], managers_df["manager_name"]))
        transfer_df["manager_name"] = transfer_df["manager_id"].map(manager_id_to_name)
        
        # Map player IDs to names
        transfer_df["player_in_name"] = transfer_df["player_in_id"].map(lambda x: players_dict.get(x, {}).get("name", "Unknown"))
        transfer_df["player_out_name"] = transfer_df["player_out_id"].map(lambda x: players_dict.get(x, {}).get("name", "Unknown"))
        
        # Filter for selected manager
        transfer_filtered = transfer_df[transfer_df["manager_name"] == selected_manager].copy()
        
        if not transfer_filtered.empty:
            # Sort by gameweek for time-series analysis
            transfer_filtered = transfer_filtered.sort_values("gameweek")
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_transfers = len(transfer_filtered)
                st.metric(
                    "Total Transfers",
                    total_transfers,
                    help="Total transfers made by selected managers"
                )
            
            with col2:
                successful_transfers = transfer_filtered["was_successful"].sum()
                success_rate = (successful_transfers / total_transfers * 100) if total_transfers > 0 else 0
                st.metric(
                    "Successful Transfers",
                    f"{successful_transfers}",
                    f"{success_rate:.1f}% success rate"
                )
            
            with col3:
                avg_net_benefit = transfer_filtered["net_benefit"].mean()
                st.metric(
                    "Avg Net Benefit",
                    f"{avg_net_benefit:.1f} pts",
                    help="Average point difference (player in - player out)"
                )
            
            with col4:
                total_cost = transfer_filtered["transfer_cost"].sum()
                st.metric(
                    "Total Cost",
                    f"{total_cost} pts",
                    help="Total points lost to transfer costs"
                )
            
            # Week-by-week transfer impact
            st.subheader("Cumulative Transfer Impact Over Time")
            st.write("What if you didn't make those transfers? This shows the running impact of your transfer decisions.")
            
            # Calculate cumulative impact
            transfer_filtered['cumulative_benefit'] = transfer_filtered['net_benefit'].cumsum()
            transfer_filtered['cumulative_cost'] = transfer_filtered['transfer_cost'].cumsum()
            transfer_filtered['cumulative_net'] = transfer_filtered['cumulative_benefit'] - transfer_filtered['cumulative_cost']
            
            fig = go.Figure()
            
            # Add line for cumulative benefit (if you kept old players)
            fig.add_trace(go.Scatter(
                x=transfer_filtered['gameweek'],
                y=[0] * len(transfer_filtered),  # Baseline if no transfers
                mode='lines',
                name='No Transfers Made',
                line=dict(color='rgba(128, 128, 128, 0.5)', width=2, dash='dash'),
                hovertemplate='GW %{x}<br>No transfers: 0 pts<extra></extra>'
            ))
            
            # Add line for cumulative benefit before costs
            fig.add_trace(go.Scatter(
                x=transfer_filtered['gameweek'],
                y=transfer_filtered['cumulative_benefit'],
                mode='lines+markers',
                name='Benefit (before costs)',
                line=dict(color='rgba(100, 200, 255, 0.8)', width=2),
                marker=dict(size=6),
                hovertemplate='GW %{x}<br>Cumulative benefit: %{y:.1f} pts<extra></extra>'
            ))
            
            # Add line for net benefit (after costs)
            fig.add_trace(go.Scatter(
                x=transfer_filtered['gameweek'],
                y=transfer_filtered['cumulative_net'],
                mode='lines+markers',
                name='Net Benefit (after costs)',
                line=dict(color='rgba(0, 255, 150, 0.9)', width=3),
                marker=dict(size=8),
                fill='tonexty',
                fillcolor='rgba(0, 255, 150, 0.1)',
                hovertemplate='GW %{x}<br>Net benefit: %{y:.1f} pts<extra></extra>'
            ))
            
            # Add markers for individual transfers
            colors = ['green' if x > 0 else 'red' for x in transfer_filtered['net_benefit']]
            fig.add_trace(go.Scatter(
                x=transfer_filtered['gameweek'],
                y=transfer_filtered['cumulative_net'],
                mode='markers',
                name='Transfer Points',
                marker=dict(
                    size=12,
                    color=colors,
                    symbol='circle',
                    line=dict(width=1, color='white')
                ),
                hovertemplate='<b>GW %{x}</b><br>' +
                              'Transfer: ' + transfer_filtered['player_out_name'] + ' → ' + transfer_filtered['player_in_name'] + '<br>' +
                              'Net benefit this GW: ' + transfer_filtered['net_benefit'].apply(lambda x: f'{x:.1f}') + ' pts<br>' +
                              'Cumulative: %{y:.1f} pts<extra></extra>',
                showlegend=False
            ))
            
            fig.update_layout(
                title=f"Transfer Impact: {selected_manager}",
                xaxis_title="Gameweek",
                yaxis_title="Cumulative Points Impact",
                height=500,
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
            
            # Summary interpretation
            final_net = transfer_filtered['cumulative_net'].iloc[-1]
            if final_net > 0:
                st.success(f"✅ Overall, {selected_manager}'s transfers gained **{final_net:.1f} points** compared to not transferring!")
            elif final_net < 0:
                st.error(f"❌ Overall, {selected_manager}'s transfers cost **{abs(final_net):.1f} points** compared to not transferring.")
            else:
                st.info(f"➖ Overall, {selected_manager}'s transfers broke even.")
            
            # All transfers detail
            st.subheader("Transfer History")
            recent_transfers = transfer_filtered.sort_values("gameweek", ascending=False)
            
            display_transfers = recent_transfers[[
                "gameweek", "player_out_name", "player_in_name",
                "net_benefit", "transfer_cost", "was_successful"
            ]].copy()
            
            display_transfers.columns = [
                "GW", "Player Out", "Player In", "Benefit", "Cost", "Success"
            ]
            
            # Add visual indicators
            display_transfers["Success"] = display_transfers["Success"].apply(
                lambda x: "✅" if x else "❌"
            )
            
            st.dataframe(
                display_transfers.style.format({
                    "Benefit": "{:.0f}",
                    "Cost": "{:.0f}"
                }).apply(
                    lambda x: ['background-color: #d4edda' if v == "✅" else 'background-color: #f8d7da' 
                               for v in x], subset=["Success"]
                ),
                use_container_width=True,
                height=400
            )
            
            # Transfer breakdown - horizontal bar chart
            st.subheader("Individual Transfer Performance")
            
            # Prepare data with labels
            transfer_sorted = transfer_filtered.sort_values('net_benefit', ascending=True)
            transfer_sorted['transfer_label'] = (
                'GW' + transfer_sorted['gameweek'].astype(str) + ': ' + 
                transfer_sorted['player_in_name'].apply(lambda x: x.split()[-1] if x != 'Unknown' else 'Unknown') +
                ' (out: ' + transfer_sorted['player_out_name'].apply(lambda x: x.split()[-1] if x != 'Unknown' else 'Unknown') + ')'
            )
            
            fig = go.Figure()
            
            # Create horizontal bar chart
            colors = ['rgba(239, 68, 68, 0.8)' if x < 0 else 'rgba(34, 197, 94, 0.8)' for x in transfer_sorted['net_benefit']]
            
            fig.add_trace(go.Bar(
                y=transfer_sorted['transfer_label'],
                x=transfer_sorted['net_benefit'],
                orientation='h',
                marker=dict(
                    color=colors,
                    line=dict(color='rgba(255,255,255,0.3)', width=1)
                ),
                text=transfer_sorted['net_benefit'].apply(lambda x: f"{x:+.0f} pts"),
                textposition='outside',
                textfont=dict(size=11, color='white'),
                hovertemplate='<b>%{y}</b><br>Net benefit: %{x:.1f} pts<extra></extra>',
                showlegend=False
            ))
            
            # Add vertical line at zero
            fig.add_vline(
                x=0, 
                line_dash="solid", 
                line_color="rgba(255, 255, 255, 0.5)", 
                line_width=2
            )
            
            fig.update_layout(
                title=f"All Transfers Ranked by Performance",
                xaxis_title="Net Benefit (points)",
                yaxis_title="",
                height=max(400, len(transfer_sorted) * 35),  # Dynamic height based on number of transfers
                hovermode='y',
                xaxis=dict(zeroline=False),
                yaxis=dict(
                    tickfont=dict(size=10)
                ),
                margin=dict(l=250, r=100)  # More space for labels
            )
            
            apply_plotly_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info(f"No transfer data available for {selected_manager}")
    else:
        st.warning("⚠️ No transfer data found in CDF. Please run the transfer analysis in the notebook first.")
        st.info("""
        **To enable transfer analysis:**
        1. Open `notebooks/load_fpl_to_cdf.ipynb`
        2. Run the transfer analysis cells to fetch and calculate transfer success metrics
        3. Refresh this dashboard
        """)

