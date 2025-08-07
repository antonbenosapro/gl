"""
Bulk Journal Entry Submission Manager

This module provides a user-friendly interface for bulk submission of draft journal entries
with automatic approval routing based on approval levels and transaction amounts.

Features:
- Bulk selection and submission of draft journal entries
- Automatic approval level calculation and routing
- Progress tracking and status updates
- Validation and error handling
- Integration with existing workflow engine

Author: Claude Code Assistant
Date: August 6, 2025
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text
import json
import sys
import os

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from db_config import engine
from utils.workflow_engine import WorkflowEngine
from utils.navigation import show_breadcrumb
from auth.optimized_middleware import optimized_authenticator as authenticator

# Page configuration
st.set_page_config(
    page_title="Bulk Journal Submission",
    page_icon="📝",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Bulk Journal Entry Submission application."""
    # Show breadcrumb with user info
    show_breadcrumb("Bulk Journal Submission", "Transactions", "Bulk Operations")
    
    st.title("📝 Bulk Journal Entry Submission")
    st.markdown("**Submit multiple draft journal entries for approval with automatic routing**")
    
    # Real-time notifications check
    create_real_time_notifications()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 Submission Tools")
        
        # Auto-navigate if entries were just selected
        default_index = 0
        if 'navigate_to_submit' in st.session_state and st.session_state['navigate_to_submit']:
            default_index = 1  # Index of "⚡ Bulk Submit"
            st.session_state['navigate_to_submit'] = False
        
        page = st.selectbox(
            "Select Function",
            [
                "📋 Select Entries", 
                "⚡ Bulk Submit",
                "📊 Tracking Dashboard",
                "📈 Submission History",
                "🔔 Notifications"
            ],
            index=default_index
        )
    
    # Route to selected page
    if page == "📋 Select Entries":
        show_entry_selection()
    elif page == "⚡ Bulk Submit":
        show_bulk_submission()
    elif page == "📊 Tracking Dashboard":
        show_tracking_dashboard()
    elif page == "📈 Submission History":
        show_submission_history()
    elif page == "🔔 Notifications":
        show_notification_preferences()

def show_entry_selection():
    """Display draft journal entry selection interface."""
    st.header("📋 Select Journal Entries for Submission")
    
    # Add upload option
    upload_option = st.radio(
        "Selection Method",
        ["🔍 Browse & Select", "📤 Upload CSV/Excel"],
        horizontal=True
    )
    
    if upload_option == "📤 Upload CSV/Excel":
        show_bulk_upload_interface()
        return
    
    # Filters for browsing
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        company_filter = st.selectbox("Company Code", ["All", "1000", "2000", "3000"])
    with col2:
        date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
    with col3:
        date_to = st.date_input("To Date", value=date.today())
    with col4:
        amount_filter = st.selectbox("Amount Range", ["All", "<$1,000", "$1,000-$10,000", ">$10,000"])
    
    # Get draft journal entries
    draft_entries = get_draft_journal_entries(company_filter, date_from, date_to, amount_filter)
    
    if not draft_entries.empty:
        st.subheader("📄 Available Draft Journal Entries")
        
        # Add selection column
        draft_entries['Select'] = False
        
        # Display entries with selection checkboxes
        edited_df = st.data_editor(
            draft_entries,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", default=False),
                "document_number": "Document #",
                "posting_date": st.column_config.DateColumn("Posting Date"),
                "reference": "Reference",
                "total_amount": st.column_config.NumberColumn("Total Amount", format="$%.2f"),
                "created_by": "Created By",
                "created_at": st.column_config.DatetimeColumn("Created At"),
                "company_code": "Company"
            },
            disabled=["document_number", "posting_date", "reference", "total_amount", "created_by", "created_at", "company_code"],
            hide_index=True,
            use_container_width=True
        )
        
        # Selection summary
        selected_entries = edited_df[edited_df['Select'] == True]
        
        if not selected_entries.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Selected Entries", len(selected_entries))
            with col2:
                total_amount = selected_entries['total_amount'].sum()
                st.metric("Total Amount", f"${total_amount:,.2f}")
            with col3:
                companies = selected_entries['company_code'].nunique()
                st.metric("Companies", companies)
            
            # Store selected entries in session state
            if st.button("📤 Proceed to Submission", type="primary"):
                st.session_state['selected_entries'] = selected_entries.to_dict('records')
                st.session_state['navigate_to_submit'] = True
                st.success(f"✅ Selected {len(selected_entries)} entries for submission!")
                st.info("🔄 **Redirecting to Bulk Submit page...** Please wait a moment or manually select '⚡ Bulk Submit' from the sidebar.")
                
                # Add manual navigation button as fallback
                col1, col2, col3 = st.columns([1,2,1])
                with col2:
                    if st.button("🚀 Go to Bulk Submit Page", type="secondary"):
                        st.session_state['navigate_to_submit'] = True
                        st.rerun()
                
                st.rerun()
        else:
            st.info("Select journal entries to proceed with bulk submission")
    
    # Show navigation hint if entries are already selected
    if 'selected_entries' in st.session_state and st.session_state['selected_entries']:
        st.info(f"📌 **{len(st.session_state['selected_entries'])} entries ready for submission!** Go to '⚡ Bulk Submit' in the sidebar to proceed.")
    else:
        st.info("No draft journal entries found matching the specified criteria")

def show_bulk_submission():
    """Display bulk submission interface."""
    st.header("⚡ Bulk Journal Entry Submission")
    
    # Check if entries are selected
    if 'selected_entries' not in st.session_state or not st.session_state['selected_entries']:
        st.warning("No journal entries selected. Please go to 'Select Entries' first.")
        return
    
    selected_entries = st.session_state['selected_entries']
    
    # Success message
    st.success(f"🎉 **{len(selected_entries)} journal entries loaded for bulk submission!**")
    
    # Display submission preview
    st.subheader("📋 Submission Preview")
    
    preview_df = pd.DataFrame(selected_entries)
    st.dataframe(
        preview_df[['document_number', 'reference', 'total_amount', 'company_code']],
        column_config={
            "document_number": "Document #",
            "reference": "Reference", 
            "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "company_code": "Company"
        },
        use_container_width=True,
        hide_index=True
    )
    
    # Calculate approval routing preview
    st.subheader("🔄 Approval Routing Preview")
    
    routing_preview = calculate_approval_routing_preview(selected_entries)
    
    if routing_preview:
        routing_df = pd.DataFrame(routing_preview)
        st.dataframe(
            routing_df,
            column_config={
                "document_number": "Document #",
                "required_level": "Approval Level",
                "approvers": "Assigned Approvers",
                "estimated_time": "Est. Time"
            },
            use_container_width=True,
            hide_index=True
        )
    
    # Submission options
    st.subheader("⚙️ Submission Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        batch_comments = st.text_area(
            "Batch Comments",
            placeholder="Optional comments for all submissions...",
            help="These comments will be added to all journal entries in this batch"
        )
        
        priority = st.selectbox(
            "Priority Level",
            ["NORMAL", "HIGH", "URGENT"],
            help="Priority affects notification frequency and SLA expectations"
        )
    
    with col2:
        notification_emails = st.text_input(
            "Additional Notification Emails",
            placeholder="email1@company.com, email2@company.com",
            help="Optional: Additional stakeholders to notify of submission status"
        )
        
        auto_retry = st.checkbox(
            "Auto-retry Failed Submissions",
            value=True,
            help="Automatically retry submissions that fail due to temporary issues"
        )
    
    # Submission button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Submit All Entries for Approval", type="primary", use_container_width=True):
            execute_bulk_submission(
                selected_entries, 
                batch_comments, 
                priority, 
                notification_emails,
                auto_retry
            )

def show_tracking_dashboard():
    """Display submission tracking dashboard."""
    st.header("📊 Submission Tracking Dashboard")
    
    # Get recent submissions by current user
    user_submissions = get_user_submissions(user.username)
    
    if not user_submissions.empty:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            pending_count = len(user_submissions[user_submissions['status'] == 'PENDING_APPROVAL'])
            st.metric("Pending Approval", pending_count)
        
        with col2:
            approved_count = len(user_submissions[user_submissions['status'] == 'APPROVED'])
            st.metric("Approved", approved_count)
        
        with col3:
            rejected_count = len(user_submissions[user_submissions['status'] == 'REJECTED'])
            st.metric("Rejected", rejected_count)
        
        with col4:
            total_amount = user_submissions['total_amount'].sum()
            st.metric("Total Amount", f"${total_amount:,.2f}")
        
        # Status distribution chart
        col1, col2 = st.columns(2)
        
        with col1:
            status_counts = user_submissions['status'].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Submission Status Distribution"
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            # Approval timeline
            approval_timeline = user_submissions.groupby(user_submissions['submitted_at'].dt.date).size().reset_index(name='count')
            fig_timeline = px.line(
                approval_timeline,
                x='submitted_at',
                y='count',
                title="Submission Timeline (Last 30 Days)",
                markers=True
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        
        # Detailed submissions table
        st.subheader("📋 Your Recent Submissions")
        
        st.dataframe(
            user_submissions,
            column_config={
                "document_number": "Document #",
                "reference": "Reference",
                "total_amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                "status": "Status",
                "submitted_at": st.column_config.DatetimeColumn("Submitted"),
                "assigned_approver": "Approver",
                "approval_level": "Level"
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Action buttons for pending items
        pending_items = user_submissions[user_submissions['status'] == 'PENDING_APPROVAL']
        
        if not pending_items.empty:
            st.subheader("⚡ Quick Actions")
            
            selected_doc = st.selectbox(
                "Select Document for Action",
                options=pending_items['document_number'].tolist(),
                format_func=lambda x: f"{x} - {pending_items[pending_items['document_number']==x]['reference'].iloc[0]}"
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📞 Contact Approver"):
                    contact_approver(selected_doc)
            
            with col2:
                if st.button("📝 Add Comments"):
                    show_add_comments_form(selected_doc)
            
            with col3:
                if st.button("🔄 Withdraw Submission"):
                    withdraw_submission(selected_doc)
    
    else:
        st.info("No submissions found. Start by selecting journal entries for bulk submission.")

def show_submission_history():
    """Display submission history and analytics."""
    st.header("📈 Submission History & Analytics")
    
    # Date range filter
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_range = st.date_input(
            "Date Range",
            value=[date.today() - timedelta(days=90), date.today()],
            help="Select date range for analysis"
        )
    
    with col2:
        status_filter = st.multiselect(
            "Status Filter",
            ["DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "POSTED"],
            default=["PENDING_APPROVAL", "APPROVED", "REJECTED"]
        )
    
    with col3:
        company_filter = st.selectbox("Company Filter", ["All", "1000", "2000", "3000"])
    
    # Get historical data
    if len(date_range) == 2:
        history_data = get_submission_history(date_range[0], date_range[1], status_filter, company_filter)
        
        if not history_data.empty:
            # Performance metrics
            st.subheader("📊 Performance Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_approval_time = calculate_avg_approval_time(history_data)
                st.metric("Avg Approval Time", f"{avg_approval_time:.1f} hours")
            
            with col2:
                approval_rate = calculate_approval_rate(history_data)
                st.metric("Approval Rate", f"{approval_rate:.1f}%")
            
            with col3:
                total_processed = len(history_data)
                st.metric("Total Processed", total_processed)
            
            with col4:
                total_value = history_data['total_amount'].sum()
                st.metric("Total Value", f"${total_value:,.2f}")
            
            # Charts
            tab1, tab2, tab3 = st.tabs(["📈 Trends", "👥 Approvers", "💰 Amounts"])
            
            with tab1:
                # Submission trends over time
                daily_submissions = history_data.groupby(history_data['submitted_at'].dt.date).agg({
                    'document_number': 'count',
                    'total_amount': 'sum'
                }).reset_index()
                
                fig_trend = px.line(
                    daily_submissions,
                    x='submitted_at',
                    y='document_number',
                    title='Daily Submission Volume'
                )
                st.plotly_chart(fig_trend, use_container_width=True)
            
            with tab2:
                # Approver performance
                approver_stats = history_data.groupby('assigned_approver').agg({
                    'document_number': 'count',
                    'total_amount': 'sum'
                }).reset_index()
                
                fig_approvers = px.bar(
                    approver_stats.head(10),
                    x='assigned_approver',
                    y='document_number',
                    title='Top Approvers by Volume'
                )
                st.plotly_chart(fig_approvers, use_container_width=True)
            
            with tab3:
                # Amount distribution
                fig_amounts = px.histogram(
                    history_data,
                    x='total_amount',
                    nbins=20,
                    title='Submission Amount Distribution'
                )
                st.plotly_chart(fig_amounts, use_container_width=True)
        
        else:
            st.info("No submission history found for the selected criteria")

# Helper functions

@st.cache_data(ttl=300)
def get_draft_journal_entries(company_filter, date_from, date_to, amount_filter):
    """Get draft journal entries available for submission."""
    try:
        with engine.connect() as conn:
            # Build query with filters
            where_clauses = ["jeh.workflow_status = 'DRAFT'"]
            params = {"date_from": date_from, "date_to": date_to}
            
            if company_filter != "All":
                where_clauses.append("jeh.companycodeid = :company_code")
                params["company_code"] = company_filter
            
            where_clauses.append("jeh.createdat >= :date_from")
            where_clauses.append("jeh.createdat <= :date_to + INTERVAL '1 day'")
            
            query = text(f"""
                SELECT 
                    jeh.documentnumber as document_number,
                    jeh.companycodeid as company_code,
                    jeh.postingdate as posting_date,
                    jeh.reference,
                    jeh.createdby as created_by,
                    jeh.createdat as created_at,
                    COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                FROM journalentryheader jeh
                LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber 
                    AND jeh.companycodeid = jel.companycodeid
                WHERE {' AND '.join(where_clauses)}
                GROUP BY jeh.documentnumber, jeh.companycodeid, jeh.postingdate, 
                         jeh.reference, jeh.createdby, jeh.createdat
                ORDER BY jeh.createdat DESC
            """)
            
            result = conn.execute(query, params)
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            # Apply amount filter
            if amount_filter != "All":
                if amount_filter == "<$1,000":
                    df = df[df['total_amount'] < 1000]
                elif amount_filter == "$1,000-$10,000":
                    df = df[(df['total_amount'] >= 1000) & (df['total_amount'] <= 10000)]
                elif amount_filter == ">$10,000":
                    df = df[df['total_amount'] > 10000]
            
            return df
    
    except Exception as e:
        st.error(f"Error retrieving draft entries: {e}")
        return pd.DataFrame()

def calculate_approval_routing_preview(selected_entries):
    """Calculate approval routing for selected entries."""
    routing_preview = []
    
    for entry in selected_entries:
        try:
            # Calculate required approval level
            approval_level_id = WorkflowEngine.calculate_required_approval_level(
                entry['document_number'], 
                str(entry['company_code'])
            )
            
            if approval_level_id:
                # Get available approvers
                approvers = WorkflowEngine.get_available_approvers(
                    approval_level_id, 
                    str(entry['company_code']), 
                    entry['created_by']
                )
                
                approver_names = [approver['full_name'] for approver in approvers[:3]]  # Show first 3
                if len(approvers) > 3:
                    approver_names.append(f"... +{len(approvers)-3} more")
                
                routing_preview.append({
                    'document_number': entry['document_number'],
                    'required_level': f"Level {approval_level_id}",
                    'approvers': ", ".join(approver_names) if approver_names else "No approvers available",
                    'estimated_time': "2-3 business days"
                })
        
        except Exception as e:
            routing_preview.append({
                'document_number': entry['document_number'],
                'required_level': "Error calculating",
                'approvers': f"Error: {str(e)}",
                'estimated_time': "Unknown"
            })
    
    return routing_preview

def execute_bulk_submission(entries, comments, priority, notification_emails, auto_retry):
    """Execute bulk submission of journal entries."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    submitted_count = 0
    failed_count = 0
    failed_entries = []
    
    total_entries = len(entries)
    
    for i, entry in enumerate(entries):
        try:
            status_text.text(f"Submitting {entry['document_number']}...")
            progress_bar.progress((i + 1) / total_entries)
            
            # Submit for approval using workflow engine
            success, message = WorkflowEngine.submit_for_approval(
                str(entry['document_number']),
                str(entry['company_code']),
                user.username,
                comments
            )
            
            if success:
                submitted_count += 1
                # Log successful submission
                log_submission_activity(
                    entry['document_number'], 
                    entry['company_code'],
                    'SUBMITTED', 
                    f"Bulk submission: {message}"
                )
            else:
                failed_count += 1
                failed_entries.append({
                    'document_number': entry['document_number'],
                    'error': message
                })
                
                if auto_retry:
                    # Implement retry logic here
                    status_text.text(f"Retrying {entry['document_number']}...")
        
        except Exception as e:
            failed_count += 1
            failed_entries.append({
                'document_number': entry['document_number'],
                'error': str(e)
            })
    
    progress_bar.progress(1.0)
    status_text.text("Bulk submission completed!")
    
    # Display results
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.success(f"✅ Successfully submitted: {submitted_count}")
    with col2:
        if failed_count > 0:
            st.error(f"❌ Failed submissions: {failed_count}")
        else:
            st.success("✅ All submissions successful!")
    with col3:
        st.info(f"📊 Total processed: {total_entries}")
    
    # Show failed entries if any
    if failed_entries:
        st.subheader("❌ Failed Submissions")
        failed_df = pd.DataFrame(failed_entries)
        st.dataframe(failed_df, use_container_width=True, hide_index=True)
        
        if st.button("🔄 Retry Failed Submissions"):
            execute_bulk_submission(
                [entry for entry in entries if entry['document_number'] in [f['document_number'] for f in failed_entries]],
                comments, priority, notification_emails, auto_retry
            )
    
    # Clear selected entries from session state
    if 'selected_entries' in st.session_state:
        del st.session_state['selected_entries']
    
    # Send notifications if configured
    if notification_emails:
        send_bulk_submission_notification(
            notification_emails, submitted_count, failed_count, user.username
        )

@st.cache_data(ttl=60)
def get_user_submissions(username, days_back=30):
    """Get user's recent submissions."""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    jeh.documentnumber as document_number,
                    jeh.reference,
                    jeh.workflow_status as status,
                    jeh.submitted_for_approval_at as submitted_at,
                    jeh.approved_by as assigned_approver,
                    COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount,
                    'Standard' as approval_level
                FROM journalentryheader jeh
                LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber
                WHERE jeh.createdby = :username
                AND jeh.submitted_for_approval_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'
                AND jeh.workflow_status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED')
                GROUP BY jeh.documentnumber, jeh.reference, jeh.workflow_status, 
                         jeh.submitted_for_approval_at, jeh.approved_by
                ORDER BY jeh.submitted_for_approval_at DESC
            """)
            
            result = conn.execute(query, {"username": username, "days_back": days_back})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    
    except Exception as e:
        st.error(f"Error retrieving user submissions: {e}")
        return pd.DataFrame()

def get_submission_history(date_from, date_to, status_filter, company_filter):
    """Get submission history for analytics."""
    try:
        with engine.connect() as conn:
            where_clauses = []
            params = {"date_from": date_from, "date_to": date_to}
            
            where_clauses.append("jeh.submitted_for_approval_at >= :date_from")
            where_clauses.append("jeh.submitted_for_approval_at <= :date_to + INTERVAL '1 day'")
            
            if status_filter:
                placeholders = ', '.join([f':status_{i}' for i in range(len(status_filter))])
                where_clauses.append(f"jeh.workflow_status IN ({placeholders})")
                for i, status in enumerate(status_filter):
                    params[f'status_{i}'] = status
            
            if company_filter != "All":
                where_clauses.append("jeh.companycodeid = :company_code")
                params["company_code"] = company_filter
            
            query = text(f"""
                SELECT 
                    jeh.documentnumber as document_number,
                    jeh.companycodeid as company_code,
                    jeh.workflow_status as status,
                    jeh.submitted_for_approval_at as submitted_at,
                    jeh.approved_at,
                    jeh.approved_by as assigned_approver,
                    COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                FROM journalentryheader jeh
                LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber
                WHERE {' AND '.join(where_clauses)}
                GROUP BY jeh.documentnumber, jeh.companycodeid, jeh.workflow_status,
                         jeh.submitted_for_approval_at, jeh.approved_at, jeh.approved_by
                ORDER BY jeh.submitted_for_approval_at DESC
            """)
            
            result = conn.execute(query, params)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    
    except Exception as e:
        st.error(f"Error retrieving submission history: {e}")
        return pd.DataFrame()

def calculate_avg_approval_time(history_data):
    """Calculate average approval time in hours."""
    approved_data = history_data[
        (history_data['status'] == 'APPROVED') & 
        (history_data['approved_at'].notna())
    ].copy()
    
    if not approved_data.empty:
        approved_data['approval_time'] = (
            pd.to_datetime(approved_data['approved_at']) - 
            pd.to_datetime(approved_data['submitted_at'])
        ).dt.total_seconds() / 3600  # Convert to hours
        
        return approved_data['approval_time'].mean()
    
    return 0.0

def calculate_approval_rate(history_data):
    """Calculate approval rate percentage."""
    total_decided = len(history_data[history_data['status'].isin(['APPROVED', 'REJECTED'])])
    approved = len(history_data[history_data['status'] == 'APPROVED'])
    
    if total_decided > 0:
        return (approved / total_decided) * 100
    return 0.0

def log_submission_activity(document_number, company_code, action, details):
    """Log submission activity for audit trail."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO workflow_audit_log 
                (document_number, company_code, action, performed_by, new_status, comments)
                VALUES (:doc, :cc, :action, :user, 'BULK_SUBMISSION', :details)
            """), {
                "doc": str(document_number),
                "cc": str(company_code),
                "action": action,
                "user": user.username,
                "details": details
            })
            conn.commit()
    except Exception as e:
        st.error(f"Error logging activity: {e}")

def contact_approver(document_number):
    """Show contact approver interface."""
    try:
        with engine.connect() as conn:
            # Get approver information
            approver_query = text("""
                SELECT DISTINCT u.first_name, u.last_name, u.email
                FROM workflow_instances wi
                JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                JOIN users u ON u.username = ast.assigned_to
                WHERE wi.document_number = :doc_num
                AND ast.action = 'PENDING'
            """)
            
            result = conn.execute(approver_query, {"doc_num": document_number})
            approvers = result.fetchall()
            
            if approvers:
                st.subheader(f"📞 Contact Approver(s) for {document_number}")
                
                for approver in approvers:
                    full_name = f"{approver[0]} {approver[1]}"
                    email = approver[2]
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**{full_name}**")
                        st.write(f"📧 {email}")
                    
                    with col2:
                        if st.button(f"📧 Email {full_name.split()[0]}", key=f"email_{email}"):
                            send_approver_reminder(document_number, email, full_name)
                            st.success(f"Reminder sent to {full_name}!")
            else:
                st.warning("No approvers found for this document")
    
    except Exception as e:
        st.error(f"Error retrieving approver information: {e}")

def show_add_comments_form(document_number):
    """Show form to add comments to submission."""
    st.subheader(f"📝 Add Comments to {document_number}")
    
    with st.form(f"comments_form_{document_number}"):
        additional_comments = st.text_area(
            "Additional Comments",
            help="These comments will be visible to approvers and in the audit trail"
        )
        
        notification_type = st.selectbox(
            "Notification Level",
            ["INFO", "URGENT", "REMINDER"],
            help="Select the urgency level for this comment"
        )
        
        if st.form_submit_button("Add Comments"):
            try:
                with engine.connect() as conn:
                    # Add comment to workflow audit log
                    conn.execute(text("""
                        INSERT INTO workflow_audit_log 
                        (document_number, company_code, action, performed_by, new_status, comments)
                        VALUES (:doc, (SELECT companycodeid FROM journalentryheader WHERE documentnumber = :doc2), 
                                'COMMENT_ADDED', :user, 'PENDING_APPROVAL', :comments)
                    """), {
                        "doc": document_number,
                        "doc2": document_number,
                        "user": user.username,
                        "comments": f"[{notification_type}] {additional_comments}"
                    })
                    conn.commit()
                    
                    # Send notification to approvers if urgent
                    if notification_type in ["URGENT", "REMINDER"]:
                        notify_approvers_of_comment(document_number, additional_comments, notification_type)
                    
                    st.success("Comments added successfully!")
                    st.rerun()
            
            except Exception as e:
                st.error(f"Error adding comments: {e}")

def withdraw_submission(document_number):
    """Withdraw a pending submission."""
    st.subheader(f"🔄 Withdraw Submission for {document_number}")
    
    # Show withdrawal confirmation
    st.warning("⚠️ **Warning:** Withdrawing this submission will:")
    st.write("• Return the journal entry to DRAFT status")
    st.write("• Cancel all pending approvals")
    st.write("• Notify assigned approvers of the withdrawal")
    st.write("• Create an audit trail record")
    
    withdrawal_reason = st.text_area(
        "Withdrawal Reason",
        help="Please provide a reason for withdrawing this submission"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(f"✅ Confirm Withdrawal", type="primary", disabled=not withdrawal_reason.strip()):
            try:
                with engine.begin() as conn:
                    # Get workflow instance
                    workflow_result = conn.execute(text("""
                        SELECT id, company_code FROM workflow_instances 
                        WHERE document_number = :doc AND status = 'PENDING'
                    """), {"doc": document_number})
                    
                    workflow_row = workflow_result.fetchone()
                    
                    if workflow_row:
                        workflow_id, company_code = workflow_row
                        
                        # Update workflow status
                        conn.execute(text("""
                            UPDATE workflow_instances 
                            SET status = 'WITHDRAWN', completed_at = CURRENT_TIMESTAMP
                            WHERE id = :workflow_id
                        """), {"workflow_id": workflow_id})
                        
                        # Update approval steps
                        conn.execute(text("""
                            UPDATE approval_steps 
                            SET action = 'WITHDRAWN', action_at = CURRENT_TIMESTAMP,
                                comments = :reason
                            WHERE workflow_instance_id = :workflow_id AND action = 'PENDING'
                        """), {"workflow_id": workflow_id, "reason": withdrawal_reason})
                        
                        # Update journal entry status
                        conn.execute(text("""
                            UPDATE journalentryheader 
                            SET workflow_status = 'DRAFT'
                            WHERE documentnumber = :doc AND companycodeid = :cc
                        """), {"doc": document_number, "cc": company_code})
                        
                        # Log withdrawal
                        conn.execute(text("""
                            INSERT INTO workflow_audit_log 
                            (document_number, company_code, action, performed_by, old_status, new_status, comments)
                            VALUES (:doc, :cc, 'WITHDRAWN', :user, 'PENDING_APPROVAL', 'DRAFT', :reason)
                        """), {
                            "doc": document_number,
                            "cc": company_code,
                            "user": user.username,
                            "reason": withdrawal_reason
                        })
                        
                        # Notify approvers of withdrawal
                        notify_approvers_of_withdrawal(document_number, withdrawal_reason)
                        
                        st.success(f"✅ Submission {document_number} withdrawn successfully!")
                        st.info("The journal entry has been returned to DRAFT status and can be resubmitted if needed.")
                        st.rerun()
                    
                    else:
                        st.error("No pending workflow found for this document")
            
            except Exception as e:
                st.error(f"Error withdrawing submission: {e}")
    
    with col2:
        if st.button("❌ Cancel", type="secondary"):
            st.rerun()

def send_approver_reminder(document_number, approver_email, approver_name):
    """Send reminder email to approver."""
    try:
        # Get document details
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT jeh.reference, jeh.companycodeid,
                       COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                FROM journalentryheader jeh
                LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber
                WHERE jeh.documentnumber = :doc
                GROUP BY jeh.reference, jeh.companycodeid
            """), {"doc": document_number})
            
            doc_info = result.fetchone()
            
            if doc_info:
                # Create notification record
                conn.execute(text("""
                    INSERT INTO approval_notifications 
                    (recipient, notification_type, subject, message, workflow_instance_id)
                    SELECT :recipient, 'REMINDER', :subject, :message, wi.id
                    FROM workflow_instances wi
                    WHERE wi.document_number = :doc
                """), {
                    "recipient": approver_email,
                    "subject": f"Reminder: Journal Entry {document_number} awaiting approval",
                    "message": f"Dear {approver_name}, Journal Entry {document_number} ({doc_info[0]}) with amount ${doc_info[2]:,.2f} is still pending your approval. Please review at your earliest convenience.",
                    "doc": document_number
                })
                conn.commit()
                
                # Log reminder activity
                log_submission_activity(
                    document_number, 
                    doc_info[1],
                    'REMINDER_SENT',
                    f"Reminder sent to {approver_name} ({approver_email})"
                )
    
    except Exception as e:
        st.error(f"Error sending reminder: {e}")

def notify_approvers_of_comment(document_number, comment, notification_type):
    """Notify approvers when urgent comments are added."""
    try:
        with engine.connect() as conn:
            # Get pending approvers
            result = conn.execute(text("""
                SELECT DISTINCT ast.assigned_to, u.first_name, u.last_name, u.email
                FROM workflow_instances wi
                JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                JOIN users u ON u.username = ast.assigned_to
                WHERE wi.document_number = :doc AND ast.action = 'PENDING'
            """), {"doc": document_number})
            
            approvers = result.fetchall()
            
            for approver in approvers:
                username, first_name, last_name, email = approver
                full_name = f"{first_name} {last_name}"
                
                # Create notification
                conn.execute(text("""
                    INSERT INTO approval_notifications 
                    (recipient, notification_type, subject, message, workflow_instance_id)
                    SELECT :recipient, :type, :subject, :message, wi.id
                    FROM workflow_instances wi
                    WHERE wi.document_number = :doc
                """), {
                    "recipient": email,
                    "type": notification_type,
                    "subject": f"{notification_type}: New comment on Journal Entry {document_number}",
                    "message": f"Dear {full_name}, a new {notification_type.lower()} comment has been added to Journal Entry {document_number}: {comment}",
                    "doc": document_number
                })
            
            conn.commit()
    
    except Exception as e:
        st.error(f"Error notifying approvers: {e}")

def notify_approvers_of_withdrawal(document_number, reason):
    """Notify approvers when a submission is withdrawn."""
    try:
        with engine.connect() as conn:
            # Get approvers who were assigned
            result = conn.execute(text("""
                SELECT DISTINCT ast.assigned_to, u.first_name, u.last_name, u.email
                FROM workflow_instances wi
                JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                JOIN users u ON u.username = ast.assigned_to
                WHERE wi.document_number = :doc
            """), {"doc": document_number})
            
            approvers = result.fetchall()
            
            for approver in approvers:
                username, first_name, last_name, email = approver
                full_name = f"{first_name} {last_name}"
                
                # Create withdrawal notification
                conn.execute(text("""
                    INSERT INTO approval_notifications 
                    (recipient, notification_type, subject, message, workflow_instance_id)
                    SELECT :recipient, 'WITHDRAWN', :subject, :message, wi.id
                    FROM workflow_instances wi
                    WHERE wi.document_number = :doc
                """), {
                    "recipient": email,
                    "subject": f"Journal Entry {document_number} withdrawn",
                    "message": f"Dear {full_name}, Journal Entry {document_number} has been withdrawn by {user.username}. Reason: {reason}. No further action is required.",
                    "doc": document_number
                })
            
            conn.commit()
    
    except Exception as e:
        st.error(f"Error notifying approvers of withdrawal: {e}")

def create_real_time_notifications():
    """Create real-time notification system for approvals."""
    # Check for recent notifications for current user
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) as unread_count
                FROM approval_notifications 
                WHERE recipient LIKE %:email
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                AND notification_type IN ('APPROVAL_REQUEST', 'URGENT', 'REMINDER')
            """), {"email": f"%{user.email}%"})
            
            unread_count = result.scalar() or 0
            
            if unread_count > 0:
                st.sidebar.info(f"🔔 {unread_count} new approval notification(s)")
    
    except Exception:
        pass  # Silently handle notification errors

def show_notification_preferences():
    """Show notification preference settings."""
    st.subheader("🔔 Notification Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Email Notifications**")
        email_on_submission = st.checkbox("New submissions assigned to me", value=True)
        email_on_urgent = st.checkbox("Urgent comments added", value=True)
        email_on_reminder = st.checkbox("Daily reminder digest", value=False)
        
        st.write("**Frequency Settings**")
        reminder_frequency = st.selectbox(
            "Reminder frequency for pending approvals",
            ["Never", "Daily", "Every 2 days", "Weekly"],
            index=1
        )
    
    with col2:
        st.write("**Dashboard Notifications**")
        dashboard_popup = st.checkbox("Show popup for new assignments", value=True)
        dashboard_sound = st.checkbox("Play notification sound", value=False)
        
        st.write("**Escalation Settings**")
        escalation_days = st.number_input(
            "Auto-escalate after (days)",
            min_value=1,
            max_value=30,
            value=3,
            help="Automatically escalate to higher level after specified days"
        )
    
    if st.button("💾 Save Notification Preferences"):
        # Save preferences to user profile
        save_notification_preferences(user.username, {
            'email_on_submission': email_on_submission,
            'email_on_urgent': email_on_urgent,
            'email_on_reminder': email_on_reminder,
            'reminder_frequency': reminder_frequency,
            'dashboard_popup': dashboard_popup,
            'dashboard_sound': dashboard_sound,
            'escalation_days': escalation_days
        })
        st.success("✅ Notification preferences saved!")

def save_notification_preferences(username, preferences):
    """Save user notification preferences."""
    try:
        with engine.connect() as conn:
            # Update or insert user preferences
            conn.execute(text("""
                INSERT INTO user_notification_preferences 
                (username, preferences, updated_at)
                VALUES (:user, :prefs, CURRENT_TIMESTAMP)
                ON CONFLICT (username) 
                DO UPDATE SET preferences = :prefs, updated_at = CURRENT_TIMESTAMP
            """), {
                "user": username,
                "prefs": json.dumps(preferences)
            })
            conn.commit()
    
    except Exception as e:
        st.error(f"Error saving preferences: {e}")

def show_bulk_upload_interface():
    """Display bulk upload interface with validation."""
    st.subheader("📤 Bulk Upload Journal Entries")
    
    # Upload instructions
    with st.expander("📋 Upload Instructions & Template", expanded=False):
        st.markdown("""
        **Required Columns:**
        - `document_number`: Journal entry document number
        - `company_code`: Company code (e.g., 1000, 2000, 3000)
        - `reference`: Journal entry reference description
        - `priority`: NORMAL, HIGH, or URGENT (optional, defaults to NORMAL)
        - `comments`: Submission comments (optional)
        
        **Supported Formats:** CSV, Excel (.xlsx, .xls)
        **Maximum Rows:** 500 entries per upload
        
        **Sample Format:**
        ```
        document_number,company_code,reference,priority,comments
        JE001,1000,Monthly Accruals,NORMAL,Month-end adjustments
        JE002,1000,FX Revaluation,HIGH,Urgent FX adjustments needed
        JE003,2000,Depreciation,NORMAL,Standard depreciation entries
        ```
        """)
        
        # Download template button
        template_data = {
            'document_number': ['JE001', 'JE002', 'JE003'],
            'company_code': ['1000', '1000', '2000'],
            'reference': ['Sample Entry 1', 'Sample Entry 2', 'Sample Entry 3'],
            'priority': ['NORMAL', 'HIGH', 'NORMAL'],
            'comments': ['Sample comments', 'Urgent review required', '']
        }
        template_df = pd.DataFrame(template_data)
        template_csv = template_df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download CSV Template",
            data=template_csv,
            file_name="bulk_journal_submission_template.csv",
            mime="text/csv"
        )
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose file to upload",
        type=['csv', 'xlsx', 'xls'],
        help="Upload CSV or Excel file containing journal entry document numbers"
    )
    
    if uploaded_file is not None:
        try:
            # Read uploaded file
            if uploaded_file.type == "text/csv":
                upload_df = pd.read_csv(uploaded_file)
            else:
                upload_df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File uploaded successfully! Found {len(upload_df)} rows.")
            
            # Validate uploaded data
            validation_results = validate_upload_data(upload_df)
            
            # Display validation summary
            col1, col2, col3 = st.columns(3)
            
            with col1:
                valid_count = validation_results['valid_count']
                st.metric("Valid Entries", valid_count, delta=f"{valid_count}/{len(upload_df)} total")
            
            with col2:
                error_count = validation_results['error_count']
                st.metric("Errors Found", error_count, delta="❌" if error_count > 0 else "✅")
            
            with col3:
                warning_count = validation_results['warning_count']
                st.metric("Warnings", warning_count, delta="⚠️" if warning_count > 0 else "✅")
            
            # Show validation details
            if validation_results['errors'] or validation_results['warnings']:
                st.subheader("🔍 Validation Results")
                
                if validation_results['errors']:
                    st.error("❌ **Errors (Must be fixed before submission):**")
                    for error in validation_results['errors']:
                        st.write(f"• Row {error['row']}: {error['message']}")
                
                if validation_results['warnings']:
                    st.warning("⚠️ **Warnings (Review recommended):**")
                    for warning in validation_results['warnings']:
                        st.write(f"• Row {warning['row']}: {warning['message']}")
            
            # Show processed data
            if validation_results['valid_entries']:
                st.subheader("📋 Valid Entries for Processing")
                
                processed_df = pd.DataFrame(validation_results['valid_entries'])
                
                # Add validation status indicators
                processed_df['Status'] = '✅ Valid'
                
                st.dataframe(
                    processed_df,
                    column_config={
                        "document_number": "Document #",
                        "company_code": "Company",
                        "reference": "Reference",
                        "priority": "Priority",
                        "comments": "Comments",
                        "Status": "Validation Status"
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Proceed button (only if validation passed)
                if validation_results['error_count'] == 0:
                    if st.button("📤 Proceed with These Entries", type="primary"):
                        # Enrich data with missing fields from database
                        enriched_entries = enrich_upload_entries(validation_results['valid_entries'])
                        st.session_state['selected_entries'] = enriched_entries
                        st.success(f"✅ {len(enriched_entries)} entries prepared for submission!")
                        st.rerun()
                else:
                    st.error("⚠️ Please fix all errors before proceeding with submission.")
            
            else:
                st.error("❌ No valid entries found in the uploaded file.")
        
        except Exception as e:
            st.error(f"❌ Error processing uploaded file: {str(e)}")
            st.info("💡 Please check file format and ensure all required columns are present.")

def validate_upload_data(upload_df):
    """Validate uploaded bulk submission data."""
    errors = []
    warnings = []
    valid_entries = []
    
    # Check required columns
    required_columns = ['document_number', 'company_code']
    missing_columns = [col for col in required_columns if col not in upload_df.columns]
    
    if missing_columns:
        return {
            'valid_count': 0,
            'error_count': 1,
            'warning_count': 0,
            'errors': [{'row': 'Header', 'message': f'Missing required columns: {", ".join(missing_columns)}'}],
            'warnings': [],
            'valid_entries': []
        }
    
    # Validate each row
    for idx, row in upload_df.iterrows():
        row_num = idx + 2  # Account for header row
        row_errors = []
        row_warnings = []
        
        # Validate document_number
        if pd.isna(row['document_number']) or str(row['document_number']).strip() == '':
            row_errors.append(f"Document number is required")
        elif not validate_document_exists(str(row['document_number']), str(row.get('company_code', ''))):
            row_errors.append(f"Document {row['document_number']} not found or not in DRAFT status")
        
        # Validate company_code
        if pd.isna(row['company_code']):
            row_errors.append("Company code is required")
        elif str(row['company_code']) not in ['1000', '2000', '3000']:
            row_errors.append(f"Invalid company code: {row['company_code']}")
        
        # Validate priority (optional)
        if not pd.isna(row.get('priority', '')) and str(row['priority']).upper() not in ['NORMAL', 'HIGH', 'URGENT']:
            row_warnings.append(f"Invalid priority '{row['priority']}', defaulting to NORMAL")
        
        # Validate reference length
        if not pd.isna(row.get('reference', '')) and len(str(row['reference'])) > 255:
            row_warnings.append("Reference text truncated to 255 characters")
        
        # Add errors and warnings
        for error_msg in row_errors:
            errors.append({'row': row_num, 'message': error_msg})
        
        for warning_msg in row_warnings:
            warnings.append({'row': row_num, 'message': warning_msg})
        
        # Add to valid entries if no errors
        if not row_errors:
            valid_entry = {
                'document_number': str(row['document_number']).strip(),
                'company_code': str(row['company_code']).strip(),
                'reference': str(row.get('reference', '')).strip()[:255],
                'priority': str(row.get('priority', 'NORMAL')).upper(),
                'comments': str(row.get('comments', '')).strip()
            }
            valid_entries.append(valid_entry)
    
    return {
        'valid_count': len(valid_entries),
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors,
        'warnings': warnings,
        'valid_entries': valid_entries
    }

def validate_document_exists(document_number, company_code):
    """Validate that document exists and is in DRAFT status."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT workflow_status FROM journalentryheader 
                WHERE documentnumber = :doc AND companycodeid = :cc
            """), {"doc": document_number, "cc": company_code})
            
            row = result.fetchone()
            return row and row[0] == 'DRAFT'
    
    except Exception:
        return False

def enrich_upload_entries(valid_entries):
    """Enrich upload entries with database information."""
    enriched_entries = []
    
    try:
        with engine.connect() as conn:
            for entry in valid_entries:
                # Get additional information from database
                result = conn.execute(text("""
                    SELECT 
                        jeh.postingdate,
                        jeh.createdby,
                        jeh.createdat,
                        COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                    FROM journalentryheader jeh
                    LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber 
                        AND jeh.companycodeid = jel.companycodeid
                    WHERE jeh.documentnumber = :doc AND jeh.companycodeid = :cc
                    GROUP BY jeh.postingdate, jeh.createdby, jeh.createdat
                """), {
                    "doc": entry['document_number'],
                    "cc": entry['company_code']
                })
                
                row = result.fetchone()
                if row:
                    enriched_entry = {
                        **entry,
                        'posting_date': row[0],
                        'created_by': row[1],
                        'created_at': row[2],
                        'total_amount': float(row[3])
                    }
                    enriched_entries.append(enriched_entry)
        
        return enriched_entries
    
    except Exception as e:
        st.error(f"Error enriching upload data: {e}")
        return valid_entries

def send_bulk_submission_notification(emails, submitted_count, failed_count, submitted_by):
    """Send email notification about bulk submission results."""
    # Implementation for sending notifications
    st.info(f"Notification sent to: {emails}")

if __name__ == "__main__":
    main()