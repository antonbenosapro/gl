import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from db_config import engine
from auth.middleware import authenticator
from utils.logger import StreamlitLogHandler
from utils.navigation import show_sap_sidebar, show_breadcrumb
from utils.workflow_engine import WorkflowEngine

# Require authentication and permission
authenticator.require_auth()
authenticator.require_permission("journal.approve")

current_user = authenticator.get_current_user()
StreamlitLogHandler.log_page_access("Approval Dashboard", current_user.username)

# Configure page
st.set_page_config(page_title="📋 Approval Dashboard", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Approval Dashboard", "Workflow", "Approvals")

st.title("📋 Journal Entry Approval Dashboard")

# Check if user is admin to show admin view option
is_admin = authenticator.has_permission("admin.full_access")

# View mode selection for admin users
if is_admin:
    view_mode = st.radio(
        "**📊 View Mode:**",
        ["👤 My Approvals", "🌐 All Workflows (Admin)"],
        horizontal=True
    )
else:
    view_mode = "👤 My Approvals"

if view_mode == "👤 My Approvals":
    # Get pending approvals for current user
    pending_approvals = WorkflowEngine.get_pending_approvals(current_user.username)
    show_user_dashboard = True
else:
    # Admin view - get all workflows
    show_user_dashboard = False
    
    # Admin filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "**Status Filter:**",
            ["ALL", "PENDING", "APPROVED", "REJECTED"],
            index=0
        )
    
    with col2:
        days_back = st.selectbox(
            "**Time Period:**",
            [7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"Last {x} days"
        )
    
    with col3:
        st.write("**Refresh Data:**")
        if st.button("🔄 Refresh", type="secondary"):
            st.rerun()
    
    # Get all workflows for admin
    all_workflows = WorkflowEngine.get_all_workflows(status_filter, days_back)
    workflow_stats = WorkflowEngine.get_workflow_statistics()

if show_user_dashboard:
    # Original user dashboard code
    pending_approvals = WorkflowEngine.get_pending_approvals(current_user.username)

# Dashboard metrics
col1, col2, col3, col4 = st.columns(4)

if show_user_dashboard:
    with col1:
        st.metric("Pending Approvals", len(pending_approvals))

    with col2:
        overdue_count = sum(1 for approval in pending_approvals if approval.get('is_overdue', False))
        st.metric("Overdue", overdue_count, delta=f"+{overdue_count}" if overdue_count > 0 else None)

    with col3:
        total_amount = sum(approval.get('total_amount', 0) for approval in pending_approvals)
        st.metric("Total Amount", f"${total_amount:,.2f}")

    with col4:
        # Get approval statistics for current user
        try:
            with engine.connect() as conn:
                stats = conn.execute(text("""
                    SELECT 
                        COUNT(CASE WHEN ast.action = 'APPROVED' THEN 1 END) as approved_count,
                        COUNT(CASE WHEN ast.action = 'REJECTED' THEN 1 END) as rejected_count
                    FROM approval_steps ast
                    WHERE ast.action_by = :user_id
                    AND ast.action_at >= CURRENT_DATE - INTERVAL '30 days'
                """), {"user_id": current_user.username}).fetchone()
                
                approved_this_month = stats[0] if stats else 0
                st.metric("Approved This Month", approved_this_month)
        except:
            st.metric("Approved This Month", "N/A")
else:
    # Admin dashboard metrics
    with col1:
        st.metric("Total Workflows", workflow_stats["total_workflows"])

    with col2:
        st.metric("Pending", workflow_stats["pending_count"], 
                 delta=f"+{workflow_stats['overdue_count']} overdue" if workflow_stats['overdue_count'] > 0 else None)

    with col3:
        st.metric("Approved", workflow_stats["approved_count"])

    with col4:
        st.metric("Avg Hours", f"{workflow_stats['avg_completion_hours']:.1f}")

st.divider()

if show_user_dashboard and not pending_approvals:
    st.info("🎉 **No pending approvals!** All caught up.")
    
    # Show recent approval history
    st.subheader("📈 Recent Approval Activity")
    
    try:
        with engine.connect() as conn:
            recent_activity = conn.execute(text("""
                SELECT ast.workflow_instance_id, wi.document_number, wi.company_code,
                       ast.action, ast.action_at, ast.comments,
                       jeh.reference, jeh.createdby,
                       COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                FROM approval_steps ast
                JOIN workflow_instances wi ON wi.id = ast.workflow_instance_id
                JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number 
                    AND jeh.companycodeid = wi.company_code
                LEFT JOIN journalentryline jel ON jel.documentnumber = wi.document_number 
                    AND jel.companycodeid = wi.company_code
                WHERE ast.action_by = :user_id
                AND ast.action_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY ast.workflow_instance_id, wi.document_number, wi.company_code,
                         ast.action, ast.action_at, ast.comments, jeh.reference, jeh.createdby
                ORDER BY ast.action_at DESC
                LIMIT 10
            """), {"user_id": current_user.username})
            
            activity_data = []
            for row in recent_activity:
                activity_data.append({
                    "Document": row[1],
                    "Company": row[2],
                    "Action": row[3],
                    "Date": row[4],
                    "Amount": f"${row[8]:,.2f}",
                    "Reference": row[6] or "N/A",
                    "Created By": row[7],
                    "Comments": row[5] or "None"
                })
            
            if activity_data:
                df_activity = pd.DataFrame(activity_data)
                st.dataframe(df_activity, use_container_width=True, hide_index=True)
            else:
                st.info("No recent approval activity found.")
    except Exception as e:
        st.error(f"Error loading recent activity: {e}")

elif show_user_dashboard:
    st.subheader(f"⏳ Pending Approvals ({len(pending_approvals)})")
    
    # Approval actions
    for i, approval in enumerate(pending_approvals):
        with st.expander(
            f"📄 {approval['document_number']} | {approval['company_code']} - ${approval['total_amount']:,.2f}" + 
            (" ⚠️ OVERDUE" if approval.get('is_overdue', False) else ""),
            expanded=i == 0  # Expand first item by default
        ):
            # Document details
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Document Number:** {approval['document_number']}")
                st.write(f"**Company Code:** {approval['company_code']}")
                st.write(f"**Amount:** ${approval['total_amount']:,.2f}")
                st.write(f"**Currency:** {approval['currency']}")
                st.write(f"**Reference:** {approval['reference'] or 'N/A'}")
            
            with col2:
                st.write(f"**Created By:** {approval['created_by']}")
                st.write(f"**Posting Date:** {approval['posting_date']}")
                st.write(f"**Submitted:** {approval['submitted_at']}")
                st.write(f"**Approval Level:** {approval['approval_level']}")
                if approval.get('time_limit'):
                    time_limit_str = approval['time_limit'].strftime('%Y-%m-%d %H:%M')
                    if approval.get('is_overdue'):
                        st.write(f"**⚠️ Due Date:** {time_limit_str} (OVERDUE)")
                    else:
                        st.write(f"**Due Date:** {time_limit_str}")
            
            # Show journal entry lines
            st.write("**📋 Journal Entry Lines:**")
            try:
                with engine.connect() as conn:
                    lines = conn.execute(text("""
                        SELECT linenumber, glaccountid, description, debitamount, creditamount, currencycode
                        FROM journalentryline
                        WHERE documentnumber = :doc AND companycodeid = :cc
                        ORDER BY linenumber
                    """), {"doc": approval['document_number'], "cc": approval['company_code']})
                    
                    lines_data = []
                    for line in lines:
                        lines_data.append({
                            "Line": line[0],
                            "GL Account": line[1],
                            "Description": line[2],
                            "Debit": f"${line[3]:,.2f}" if line[3] and line[3] > 0 else "",
                            "Credit": f"${line[4]:,.2f}" if line[4] and line[4] > 0 else "",
                            "Currency": line[5]
                        })
                    
                    if lines_data:
                        df_lines = pd.DataFrame(lines_data)
                        st.dataframe(df_lines, use_container_width=True, hide_index=True)
                    else:
                        st.info("No line items found")
                        
            except Exception as e:
                st.error(f"Error loading journal entry lines: {e}")
            
            st.divider()
            
            # Approval actions
            st.write("**🔄 Approval Actions:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**✅ Approve Entry**")
                approval_comments = st.text_area(
                    "Approval Comments (optional)", 
                    key=f"approve_comments_{approval['workflow_id']}",
                    placeholder="Optional comments for approval..."
                )
                
                if st.button(
                    "✅ APPROVE", 
                    key=f"approve_{approval['workflow_id']}", 
                    type="primary"
                ):
                    success, message = WorkflowEngine.approve_document_by_id(
                        approval['workflow_id'], 
                        current_user.username, 
                        approval_comments
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
            
            with col2:
                st.write("**❌ Reject Entry**")
                rejection_reason = st.text_area(
                    "Rejection Reason (required)", 
                    key=f"reject_reason_{approval['workflow_id']}",
                    placeholder="Please provide reason for rejection..."
                )
                
                if st.button(
                    "❌ REJECT", 
                    key=f"reject_{approval['workflow_id']}", 
                    disabled=not rejection_reason.strip()
                ):
                    success, message = WorkflowEngine.reject_document(
                        approval['workflow_id'], 
                        current_user.username, 
                        rejection_reason.strip()
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")

st.divider()

# Admin workflow display
if not show_user_dashboard:
    st.subheader(f"🌐 All Workflows ({len(all_workflows)})")
    
    if not all_workflows:
        st.info("📋 No workflows found for the selected criteria.")
    else:
        # Convert workflows to DataFrame for display
        workflow_data = []
        for workflow in all_workflows:
            status_icon = {
                "PENDING": "⏳",
                "APPROVED": "✅", 
                "REJECTED": "❌"
            }.get(workflow["status"], "❓")
            
            priority_icon = {
                "HIGH": "🔴",
                "NORMAL": "🟡",
                "LOW": "🟢"
            }.get(workflow["priority"], "🟡")
            
            workflow_data.append({
                "Status": f"{status_icon} {workflow['status']}",
                "Priority": f"{priority_icon} {workflow['priority']}",
                "Document": workflow["document_number"],
                "Company": workflow["company_code"],
                "Amount": f"${workflow['total_amount']:,.2f}",
                "Level": workflow["approval_level"] or "N/A",
                "Created By": workflow["created_by"],
                "Assigned To": workflow["assigned_to"] or "N/A",
                "Created": workflow["created_at"].strftime("%Y-%m-%d %H:%M") if workflow["created_at"] else "N/A",
                "Completed": workflow["completed_at"].strftime("%Y-%m-%d %H:%M") if workflow["completed_at"] else "N/A",
                "Reference": workflow["reference"] or "N/A"
            })
        
        # Display workflow table
        df_workflows = pd.DataFrame(workflow_data)
        st.dataframe(df_workflows, use_container_width=True, hide_index=True)
        
        # Workflow details expandable sections
        st.subheader("📋 Workflow Details")
        
        for i, workflow in enumerate(all_workflows):
            status_icon = {
                "PENDING": "⏳",
                "APPROVED": "✅", 
                "REJECTED": "❌"
            }.get(workflow["status"], "❓")
            
            overdue_text = " ⚠️ OVERDUE" if workflow.get('is_overdue', False) else ""
            
            with st.expander(
                f"{status_icon} {workflow['document_number']} | {workflow['company_code']} - "
                f"${workflow['total_amount']:,.2f} | {workflow['status']}{overdue_text}",
                expanded=False
            ):
                # Workflow details
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write("**📄 Document Info:**")
                    st.write(f"**Document:** {workflow['document_number']}")
                    st.write(f"**Company:** {workflow['company_code']}")
                    st.write(f"**Amount:** ${workflow['total_amount']:,.2f}")
                    st.write(f"**Currency:** {workflow['currency']}")
                    st.write(f"**Reference:** {workflow['reference'] or 'N/A'}")
                
                with col2:
                    st.write("**👥 People & Status:**")
                    st.write(f"**Status:** {workflow['status']}")
                    st.write(f"**Priority:** {workflow['priority']}")
                    st.write(f"**Created By:** {workflow['created_by']}")
                    st.write(f"**Assigned To:** {workflow['assigned_to'] or 'N/A'}")
                    st.write(f"**Approval Level:** {workflow['approval_level'] or 'N/A'}")
                
                with col3:
                    st.write("**📅 Timeline:**")
                    st.write(f"**Created:** {workflow['created_at'].strftime('%Y-%m-%d %H:%M') if workflow['created_at'] else 'N/A'}")
                    st.write(f"**Submitted:** {workflow['submitted_at'].strftime('%Y-%m-%d %H:%M') if workflow['submitted_at'] else 'N/A'}")
                    if workflow['completed_at']:
                        st.write(f"**Completed:** {workflow['completed_at'].strftime('%Y-%m-%d %H:%M')}")
                    if workflow['approved_at']:
                        st.write(f"**Approved:** {workflow['approved_at'].strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Approved By:** {workflow['approved_by']}")
                
                # Show comments if any
                if workflow.get('comments'):
                    st.write("**💬 Comments:**")
                    st.write(workflow['comments'])
                
                # Show journal entry lines for pending/recent workflows
                if workflow['status'] in ['PENDING', 'APPROVED', 'REJECTED']:
                    st.write("**📋 Journal Entry Lines:**")
                    try:
                        with engine.connect() as conn:
                            lines = conn.execute(text("""
                                SELECT linenumber, glaccountid, description, debitamount, creditamount, currencycode
                                FROM journalentryline
                                WHERE documentnumber = :doc AND companycodeid = :cc
                                ORDER BY linenumber
                            """), {"doc": workflow['document_number'], "cc": workflow['company_code']})
                            
                            lines_data = []
                            for line in lines:
                                lines_data.append({
                                    "Line": line[0],
                                    "GL Account": line[1],
                                    "Description": line[2],
                                    "Debit": f"${line[3]:,.2f}" if line[3] and line[3] > 0 else "",
                                    "Credit": f"${line[4]:,.2f}" if line[4] and line[4] > 0 else "",
                                    "Currency": line[5]
                                })
                            
                            if lines_data:
                                df_lines = pd.DataFrame(lines_data)
                                st.dataframe(df_lines, use_container_width=True, hide_index=True)
                            else:
                                st.info("No line items found")
                                
                    except Exception as e:
                        st.error(f"Error loading journal entry lines: {e}")
        
    st.divider()
    
    # Admin statistics
    st.subheader("📊 Workflow Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📈 Workflow Volume by Level**")
        if workflow_stats["level_breakdown"]:
            df_levels = pd.DataFrame(workflow_stats["level_breakdown"])
            st.dataframe(df_levels, use_container_width=True, hide_index=True)
        else:
            st.info("No level data available")
    
    with col2:
        st.write("**👥 Top Approvers (30 days)**")
        if workflow_stats["top_approvers"]:
            df_approvers = pd.DataFrame(workflow_stats["top_approvers"])
            df_approvers.columns = ["Approver", "Count"]
            st.dataframe(df_approvers, use_container_width=True, hide_index=True)
        else:
            st.info("No approver data available")

# Approval statistics and insights (for user view)
if show_user_dashboard:
    st.subheader("📊 Approval Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**📈 Approval Volume by Level**")
        try:
            with engine.connect() as conn:
                level_stats = conn.execute(text("""
                    SELECT al.level_name, COUNT(*) as approval_count
                    FROM approval_steps ast
                    JOIN approval_levels al ON al.id = ast.approval_level_id
                    WHERE ast.action_by = :user_id
                    AND ast.action_at >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY al.level_name
                    ORDER BY approval_count DESC
                """), {"user_id": current_user.username})
                
                level_data = []
                for row in level_stats:
                    level_data.append({"Level": row[0], "Count": row[1]})
                
                if level_data:
                    df_levels = pd.DataFrame(level_data)
                    st.dataframe(df_levels, use_container_width=True, hide_index=True)
                else:
                    st.info("No approval data for the last 30 days")
                    
        except Exception as e:
            st.error(f"Error loading level statistics: {e}")

    with col2:
        st.write("**⏱️ Average Approval Time**")
        try:
            with engine.connect() as conn:
                time_stats = conn.execute(text("""
                    SELECT 
                        AVG(EXTRACT(EPOCH FROM (ast.action_at - wi.created_at))/3600)::NUMERIC(10,2) as avg_hours,
                        MIN(EXTRACT(EPOCH FROM (ast.action_at - wi.created_at))/3600)::NUMERIC(10,2) as min_hours,
                        MAX(EXTRACT(EPOCH FROM (ast.action_at - wi.created_at))/3600)::NUMERIC(10,2) as max_hours
                    FROM approval_steps ast
                    JOIN workflow_instances wi ON wi.id = ast.workflow_instance_id
                    WHERE ast.action_by = :user_id
                    AND ast.action IS NOT NULL
                    AND ast.action_at >= CURRENT_DATE - INTERVAL '30 days'
                """), {"user_id": current_user.username}).fetchone()
                
                if time_stats and time_stats[0]:
                    st.metric("Average Time", f"{time_stats[0]:.1f} hours")
                    st.metric("Fastest Approval", f"{time_stats[1]:.1f} hours")
                    st.metric("Longest Approval", f"{time_stats[2]:.1f} hours")
                else:
                    st.info("No timing data available")
                    
        except Exception as e:
            st.error(f"Error loading timing statistics: {e}")

# Auto-refresh option
if (show_user_dashboard and pending_approvals) or (not show_user_dashboard and all_workflows):
    st.divider()
    if st.checkbox("🔄 Auto-refresh every 30 seconds"):
        st.rerun()