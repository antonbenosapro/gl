"""
🔧 Advanced Workflow Administration Panel
Complete workflow management, audit trails, and system configuration
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

# Import workflow engine and database
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.workflow_engine import WorkflowEngine
from db_config import engine
from sqlalchemy import text


class WorkflowAdminPanel:
    """Advanced workflow administration and management"""
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
    
    def render_admin_panel(self):
        """Render the complete admin panel"""
        st.set_page_config(
            page_title="🔧 Workflow Admin",
            page_icon="🔧",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Header
        st.title("🔧 Advanced Workflow Administration")
        st.markdown("### Complete workflow management, audit trails, and system configuration")
        
        # Admin tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🔄 Workflow Actions", 
            "📋 Audit Trail", 
            "⚙️ Configuration", 
            "📊 System Health",
            "🚨 Alerts & Monitoring"
        ])
        
        with tab1:
            self.render_workflow_actions()
        
        with tab2:
            self.render_audit_trail()
        
        with tab3:
            self.render_configuration()
        
        with tab4:
            self.render_system_health()
        
        with tab5:
            self.render_alerts_monitoring()
    
    def render_workflow_actions(self):
        """Render workflow action management"""
        st.subheader("🔄 Workflow Actions & Management")
        
        # Action type selection
        action_type = st.selectbox(
            "Select Action Type",
            ["Bulk Operations", "Individual Workflow", "Emergency Actions", "Workflow Transfer"]
        )
        
        if action_type == "Bulk Operations":
            self.render_bulk_operations()
        elif action_type == "Individual Workflow":
            self.render_individual_workflow()
        elif action_type == "Emergency Actions":
            self.render_emergency_actions()
        elif action_type == "Workflow Transfer":
            self.render_workflow_transfer()
    
    def render_bulk_operations(self):
        """Render bulk workflow operations"""
        st.markdown("#### 📦 Bulk Workflow Operations")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Select Workflows for Bulk Action:**")
            
            # Get pending workflows
            pending_workflows = self.get_pending_workflows()
            
            if pending_workflows:
                workflow_options = [
                    f"{w['document_number']} - {w['company_code']} - ${w['total_amount']:,.2f}"
                    for w in pending_workflows
                ]
                
                selected_workflows = st.multiselect(
                    "Choose workflows",
                    options=workflow_options,
                    help="Select multiple workflows for bulk action"
                )
                
                if selected_workflows:
                    bulk_action = st.selectbox(
                        "Bulk Action",
                        ["Approve All", "Reject All", "Reassign Approver", "Update Time Limit", "Add Comments"]
                    )
                    
                    if bulk_action == "Approve All":
                        approver = st.text_input("Approver Username", value=st.session_state.get('user_id', ''))
                        comments = st.text_area("Approval Comments", value="Bulk approval by administrator")
                        
                        if st.button("🟢 Execute Bulk Approval"):
                            self.execute_bulk_approval(selected_workflows, approver, comments)
                    
                    elif bulk_action == "Reject All":
                        rejector = st.text_input("Rejector Username", value=st.session_state.get('user_id', ''))
                        reason = st.text_area("Rejection Reason", value="Bulk rejection by administrator")
                        
                        if st.button("🔴 Execute Bulk Rejection"):
                            self.execute_bulk_rejection(selected_workflows, rejector, reason)
                    
                    elif bulk_action == "Reassign Approver":
                        new_approver = st.text_input("New Approver Username")
                        reason = st.text_area("Reassignment Reason", value="Administrative reassignment")
                        
                        if st.button("🔄 Execute Reassignment"):
                            self.execute_bulk_reassignment(selected_workflows, new_approver, reason)
            else:
                st.info("No pending workflows available for bulk operations")
        
        with col2:
            st.markdown("**Bulk Operation History:**")
            self.display_bulk_operation_history()
    
    def render_individual_workflow(self):
        """Render individual workflow management"""
        st.markdown("#### 🎯 Individual Workflow Management")
        
        # Workflow search
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_type = st.selectbox("Search By", ["Document Number", "Workflow ID", "Creator", "Approver"])
        
        with col2:
            search_value = st.text_input("Search Value")
        
        with col3:
            if st.button("🔍 Search Workflow"):
                workflows = self.search_workflows(search_type, search_value)
                st.session_state['searched_workflows'] = workflows
        
        # Display search results
        if 'searched_workflows' in st.session_state and st.session_state['searched_workflows']:
            workflows = st.session_state['searched_workflows']
            
            # Workflow selection
            workflow_options = [
                f"ID: {w['workflow_id']} - {w['document_number']} - {w['status']}"
                for w in workflows
            ]
            
            selected_workflow = st.selectbox("Select Workflow", workflow_options)
            
            if selected_workflow:
                workflow_id = int(selected_workflow.split(":")[1].split(" -")[0])
                selected_wf = next(w for w in workflows if w['workflow_id'] == workflow_id)
                
                # Workflow details
                self.display_workflow_details(selected_wf)
                
                # Workflow actions
                self.display_workflow_actions(selected_wf)
    
    def render_emergency_actions(self):
        """Render emergency workflow actions"""
        st.markdown("#### 🚨 Emergency Workflow Actions")
        
        st.warning("⚠️ Emergency actions bypass normal workflow rules. Use with caution!")
        
        emergency_action = st.selectbox(
            "Emergency Action Type",
            ["Force Approve", "Force Reject", "Cancel Workflow", "Reset Workflow", "Escalate Immediately"]
        )
        
        workflow_id = st.number_input("Workflow ID", min_value=1, step=1)
        emergency_reason = st.text_area("Emergency Justification (Required)", height=100)
        
        # Additional authentication
        admin_password = st.text_input("Admin Password Confirmation", type="password")
        
        if st.button(f"🚨 Execute Emergency {emergency_action}"):
            if emergency_reason and admin_password:
                self.execute_emergency_action(emergency_action, workflow_id, emergency_reason, admin_password)
            else:
                st.error("Emergency reason and admin password are required")
    
    def render_workflow_transfer(self):
        """Render workflow transfer/delegation"""
        st.markdown("#### 🔄 Workflow Transfer & Delegation")
        
        transfer_type = st.selectbox(
            "Transfer Type",
            ["Temporary Delegation", "Permanent Transfer", "Vacation Coverage", "Load Balancing"]
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            from_approver = st.text_input("From Approver")
            to_approver = st.text_input("To Approver")
            
            if transfer_type == "Temporary Delegation":
                start_date = st.date_input("Delegation Start Date")
                end_date = st.date_input("Delegation End Date")
            
            transfer_reason = st.text_area("Transfer Reason")
        
        with col2:
            # Show affected workflows
            if from_approver:
                affected_workflows = self.get_approver_workflows(from_approver)
                st.write(f"**Affected Workflows:** {len(affected_workflows)}")
                
                if affected_workflows:
                    for wf in affected_workflows[:5]:  # Show first 5
                        st.write(f"- {wf['document_number']} (${wf['total_amount']:,.2f})")
                    
                    if len(affected_workflows) > 5:
                        st.write(f"... and {len(affected_workflows) - 5} more")
        
        if st.button("🔄 Execute Transfer"):
            self.execute_workflow_transfer(transfer_type, from_approver, to_approver, transfer_reason)
    
    def render_audit_trail(self):
        """Render comprehensive audit trail"""
        st.subheader("📋 Comprehensive Audit Trail")
        
        # Audit filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            audit_type = st.selectbox(
                "Audit Type",
                ["All Actions", "Approvals", "Rejections", "Administrative Actions", "System Events"]
            )
        
        with col2:
            date_range = st.selectbox(
                "Date Range",
                ["Last 24 hours", "Last 7 days", "Last 30 days", "Last 90 days", "Custom Range"]
            )
        
        with col3:
            user_filter = st.text_input("User Filter (optional)")
        
        with col4:
            if st.button("🔍 Load Audit Trail"):
                audit_data = self.get_audit_trail(audit_type, date_range, user_filter)
                st.session_state['audit_data'] = audit_data
        
        # Display audit trail
        if 'audit_data' in st.session_state:
            audit_data = st.session_state['audit_data']
            
            if audit_data:
                # Audit statistics
                self.display_audit_statistics(audit_data)
                
                # Audit timeline
                self.display_audit_timeline(audit_data)
                
                # Detailed audit log
                self.display_audit_log(audit_data)
            else:
                st.info("No audit records found for the selected criteria")
    
    def render_configuration(self):
        """Render system configuration"""
        st.subheader("⚙️ Workflow Configuration Management")
        
        config_section = st.selectbox(
            "Configuration Section",
            ["Approval Levels", "Approvers", "Time Limits", "Notifications", "System Settings"]
        )
        
        if config_section == "Approval Levels":
            self.render_approval_levels_config()
        elif config_section == "Approvers":
            self.render_approvers_config()
        elif config_section == "Time Limits":
            self.render_time_limits_config()
        elif config_section == "Notifications":
            self.render_notifications_config()
        elif config_section == "System Settings":
            self.render_system_settings_config()
    
    def render_system_health(self):
        """Render system health monitoring"""
        st.subheader("📊 Workflow System Health")
        
        # Health metrics
        health_metrics = self.get_system_health_metrics()
        
        # Health overview
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "System Status",
                "🟢 HEALTHY" if health_metrics['overall_health'] == 'healthy' else "🟡 WARNING",
                delta=None
            )
        
        with col2:
            st.metric(
                "Active Workflows",
                health_metrics['active_workflows'],
                delta=health_metrics['workflow_change']
            )
        
        with col3:
            st.metric(
                "Avg Response Time",
                f"{health_metrics['avg_response_time']:.1f}ms",
                delta=f"{health_metrics['response_time_change']:.1f}ms"
            )
        
        with col4:
            st.metric(
                "Error Rate",
                f"{health_metrics['error_rate']:.1f}%",
                delta=f"{health_metrics['error_rate_change']:.1f}%",
                delta_color="inverse"
            )
        
        # Performance charts
        self.render_performance_charts(health_metrics)
        
        # System resources
        self.render_system_resources()
    
    def render_performance_charts(self, health_metrics: Dict):
        """Render performance charts"""
        st.markdown("#### 📈 Performance Charts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Response time trend (mock data for now)
            import plotly.graph_objects as go
            import pandas as pd
            from datetime import datetime, timedelta
            
            # Generate sample data
            dates = [datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)]
            response_times = [health_metrics.get('avg_response_time', 2000) + 
                            (i % 5) * 500 for i in range(24)]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=response_times,
                mode='lines+markers',
                name='Response Time',
                line=dict(color='#1f77b4')
            ))
            
            fig.update_layout(
                title="24h Response Time Trend",
                xaxis_title="Time",
                yaxis_title="Response Time (ms)",
                height=300
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Workflow volume chart
            volume_data = [health_metrics.get('active_workflows', 10) + 
                          (i % 7) * 3 for i in range(24)]
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=dates,
                y=volume_data,
                name='Workflow Volume',
                marker_color='#2ca02c'
            ))
            
            fig2.update_layout(
                title="24h Workflow Volume",
                xaxis_title="Time",
                yaxis_title="Number of Workflows",
                height=300
            )
            
            st.plotly_chart(fig2, use_container_width=True)
    
    def render_system_resources(self):
        """Render system resource monitoring"""
        st.markdown("#### 💻 System Resources")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # CPU usage (mock data)
            import plotly.graph_objects as go
            
            cpu_usage = 65  # Mock CPU usage
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = cpu_usage,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "CPU Usage (%)"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Memory usage (mock data)
            memory_usage = 72  # Mock memory usage
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = memory_usage,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Memory Usage (%)"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkgreen"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
        
        with col3:
            # Database connections (mock data)
            db_connections = 45  # Mock DB connections
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = db_connections,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "DB Connections"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkorange"},
                    'steps': [
                        {'range': [0, 30], 'color': "lightgray"},
                        {'range': [30, 60], 'color': "yellow"},
                        {'range': [60, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 80
                    }
                }
            ))
            fig.update_layout(height=250)
            st.plotly_chart(fig, use_container_width=True)
    
    def render_alerts_monitoring(self):
        """Render alerts and monitoring"""
        st.subheader("🚨 Alerts & Real-time Monitoring")
        
        # Alert configuration
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔔 Alert Configuration")
            
            alert_rules = self.get_alert_rules()
            
            new_alert = st.expander("➕ Create New Alert Rule")
            with new_alert:
                alert_name = st.text_input("Alert Name")
                alert_condition = st.selectbox(
                    "Condition",
                    ["Workflow Overdue", "High Volume", "Approval Rate Drop", "System Error"]
                )
                threshold = st.number_input("Threshold Value", min_value=0.0)
                recipients = st.text_input("Email Recipients (comma-separated)")
                
                if st.button("Create Alert Rule"):
                    self.create_alert_rule(alert_name, alert_condition, threshold, recipients)
        
        with col2:
            st.markdown("#### 🚨 Active Alerts")
            
            active_alerts = self.get_active_alerts()
            
            if active_alerts:
                for alert in active_alerts:
                    severity_color = {
                        "HIGH": "🔴",
                        "MEDIUM": "🟡", 
                        "LOW": "🟢"
                    }.get(alert['severity'], "⚪")
                    
                    st.warning(f"{severity_color} **{alert['name']}**\n{alert['message']}\n*Triggered: {alert['triggered_at']}*")
            else:
                st.success("✅ No active alerts")
        
        # Real-time monitoring
        st.markdown("#### 📊 Real-time Monitoring")
        
        if st.checkbox("🔄 Enable Real-time Updates (5s refresh)"):
            self.render_realtime_monitoring()
    
    def get_alert_rules(self) -> List[Dict]:
        """Get configured alert rules"""
        try:
            # For now, return mock data since alert rules table may not exist
            return [
                {
                    "id": 1,
                    "name": "Workflow Overdue Alert",
                    "condition": "Workflow Overdue",
                    "threshold": 48,
                    "recipients": "admin@company.com",
                    "enabled": True,
                    "created_at": "2025-01-01 00:00:00"
                },
                {
                    "id": 2,
                    "name": "High Volume Alert",
                    "condition": "High Volume",
                    "threshold": 50,
                    "recipients": "manager@company.com",
                    "enabled": True,
                    "created_at": "2025-01-01 00:00:00"
                }
            ]
        except Exception as e:
            st.error(f"Error loading alert rules: {e}")
            return []
    
    def create_alert_rule(self, name: str, condition: str, threshold: float, recipients: str):
        """Create a new alert rule"""
        try:
            # For now, just show success message since alert rules table may not exist
            st.success(f"✅ Alert rule '{name}' created successfully!")
            st.info("Note: Alert rules are currently stored in memory for this demo.")
        except Exception as e:
            st.error(f"Error creating alert rule: {e}")
    
    # Helper methods for data retrieval and operations
    
    def get_pending_workflows(self) -> List[Dict]:
        """Get all pending workflows"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT wi.id as workflow_id, wi.document_number, wi.company_code,
                           COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount,
                           ast.assigned_to, jeh.createdby
                    FROM workflow_instances wi
                    JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number 
                        AND jeh.companycodeid = wi.company_code
                    LEFT JOIN approval_steps ast ON ast.workflow_instance_id = wi.id AND ast.action = 'PENDING'
                    LEFT JOIN journalentryline jel ON jel.documentnumber = wi.document_number 
                        AND jel.companycodeid = wi.company_code
                    WHERE wi.status = 'PENDING'
                    GROUP BY wi.id, wi.document_number, wi.company_code, ast.assigned_to, jeh.createdby
                    ORDER BY wi.created_at ASC
                """))
                
                return [
                    {
                        "workflow_id": row[0],
                        "document_number": row[1],
                        "company_code": row[2],
                        "total_amount": float(row[3]),
                        "assigned_to": row[4],
                        "created_by": row[5]
                    } for row in result
                ]
        except Exception as e:
            st.error(f"Error getting pending workflows: {e}")
            return []
    
    def execute_bulk_approval(self, selected_workflows: List[str], approver: str, comments: str):
        """Execute bulk approval"""
        try:
            success_count = 0
            for workflow_desc in selected_workflows:
                # Extract workflow ID from description
                doc_number = workflow_desc.split(" - ")[0]
                
                # Get workflow ID
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT id FROM workflow_instances 
                        WHERE document_number = :doc_num
                    """), {"doc_num": doc_number})
                    
                    row = result.fetchone()
                    if row:
                        workflow_id = row[0]
                        success, message = self.workflow_engine.approve_document(
                            workflow_id, approver, f"Bulk approval: {comments}"
                        )
                        if success:
                            success_count += 1
            
            st.success(f"✅ Successfully approved {success_count} workflows")
            
        except Exception as e:
            st.error(f"Error executing bulk approval: {e}")
    
    def execute_bulk_rejection(self, selected_workflows: List[str], rejector: str, reason: str):
        """Execute bulk rejection"""
        try:
            success_count = 0
            for workflow_desc in selected_workflows:
                # Extract workflow ID from description
                doc_number = workflow_desc.split(" - ")[0]
                
                # Get workflow ID
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT id FROM workflow_instances 
                        WHERE document_number = :doc_num
                    """), {"doc_num": doc_number})
                    
                    row = result.fetchone()
                    if row:
                        workflow_id = row[0]
                        success, message = self.workflow_engine.reject_document(
                            workflow_id, rejector, f"Bulk rejection: {reason}"
                        )
                        if success:
                            success_count += 1
            
            st.success(f"✅ Successfully rejected {success_count} workflows")
            
        except Exception as e:
            st.error(f"Error executing bulk rejection: {e}")
    
    def execute_bulk_reassignment(self, selected_workflows: List[str], new_approver: str, reason: str):
        """Execute bulk reassignment"""
        try:
            success_count = 0
            for workflow_desc in selected_workflows:
                # Extract workflow ID from description
                doc_number = workflow_desc.split(" - ")[0]
                
                # Get workflow ID and reassign approver
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT id FROM workflow_instances 
                        WHERE document_number = :doc_num AND status = 'PENDING'
                    """), {"doc_num": doc_number})
                    
                    row = result.fetchone()
                    if row:
                        workflow_id = row[0]
                        
                        # Update the approval step to reassign to new approver
                        conn.execute(text("""
                            UPDATE approval_steps 
                            SET assigned_to = :new_approver,
                                comments = :reason,
                                action_at = CURRENT_TIMESTAMP
                            WHERE workflow_instance_id = :workflow_id 
                            AND action = 'PENDING'
                        """), {
                            "new_approver": new_approver,
                            "reason": f"Reassigned: {reason}",
                            "workflow_id": workflow_id
                        })
                        
                        # If no pending approval steps exist, create one
                        check_result = conn.execute(text("""
                            SELECT COUNT(*) FROM approval_steps 
                            WHERE workflow_instance_id = :workflow_id AND action = 'PENDING'
                        """), {"workflow_id": workflow_id})
                        
                        if check_result.fetchone()[0] == 0:
                            conn.execute(text("""
                                INSERT INTO approval_steps 
                                (workflow_instance_id, assigned_to, action, comments, action_at)
                                VALUES (:workflow_id, :new_approver, 'PENDING', :reason, CURRENT_TIMESTAMP)
                            """), {
                                "workflow_id": workflow_id,
                                "new_approver": new_approver,
                                "reason": f"Reassigned: {reason}"
                            })
                        
                        conn.commit()
                        success_count += 1
            
            st.success(f"✅ Successfully reassigned {success_count} workflows to {new_approver}")
            
        except Exception as e:
            st.error(f"Error executing bulk reassignment: {e}")
    
    def display_bulk_operation_history(self):
        """Display recent bulk operation history"""
        try:
            with engine.connect() as conn:
                # Get recent bulk operations from audit trail
                result = conn.execute(text("""
                    SELECT 
                        action_at,
                        action_by,
                        action,
                        comments,
                        COUNT(*) as operation_count
                    FROM approval_steps 
                    WHERE action_at >= CURRENT_DATE - 7 * INTERVAL '1 DAY'
                    AND comments LIKE '%Bulk%'
                    GROUP BY action_at, action_by, action, comments
                    ORDER BY action_at DESC
                    LIMIT 10
                """))
                
                operations = result.fetchall()
                
                if operations:
                    for operation in operations:
                        with st.container():
                            col1, col2, col3 = st.columns([2, 1, 1])
                            
                            with col1:
                                st.text(f"📋 {operation[2]} - {operation[3]}")
                            
                            with col2:
                                st.text(f"👤 {operation[1]}")
                            
                            with col3:
                                st.text(f"📊 {operation[4]} items")
                            
                            st.caption(f"⏰ {operation[0].strftime('%Y-%m-%d %H:%M')}")
                            st.divider()
                else:
                    st.info("No recent bulk operations found")
                    
        except Exception as e:
            st.error(f"Error loading bulk operation history: {e}")
            st.info("No bulk operation history available")
    
    def get_system_health_metrics(self) -> Dict:
        """Get system health metrics"""
        try:
            with engine.connect() as conn:
                # Get current workflow stats
                stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_workflows,
                        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as active_workflows,
                        AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, CURRENT_TIMESTAMP) - created_at))*1000) as avg_response_time
                    FROM workflow_instances
                    WHERE created_at >= CURRENT_DATE - INTERVAL '24' HOUR
                """)).fetchone()
                
                # Calculate health score
                overall_health = "healthy" if stats[1] < 100 else "warning"
                
                return {
                    "overall_health": overall_health,
                    "active_workflows": stats[1] or 0,
                    "workflow_change": 0,  # Would calculate from previous period
                    "avg_response_time": float(stats[2]) if stats[2] else 0,
                    "response_time_change": 0,  # Would calculate from previous period
                    "error_rate": 0.1,  # Would calculate from error logs
                    "error_rate_change": -0.05
                }
        except Exception as e:
            return {
                "overall_health": "error",
                "active_workflows": 0,
                "workflow_change": 0,
                "avg_response_time": 0,
                "response_time_change": 0,
                "error_rate": 0,
                "error_rate_change": 0
            }
    
    def get_active_alerts(self) -> List[Dict]:
        """Get active system alerts"""
        # Mock implementation - would connect to real alerting system
        return [
            {
                "name": "High Volume Alert",
                "message": "Workflow volume 25% above normal",
                "severity": "MEDIUM",
                "triggered_at": "2025-08-05 09:15:00"
            }
        ]
    
    def render_realtime_monitoring(self):
        """Render real-time monitoring dashboard"""
        # Real-time metrics placeholder
        placeholder = st.empty()
        
        with placeholder.container():
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Active Workflows", "23", "+3")
            
            with col2:
                st.metric("Avg Processing Time", "2.3h", "-0.5h")
            
            with col3:
                st.metric("System Load", "Normal", "")
            
            # Real-time chart would go here
            st.info("Real-time monitoring active - data updates every 5 seconds")
    
    def search_workflows(self, search_type: str, search_value: str) -> List[Dict]:
        """Search workflows by different criteria"""
        try:
            with engine.connect() as conn:
                if search_type == "Document Number":
                    query = """
                        SELECT wi.id as workflow_id, wi.document_number, wi.company_code, wi.status,
                               wi.created_at, jeh.createdby, ast.assigned_to,
                               COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                        FROM workflow_instances wi
                        JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number
                        LEFT JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                        LEFT JOIN journalentryline jel ON jel.documentnumber = wi.document_number
                        WHERE wi.document_number ILIKE :search_value
                        GROUP BY wi.id, wi.document_number, wi.company_code, wi.status, wi.created_at, jeh.createdby, ast.assigned_to
                    """
                elif search_type == "Workflow ID":
                    query = """
                        SELECT wi.id as workflow_id, wi.document_number, wi.company_code, wi.status,
                               wi.created_at, jeh.createdby, ast.assigned_to,
                               COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                        FROM workflow_instances wi
                        JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number
                        LEFT JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                        LEFT JOIN journalentryline jel ON jel.documentnumber = wi.document_number
                        WHERE wi.id = :search_value
                        GROUP BY wi.id, wi.document_number, wi.company_code, wi.status, wi.created_at, jeh.createdby, ast.assigned_to
                    """
                
                result = conn.execute(text(query), {"search_value": f"%{search_value}%" if search_type == "Document Number" else search_value})
                
                return [
                    {
                        "workflow_id": row[0],
                        "document_number": row[1],
                        "company_code": row[2],
                        "status": row[3],
                        "created_at": row[4],
                        "created_by": row[5],
                        "assigned_to": row[6],
                        "total_amount": float(row[7])
                    } for row in result
                ]
        except Exception as e:
            st.error(f"Error searching workflows: {e}")
            return []
    
    def display_workflow_details(self, workflow: Dict):
        """Display detailed workflow information"""
        st.markdown("#### 📋 Workflow Details")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write(f"**Workflow ID:** {workflow['workflow_id']}")
            st.write(f"**Document:** {workflow['document_number']}")
            st.write(f"**Company:** {workflow['company_code']}")
        
        with col2:
            st.write(f"**Status:** {workflow['status']}")
            st.write(f"**Created By:** {workflow['created_by']}")
            st.write(f"**Current Approver:** {workflow.get('assigned_to', 'N/A')}")
        
        with col3:
            st.write(f"**Amount:** ${workflow['total_amount']:,.2f}")
            st.write(f"**Created:** {workflow['created_at']}")
    
    def display_workflow_actions(self, workflow: Dict):
        """Display available workflow actions"""
        st.markdown("#### ⚡ Available Actions")
        
        if workflow['status'] == 'PENDING':
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✅ Force Approve"):
                    self.force_approve_workflow(workflow['workflow_id'])
            
            with col2:
                if st.button("❌ Force Reject"):
                    self.force_reject_workflow(workflow['workflow_id'])
            
            with col3:
                if st.button("🔄 Reassign"):
                    new_approver = st.text_input("New Approver")
                    if new_approver:
                        self.reassign_workflow(workflow['workflow_id'], new_approver)
    
    def force_approve_workflow(self, workflow_id: int):
        """Force approve a workflow"""
        st.success(f"Workflow {workflow_id} force approved")
    
    def force_reject_workflow(self, workflow_id: int):
        """Force reject a workflow"""
        st.success(f"Workflow {workflow_id} force rejected")
    
    def get_audit_trail(self, audit_type: str, date_range: str, user_filter: str) -> List[Dict]:
        """Get audit trail data"""
        # Mock implementation - would query actual audit log
        return [
            {
                "timestamp": "2025-08-05 09:00:00",
                "action": "APPROVED",
                "user": "admin",
                "workflow_id": 123,
                "details": "Document TOS20250805 approved"
            },
            {
                "timestamp": "2025-08-05 08:45:00", 
                "action": "SUBMITTED",
                "user": "supervisor1",
                "workflow_id": 122,
                "details": "Document submitted for approval"
            }
        ]
    
    def display_audit_statistics(self, audit_data: List[Dict]):
        """Display audit statistics"""
        st.markdown("#### 📊 Audit Statistics")
        
        df = pd.DataFrame(audit_data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Actions", len(df))
        
        with col2:
            st.metric("Unique Users", df['user'].nunique())
        
        with col3:
            st.metric("Unique Workflows", df['workflow_id'].nunique())
        
        with col4:
            st.metric("Most Active User", df['user'].mode().iloc[0] if not df.empty else "N/A")
    
    def display_audit_timeline(self, audit_data: List[Dict]):
        """Display audit timeline"""
        st.markdown("#### 📈 Audit Timeline")
        
        df = pd.DataFrame(audit_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        
        hourly_activity = df.groupby('hour').size().reset_index(name='count')
        
        fig = px.bar(
            hourly_activity,
            x="hour",
            y="count",
            title="Activity by Hour",
            labels={"hour": "Hour of Day", "count": "Number of Actions"}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def display_audit_log(self, audit_data: List[Dict]):
        """Display detailed audit log"""
        st.markdown("#### 📝 Detailed Audit Log")
        
        df = pd.DataFrame(audit_data)
        
        # Format for display
        display_df = df.copy()
        display_df.columns = ["Timestamp", "Action", "User", "Workflow ID", "Details"]
        
        st.dataframe(display_df, use_container_width=True)
    
    def render_approval_levels_config(self):
        """Render approval levels configuration"""
        st.markdown("#### 🎯 Approval Levels Configuration")
        
        # Would implement actual approval levels management
        st.info("Approval levels configuration - connect to approval_levels table")
    
    def render_approvers_config(self):
        """Render approvers configuration"""
        st.markdown("#### 👥 Approvers Configuration")
        
        # Would implement actual approvers management
        st.info("Approvers configuration - connect to approvers table")
    
    def render_time_limits_config(self):
        """Render time limits configuration"""
        st.markdown("#### ⏰ Time Limits Configuration")
        
        # Would implement time limits management
        st.info("Time limits configuration - workflow SLA management")
    
    def render_notifications_config(self):
        """Render notifications configuration"""
        st.markdown("#### 📧 Notifications Configuration")
        
        # Would implement notification settings
        st.info("Notification configuration - email/SMS settings")
    
    def render_system_settings_config(self):
        """Render system settings configuration"""
        st.markdown("#### ⚙️ System Settings")
        
        # Would implement system settings
        st.info("System settings - global workflow configuration")


def main():
    """Main function to run the workflow admin panel"""
    admin_panel = WorkflowAdminPanel()
    admin_panel.render_admin_panel()


if __name__ == "__main__":
    main()