"""
🔄 Enterprise Workflow Dashboard
Real-time monitoring and analytics for journal entry approval workflows
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta, date
import time
from typing import Dict, List, Any
import numpy as np

# Import workflow engine and database
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.workflow_engine import WorkflowEngine
from db_config import engine
from sqlalchemy import text


class WorkflowDashboard:
    """Enterprise workflow dashboard with analytics and monitoring"""
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
        
    def get_workflow_statistics(self, days_back: int = 30, status_filter: str = "ALL") -> Dict:
        """Get comprehensive workflow statistics"""
        try:
            with engine.connect() as conn:
                # Base query with filters
                where_clause = "WHERE wi.created_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'"
                params = {"days_back": days_back}
                
                if status_filter != "ALL":
                    where_clause += " AND wi.status = :status"
                    params["status"] = status_filter
                
                # Overall statistics
                stats_query = f"""
                    SELECT 
                        COUNT(*) as total_workflows,
                        COUNT(CASE WHEN wi.status = 'PENDING' THEN 1 END) as pending_count,
                        COUNT(CASE WHEN wi.status = 'APPROVED' THEN 1 END) as approved_count,
                        COUNT(CASE WHEN wi.status = 'REJECTED' THEN 1 END) as rejected_count,
                        COUNT(CASE WHEN ast.time_limit < CURRENT_TIMESTAMP AND wi.status = 'PENDING' THEN 1 END) as overdue_count,
                        AVG(EXTRACT(EPOCH FROM (COALESCE(wi.completed_at, CURRENT_TIMESTAMP) - wi.created_at))/3600) as avg_completion_hours,
                        SUM(CASE WHEN wi.status = 'APPROVED' THEN 
                            COALESCE((SELECT SUM(jel.debitamount) 
                                    FROM journalentryline jel 
                                    WHERE jel.documentnumber = wi.document_number 
                                    AND jel.companycodeid = wi.company_code
                                    AND jel.debitamount > 0), 0) 
                            ELSE 0 END) as total_approved_amount,
                        MIN(wi.created_at) as earliest_workflow,
                        MAX(wi.created_at) as latest_workflow
                    FROM workflow_instances wi
                    LEFT JOIN approval_steps ast ON ast.workflow_instance_id = wi.id AND ast.action = 'PENDING'
                    {where_clause}
                """
                
                stats = conn.execute(text(stats_query), params).fetchone()
                
                # Daily workflow trends
                trend_query = f"""
                    SELECT 
                        DATE(wi.created_at) as workflow_date,
                        COUNT(*) as daily_count,
                        COUNT(CASE WHEN wi.status = 'APPROVED' THEN 1 END) as daily_approved,
                        COUNT(CASE WHEN wi.status = 'REJECTED' THEN 1 END) as daily_rejected,
                        COUNT(CASE WHEN wi.status = 'PENDING' THEN 1 END) as daily_pending,
                        SUM(COALESCE((SELECT SUM(jel.debitamount) 
                                    FROM journalentryline jel 
                                    WHERE jel.documentnumber = wi.document_number 
                                    AND jel.companycodeid = wi.company_code
                                    AND jel.debitamount > 0), 0)) as daily_amount
                    FROM workflow_instances wi
                    {where_clause}
                    GROUP BY DATE(wi.created_at)
                    ORDER BY workflow_date DESC
                    LIMIT 30
                """
                
                trends = conn.execute(text(trend_query), params).fetchall()
                
                # Approval level breakdown
                level_query = f"""
                    SELECT 
                        al.level_name,
                        al.level_order,
                        COUNT(*) as count,
                        COUNT(CASE WHEN wi.status = 'PENDING' THEN 1 END) as pending,
                        COUNT(CASE WHEN wi.status = 'APPROVED' THEN 1 END) as approved,
                        COUNT(CASE WHEN wi.status = 'REJECTED' THEN 1 END) as rejected,
                        AVG(EXTRACT(EPOCH FROM (COALESCE(wi.completed_at, CURRENT_TIMESTAMP) - wi.created_at))/3600) as avg_hours
                    FROM workflow_instances wi
                    JOIN approval_levels al ON al.id = wi.required_approval_level_id
                    {where_clause}
                    GROUP BY al.level_name, al.level_order
                    ORDER BY al.level_order
                """
                
                levels = conn.execute(text(level_query), params).fetchall()
                
                # Top approvers
                approver_query = f"""
                    SELECT 
                        ast.action_by,
                        COUNT(*) as total_actions,
                        COUNT(CASE WHEN ast.action = 'APPROVED' THEN 1 END) as approved_count,
                        COUNT(CASE WHEN ast.action = 'REJECTED' THEN 1 END) as rejected_count,
                        AVG(EXTRACT(EPOCH FROM (ast.action_at - wi.created_at))/3600) as avg_response_hours
                    FROM approval_steps ast
                    JOIN workflow_instances wi ON wi.id = ast.workflow_instance_id
                    WHERE ast.action IN ('APPROVED', 'REJECTED')
                    AND ast.action_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'
                    GROUP BY ast.action_by
                    ORDER BY total_actions DESC
                    LIMIT 10
                """
                
                approvers = conn.execute(text(approver_query), {"days_back": days_back}).fetchall()
                
                # Company breakdown
                company_query = f"""
                    SELECT 
                        wi.company_code,
                        COUNT(*) as total_workflows,
                        COUNT(CASE WHEN wi.status = 'PENDING' THEN 1 END) as pending,
                        COUNT(CASE WHEN wi.status = 'APPROVED' THEN 1 END) as approved,
                        COUNT(CASE WHEN wi.status = 'REJECTED' THEN 1 END) as rejected,
                        SUM(COALESCE((SELECT SUM(jel.debitamount) 
                                    FROM journalentryline jel 
                                    WHERE jel.documentnumber = wi.document_number 
                                    AND jel.companycodeid = wi.company_code
                                    AND jel.debitamount > 0), 0)) as total_amount
                    FROM workflow_instances wi
                    {where_clause}
                    GROUP BY wi.company_code
                    ORDER BY total_workflows DESC
                """
                
                companies = conn.execute(text(company_query), params).fetchall()
                
                return {
                    "overall": {
                        "total_workflows": stats[0] or 0,
                        "pending_count": stats[1] or 0,
                        "approved_count": stats[2] or 0,
                        "rejected_count": stats[3] or 0,
                        "overdue_count": stats[4] or 0,
                        "avg_completion_hours": float(stats[5]) if stats[5] else 0,
                        "total_approved_amount": float(stats[6]) if stats[6] else 0,
                        "earliest_workflow": stats[7],
                        "latest_workflow": stats[8]
                    },
                    "daily_trends": [
                        {
                            "date": row[0],
                            "total": row[1],
                            "approved": row[2],
                            "rejected": row[3],
                            "pending": row[4],
                            "amount": float(row[5]) if row[5] else 0
                        } for row in trends
                    ],
                    "approval_levels": [
                        {
                            "level_name": row[0],
                            "level_order": row[1],
                            "total": row[2],
                            "pending": row[3],
                            "approved": row[4],
                            "rejected": row[5],
                            "avg_hours": float(row[6]) if row[6] else 0
                        } for row in levels
                    ],
                    "top_approvers": [
                        {
                            "approver": row[0],
                            "total_actions": row[1],
                            "approved": row[2],
                            "rejected": row[3],
                            "avg_response_hours": float(row[4]) if row[4] else 0
                        } for row in approvers
                    ],
                    "companies": [
                        {
                            "company_code": row[0],
                            "total": row[1],
                            "pending": row[2],
                            "approved": row[3],
                            "rejected": row[4],
                            "total_amount": float(row[5]) if row[5] else 0
                        } for row in companies
                    ]
                }
                
        except Exception as e:
            st.error(f"Error getting workflow statistics: {e}")
            return {"overall": {}, "daily_trends": [], "approval_levels": [], "top_approvers": [], "companies": []}
    
    def get_detailed_workflows(self, status_filter: str = "ALL", days_back: int = 30, 
                              company_filter: str = "ALL", approver_filter: str = "ALL",
                              amount_min: float = 0, amount_max: float = 999999999) -> List[Dict]:
        """Get detailed workflow list with filters"""
        try:
            with engine.connect() as conn:
                where_conditions = ["wi.created_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'"]
                params = {"days_back": days_back, "amount_min": amount_min, "amount_max": amount_max}
                
                if status_filter != "ALL":
                    where_conditions.append("wi.status = :status")
                    params["status"] = status_filter
                
                if company_filter != "ALL":
                    where_conditions.append("wi.company_code = :company")
                    params["company"] = company_filter
                
                if approver_filter != "ALL":
                    where_conditions.append("ast.assigned_to = :approver")
                    params["approver"] = approver_filter
                
                where_clause = "WHERE " + " AND ".join(where_conditions)
                
                query = f"""
                    SELECT 
                        wi.id as workflow_id,
                        wi.document_number,
                        wi.company_code,
                        wi.status,
                        wi.created_at,
                        wi.completed_at,
                        jeh.reference,
                        jeh.createdby as created_by,
                        jeh.submitted_for_approval_at,
                        jeh.approved_by,
                        jeh.approved_at,
                        jeh.rejected_by,
                        jeh.rejected_at,
                        jeh.rejection_reason,
                        al.level_name as approval_level,
                        ast.assigned_to as current_approver,
                        ast.action as approver_action,
                        ast.action_at,
                        ast.comments as approver_comments,
                        ast.time_limit,
                        COALESCE(SUM(CASE WHEN jel.debitamount > 0 THEN jel.debitamount ELSE 0 END), 0) as total_amount,
                        CASE 
                            WHEN ast.time_limit < CURRENT_TIMESTAMP AND wi.status = 'PENDING' THEN true 
                            ELSE false 
                        END as is_overdue,
                        EXTRACT(EPOCH FROM (COALESCE(wi.completed_at, CURRENT_TIMESTAMP) - wi.created_at))/3600 as duration_hours
                    FROM workflow_instances wi
                    JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number 
                        AND jeh.companycodeid = wi.company_code
                    LEFT JOIN approval_levels al ON al.id = wi.required_approval_level_id
                    LEFT JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                    LEFT JOIN journalentryline jel ON jel.documentnumber = wi.document_number 
                        AND jel.companycodeid = wi.company_code
                    {where_clause}
                    GROUP BY wi.id, wi.document_number, wi.company_code, wi.status, wi.created_at,
                             wi.completed_at, jeh.reference, jeh.createdby, jeh.submitted_for_approval_at,
                             jeh.approved_by, jeh.approved_at, jeh.rejected_by, jeh.rejected_at,
                             jeh.rejection_reason, al.level_name, ast.assigned_to, ast.action,
                             ast.action_at, ast.comments, ast.time_limit
                    HAVING COALESCE(SUM(CASE WHEN jel.debitamount > 0 THEN jel.debitamount ELSE 0 END), 0) BETWEEN :amount_min AND :amount_max
                    ORDER BY wi.created_at DESC
                    LIMIT 500
                """
                
                result = conn.execute(text(query), params)
                
                workflows = []
                for row in result:
                    workflows.append({
                        "workflow_id": row[0],
                        "document_number": row[1],
                        "company_code": row[2],
                        "status": row[3],
                        "created_at": row[4],
                        "completed_at": row[5],
                        "reference": row[6],
                        "created_by": row[7],
                        "submitted_at": row[8],
                        "approved_by": row[9],
                        "approved_at": row[10],
                        "rejected_by": row[11],
                        "rejected_at": row[12],
                        "rejection_reason": row[13],
                        "approval_level": row[14],
                        "current_approver": row[15],
                        "approver_action": row[16],
                        "action_at": row[17],
                        "approver_comments": row[18],
                        "time_limit": row[19],
                        "total_amount": float(row[20]),
                        "is_overdue": row[21],
                        "duration_hours": float(row[22]) if row[22] else 0
                    })
                
                return workflows
                
        except Exception as e:
            st.error(f"Error getting detailed workflows: {e}")
            return []
    
    def render_dashboard(self):
        """Render the complete enterprise workflow dashboard"""
        st.set_page_config(
            page_title="🔄 Workflow Dashboard",
            page_icon="🔄",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Header
        st.title("🔄 Enterprise Workflow Dashboard")
        st.markdown("### Real-time monitoring and analytics for journal entry approval workflows")
        
        # Sidebar filters
        with st.sidebar:
            st.header("📊 Dashboard Filters")
            
            # Time range filter
            days_back = st.selectbox(
                "📅 Time Range",
                [7, 14, 30, 60, 90, 180, 365],
                index=2,  # Default to 30 days
                format_func=lambda x: f"Last {x} days"
            )
            
            # Status filter
            status_filter = st.selectbox(
                "🔄 Workflow Status",
                ["ALL", "PENDING", "APPROVED", "REJECTED"],
                index=0
            )
            
            # Company filter
            companies = self.get_available_companies()
            company_filter = st.selectbox(
                "🏢 Company",
                ["ALL"] + companies,
                index=0
            )
            
            # Approver filter
            approvers = self.get_available_approvers()
            approver_filter = st.selectbox(
                "👤 Current Approver",
                ["ALL"] + approvers,
                index=0
            )
            
            # Amount range filter
            st.subheader("💰 Amount Range")
            amount_range = st.slider(
                "Transaction Amount ($)",
                min_value=0,
                max_value=50000000,
                value=(0, 50000000),
                step=10000,
                format="$%d"
            )
            
            # Auto-refresh option
            auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
            
            if st.button("🔍 Apply Filters") or auto_refresh:
                st.rerun()
        
        # Get data
        stats = self.get_workflow_statistics(days_back, status_filter)
        workflows = self.get_detailed_workflows(
            status_filter, days_back, company_filter, approver_filter,
            amount_range[0], amount_range[1]
        )
        
        # Auto-refresh logic
        if auto_refresh:
            time.sleep(30)
            st.rerun()
        
        # Main dashboard content
        self.render_overview_metrics(stats["overall"])
        self.render_analytics_charts(stats)
        self.render_workflow_table(workflows)
        self.render_performance_insights(stats, workflows)
    
    def get_available_companies(self) -> List[str]:
        """Get list of available companies"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT DISTINCT companycodeid FROM companycode ORDER BY companycodeid"))
                return [row[0] for row in result]
        except:
            return ["1000", "2000"]
    
    def get_available_approvers(self) -> List[str]:
        """Get list of available approvers"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT assigned_to 
                    FROM approval_steps 
                    WHERE assigned_to IS NOT NULL 
                    ORDER BY assigned_to
                """))
                return [row[0] for row in result]
        except:
            return ["admin", "supervisor1", "manager1", "director1"]
    
    def render_overview_metrics(self, stats: Dict):
        """Render overview metrics cards"""
        st.subheader("📊 Overview Metrics")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "Total Workflows",
                stats.get("total_workflows", 0),
                delta=None
            )
        
        with col2:
            pending = stats.get("pending_count", 0)
            st.metric(
                "⏳ Pending",
                pending,
                delta=None,
                delta_color="inverse" if pending > 0 else "normal"
            )
        
        with col3:
            approved = stats.get("approved_count", 0)
            st.metric(
                "✅ Approved",
                approved,
                delta=None,
                delta_color="normal"
            )
        
        with col4:
            rejected = stats.get("rejected_count", 0)
            st.metric(
                "❌ Rejected",
                rejected,
                delta=None,
                delta_color="inverse" if rejected > 0 else "normal"
            )
        
        with col5:
            overdue = stats.get("overdue_count", 0)
            st.metric(
                "🚨 Overdue",
                overdue,
                delta=None,
                delta_color="inverse" if overdue > 0 else "normal"
            )
        
        # Additional metrics row
        col6, col7, col8, col9 = st.columns(4)
        
        with col6:
            avg_hours = stats.get("avg_completion_hours", 0)
            st.metric(
                "⏱️ Avg Completion",
                f"{avg_hours:.1f}h",
                delta=None
            )
        
        with col7:
            approved_amount = stats.get("total_approved_amount", 0)
            st.metric(
                "💰 Approved Amount",
                f"${approved_amount:,.0f}",
                delta=None
            )
        
        with col8:
            total = stats.get("total_workflows", 1)
            approved = stats.get("approved_count", 0)
            approval_rate = (approved / total) * 100 if total > 0 else 0
            st.metric(
                "📈 Approval Rate",
                f"{approval_rate:.1f}%",
                delta=None
            )
        
        with col9:
            st.metric(
                "🔄 Active Period",
                f"{(stats.get('latest_workflow', datetime.now()) - stats.get('earliest_workflow', datetime.now())).days} days" if stats.get('earliest_workflow') else "N/A",
                delta=None
            )
    
    def render_analytics_charts(self, stats: Dict):
        """Render analytics charts"""
        st.subheader("📈 Analytics & Trends")
        
        # Create tabs for different chart categories
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Status Distribution", "📈 Daily Trends", "🎯 Approval Levels", "👥 Approver Performance"])
        
        with tab1:
            self.render_status_charts(stats)
        
        with tab2:
            self.render_trend_charts(stats)
        
        with tab3:
            self.render_approval_level_charts(stats)
        
        with tab4:
            self.render_approver_charts(stats)
    
    def render_status_charts(self, stats: Dict):
        """Render status distribution charts"""
        col1, col2 = st.columns(2)
        
        with col1:
            # Status pie chart
            overall = stats["overall"]
            if overall.get("total_workflows", 0) > 0:
                status_data = {
                    "Status": ["Pending", "Approved", "Rejected"],
                    "Count": [
                        overall.get("pending_count", 0),
                        overall.get("approved_count", 0),
                        overall.get("rejected_count", 0)
                    ],
                    "Color": ["#ff9999", "#66b3ff", "#99ff99"]
                }
                
                fig = px.pie(
                    values=status_data["Count"],
                    names=status_data["Status"],
                    title="Workflow Status Distribution",
                    color_discrete_sequence=["#ff6b6b", "#4ecdc4", "#45b7d1"]
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No workflows found for the selected period")
        
        with col2:
            # Company distribution
            companies = stats.get("companies", [])
            if companies:
                company_df = pd.DataFrame(companies)
                fig = px.bar(
                    company_df,
                    x="company_code",
                    y="total",
                    title="Workflows by Company",
                    color="total",
                    color_continuous_scale="Blues"
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No company data available")
    
    def render_trend_charts(self, stats: Dict):
        """Render trend charts"""
        trends = stats.get("daily_trends", [])
        if trends:
            trend_df = pd.DataFrame(trends)
            trend_df['date'] = pd.to_datetime(trend_df['date'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Daily workflow volume
                fig = px.line(
                    trend_df,
                    x="date",
                    y="total",
                    title="Daily Workflow Volume",
                    markers=True
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Daily workflow amounts
                fig = px.bar(
                    trend_df,
                    x="date",
                    y="amount",
                    title="Daily Transaction Amounts",
                    color="amount",
                    color_continuous_scale="Greens"
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Stacked area chart for status trends
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend_df['date'], y=trend_df['approved'],
                mode='lines', stackgroup='one', name='Approved',
                fill='tonexty', fillcolor='rgba(76, 175, 80, 0.3)'
            ))
            fig.add_trace(go.Scatter(
                x=trend_df['date'], y=trend_df['rejected'],
                mode='lines', stackgroup='one', name='Rejected',
                fill='tonexty', fillcolor='rgba(244, 67, 54, 0.3)'
            ))
            fig.add_trace(go.Scatter(
                x=trend_df['date'], y=trend_df['pending'],
                mode='lines', stackgroup='one', name='Pending',
                fill='tonexty', fillcolor='rgba(255, 193, 7, 0.3)'
            ))
            
            fig.update_layout(
                title="Workflow Status Trends Over Time",
                xaxis_title="Date",
                yaxis_title="Number of Workflows"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trend data available")
    
    def render_approval_level_charts(self, stats: Dict):
        """Render approval level analytics"""
        levels = stats.get("approval_levels", [])
        if levels:
            level_df = pd.DataFrame(levels)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Approval level distribution
                fig = px.bar(
                    level_df,
                    x="level_name",
                    y="total",
                    title="Workflows by Approval Level",
                    color="total",
                    color_continuous_scale="Purples"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Average processing time by level
                fig = px.bar(
                    level_df,
                    x="level_name",
                    y="avg_hours",
                    title="Average Processing Time by Level",
                    color="avg_hours",
                    color_continuous_scale="Reds"
                )
                fig.update_layout(yaxis_title="Hours")
                st.plotly_chart(fig, use_container_width=True)
            
            # Stacked bar for status by level
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Approved',
                x=level_df['level_name'],
                y=level_df['approved'],
                marker_color='rgb(76, 175, 80)'
            ))
            fig.add_trace(go.Bar(
                name='Rejected',
                x=level_df['level_name'],
                y=level_df['rejected'],
                marker_color='rgb(244, 67, 54)'
            ))
            fig.add_trace(go.Bar(
                name='Pending',
                x=level_df['level_name'],
                y=level_df['pending'],
                marker_color='rgb(255, 193, 7)'
            ))
            
            fig.update_layout(
                title="Workflow Status by Approval Level",
                barmode='stack',
                xaxis_title="Approval Level",
                yaxis_title="Number of Workflows"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No approval level data available")
    
    def render_approver_charts(self, stats: Dict):
        """Render approver performance charts"""
        approvers = stats.get("top_approvers", [])
        if approvers:
            approver_df = pd.DataFrame(approvers)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Top approvers by volume
                fig = px.bar(
                    approver_df.head(10),
                    x="total_actions",
                    y="approver",
                    orientation='h',
                    title="Top Approvers by Volume",
                    color="total_actions",
                    color_continuous_scale="Blues"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Average response time
                fig = px.bar(
                    approver_df.head(10),
                    x="avg_response_hours",
                    y="approver",
                    orientation='h',
                    title="Average Response Time by Approver",
                    color="avg_response_hours",
                    color_continuous_scale="Oranges"
                )
                fig.update_layout(xaxis_title="Hours")
                st.plotly_chart(fig, use_container_width=True)
            
            # Approval vs rejection ratio
            approver_df['approval_rate'] = approver_df['approved'] / approver_df['total_actions'] * 100
            fig = px.scatter(
                approver_df,
                x="total_actions",
                y="approval_rate",
                size="total_actions",
                hover_name="approver",
                title="Approver Performance: Volume vs Approval Rate",
                labels={"approval_rate": "Approval Rate (%)", "total_actions": "Total Actions"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No approver data available")
    
    def render_workflow_table(self, workflows: List[Dict]):
        """Render detailed workflow table"""
        st.subheader("📋 Detailed Workflow List")
        
        if not workflows:
            st.info("No workflows found matching the current filters")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(workflows)
        
        # Add calculated columns
        df['age_days'] = (datetime.now() - pd.to_datetime(df['created_at'])).dt.days
        df['amount_formatted'] = df['total_amount'].apply(lambda x: f"${x:,.2f}")
        df['status_emoji'] = df['status'].map({
            'PENDING': '⏳',
            'APPROVED': '✅', 
            'REJECTED': '❌'
        })
        
        # Display options
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            show_overdue = st.checkbox("🚨 Show only overdue", value=False)
        
        with col2:
            show_pending = st.checkbox("⏳ Show only pending", value=False)
        
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                ["created_at", "total_amount", "duration_hours", "status"],
                format_func=lambda x: {
                    "created_at": "Creation Date",
                    "total_amount": "Amount",
                    "duration_hours": "Duration",
                    "status": "Status"
                }[x]
            )
        
        with col4:
            sort_order = st.selectbox("Order", ["Descending", "Ascending"])
        
        # Apply filters
        filtered_df = df.copy()
        
        if show_overdue:
            filtered_df = filtered_df[filtered_df['is_overdue'] == True]
        
        if show_pending:
            filtered_df = filtered_df[filtered_df['status'] == 'PENDING']
        
        # Sort
        ascending = sort_order == "Ascending"
        filtered_df = filtered_df.sort_values(sort_by, ascending=ascending)
        
        # Display summary
        st.write(f"**Showing {len(filtered_df)} of {len(df)} workflows**")
        
        # Create display columns
        display_columns = [
            'workflow_id', 'document_number', 'company_code', 'status_emoji',
            'amount_formatted', 'approval_level', 'current_approver', 'created_by',
            'age_days', 'duration_hours'
        ]
        
        display_df = filtered_df[display_columns].copy()
        display_df.columns = [
            'ID', 'Document', 'Company', 'Status', 'Amount', 
            'Level', 'Approver', 'Creator', 'Age (days)', 'Duration (hrs)'
        ]
        
        # Color-code rows based on status and overdue with better styling
        def highlight_rows(row):
            if row.name < len(filtered_df):
                original_row = filtered_df.iloc[row.name]
                if original_row['is_overdue']:
                    return ['background-color: #ffebee; border: 1px solid #e0e0e0; color: #d32f2f'] * len(row)  # Light red for overdue
                elif original_row['status'] == 'PENDING':
                    return ['background-color: #fff8e1; border: 1px solid #e0e0e0; color: #f57c00'] * len(row)  # Light amber for pending
                elif original_row['status'] == 'APPROVED':
                    return ['background-color: #e8f5e8; border: 1px solid #e0e0e0; color: #388e3c'] * len(row)  # Light green for approved
                elif original_row['status'] == 'REJECTED':
                    return ['background-color: #ffebee; border: 1px solid #e0e0e0; color: #d32f2f'] * len(row)  # Light red for rejected
            return ['border: 1px solid #e0e0e0; color: #333333'] * len(row)
        
        # Apply styling with better table formatting
        styled_df = display_df.style.apply(highlight_rows, axis=1).set_table_styles([
            {'selector': 'th', 'props': [
                ('background-color', '#f5f5f5'),
                ('color', '#333333'),
                ('font-weight', 'bold'),
                ('border', '1px solid #e0e0e0'),
                ('text-align', 'center')
            ]},
            {'selector': 'td', 'props': [
                ('text-align', 'center'),
                ('padding', '8px'),
                ('font-size', '14px')
            ]},
            {'selector': 'table', 'props': [
                ('border-collapse', 'collapse'),
                ('border', '1px solid #e0e0e0'),
                ('width', '100%')
            ]}
        ])
        
        # Display the table
        st.dataframe(
            styled_df,
            use_container_width=True,
            height=600
        )
        
        # Export options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export to CSV"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"workflows_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📈 Generate Report"):
                self.generate_executive_report(workflows)
        
        with col3:
            if st.button("🔄 Refresh Data"):
                st.rerun()
    
    def render_performance_insights(self, stats: Dict, workflows: List[Dict]):
        """Render performance insights and recommendations"""
        st.subheader("🎯 Performance Insights & Recommendations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Key Performance Indicators")
            
            overall = stats["overall"]
            total = overall.get("total_workflows", 1)
            
            # Calculate KPIs
            approval_rate = (overall.get("approved_count", 0) / total) * 100 if total > 0 else 0
            avg_completion = overall.get("avg_completion_hours", 0)
            overdue_rate = (overall.get("overdue_count", 0) / overall.get("pending_count", 1)) * 100 if overall.get("pending_count", 0) > 0 else 0
            
            # KPI cards with status
            kpis = [
                ("Approval Rate", f"{approval_rate:.1f}%", "🟢" if approval_rate >= 80 else "🟡" if approval_rate >= 60 else "🔴"),
                ("Avg Completion Time", f"{avg_completion:.1f}h", "🟢" if avg_completion <= 24 else "🟡" if avg_completion <= 72 else "🔴"),
                ("Overdue Rate", f"{overdue_rate:.1f}%", "🟢" if overdue_rate <= 5 else "🟡" if overdue_rate <= 15 else "🔴"),
                ("Total Volume", f"{total:,}", "🟢" if total >= 10 else "🟡" if total >= 5 else "🔴")
            ]
            
            for kpi_name, kpi_value, kpi_status in kpis:
                st.metric(f"{kpi_status} {kpi_name}", kpi_value)
        
        with col2:
            st.markdown("### 💡 Smart Recommendations")
            
            recommendations = []
            
            # Generate dynamic recommendations
            if approval_rate < 70:
                recommendations.append("🔴 **Low Approval Rate**: Review rejection reasons and provide additional training")
            
            if avg_completion > 48:
                recommendations.append("🟡 **Slow Processing**: Consider adding more approvers or reducing approval levels")
            
            if overdue_rate > 10:
                recommendations.append("🔴 **High Overdue Rate**: Implement automated reminders and escalation")
            
            if overall.get("pending_count", 0) > 20:
                recommendations.append("🟡 **High Pending Volume**: Consider workflow optimization or resource allocation")
            
            # Approver-specific recommendations
            approvers = stats.get("top_approvers", [])
            if approvers:
                slow_approvers = [a for a in approvers if a["avg_response_hours"] > 48]
                if slow_approvers:
                    recommendations.append(f"⚠️ **Slow Approvers**: {len(slow_approvers)} approvers averaging >48h response time")
            
            if not recommendations:
                recommendations.append("✅ **Excellent Performance**: All KPIs are within target ranges")
            
            for rec in recommendations:
                st.markdown(rec)
        
        # Performance trends
        st.markdown("### 📈 Performance Trends")
        
        if workflows:
            df = pd.DataFrame(workflows)
            
            # Weekly performance analysis
            df['created_date'] = pd.to_datetime(df['created_at']).dt.date
            df['week'] = pd.to_datetime(df['created_at']).dt.to_period('W')
            
            weekly_stats = df.groupby('week').agg({
                'workflow_id': 'count',
                'duration_hours': 'mean',
                'total_amount': 'sum'
            }).reset_index()
            weekly_stats.columns = ['Week', 'Volume', 'Avg Duration (hrs)', 'Total Amount']
            weekly_stats['Week'] = weekly_stats['Week'].astype(str)
            
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Weekly Volume', 'Average Duration', 'Total Amount', 'Efficiency Score'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Weekly volume
            fig.add_trace(
                go.Scatter(x=weekly_stats['Week'], y=weekly_stats['Volume'], name='Volume'),
                row=1, col=1
            )
            
            # Average duration
            fig.add_trace(
                go.Scatter(x=weekly_stats['Week'], y=weekly_stats['Avg Duration (hrs)'], name='Duration'),
                row=1, col=2
            )
            
            # Total amount
            fig.add_trace(
                go.Scatter(x=weekly_stats['Week'], y=weekly_stats['Total Amount'], name='Amount'),
                row=2, col=1
            )
            
            # Efficiency score (volume / duration)
            weekly_stats['Efficiency'] = weekly_stats['Volume'] / (weekly_stats['Avg Duration (hrs)'] + 1)
            fig.add_trace(
                go.Scatter(x=weekly_stats['Week'], y=weekly_stats['Efficiency'], name='Efficiency'),
                row=2, col=2
            )
            
            fig.update_layout(height=600, showlegend=False, title_text="Weekly Performance Trends")
            st.plotly_chart(fig, use_container_width=True)
    
    def generate_executive_report(self, workflows: List[Dict]):
        """Generate executive summary report"""
        st.markdown("### 📋 Executive Summary Report")
        
        if not workflows:
            st.warning("No data available for report generation")
            return
        
        df = pd.DataFrame(workflows)
        
        # Report content
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
        # Workflow Performance Executive Report
        **Generated:** {report_date}
        
        ## Summary Statistics
        - **Total Workflows Analyzed:** {len(df):,}
        - **Approval Rate:** {(len(df[df['status'] == 'APPROVED']) / len(df) * 100):.1f}%
        - **Average Processing Time:** {df['duration_hours'].mean():.1f} hours
        - **Total Transaction Value:** ${df['total_amount'].sum():,.2f}
        
        ## Status Breakdown
        - **Pending:** {len(df[df['status'] == 'PENDING']):,} ({len(df[df['status'] == 'PENDING']) / len(df) * 100:.1f}%)
        - **Approved:** {len(df[df['status'] == 'APPROVED']):,} ({len(df[df['status'] == 'APPROVED']) / len(df) * 100:.1f}%)
        - **Rejected:** {len(df[df['status'] == 'REJECTED']):,} ({len(df[df['status'] == 'REJECTED']) / len(df) * 100:.1f}%)
        
        ## Key Metrics
        - **Fastest Approval:** {df['duration_hours'].min():.1f} hours
        - **Slowest Approval:** {df['duration_hours'].max():.1f} hours
        - **Largest Transaction:** ${df['total_amount'].max():,.2f}
        - **Average Transaction:** ${df['total_amount'].mean():,.2f}
        
        ## Recommendations
        Based on the analysis, consider the following actions:
        1. **Process Optimization:** Review workflows taking >72 hours
        2. **Resource Allocation:** Balance approver workloads
        3. **Training:** Address high rejection rate areas
        4. **Automation:** Implement auto-approval for low-risk transactions
        
        ---
        *Report generated by Workflow Dashboard v1.0*
        """
        
        st.markdown(report)
        
        # Download option
        st.download_button(
            label="📄 Download Report",
            data=report,
            file_name=f"workflow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )


def main():
    """Main function to run the workflow dashboard"""
    dashboard = WorkflowDashboard()
    dashboard.render_dashboard()


if __name__ == "__main__":
    main()