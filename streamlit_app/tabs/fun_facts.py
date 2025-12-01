"""
Fun Facts Tab - Interesting Stats and Category Leaders
"""
import streamlit as st
import pandas as pd


def render(managers_df):
    """Render the Fun Facts tab"""
    st.header("🎉 Fun Facts & Category Leaders")
    st.write("Discover the most interesting stats and see who leads in different categories!")
    
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
    
    # Fun Stats Section
    st.subheader("🤓 Interesting Stats")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔥 The Risk Taker")
        st.caption("_High volatility but crushing it with points_")
        # Manager with highest std dev but also in top 50% of points
        median_points = managers_df["overall_points"].median()
        risk_takers = managers_df[managers_df["overall_points"] >= median_points]
        if not risk_takers.empty:
            top_risk = risk_takers.nlargest(1, "points_std_dev").iloc[0]
            st.markdown(f"**{top_risk['manager_name']}**")
            st.write(f"📊 Std Dev: {top_risk['points_std_dev']:.1f} | 🎯 Points: {int(top_risk['overall_points']):,}")
        
        st.markdown("---")
        
        st.markdown("### 🎯 Best Bargain Hunter")
        st.caption("_Highest value growth with fewest transfers_")
        # Create efficiency metric: value growth per transfer
        managers_df_copy = managers_df.copy()
        managers_df_copy["value_efficiency"] = managers_df_copy.apply(
            lambda x: x["team_value_growth"] / x["total_transfers"] if x["total_transfers"] > 0 else 0,
            axis=1
        )
        if not managers_df_copy.empty:
            # Only consider managers with some value growth and transfers
            bargain_hunters = managers_df_copy[
                (managers_df_copy["team_value_growth"] > 0) & 
                (managers_df_copy["total_transfers"] > 0)
            ]
            if not bargain_hunters.empty:
                best_bargain = bargain_hunters.nlargest(1, "value_efficiency").iloc[0]
                st.markdown(f"**{best_bargain['manager_name']}**")
                st.write(f"💎 £{best_bargain['value_efficiency']:.2f}m per transfer")
                st.write(f"Total: £{best_bargain['team_value_growth']:.1f}m with {int(best_bargain['total_transfers'])} transfers")
        
        st.markdown("---")
        
        st.markdown("### 🔄 Most Active Trader")
        st.caption("_Who's hitting that transfer button?_")
        most_active = managers_df.nlargest(1, "total_transfers").iloc[0]
        st.markdown(f"**{most_active['manager_name']}**")
        st.write(f"🔄 {int(most_active['total_transfers'])} transfers made")
        st.write(f"Points: {int(most_active['overall_points']):,} | Rank: {int(most_active['overall_rank'])}")
    
    with col2:
        st.markdown("### 💎 The Set & Forget Legend")
        st.caption("_Fewest transfers, still performing_")
        # Manager with fewest transfers but still in top 50% of points
        median_points = managers_df["overall_points"].median()
        performers = managers_df[managers_df["overall_points"] >= median_points]
        if not performers.empty:
            set_forget = performers.nsmallest(1, "total_transfers").iloc[0]
            st.markdown(f"**{set_forget['manager_name']}**")
            st.write(f"🔄 Only {int(set_forget['total_transfers'])} transfers | 🎯 {int(set_forget['overall_points']):,} points")
        
        st.markdown("---")
        
        st.markdown("### 📊 Best Points per Transfer")
        st.caption("_Making every move count_")
        # Calculate points per transfer
        managers_df_copy = managers_df.copy()
        managers_df_copy["points_per_transfer"] = managers_df_copy.apply(
            lambda x: x["overall_points"] / x["total_transfers"] if x["total_transfers"] > 0 else 0,
            axis=1
        )
        valid_managers = managers_df_copy[managers_df_copy["total_transfers"] > 0]
        if not valid_managers.empty:
            best_efficiency = valid_managers.nlargest(1, "points_per_transfer").iloc[0]
            st.markdown(f"**{best_efficiency['manager_name']}**")
            st.write(f"⚡ {best_efficiency['points_per_transfer']:.1f} points per transfer")
            st.write(f"Total: {int(best_efficiency['overall_points']):,} points with {int(best_efficiency['total_transfers'])} transfers")
        
        st.markdown("---")
        
        st.markdown("### 🎲 The Wildcard King")
        st.caption("_Most transfers but still in top ranks_")
        # Manager with most transfers who is in top 30% of ranks
        top_30_rank_threshold = managers_df["overall_rank"].quantile(0.3)
        top_rankers = managers_df[managers_df["overall_rank"] <= top_30_rank_threshold]
        if not top_rankers.empty:
            wildcard = top_rankers.nlargest(1, "total_transfers").iloc[0]
            st.markdown(f"**{wildcard['manager_name']}**")
            st.write(f"🔄 {int(wildcard['total_transfers'])} transfers | 🏆 Rank: {int(wildcard['overall_rank'])}")
    
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

