"""
Parallel Ledger Operations Dashboard

Real-time monitoring dashboard for parallel ledger operations, showing posting status,
performance metrics, and operational health across all ledgers.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from utils.parallel_ledger_reporting_service import ParallelLedgerReportingService
from utils.enhanced_auto_posting_service import EnhancedAutoPostingService
from db_config import engine
from sqlalchemy import text
import time

# Page configuration
st.set_page_config(
    page_title="Parallel Ledger Dashboard",
    page_icon="🎛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def main():
    st.title("🎛️ Parallel Ledger Operations Dashboard")
    st.markdown("Real-time monitoring and control center for parallel ledger operations")
    
    # Auto-refresh controls
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.markdown("**Live Dashboard** - Updated every 30 seconds")
    
    with col2:
        auto_refresh = st.checkbox("🔄 Auto Refresh", value=True)
    
    with col3:
        if st.button("🔄 Refresh Now"):
            st.rerun()
    
    with col4:
        st.metric("⏰ Last Updated", datetime.now().strftime("%H:%M:%S"))
    
    # Main dashboard content
    show_system_overview()
    show_real_time_metrics()
    show_ledger_status()
    show_recent_activity()
    show_performance_analytics()
    
    # Auto-refresh mechanism
    if auto_refresh:
        time.sleep(30)
        st.rerun()

def show_system_overview():
    """Show high-level system overview metrics."""
    st.subheader("🌟 System Overview")
    
    try:
        with engine.connect() as conn:
            # Get system metrics
            metrics = {}
            
            # Total ledgers
            metrics['total_ledgers'] = conn.execute(text("SELECT COUNT(*) FROM ledger")).scalar()
            
            # Active parallel posting
            metrics['parallel_posted_today'] = conn.execute(text("""
                SELECT COUNT(*) FROM journalentryheader 
                WHERE parallel_posted = true 
                AND DATE(parallel_posted_at) = CURRENT_DATE
            """)).scalar() or 0
            
            # Success rate today
            success_data = conn.execute(text("""
                SELECT 
                    SUM(parallel_ledger_count) as total_attempts,
                    SUM(parallel_success_count) as total_successes
                FROM journalentryheader 
                WHERE parallel_posted = true 
                AND DATE(parallel_posted_at) = CURRENT_DATE
            """)).fetchone()
            
            if success_data and success_data[0]:
                metrics['success_rate'] = (success_data[1] / success_data[0] * 100)
            else:
                metrics['success_rate'] = 100.0
            
            # Pending approvals
            metrics['pending_approvals'] = conn.execute(text("""
                SELECT COUNT(*) FROM journalentryheader 
                WHERE workflow_status = 'PENDING_APPROVAL'
            """)).scalar() or 0
            
            # Financial volume today
            metrics['financial_volume'] = conn.execute(text("""
                SELECT COALESCE(SUM(source_amounts.total_amount), 0)
                FROM journalentryheader jeh
                LEFT JOIN (
                    SELECT 
                        documentnumber, 
                        companycodeid,
                        SUM(GREATEST(debitamount, creditamount)) as total_amount
                    FROM journalentryline
                    GROUP BY documentnumber, companycodeid
                ) source_amounts ON source_amounts.documentnumber = jeh.documentnumber 
                    AND source_amounts.companycodeid = jeh.companycodeid
                WHERE jeh.parallel_posted = true 
                AND DATE(jeh.parallel_posted_at) = CURRENT_DATE
            """)).scalar() or 0
        
        # Display metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "🏛️ Active Ledgers", 
                metrics['total_ledgers'],
                help="Total number of configured ledgers"
            )
        
        with col2:
            st.metric(
                "📋 Documents Today", 
                metrics['parallel_posted_today'],
                help="Documents processed with parallel posting today"
            )
        
        with col3:
            success_rate = metrics['success_rate']
            delta_color = "normal" if success_rate >= 95 else "inverse"
            st.metric(
                "✅ Success Rate", 
                f"{success_rate:.1f}%",
                delta=f"{success_rate - 100:.1f}%" if success_rate < 100 else "Perfect",
                help="Parallel posting success rate today"
            )
        
        with col4:
            st.metric(
                "⏳ Pending Approvals", 
                metrics['pending_approvals'],
                delta=f"+{metrics['pending_approvals']}" if metrics['pending_approvals'] > 0 else "All Clear",
                delta_color="inverse" if metrics['pending_approvals'] > 0 else "normal",
                help="Documents awaiting approval"
            )
        
        with col5:
            st.metric(
                "💰 Volume Today", 
                f"${metrics['financial_volume']:,.0f}",
                help="Total financial volume processed today"
            )
    
    except Exception as e:
        st.error(f"Error loading system overview: {e}")

def show_real_time_metrics():
    """Show real-time processing metrics."""
    st.subheader("⚡ Real-Time Processing Metrics")
    
    try:
        with engine.connect() as conn:
            # Get hourly processing data for today
            hourly_data = conn.execute(text("""
                SELECT 
                    EXTRACT(HOUR FROM parallel_posted_at) as hour,
                    COUNT(*) as documents_processed,
                    SUM(parallel_ledger_count) as ledger_attempts,
                    SUM(parallel_success_count) as ledger_successes,
                    AVG(parallel_success_count::numeric / NULLIF(parallel_ledger_count, 0) * 100) as success_rate
                FROM journalentryheader 
                WHERE parallel_posted = true 
                AND DATE(parallel_posted_at) = CURRENT_DATE
                GROUP BY EXTRACT(HOUR FROM parallel_posted_at)
                ORDER BY hour
            """)).fetchall()
            
            if hourly_data:
                df = pd.DataFrame(hourly_data, columns=[
                    'Hour', 'Documents', 'Attempts', 'Successes', 'Success Rate'
                ])
                
                # Create dual-axis chart
                fig = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=("Documents Processed by Hour", "Success Rate Trend"),
                    specs=[[{"secondary_y": False}, {"secondary_y": False}]]
                )
                
                # Documents processed
                fig.add_trace(
                    go.Bar(x=df['Hour'], y=df['Documents'], name="Documents", marker_color='lightblue'),
                    row=1, col=1
                )
                
                # Success rate line
                fig.add_trace(
                    go.Scatter(x=df['Hour'], y=df['Success Rate'], name="Success Rate", 
                             mode='lines+markers', line=dict(color='green', width=3)),
                    row=1, col=2
                )
                
                fig.update_layout(
                    height=400,
                    showlegend=False,
                    title_text="Today's Processing Activity"
                )
                
                fig.update_xaxes(title_text="Hour of Day", row=1, col=1)
                fig.update_xaxes(title_text="Hour of Day", row=1, col=2)
                fig.update_yaxes(title_text="Documents", row=1, col=1)
                fig.update_yaxes(title_text="Success Rate (%)", range=[0, 100], row=1, col=2)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 No parallel posting activity today. Waiting for documents to process...")
    
    except Exception as e:
        st.error(f"Error loading real-time metrics: {e}")

def show_ledger_status():
    """Show status of individual ledgers."""
    st.subheader("🏛️ Individual Ledger Status")
    
    try:
        with engine.connect() as conn:
            # Get ledger-specific statistics
            ledger_stats = conn.execute(text("""
                SELECT 
                    l.ledgerid,
                    l.description,
                    l.accounting_principle,
                    l.currencycode,
                    l.isleadingledger,
                    -- Documents created for this ledger
                    COUNT(jeh_parallel.documentnumber) as documents_created,
                    -- Recent activity (last 7 days)
                    COUNT(CASE WHEN jeh_parallel.createdat >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as recent_activity,
                    -- Success rate
                    COUNT(CASE WHEN jeh_parallel.posted_at IS NOT NULL THEN 1 END) as successful_posts,
                    -- Latest activity
                    MAX(jeh_parallel.createdat) as latest_activity
                FROM ledger l
                LEFT JOIN journalentryheader jeh_parallel ON jeh_parallel.documentnumber LIKE '%_' || l.ledgerid
                    AND jeh_parallel.parallel_source_doc IS NOT NULL
                GROUP BY l.ledgerid, l.description, l.accounting_principle, l.currencycode, l.isleadingledger
                ORDER BY l.isleadingledger DESC, l.ledgerid
            """)).fetchall()
            
            # Create ledger status cards
            cols = st.columns(min(len(ledger_stats), 5))
            
            for i, ledger_stat in enumerate(ledger_stats):
                col_idx = i % 5
                with cols[col_idx]:
                    ledger_id = ledger_stat[0]
                    description = ledger_stat[1]
                    accounting_principle = ledger_stat[2]
                    currency = ledger_stat[3]
                    is_leading = ledger_stat[4]
                    docs_created = ledger_stat[5] or 0
                    recent_activity = ledger_stat[6] or 0
                    successful_posts = ledger_stat[7] or 0
                    latest_activity = ledger_stat[8]
                    
                    # Calculate success rate
                    success_rate = (successful_posts / docs_created * 100) if docs_created > 0 else 100
                    
                    # Determine status color
                    if is_leading:
                        status_color = "🟦"  # Blue for leading
                        ledger_type = "Leading"
                    elif recent_activity > 0:
                        status_color = "🟢"  # Green for active
                        ledger_type = "Active"
                    elif docs_created > 0:
                        status_color = "🟡"  # Yellow for inactive but has history
                        ledger_type = "Inactive"
                    else:
                        status_color = "⚪"  # White for unused
                        ledger_type = "Unused"
                    
                    with st.container():
                        st.markdown(f"""
                        **{status_color} {ledger_id}** - {ledger_type}
                        
                        *{description}*
                        
                        📊 **{accounting_principle}** | 💱 **{currency}**
                        
                        📋 Documents: **{docs_created}**
                        
                        ✅ Success Rate: **{success_rate:.1f}%**
                        
                        🕐 Recent (7d): **{recent_activity}**
                        """)
                        
                        if latest_activity:
                            st.caption(f"Last activity: {latest_activity.strftime('%Y-%m-%d %H:%M')}")
                        else:
                            st.caption("No recent activity")
        
        # Ledger performance comparison chart
        if ledger_stats:
            st.subheader("📊 Ledger Performance Comparison")
            
            chart_data = []
            for stat in ledger_stats:
                if not stat[4]:  # Non-leading ledgers only
                    docs_created = stat[5] or 0
                    successful_posts = stat[7] or 0
                    success_rate = (successful_posts / docs_created * 100) if docs_created > 0 else 100
                    
                    chart_data.append({
                        "Ledger": f"{stat[0]}\n({stat[2]})",
                        "Documents Created": docs_created,
                        "Success Rate": success_rate,
                        "Recent Activity": stat[6] or 0
                    })
            
            if chart_data:
                chart_df = pd.DataFrame(chart_data)
                
                fig = px.scatter(
                    chart_df,
                    x="Documents Created",
                    y="Success Rate",
                    size="Recent Activity",
                    hover_name="Ledger",
                    title="Ledger Performance: Documents Created vs Success Rate",
                    labels={"Recent Activity": "Recent Activity (7 days)"}
                )
                
                fig.update_yaxis(range=[0, 105])
                fig.add_hline(y=95, line_dash="dash", line_color="red", 
                             annotation_text="95% Success Target")
                
                st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error loading ledger status: {e}")

def show_recent_activity():
    """Show recent parallel posting activity."""
    st.subheader("📋 Recent Parallel Posting Activity")
    
    try:
        with engine.connect() as conn:
            # Get recent parallel posting activity
            recent_activity = conn.execute(text("""
                SELECT 
                    jeh.documentnumber as source_document,
                    jeh.parallel_posted_at,
                    jeh.parallel_posted_by,
                    jeh.parallel_ledger_count,
                    jeh.parallel_success_count,
                    jeh.description,
                    -- Source amount
                    COALESCE(source_amounts.total_amount, 0) as source_amount,
                    -- Success rate
                    CASE WHEN jeh.parallel_ledger_count > 0 
                    THEN jeh.parallel_success_count::numeric / jeh.parallel_ledger_count * 100 
                    ELSE 0 END as success_rate
                FROM journalentryheader jeh
                LEFT JOIN (
                    SELECT 
                        documentnumber, 
                        companycodeid,
                        SUM(GREATEST(debitamount, creditamount)) as total_amount
                    FROM journalentryline
                    GROUP BY documentnumber, companycodeid
                ) source_amounts ON source_amounts.documentnumber = jeh.documentnumber 
                    AND source_amounts.companycodeid = jeh.companycodeid
                WHERE jeh.parallel_posted = true
                ORDER BY jeh.parallel_posted_at DESC
                LIMIT 20
            """)).fetchall()
            
            if recent_activity:
                # Convert to DataFrame for display
                df = pd.DataFrame(recent_activity, columns=[
                    'Document', 'Posted At', 'Posted By', 'Target Ledgers', 
                    'Successful Ledgers', 'Description', 'Amount', 'Success Rate'
                ])
                
                # Format for display
                df['Posted At'] = pd.to_datetime(df['Posted At']).dt.strftime('%Y-%m-%d %H:%M:%S')
                df['Amount'] = df['Amount'].apply(lambda x: f"${x:,.2f}")
                df['Success Rate'] = df['Success Rate'].apply(lambda x: f"{x:.1f}%")
                df['Ledger Status'] = df.apply(lambda row: 
                    f"{row['Successful Ledgers']}/{row['Target Ledgers']}", axis=1)
                
                # Add status indicators
                def get_status_indicator(row):
                    if row['Successful Ledgers'] == row['Target Ledgers']:
                        return "✅ Complete"
                    elif row['Successful Ledgers'] > 0:
                        return "⚠️ Partial"
                    else:
                        return "❌ Failed"
                
                df['Status'] = df.apply(get_status_indicator, axis=1)
                
                # Display table
                display_df = df[['Document', 'Posted At', 'Status', 'Ledger Status', 
                               'Amount', 'Success Rate', 'Posted By']].copy()
                
                st.dataframe(display_df, use_container_width=True)
                
                # Activity timeline chart
                timeline_df = df.copy()
                timeline_df['Posted At'] = pd.to_datetime(timeline_df['Posted At'])
                timeline_df['Hour'] = timeline_df['Posted At'].dt.floor('H')
                
                hourly_summary = timeline_df.groupby('Hour').agg({
                    'Document': 'count',
                    'Success Rate': 'mean'
                }).reset_index()
                
                if len(hourly_summary) > 1:
                    fig = px.line(
                        hourly_summary,
                        x='Hour',
                        y='Document',
                        title="Recent Activity Timeline",
                        markers=True
                    )
                    
                    fig.update_layout(
                        xaxis_title="Time",
                        yaxis_title="Documents Processed"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📊 No recent parallel posting activity found.")
    
    except Exception as e:
        st.error(f"Error loading recent activity: {e}")

def show_performance_analytics():
    """Show performance analytics and trends."""
    st.subheader("📈 Performance Analytics")
    
    try:
        with engine.connect() as conn:
            # Get daily performance data for the last 30 days
            daily_performance = conn.execute(text("""
                SELECT 
                    DATE(parallel_posted_at) as posting_date,
                    COUNT(*) as documents_processed,
                    SUM(parallel_ledger_count) as total_attempts,
                    SUM(parallel_success_count) as total_successes,
                    AVG(parallel_success_count::numeric / NULLIF(parallel_ledger_count, 0) * 100) as avg_success_rate,
                    SUM(COALESCE(source_amounts.total_amount, 0)) as daily_volume
                FROM journalentryheader jeh
                LEFT JOIN (
                    SELECT 
                        documentnumber, 
                        companycodeid,
                        SUM(GREATEST(debitamount, creditamount)) as total_amount
                    FROM journalentryline
                    GROUP BY documentnumber, companycodeid
                ) source_amounts ON source_amounts.documentnumber = jeh.documentnumber 
                    AND source_amounts.companycodeid = jeh.companycodeid
                WHERE jeh.parallel_posted = true 
                AND jeh.parallel_posted_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(parallel_posted_at)
                ORDER BY posting_date DESC
                LIMIT 30
            """)).fetchall()
            
            if daily_performance:
                perf_df = pd.DataFrame(daily_performance, columns=[
                    'Date', 'Documents', 'Attempts', 'Successes', 'Success Rate', 'Volume'
                ])
                
                # Create performance dashboard
                col1, col2 = st.columns(2)
                
                with col1:
                    # Document processing trend
                    fig1 = px.line(
                        perf_df,
                        x='Date',
                        y='Documents',
                        title="Daily Document Processing Trend",
                        markers=True
                    )
                    fig1.update_layout(xaxis_title="Date", yaxis_title="Documents Processed")
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # Success rate trend
                    fig2 = px.line(
                        perf_df,
                        x='Date',
                        y='Success Rate',
                        title="Success Rate Trend",
                        markers=True,
                        color_discrete_sequence=['green']
                    )
                    fig2.add_hline(y=95, line_dash="dash", line_color="red", 
                                  annotation_text="95% Target")
                    fig2.update_layout(
                        xaxis_title="Date", 
                        yaxis_title="Success Rate (%)",
                        yaxis=dict(range=[0, 100])
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Volume analysis
                if perf_df['Volume'].sum() > 0:
                    fig3 = px.bar(
                        perf_df.head(10),  # Last 10 days
                        x='Date',
                        y='Volume',
                        title="Daily Financial Volume Processed (Last 10 Days)"
                    )
                    fig3.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Volume ($)"
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                
                # Performance summary statistics
                st.subheader("📊 30-Day Performance Summary")
                
                total_docs = perf_df['Documents'].sum()
                total_attempts = perf_df['Attempts'].sum()
                total_successes = perf_df['Successes'].sum()
                overall_success_rate = (total_successes / total_attempts * 100) if total_attempts > 0 else 100
                total_volume = perf_df['Volume'].sum()
                avg_daily_docs = perf_df['Documents'].mean()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Documents", f"{total_docs:,}")
                    st.metric("Avg Daily Documents", f"{avg_daily_docs:.1f}")
                
                with col2:
                    st.metric("Total Ledger Operations", f"{total_attempts:,}")
                    st.metric("Successful Operations", f"{total_successes:,}")
                
                with col3:
                    st.metric("Overall Success Rate", f"{overall_success_rate:.2f}%")
                    best_day = perf_df.loc[perf_df['Success Rate'].idxmax()]
                    st.metric("Best Day", f"{best_day['Success Rate']:.1f}% ({best_day['Date']})")
                
                with col4:
                    st.metric("Total Volume", f"${total_volume:,.0f}")
                    st.metric("Avg Daily Volume", f"${total_volume/len(perf_df):,.0f}")
                
            else:
                st.info("📊 No performance data available for the last 30 days.")
    
    except Exception as e:
        st.error(f"Error loading performance analytics: {e}")

if __name__ == "__main__":
    main()