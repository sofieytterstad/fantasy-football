"""
Fun Facts Tab - Interesting Stats and Category Leaders
"""
import streamlit as st
import pandas as pd


def render(managers_df, client=None, fetch_transfer_data=None, fetch_players=None):
    """Render the Fun Facts tab"""
    st.header("🎉 Fun Facts & Category Leaders")
    st.write("Discover the most interesting stats and see who leads in different categories!")
    
    # Fetch transfer data if available
    transfers_df = None
    if client and fetch_transfer_data:
        try:
            transfers_df = fetch_transfer_data(client)
            # If we have transfers but no player names, add them
            if not transfers_df.empty and 'player_out_name' not in transfers_df.columns and fetch_players:
                players_dict = fetch_players(client)
                if players_dict:
                    transfers_df['player_out_name'] = transfers_df['player_out_id'].apply(
                        lambda x: players_dict.get(x, {}).get('web_name', 'Unknown')
                    )
                    transfers_df['player_in_name'] = transfers_df['player_in_id'].apply(
                        lambda x: players_dict.get(x, {}).get('web_name', 'Unknown')
                    )
        except:
            pass
    
    # Category Leaders (keeping the existing ones)
    st.subheader("🏆 Category Leaders")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("**🎯 Most Consistent**")
        st.caption("_High avg, low volatility_")
        top_consistent = managers_df.nlargest(5, "consistency_score")[["manager_name", "consistency_score"]]
        for idx, row in top_consistent.iterrows():
            st.write(f"**{row['manager_name']}:** {row['consistency_score']:.1f}")
    
    with col2:
        st.markdown("**📈 Best Value Growth**")
        st.caption("_Team value gained_")
        top_growth = managers_df.nlargest(5, "team_value_growth")[["manager_name", "team_value_growth"]]
        for idx, row in top_growth.iterrows():
            st.write(f"**{row['manager_name']}:** £{row['team_value_growth']:.1f}m")
    
    with col3:
        st.markdown("**⚡ Highest Avg PPW**")
        st.caption("_Average points per week_")
        top_avg = managers_df.nlargest(5, "avg_points_per_week")[["manager_name", "avg_points_per_week"]]
        for idx, row in top_avg.iterrows():
            st.write(f"**{row['manager_name']}:** {row['avg_points_per_week']:.1f}")
    
    with col4:
        st.markdown("**💰 Most Valuable Squad**")
        st.caption("_Current team value_")
        top_value = managers_df.nlargest(5, "team_value")[["manager_name", "team_value"]]
        for idx, row in top_value.iterrows():
            st.write(f"**{row['manager_name']}:** £{row['team_value']:.1f}m")
    
    st.markdown("---")
    
    # Best and Worst Single Transfer - Side by Side
    st.subheader("🔄 Transfer Highlights")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 Best Single Transfer")
        st.caption("_Highest net benefit from one move_")
        if transfers_df is not None and not transfers_df.empty:
            best_single = transfers_df.nlargest(1, 'net_benefit').iloc[0]
            
            manager_id_str = best_single['manager_id']
            entry_id = manager_id_str.replace("manager_", "") if isinstance(manager_id_str, str) else manager_id_str
            try:
                entry_id = int(entry_id)
                manager_info = managers_df[managers_df['entry_id'] == entry_id]
                manager_name = manager_info['manager_name'].iloc[0] if not manager_info.empty else f"Manager {entry_id}"
            except:
                manager_name = f"Manager {manager_id_str}"
            
            st.markdown(f"**{manager_name}**")
            
            if 'player_out_name' in best_single and 'player_in_name' in best_single:
                st.write(f"🔄 {best_single['player_out_name']} → {best_single['player_in_name']}")
            else:
                st.write(f"🔄 Player transfer in GW{int(best_single['gameweek'])}")
            
            st.write(f"💰 Net gain: **+{best_single['net_benefit']:.1f} pts**")
        else:
            st.info("Transfer data not available")
    
    with col2:
        st.markdown("### 💸 Worst Single Transfer")
        st.caption("_Biggest regret of the season_")
        if transfers_df is not None and not transfers_df.empty:
            worst_single = transfers_df.nsmallest(1, 'net_benefit').iloc[0]
            
            manager_id_str = worst_single['manager_id']
            entry_id = manager_id_str.replace("manager_", "") if isinstance(manager_id_str, str) else manager_id_str
            try:
                entry_id = int(entry_id)
                manager_info = managers_df[managers_df['entry_id'] == entry_id]
                manager_name = manager_info['manager_name'].iloc[0] if not manager_info.empty else f"Manager {entry_id}"
            except:
                manager_name = f"Manager {manager_id_str}"
            
            st.markdown(f"**{manager_name}**")
            
            if 'player_out_name' in worst_single and 'player_in_name' in worst_single:
                st.write(f"🔄 {worst_single['player_out_name']} → {worst_single['player_in_name']}")
            else:
                st.write(f"🔄 Player transfer in GW{int(worst_single['gameweek'])}")
            
            st.write(f"💸 Net loss: **{worst_single['net_benefit']:.1f} pts**")
        else:
            st.info("Transfer data not available")
    
    st.markdown("---")
    
    # Wildcard King and Most Active Trader - Side by Side
    st.subheader("🎲 Transfer Activity")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎲 The Wildcard King")
        st.caption("_Most transfers but still in top ranks_")
        top_30_rank_threshold = managers_df["overall_rank"].quantile(0.3)
        top_rankers = managers_df[managers_df["overall_rank"] <= top_30_rank_threshold]
        if not top_rankers.empty:
            wildcard = top_rankers.nlargest(1, "total_transfers").iloc[0]
            st.markdown(f"**{wildcard['manager_name']}**")
            st.write(f"🔄 {int(wildcard['total_transfers'])} transfers | 🏆 Rank: {int(wildcard['overall_rank'])}")
        else:
            st.info("No managers in top 30% with high transfers")
    
    with col2:
        st.markdown("### 🔄 Most Active Trader")
        st.caption("_Who's hitting that transfer button?_")
        most_active = managers_df.nlargest(1, "total_transfers").iloc[0]
        st.markdown(f"**{most_active['manager_name']}**")
        st.write(f"🔄 {int(most_active['total_transfers'])} transfers made")
        st.write(f"Points: {int(most_active['overall_points']):,} | Rank: {int(most_active['overall_rank'])}")
    
    st.markdown("---")
    
    # Manager Types - Side by Side
    st.subheader("🤓 Manager Types")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔥 The Risk Taker")
        st.caption("_High volatility but crushing it_")
        median_points = managers_df["overall_points"].median()
        risk_takers = managers_df[managers_df["overall_points"] >= median_points]
        if not risk_takers.empty:
            top_risk = risk_takers.nlargest(1, "points_std_dev").iloc[0]
            st.markdown(f"**{top_risk['manager_name']}**")
            st.write(f"📊 Std Dev: {top_risk['points_std_dev']:.1f}")
            st.write(f"🎯 Points: {int(top_risk['overall_points']):,}")
        else:
            st.info("No data available")
    
    with col2:
        st.markdown("### 💎 Set & Forget Legend")
        st.caption("_Fewest transfers, still performing_")
        median_points = managers_df["overall_points"].median()
        performers = managers_df[managers_df["overall_points"] >= median_points]
        if not performers.empty:
            set_forget = performers.nsmallest(1, "total_transfers").iloc[0]
            st.markdown(f"**{set_forget['manager_name']}**")
            st.write(f"🔄 {int(set_forget['total_transfers'])} transfers")
            st.write(f"🎯 {int(set_forget['overall_points']):,} points")
        else:
            st.info("No data available")
    
    st.markdown("---")
    
    # Comparison Stats
    st.subheader("📈 League Averages")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_points = managers_df["overall_points"].mean()
        st.metric("Avg Points", f"{int(avg_points):,}")
    
    with col2:
        avg_ppw = managers_df["avg_points_per_week"].mean()
        st.metric("Avg PPW", f"{avg_ppw:.1f}")
    
    with col3:
        avg_transfers = managers_df["total_transfers"].mean()
        st.metric("Avg Transfers", f"{avg_transfers:.1f}")
    
    with col4:
        avg_value_growth = managers_df["team_value_growth"].mean()
        st.metric("Avg Value Growth", f"£{avg_value_growth:.1f}m")

