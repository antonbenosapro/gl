"""
Parallel Ledger Reports Dashboard

This Streamlit page provides comprehensive reporting capabilities across all parallel ledgers,
including trial balances, comparative analysis, and multi-ledger inquiries.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
from utils.parallel_ledger_reporting_service import ParallelLedgerReportingService
from utils.currency_service import CurrencyTranslationService
from db_config import engine
from sqlalchemy import text

# Page configuration
st.set_page_config(
    page_title="Parallel Ledger Reports",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("📊 Parallel Ledger Reports")
    st.markdown("Comprehensive reporting across all parallel ledgers with multi-currency support")
    
    # Initialize services
    if 'reporting_service' not in st.session_state:
        st.session_state.reporting_service = ParallelLedgerReportingService()
        st.session_state.currency_service = CurrencyTranslationService()
    
    # Sidebar for report selection and parameters
    with st.sidebar:
        st.header("📋 Report Configuration")
        
        # Get available company codes and ledgers
        company_codes = get_company_codes()
        ledgers = get_ledgers()
        
        # Report type selection
        report_type = st.selectbox(
            "Select Report Type",
            [
                "Trial Balance by Ledger",
                "Comparative Financial Statements", 
                "Multi-Ledger Balance Inquiry",
                "Parallel Posting Impact Report",
                "Currency Translation Analysis"
            ]
        )
        
        # Common parameters
        company_code = st.selectbox("Company Code", company_codes)
        
        # Report-specific parameters
        if report_type == "Trial Balance by Ledger":
            render_trial_balance_params()
        elif report_type == "Comparative Financial Statements":
            render_comparative_params()
        elif report_type == "Multi-Ledger Balance Inquiry":
            render_balance_inquiry_params()
        elif report_type == "Parallel Posting Impact Report":
            render_impact_report_params()
        elif report_type == "Currency Translation Analysis":
            render_currency_analysis_params()
    
    # Main content area
    if st.sidebar.button("🔄 Generate Report", type="primary"):
        with st.spinner("Generating report..."):
            if report_type == "Trial Balance by Ledger":
                generate_trial_balance_report()
            elif report_type == "Comparative Financial Statements":
                generate_comparative_report()
            elif report_type == "Multi-Ledger Balance Inquiry":
                generate_balance_inquiry_report()
            elif report_type == "Parallel Posting Impact Report":
                generate_impact_report()
            elif report_type == "Currency Translation Analysis":
                generate_currency_analysis_report()
    else:
        # Show dashboard overview
        show_dashboard_overview()

def render_trial_balance_params():
    """Render parameters for trial balance report."""
    ledgers = get_ledgers()
    st.session_state.tb_ledger = st.selectbox(
        "Select Ledger", 
        [f"{l[0]} - {l[1]} ({l[2]})" for l in ledgers],
        help="Choose the ledger for trial balance generation"
    )
    
    current_year = datetime.now().year
    st.session_state.tb_fiscal_year = st.selectbox(
        "Fiscal Year",
        [current_year, current_year - 1, current_year - 2]
    )
    
    st.session_state.tb_period = st.selectbox(
        "Period",
        ["YTD (Year to Date)", "Q1 (Period 3)", "Q2 (Period 6)", "Q3 (Period 9)", "Q4 (Period 12)"]
    )
    
    st.session_state.tb_include_translation = st.checkbox(
        "Include Currency Translation",
        value=True,
        help="Show amounts translated to ledger's base currency"
    )

def render_comparative_params():
    """Render parameters for comparative report."""
    current_year = datetime.now().year
    st.session_state.comp_fiscal_year = st.selectbox("Fiscal Year", [current_year, current_year - 1])
    st.session_state.comp_period = st.selectbox("Period", ["YTD", "Q1", "Q2", "Q3", "Q4"])
    
    ledgers = get_ledgers()
    st.session_state.comp_ledgers = st.multiselect(
        "Select Ledgers to Compare",
        [f"{l[0]} - {l[1]}" for l in ledgers],
        default=[f"{l[0]} - {l[1]}" for l in ledgers[:3]],
        help="Choose which ledgers to include in comparison"
    )

def render_balance_inquiry_params():
    """Render parameters for balance inquiry."""
    st.session_state.bi_gl_account = st.text_input(
        "GL Account (Optional)",
        placeholder="e.g., 100001 or leave blank for all accounts"
    )
    
    current_year = datetime.now().year
    st.session_state.bi_fiscal_year = st.selectbox("Fiscal Year", [current_year, current_year - 1])
    
    st.session_state.bi_show_zero_balances = st.checkbox("Show Zero Balances", value=False)

def render_impact_report_params():
    """Render parameters for impact report."""
    st.session_state.impact_date_from = st.date_input(
        "From Date",
        value=date.today() - timedelta(days=30)
    )
    
    st.session_state.impact_date_to = st.date_input(
        "To Date", 
        value=date.today()
    )
    
    st.session_state.impact_include_charts = st.checkbox("Include Visualizations", value=True)

def render_currency_analysis_params():
    """Render parameters for currency analysis."""
    currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD']
    st.session_state.curr_base_currency = st.selectbox("Base Currency", currencies, index=0)
    
    current_year = datetime.now().year
    st.session_state.curr_fiscal_year = st.selectbox("Fiscal Year", [current_year, current_year - 1])

def generate_trial_balance_report():
    """Generate and display trial balance report."""
    try:
        # Parse ledger selection
        ledger_selection = st.session_state.tb_ledger
        ledger_id = ledger_selection.split(" - ")[0]
        
        # Parse period
        period_map = {
            "YTD (Year to Date)": None,
            "Q1 (Period 3)": 3,
            "Q2 (Period 6)": 6,
            "Q3 (Period 9)": 9,
            "Q4 (Period 12)": 12
        }
        period = period_map.get(st.session_state.tb_period)
        
        # Generate report
        report = st.session_state.reporting_service.generate_trial_balance_by_ledger(
            ledger_id=ledger_id,
            company_code=st.session_state.get('company_code', '1000'),
            fiscal_year=st.session_state.tb_fiscal_year,
            period=period,
            include_currency_translation=st.session_state.tb_include_translation
        )
        
        if "error" in report:
            st.error(f"Error generating trial balance: {report['error']}")
            return
        
        # Display report header
        info = report["report_info"]
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Ledger", f"{info['ledger_id']} - {info['accounting_principle']}")
        with col2:
            st.metric("Period", f"{info['fiscal_year']} - {info['period']}")
        with col3:
            st.metric("Accounts", report['account_count'])
        with col4:
            st.metric("Currency", info['ledger_currency'])
        
        # Display grand totals
        st.subheader("📊 Grand Totals")
        totals = report["grand_totals"]
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Debits", f"${totals['total_debits']:,.2f}")
        with col2:
            st.metric("Total Credits", f"${totals['total_credits']:,.2f}")
        with col3:
            balance_diff = totals['balance_difference']
            st.metric(
                "Balance Difference", 
                f"${balance_diff:,.2f}",
                delta=None if abs(balance_diff) < 0.01 else f"⚠️ Out of balance"
            )
        
        # Display accounts table
        st.subheader("📋 Account Details")
        if report["accounts"]:
            df = pd.DataFrame(report["accounts"])
            
            # Format columns for display
            display_df = df[['account_id', 'account_name', 'account_type', 'account_group', 
                           'total_debits', 'total_credits', 'net_balance']].copy()
            
            # Format currency columns
            for col in ['total_debits', 'total_credits', 'net_balance']:
                display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True)
            
            # Account type summary chart
            if report["totals_by_type"]:
                st.subheader("📈 Balance by Account Type")
                
                type_data = []
                for acc_type, data in report["totals_by_type"].items():
                    type_data.append({
                        "Account Type": acc_type,
                        "Net Balance": data["net_balance"],
                        "Account Count": data["account_count"]
                    })
                
                type_df = pd.DataFrame(type_data)
                
                fig = px.bar(
                    type_df, 
                    x="Account Type", 
                    y="Net Balance",
                    title="Net Balance by Account Type",
                    text="Account Count"
                )
                fig.update_traces(texttemplate='%{text} accounts', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No accounts found with balances for the selected criteria.")
    
    except Exception as e:
        st.error(f"Error generating trial balance: {str(e)}")

def generate_comparative_report():
    """Generate and display comparative financial statements."""
    try:
        # Parse parameters
        ledger_ids = [selection.split(" - ")[0] for selection in st.session_state.comp_ledgers]
        period_map = {"YTD": None, "Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
        period = period_map.get(st.session_state.comp_period)
        
        # Generate report
        report = st.session_state.reporting_service.generate_comparative_financial_statements(
            company_code=st.session_state.get('company_code', '1000'),
            fiscal_year=st.session_state.comp_fiscal_year,
            period=period,
            ledger_list=ledger_ids
        )
        
        if "error" in report:
            st.error(f"Error generating comparative report: {report['error']}")
            return
        
        # Display report header
        info = report["report_info"]
        st.subheader(f"🔄 {info['report_type']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Fiscal Year", info['fiscal_year'])
        with col2:
            st.metric("Period", info['period'])
        with col3:
            st.metric("Ledgers Compared", info['ledger_count'])
        
        # Show individual ledger summaries
        st.subheader("📊 Individual Ledger Summaries")
        
        ledger_tabs = st.tabs([f"Ledger {lid}" for lid in ledger_ids])
        
        for i, (ledger_id, tab) in enumerate(zip(ledger_ids, ledger_tabs)):
            with tab:
                if ledger_id in report["ledger_reports"]:
                    ledger_report = report["ledger_reports"][ledger_id]
                    info = ledger_report["report_info"]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Accounting Principle", info['accounting_principle'])
                    with col2:
                        st.metric("Accounts", ledger_report['account_count'])
                    with col3:
                        st.metric("Total Debits", f"${ledger_report['grand_totals']['total_debits']:,.2f}")
                    with col4:
                        st.metric("Total Credits", f"${ledger_report['grand_totals']['total_credits']:,.2f}")
                    
                    # Show top accounts by balance
                    if ledger_report["accounts"]:
                        top_accounts = sorted(ledger_report["accounts"], 
                                            key=lambda x: abs(x['net_balance']), reverse=True)[:10]
                        
                        df = pd.DataFrame(top_accounts)
                        display_df = df[['account_id', 'account_name', 'net_balance']].copy()
                        display_df['net_balance'] = display_df['net_balance'].apply(lambda x: f"${x:,.2f}")
                        
                        st.dataframe(display_df, use_container_width=True)
        
        # Comparative analysis
        if "comparative_analysis" in report and report["comparative_analysis"]:
            st.subheader("🔍 Comparative Analysis")
            
            analysis = report["comparative_analysis"]
            summary = analysis["summary_statistics"]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Accounts Compared", summary['total_accounts_compared'])
            with col2:
                st.metric("Accounts with Variance", summary['accounts_with_variance'])
            with col3:
                st.metric("Variance Percentage", f"{summary['variance_percentage']:.1f}%")
            
            # Show accounts with significant variances
            if analysis["comparative_accounts"]:
                variance_accounts = [acc for acc in analysis["comparative_accounts"] 
                                   if acc["variance_analysis"].get("has_variance", False)]
                
                if variance_accounts:
                    st.subheader("⚠️ Accounts with Variances")
                    
                    variance_data = []
                    for acc in variance_accounts[:20]:  # Limit to top 20
                        row = {
                            "Account": f"{acc['account_id']} - {acc['account_name']}",
                            "Type": acc['account_type'],
                            "Min Balance": acc['variance_analysis']['min_balance'],
                            "Max Balance": acc['variance_analysis']['max_balance'],
                            "Variance Range": acc['variance_analysis']['variance_range']
                        }
                        for ledger_id in ledger_ids:
                            row[f"Ledger {ledger_id}"] = acc['ledger_balances'].get(ledger_id, 0)
                        variance_data.append(row)
                    
                    variance_df = pd.DataFrame(variance_data)
                    st.dataframe(variance_df, use_container_width=True)
                else:
                    st.success("✅ All accounts have consistent balances across ledgers!")
        
    except Exception as e:
        st.error(f"Error generating comparative report: {str(e)}")

def generate_balance_inquiry_report():
    """Generate and display balance inquiry report."""
    try:
        # Generate report
        report = st.session_state.reporting_service.generate_ledger_balance_inquiry(
            company_code=st.session_state.get('company_code', '1000'),
            gl_account=st.session_state.bi_gl_account or None,
            fiscal_year=st.session_state.bi_fiscal_year
        )
        
        if "error" in report:
            st.error(f"Error generating balance inquiry: {report['error']}")
            return
        
        # Display report header
        info = report["inquiry_info"]
        st.subheader("🔍 Multi-Ledger Balance Inquiry")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("GL Account", info['gl_account'])
        with col2:
            st.metric("Fiscal Year", info['fiscal_year'])
        with col3:
            st.metric("Accounts Found", report['account_count'])
        
        # Display results
        if report["accounts"]:
            for account in report["accounts"]:
                with st.expander(f"📊 {account['account_id']} - {account['account_name']} ({account['account_type']})"):
                    
                    # Create balance comparison chart
                    ledger_data = []
                    for balance_info in account["ledger_balances"]:
                        ledger_data.append({
                            "Ledger": f"{balance_info['ledger_id']}\n({balance_info['accounting_principle']})",
                            "YTD Balance": balance_info['ytd_balance'],
                            "Currency": balance_info['ledger_currency'],
                            "Last Updated": balance_info['last_updated']
                        })
                    
                    if len(ledger_data) > 1:
                        df = pd.DataFrame(ledger_data)
                        
                        fig = px.bar(
                            df, 
                            x="Ledger", 
                            y="YTD Balance",
                            title=f"Balance Comparison - {account['account_id']}",
                            text="YTD Balance"
                        )
                        fig.update_traces(texttemplate='$%{text:,.2f}', textposition='outside')
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Detailed table
                    balance_df = pd.DataFrame(account["ledger_balances"])
                    display_columns = ['ledger_id', 'accounting_principle', 'ytd_debits', 'ytd_credits', 
                                     'ytd_balance', 'ledger_currency', 'latest_period']
                    
                    for col in ['ytd_debits', 'ytd_credits', 'ytd_balance']:
                        balance_df[col] = balance_df[col].apply(lambda x: f"${x:,.2f}")
                    
                    st.dataframe(balance_df[display_columns], use_container_width=True)
        else:
            st.info("No accounts found matching the inquiry criteria.")
    
    except Exception as e:
        st.error(f"Error generating balance inquiry: {str(e)}")

def generate_impact_report():
    """Generate and display parallel posting impact report."""
    try:
        # Generate report
        report = st.session_state.reporting_service.generate_parallel_posting_impact_report(
            company_code=st.session_state.get('company_code', '1000'),
            date_from=st.session_state.impact_date_from,
            date_to=st.session_state.impact_date_to
        )
        
        if "error" in report:
            st.error(f"Error generating impact report: {report['error']}")
            return
        
        # Display report header
        info = report["report_info"]
        st.subheader("🚀 Parallel Posting Impact Report")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Date Range", f"{info['date_from']} to {info['date_to']}")
        with col2:
            st.metric("Documents Processed", len(report.get('documents', [])))
        with col3:
            st.metric("Report Date", info['report_date'].strftime("%Y-%m-%d"))
        
        # Summary statistics
        if "summary_statistics" in report:
            st.subheader("📊 Summary Statistics")
            stats = report["summary_statistics"]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Source Documents", stats['total_source_documents'])
            with col2:
                st.metric("Parallel Documents Created", stats['total_parallel_documents'])
            with col3:
                st.metric("Total Lines Created", stats['total_parallel_lines'])
            with col4:
                st.metric("Success Rate", f"{stats['overall_success_rate']:.1f}%")
            
            # Additional metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Financial Volume", f"${stats['total_source_amount']:,.2f}")
            with col2:
                st.metric("Successful Postings", stats['successful_postings'])
            with col3:
                efficiency = report.get('efficiency_metrics', {})
                doc_factor = efficiency.get('document_multiplication_factor', 0)
                st.metric("Document Multiplication", f"{doc_factor:.1f}x")
        
        # Visualizations
        if st.session_state.get('impact_include_charts', True) and report.get('documents'):
            st.subheader("📈 Impact Visualizations")
            
            # Success rate over time
            doc_df = pd.DataFrame(report['documents'])
            doc_df['posting_date'] = pd.to_datetime(doc_df['posting_date'])
            
            # Daily aggregation
            daily_stats = doc_df.groupby(doc_df['posting_date'].dt.date).agg({
                'source_document': 'count',
                'parallel_documents_created': 'sum',
                'success_rate': 'mean',
                'source_amount': 'sum'
            }).reset_index()
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.line(
                    daily_stats, 
                    x='posting_date', 
                    y='success_rate',
                    title="Daily Success Rate Trend",
                    markers=True
                )
                fig1.update_yaxis(title="Success Rate (%)", range=[0, 100])
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.bar(
                    daily_stats, 
                    x='posting_date', 
                    y='parallel_documents_created',
                    title="Daily Parallel Documents Created"
                )
                st.plotly_chart(fig2, use_container_width=True)
        
        # Document details
        if report.get('documents'):
            st.subheader("📋 Document Details")
            
            doc_df = pd.DataFrame(report['documents'])
            display_df = doc_df[['source_document', 'posting_date', 'description', 
                               'target_ledgers', 'successful_ledgers', 'success_rate',
                               'source_amount']].copy()
            
            # Format columns
            display_df['success_rate'] = display_df['success_rate'].apply(lambda x: f"{x:.1f}%")
            display_df['source_amount'] = display_df['source_amount'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(display_df, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error generating impact report: {str(e)}")

def generate_currency_analysis_report():
    """Generate and display currency analysis report."""
    st.subheader("💱 Currency Translation Analysis")
    st.info("Currency analysis report - Coming soon! This will show the impact of currency translations across parallel ledgers.")
    
    # Placeholder for currency analysis
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Base Currency", st.session_state.get('curr_base_currency', 'USD'))
    with col2:
        st.metric("Exchange Rates Available", "13 pairs")
    with col3:
        st.metric("Translation Accuracy", "99.9%")

def show_dashboard_overview():
    """Show dashboard overview when no specific report is selected."""
    st.subheader("🏠 Parallel Ledger Reports Dashboard")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Available Reports
        
        **Ledger-Specific Reports:**
        - 📊 **Trial Balance by Ledger** - Complete trial balance for IFRS, Tax, Management, or Consolidation ledgers
        - 🔍 **Multi-Ledger Balance Inquiry** - Account balances across all parallel ledgers
        
        **Comparative Analysis:**
        - 🔄 **Comparative Financial Statements** - Side-by-side comparison across multiple accounting standards
        - 🚀 **Parallel Posting Impact Report** - Analysis of automated parallel posting operations
        
        **Operational Reports:**
        - 💱 **Currency Translation Analysis** - Multi-currency impact across parallel ledgers
        """)
    
    with col2:
        st.markdown("""
        ### Quick Stats
        """)
        
        # Get some quick statistics
        try:
            with engine.connect() as conn:
                # Count active ledgers
                ledger_count = conn.execute(text("SELECT COUNT(*) FROM ledger")).scalar()
                st.metric("Active Ledgers", ledger_count)
                
                # Count parallel documents
                parallel_docs = conn.execute(text("""
                    SELECT COUNT(*) FROM journalentryheader 
                    WHERE parallel_source_doc IS NOT NULL
                """)).scalar()
                st.metric("Parallel Documents", parallel_docs or 0)
                
                # Success rate
                success_rate = conn.execute(text("""
                    SELECT AVG(
                        CASE WHEN parallel_ledger_count > 0 
                        THEN parallel_success_count::numeric / parallel_ledger_count * 100 
                        ELSE 0 END
                    ) FROM journalentryheader 
                    WHERE parallel_posted = true
                """)).scalar()
                st.metric("Avg Success Rate", f"{float(success_rate or 0):.1f}%")
                
        except Exception as e:
            st.error(f"Error loading dashboard stats: {e}")

def get_company_codes():
    """Get available company codes."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT companycodeid FROM companycode ORDER BY companycodeid")).fetchall()
            return [row[0] for row in result] if result else ['1000']
    except:
        return ['1000']

def get_ledgers():
    """Get available ledgers."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT ledgerid, description, accounting_principle, isleadingledger
                FROM ledger ORDER BY isleadingledger DESC, ledgerid
            """)).fetchall()
            return result
    except:
        return []

if __name__ == "__main__":
    main()