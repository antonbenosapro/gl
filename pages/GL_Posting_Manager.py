"""
🏦 GL Posting Manager
Enterprise General Ledger Posting Interface

This module provides the user interface for posting approved journal entries
to the General Ledger following enterprise best practices.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import time

# Import posting engine and authentication
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.gl_posting_engine import GLPostingEngine
from db_config import engine
from sqlalchemy import text

# Page configuration
st.set_page_config(
    page_title="🏦 GL Posting Manager",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

class GLPostingManager:
    """GL Posting Manager Interface"""
    
    def __init__(self):
        self.posting_engine = GLPostingEngine()
    
    def render_posting_manager(self):
        """Render the complete GL posting interface"""
        
        # Header
        st.title("🏦 GL Posting Manager")
        st.markdown("### Enterprise General Ledger Posting Interface")
        
        # Sidebar for filters and options
        with st.sidebar:
            st.header("🔧 Posting Options")
            
            # Company filter
            company_code = st.selectbox(
                "🏢 Company Code",
                self.get_available_companies(),
                index=0
            )
            
            # Posting date
            posting_date = st.date_input(
                "📅 Posting Date",
                value=date.today(),
                help="Date to use for GL posting"
            )
            
            # Auto-refresh
            auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
            
            if st.button("🔍 Refresh Data"):
                st.rerun()
        
        # Main content tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📋 Posting Queue",
            "📊 Batch Posting", 
            "📈 Account Balances",
            "📄 Posting History",
            "⚙️ Period Controls"
        ])
        
        with tab1:
            self.render_posting_queue(company_code, posting_date)
        
        with tab2:
            self.render_batch_posting(company_code, posting_date)
        
        with tab3:
            self.render_account_balances(company_code)
        
        with tab4:
            self.render_posting_history(company_code)
        
        with tab5:
            self.render_period_controls(company_code)
        
        # Auto-refresh logic
        if auto_refresh:
            time.sleep(30)
            st.rerun()
    
    def render_posting_queue(self, company_code: str, posting_date: date):
        """Render individual document posting interface"""
        st.subheader("📋 Individual Document Posting")
        
        # Get eligible documents
        eligible_docs = self.posting_engine.get_posting_eligible_documents(company_code)
        
        if not eligible_docs:
            st.info("✅ No documents currently eligible for posting")
            return
        
        st.write(f"**{len(eligible_docs)} documents ready for posting:**")
        
        # Initialize session state for preview
        if 'preview_doc' not in st.session_state:
            st.session_state.preview_doc = None
        
        # Display documents in a table with posting actions
        for i, doc in enumerate(eligible_docs):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"**{doc['document_number']}** - {doc['reference'] or 'No Reference'}")
                    st.caption(f"Created by: {doc['created_by']} | Approved by: {doc['approved_by']}")
                
                with col2:
                    st.metric("Amount", f"${doc['total_amount']:,.2f}")
                
                with col3:
                    st.write(f"**Period:** {doc['period']}/{doc['fiscal_year']}")
                    st.write(f"**Date:** {doc['posting_date']}")
                
                with col4:
                    if st.button(f"📊 Preview", key=f"preview_{i}"):
                        st.session_state.preview_doc = (doc['document_number'], doc['company_code'])
                        st.rerun()
                
                with col5:
                    if st.button(f"✅ Post", key=f"post_{i}", type="primary"):
                        self.post_single_document(
                            doc['document_number'], doc['company_code'], posting_date
                        )
                
                st.divider()
        
        # Show preview if document selected
        if st.session_state.preview_doc:
            doc_number, company_code = st.session_state.preview_doc
            self.show_document_preview(doc_number, company_code)
            
            # Add close button
            if st.button("❌ Close Preview", key="close_preview"):
                st.session_state.preview_doc = None
                st.rerun()
    
    def render_batch_posting(self, company_code: str, posting_date: date):
        """Render batch posting interface"""
        st.subheader("📊 Batch Posting")
        
        # Get eligible documents
        eligible_docs = self.posting_engine.get_posting_eligible_documents(company_code)
        
        if not eligible_docs:
            st.info("✅ No documents available for batch posting")
            return
        
        # Batch selection
        st.write("**Select documents for batch posting:**")
        
        # Create DataFrame for selection
        df = pd.DataFrame(eligible_docs)
        df['selected'] = False
        
        # Document selection interface
        selection_container = st.container()
        with selection_container:
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if st.button("☑️ Select All"):
                    df['selected'] = True
            
            with col2:
                if st.button("⬜ Clear All"):
                    df['selected'] = False
            
            with col3:
                selected_count = len(df[df['selected'] == True])
                st.metric("Selected", selected_count)
        
        # Document list with checkboxes
        selected_docs = []
        for i, doc in enumerate(eligible_docs):
            col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
            
            with col1:
                is_selected = st.checkbox("", key=f"batch_select_{i}")
                if is_selected:
                    selected_docs.append(doc['document_number'])
            
            with col2:
                st.write(f"**{doc['document_number']}**")
                st.caption(f"{doc['reference'] or 'No Reference'}")
            
            with col3:
                st.write(f"${doc['total_amount']:,.2f}")
            
            with col4:
                st.write(f"{doc['period']}/{doc['fiscal_year']}")
        
        # Batch posting execution
        if selected_docs:
            st.write(f"**Ready to post {len(selected_docs)} documents**")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                total_amount = sum(doc['total_amount'] for doc in eligible_docs 
                                 if doc['document_number'] in selected_docs)
                st.metric("Total Amount", f"${total_amount:,.2f}")
            
            with col2:
                if st.button("🚀 Execute Batch Posting", type="primary"):
                    self.execute_batch_posting(selected_docs, company_code, posting_date)
            
            with col3:
                st.info("💡 Batch posting will process all selected documents in a single transaction")
    
    def render_account_balances(self, company_code: str):
        """Render account balance overview"""
        st.subheader("📈 Account Balances")
        
        try:
            with engine.connect() as conn:
                # Get account balance summary
                result = conn.execute(text("""
                    SELECT b.gl_account, a.accountname, a.accounttype,
                           SUM(b.ytd_balance) as current_balance,
                           SUM(b.ytd_debits) as ytd_debits,
                           SUM(b.ytd_credits) as ytd_credits,
                           MAX(b.last_posting_date) as last_posting,
                           SUM(b.transaction_count) as transaction_count
                    FROM gl_account_balances b
                    JOIN glaccount a ON a.glaccountid = b.gl_account
                    WHERE b.company_code = :cc
                    AND b.fiscal_year = :fy
                    GROUP BY b.gl_account, a.accountname, a.accounttype
                    HAVING SUM(b.ytd_balance) != 0
                    ORDER BY a.accounttype, b.gl_account
                """), {"cc": company_code, "fy": datetime.now().year})
                
                balances = result.fetchall()
                
                if balances:
                    # Create DataFrame
                    df = pd.DataFrame(balances, columns=[
                        'Account', 'Account Name', 'Type', 'Balance', 
                        'YTD Debits', 'YTD Credits', 'Last Posting', 'Transactions'
                    ])
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        total_assets = df[df['Type'].str.contains('ASSET', na=False)]['Balance'].sum()
                        st.metric("Total Assets", f"${total_assets:,.2f}")
                    
                    with col2:
                        total_liabilities = df[df['Type'].str.contains('LIABILITY', na=False)]['Balance'].sum()
                        st.metric("Total Liabilities", f"${abs(total_liabilities):,.2f}")
                    
                    with col3:
                        total_equity = df[df['Type'].str.contains('EQUITY', na=False)]['Balance'].sum()
                        st.metric("Total Equity", f"${abs(total_equity):,.2f}")
                    
                    with col4:
                        total_accounts = len(df)
                        st.metric("Active Accounts", total_accounts)
                    
                    # Account type breakdown chart
                    type_summary = df.groupby('Type')['Balance'].sum().reset_index()
                    fig = px.bar(type_summary, x='Type', y='Balance', 
                               title="Account Balances by Type")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Detailed balance table
                    st.write("**Detailed Account Balances:**")
                    
                    # Format the DataFrame for display
                    display_df = df.copy()
                    display_df['Balance'] = display_df['Balance'].apply(lambda x: f"${x:,.2f}")
                    display_df['YTD Debits'] = display_df['YTD Debits'].apply(lambda x: f"${x:,.2f}")
                    display_df['YTD Credits'] = display_df['YTD Credits'].apply(lambda x: f"${x:,.2f}")
                    
                    st.dataframe(display_df, use_container_width=True, height=400)
                
                else:
                    st.info("No account balances found. Post some journal entries to see balances.")
                    
        except Exception as e:
            st.error(f"Error loading account balances: {e}")
    
    def render_posting_history(self, company_code: str):
        """Render posting history and audit trail"""
        st.subheader("📄 Posting History")
        
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From Date", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("To Date", value=date.today())
        
        try:
            with engine.connect() as conn:
                # Get posting history
                result = conn.execute(text("""
                    SELECT pat.source_document, pat.action_timestamp, pat.action_by,
                           pat.total_amount, pat.action_status, pd.document_type,
                           jeh.reference
                    FROM posting_audit_trail pat
                    LEFT JOIN posting_documents pd ON pd.source_document = pat.source_document
                        AND pd.company_code = pat.company_code
                    LEFT JOIN journalentryheader jeh ON jeh.documentnumber = pat.source_document
                        AND jeh.companycodeid = pat.company_code
                    WHERE pat.company_code = :cc
                    AND pat.action_timestamp::date BETWEEN :start_date AND :end_date
                    AND pat.action_type = 'POST'
                    ORDER BY pat.action_timestamp DESC
                    LIMIT 100
                """), {
                    "cc": company_code,
                    "start_date": start_date,
                    "end_date": end_date
                })
                
                history = result.fetchall()
                
                if history:
                    # Summary metrics
                    total_posted = len(history)
                    total_amount = sum(float(row[3] or 0) for row in history)
                    successful_posts = sum(1 for row in history if row[4] == 'SUCCESS')
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Documents Posted", total_posted)
                    with col2:
                        st.metric("Total Amount", f"${total_amount:,.2f}")
                    with col3:
                        success_rate = (successful_posts / total_posted * 100) if total_posted > 0 else 0
                        st.metric("Success Rate", f"{success_rate:.1f}%")
                    
                    # History table
                    df = pd.DataFrame(history, columns=[
                        'Document', 'Posted At', 'Posted By', 'Amount', 
                        'Status', 'Type', 'Reference'
                    ])
                    
                    # Format for display
                    df['Amount'] = df['Amount'].apply(lambda x: f"${float(x or 0):,.2f}")
                    df['Posted At'] = pd.to_datetime(df['Posted At']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    st.dataframe(df, use_container_width=True, height=400)
                    
                else:
                    st.info("No posting history found for the selected date range")
                    
        except Exception as e:
            st.error(f"Error loading posting history: {e}")
    
    def render_period_controls(self, company_code: str):
        """Render fiscal period controls"""
        st.subheader("⚙️ Fiscal Period Controls")
        
        try:
            with engine.connect() as conn:
                # Get period controls
                result = conn.execute(text("""
                    SELECT fiscal_year, posting_period, period_status,
                           period_start_date, period_end_date, allow_posting,
                           is_special_period, special_period_type
                    FROM fiscal_period_controls
                    WHERE company_code = :cc
                    ORDER BY fiscal_year DESC, posting_period
                """), {"cc": company_code})
                
                periods = result.fetchall()
                
                if periods:
                    # Current year periods
                    current_year = datetime.now().year
                    current_periods = [p for p in periods if p[0] == current_year]
                    
                    st.write(f"**Fiscal Year {current_year} Period Status:**")
                    
                    # Create period status grid
                    cols = st.columns(4)
                    for i, period in enumerate(current_periods[:12]):  # Show first 12 periods
                        with cols[i % 4]:
                            status_color = {
                                'OPEN': '🟢',
                                'CLOSED_POSTING': '🟡',
                                'CLOSED_DISPLAY': '🟠',
                                'LOCKED': '🔴'
                            }.get(period[2], '⚪')
                            
                            posting_status = "✅" if period[5] else "❌"
                            
                            st.write(f"**Period {period[1]}**")
                            st.write(f"{status_color} {period[2]}")
                            st.write(f"Posting: {posting_status}")
                            st.caption(f"{period[3]} to {period[4]}")
                    
                    # Detailed period table
                    st.write("**Detailed Period Controls:**")
                    df = pd.DataFrame(periods, columns=[
                        'Fiscal Year', 'Period', 'Status', 'Start Date', 
                        'End Date', 'Allow Posting', 'Special Period', 'Special Type'
                    ])
                    
                    st.dataframe(df, use_container_width=True, height=300)
                    
                else:
                    st.warning("No period controls configured")
                    
        except Exception as e:
            st.error(f"Error loading period controls: {e}")
    
    def post_single_document(self, doc_number: str, company_code: str, posting_date: date):
        """Post a single document"""
        current_user = st.session_state.get('user_id', 'unknown')
        
        with st.spinner(f"Posting document {doc_number}..."):
            success, message = self.posting_engine.post_journal_entry(
                doc_number, company_code, current_user, posting_date
            )
            
            if success:
                st.success(f"✅ {message}")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    def execute_batch_posting(self, doc_numbers: List[str], company_code: str, posting_date: date):
        """Execute batch posting"""
        current_user = st.session_state.get('user_id', 'unknown')
        
        with st.spinner(f"Batch posting {len(doc_numbers)} documents..."):
            results = self.posting_engine.post_multiple_journal_entries(
                doc_numbers, company_code, current_user, posting_date
            )
            
            # Display results
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Documents", results['total_documents'])
            
            with col2:
                st.metric("Posted Successfully", results['posted_successfully'])
            
            with col3:
                st.metric("Failed", len(results['failed_documents']))
            
            # Show details
            if results['posted_successfully'] > 0:
                st.success(f"✅ Successfully posted {results['posted_successfully']} documents")
            
            if results['failed_documents']:
                st.error(f"❌ {len(results['failed_documents'])} documents failed to post")
                with st.expander("View Failed Documents"):
                    for failed in results['failed_documents']:
                        st.write(f"**{failed['document']}:** {failed['error']}")
            
            time.sleep(2)
            st.rerun()
    
    def show_document_preview(self, doc_number: str, company_code: str):
        """Show document preview in an expandable section"""
        try:
            with engine.connect() as conn:
                # Get header data
                header_result = conn.execute(text("""
                    SELECT documentnumber, reference, postingdate, fiscalyear, period,
                           currencycode, createdby, approved_by, approved_at
                    FROM journalentryheader
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": doc_number, "cc": company_code})
                
                header = header_result.fetchone()
                
                if not header:
                    st.error("Document not found")
                    return
                
                # Get line data
                lines_result = conn.execute(text("""
                    SELECT jel.linenumber, jel.glaccountid, ga.accountname,
                           jel.debitamount, jel.creditamount, jel.description
                    FROM journalentryline jel
                    LEFT JOIN glaccount ga ON ga.glaccountid = jel.glaccountid
                    WHERE jel.documentnumber = :doc AND jel.companycodeid = :cc
                    ORDER BY jel.linenumber
                """), {"doc": doc_number, "cc": company_code})
                
                lines = lines_result.fetchall()
                
                # Display in expandable container
                with st.expander(f"📄 Document Preview: {doc_number}", expanded=True):
                    # Document Header
                    st.subheader("📋 Document Header")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Document Number:** {header[0]}")
                        st.write(f"**Reference:** {header[1] or 'N/A'}")
                        st.write(f"**Posting Date:** {header[2]}")
                        st.write(f"**Period:** {header[4]}/{header[3]}")
                    
                    with col2:
                        st.write(f"**Currency:** {header[5] or 'USD'}")
                        st.write(f"**Created By:** {header[6]}")
                        st.write(f"**Approved By:** {header[7]}")
                        st.write(f"**Approved At:** {header[8]}")
                    
                    st.divider()
                    
                    # Journal Lines
                    st.subheader("📊 Journal Entry Lines")
                    if lines:
                        lines_df = pd.DataFrame(lines, columns=[
                            'Line', 'Account', 'Account Name', 'Debit', 'Credit', 'Description'
                        ])
                        
                        # Format amounts
                        lines_df['Debit'] = lines_df['Debit'].apply(
                            lambda x: f"${float(x):,.2f}" if x else "-"
                        )
                        lines_df['Credit'] = lines_df['Credit'].apply(
                            lambda x: f"${float(x):,.2f}" if x else "-"
                        )
                        
                        st.dataframe(lines_df, use_container_width=True, height=300)
                        
                        # Calculate totals
                        total_debit = sum(float(line[3]) for line in lines if line[3])
                        total_credit = sum(float(line[4]) for line in lines if line[4])
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Debits", f"${total_debit:,.2f}")
                        with col2:
                            st.metric("Total Credits", f"${total_credit:,.2f}")
                        with col3:
                            balance_check = "✅ Balanced" if total_debit == total_credit else "❌ Unbalanced"
                            st.metric("Status", balance_check)
                    else:
                        st.warning("No journal lines found for this document")
                    
        except Exception as e:
            st.error(f"Error loading document preview: {e}")
    
    def get_available_companies(self):
        """Get list of available company codes"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT companycodeid 
                    FROM companycode 
                    ORDER BY companycodeid
                """))
                return [row[0] for row in result]
        except:
            return ["1000"]

def main():
    """Main function to run the GL Posting Manager"""
    
    # Check if user is logged in (simplified approach matching other pages)
    current_user = st.session_state.get('user_id')
    
    if not current_user:
        # Show simple login form
        st.title("🏦 GL Posting Manager")
        st.warning("⚠️ Please log in to access the GL Posting Manager")
        
        with st.form("simple_login"):
            st.write("**Quick Login for Testing:**")
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password", value="admin123")
            
            if st.form_submit_button("Login"):
                # Simple authentication for testing
                if username and password:
                    st.session_state['user_id'] = username
                    st.session_state['authenticated'] = True
                    st.success("✅ Logged in successfully!")
                    st.rerun()
                else:
                    st.error("❌ Please enter username and password")
        
        st.info("💡 This is a simplified login for GL Posting testing. In production, use the main authentication system.")
        return
    
    # Show current user info
    st.sidebar.success(f"👤 Logged in as: {current_user}")
    if st.sidebar.button("🚪 Logout"):
        for key in ['user_id', 'authenticated']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Initialize and render posting manager
    posting_manager = GLPostingManager()
    posting_manager.render_posting_manager()

if __name__ == "__main__":
    main()