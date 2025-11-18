"""
Transfer Analysis Tab - Transfer Success and ROI Analysis
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render(client, managers_df, fetch_transfer_data, fetch_players):
    """Render the Transfer Analysis tab"""
    st.header("Transfer Success Analysis")
    st.write("Comparing points from transferred-in players vs transferred-out players")
    
    # Manager selection at the top
    selected_managers = st.multiselect(
        "Select Managers to Analyze",
        options=managers_df["manager_name"].tolist(),
        default=managers_df["manager_name"].tolist()[:5] if len(managers_df) >= 5 else managers_df["manager_name"].tolist(),
        help="Choose one or more managers to view their transfer success"
    )
    
    if not selected_managers:
        st.info("Please select at least one manager to view transfer analysis")
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
        
        # Filter for selected managers
        transfer_filtered = transfer_df[transfer_df["manager_name"].isin(selected_managers)]
        
        if not transfer_filtered.empty:
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
            
            # Transfer success by manager
            st.subheader("Transfer Success by Manager")
            manager_transfer_stats = transfer_filtered.groupby("manager_name").agg({
                "was_successful": ["sum", "count"],
                "net_benefit": "sum",
                "transfer_cost": "sum"
            }).round(2)
            
            manager_transfer_stats.columns = ["Successful", "Total", "Total Benefit", "Total Cost"]
            manager_transfer_stats["Success Rate %"] = (
                manager_transfer_stats["Successful"] / manager_transfer_stats["Total"] * 100
            ).round(1)
            manager_transfer_stats["Net Gain"] = (
                manager_transfer_stats["Total Benefit"] - manager_transfer_stats["Total Cost"]
            ).round(1)
            
            manager_transfer_stats = manager_transfer_stats.sort_values("Success Rate %", ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name='Successful',
                    x=manager_transfer_stats.index,
                    y=manager_transfer_stats["Successful"],
                    marker_color='green'
                ))
                fig.add_trace(go.Bar(
                    name='Unsuccessful',
                    x=manager_transfer_stats.index,
                    y=manager_transfer_stats["Total"] - manager_transfer_stats["Successful"],
                    marker_color='red'
                ))
                fig.update_layout(
                    barmode='stack',
                    title="Transfer Success by Manager",
                    xaxis_title="Manager",
                    yaxis_title="Number of Transfers",
                    xaxis_tickangle=-45,
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.dataframe(
                    manager_transfer_stats[["Total", "Success Rate %", "Net Gain"]].style.format({
                        "Success Rate %": "{:.1f}%",
                        "Net Gain": "{:.0f}"
                    }).background_gradient(subset=["Success Rate %"], cmap="RdYlGn"),
                    height=400
                )
            
            # Recent transfers
            st.subheader("Recent Transfers")
            recent_transfers = transfer_filtered.sort_values("gameweek", ascending=False).head(20)
            
            display_transfers = recent_transfers[[
                "manager_name", "gameweek", "player_out_name", "player_in_name",
                "net_benefit", "was_successful"
            ]].copy()
            
            display_transfers.columns = [
                "Manager", "GW", "Player Out", "Player In", "Net Benefit", "Success"
            ]
            
            # Add visual indicators
            display_transfers["Success"] = display_transfers["Success"].apply(
                lambda x: "✅" if x else "❌"
            )
            
            st.dataframe(
                display_transfers.style.format({"Net Benefit": "{:.0f}"}).apply(
                    lambda x: ['background-color: #d4edda' if v == "✅" else 'background-color: #f8d7da' 
                               for v in x], subset=["Success"]
                ),
                use_container_width=True,
                height=400
            )
            
            # Net benefit distribution
            st.subheader("Transfer Net Benefit Distribution")
            
            # Create bins for positive and negative values
            transfer_filtered_copy = transfer_filtered.copy()
            transfer_filtered_copy['benefit_category'] = transfer_filtered_copy['net_benefit'].apply(
                lambda x: 'Positive' if x > 0 else ('Negative' if x < 0 else 'Break-even')
            )
            
            # Create a more sophisticated histogram
            fig = go.Figure()
            
            # Add histogram for negative values
            negative_data = transfer_filtered_copy[transfer_filtered_copy['net_benefit'] < 0]['net_benefit']
            if len(negative_data) > 0:
                fig.add_trace(go.Histogram(
                    x=negative_data,
                    name='Negative',
                    marker_color='rgba(239, 85, 59, 0.7)',
                    nbinsx=20,
                    hovertemplate='Net Benefit: %{x}<br>Count: %{y}<extra></extra>'
                ))
            
            # Add histogram for positive values
            positive_data = transfer_filtered_copy[transfer_filtered_copy['net_benefit'] > 0]['net_benefit']
            if len(positive_data) > 0:
                fig.add_trace(go.Histogram(
                    x=positive_data,
                    name='Positive',
                    marker_color='rgba(0, 250, 146, 0.7)',
                    nbinsx=20,
                    hovertemplate='Net Benefit: %{x}<br>Count: %{y}<extra></extra>'
                ))
            
            # Add break-even line
            fig.add_vline(
                x=0, 
                line_dash="dash", 
                line_color="rgba(255, 255, 255, 0.5)", 
                line_width=2,
                annotation_text="Break-even",
                annotation_position="top"
            )
            
            # Calculate and add median line
            median_benefit = transfer_filtered['net_benefit'].median()
            fig.add_vline(
                x=median_benefit,
                line_dash="dot",
                line_color="rgba(135, 206, 250, 0.8)",
                line_width=2,
                annotation_text=f"Median: {median_benefit:.1f}",
                annotation_position="top"
            )
            
            fig.update_layout(
                title="Distribution of Transfer Net Benefits",
                xaxis_title="Net Benefit (points)",
                yaxis_title="Number of Transfers",
                barmode='overlay',
                showlegend=True,
                height=450,
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0.05)',
                paper_bgcolor='rgba(0,0,0,0)',
            )
            
            fig.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add summary stats below the chart
            col1, col2, col3 = st.columns(3)
            with col1:
                positive_pct = (len(positive_data) / len(transfer_filtered_copy) * 100) if len(transfer_filtered_copy) > 0 else 0
                st.metric("Positive Transfers", f"{len(positive_data)}", f"{positive_pct:.1f}%")
            with col2:
                negative_pct = (len(negative_data) / len(transfer_filtered_copy) * 100) if len(transfer_filtered_copy) > 0 else 0
                st.metric("Negative Transfers", f"{len(negative_data)}", f"{negative_pct:.1f}%")
            with col3:
                st.metric("Median Benefit", f"{median_benefit:.1f} pts")
            
        else:
            st.info("No transfer data available for selected managers")
    else:
        st.warning("⚠️ No transfer data found in CDF. Please run the transfer analysis in the notebook first.")
        st.info("""
        **To enable transfer analysis:**
        1. Open `notebooks/load_fpl_to_cdf.ipynb`
        2. Run the transfer analysis cells to fetch and calculate transfer success metrics
        3. Refresh this dashboard
        """)

