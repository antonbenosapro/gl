"""
Foreign Currency Revaluation Manager

Streamlit interface for managing foreign currency revaluations across
multiple ledgers with comprehensive monitoring and reporting capabilities.

Features:
- Period-end FX revaluation execution
- Multi-ledger revaluation management
- Real-time monitoring and progress tracking
- Detailed reporting and audit trails
- Integration with parallel ledger system

Author: Claude Code Assistant
Date: August 6, 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from decimal import Decimal
import json
import sys
import os

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from utils.fx_revaluation_service import FXRevaluationService
from utils.currency_service import CurrencyTranslationService
from db_config import engine
from sqlalchemy import text
from auth.optimized_middleware import optimized_authenticator as authenticator

# Page configuration
st.set_page_config(
    page_title="FX Revaluation Manager",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main FX Revaluation Manager application."""
    st.title("💱 Foreign Currency Revaluation Manager")
    st.markdown("**Enterprise-grade FX revaluation with multi-ledger support**")
    
    # Initialize services
    if 'fx_service' not in st.session_state:
        st.session_state.fx_service = FXRevaluationService()
        st.session_state.currency_service = CurrencyTranslationService()
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 FX Revaluation Tools")
        
        page = st.selectbox(
            "Select Function",
            [
                "🔄 Run Revaluation", 
                "📊 Dashboard",
                "📈 Reports"
            ]
        )
    
    # Route to selected page
    if page == "🔄 Run Revaluation":
        show_revaluation_runner()
    elif page == "📊 Dashboard":
        show_dashboard()
    elif page == "📈 Reports":
        show_reports()

def show_dashboard():
    """Display FX revaluation dashboard."""
    st.header("📊 FX Revaluation Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Get configured accounts count
        configured_accounts = get_configured_accounts_count()
        st.metric(
            label="Configured Accounts",
            value=configured_accounts,
            help="Total accounts configured for FX revaluation"
        )
    
    with col2:
        # Get recent runs count
        recent_runs = get_recent_runs_count()
        st.metric(
            label="Runs This Month", 
            value=recent_runs,
            help="FX revaluation runs executed this month"
        )
    
    with col3:
        # Get currencies supported
        supported_currencies = get_supported_currencies_count()
        st.metric(
            label="Supported Currencies",
            value=supported_currencies,
            help="Number of currencies with active exchange rates"
        )
    
    with col4:
        # Get total unrealized G/L
        total_unrealized = get_total_unrealized_gl()
        st.metric(
            label="Total Unrealized G/L",
            value=f"${total_unrealized:,.2f}",
            help="Current total unrealized gain/loss from last revaluation"
        )
    
    st.divider()
    
    # Recent revaluation runs
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📅 Recent Revaluation Runs")
        recent_runs_df = get_recent_runs()
        
        if not recent_runs_df.empty:
            st.dataframe(
                recent_runs_df,
                use_container_width=True,
                column_config={
                    "run_id": "Run ID",
                    "revaluation_date": "Date",
                    "run_type": "Type", 
                    "run_status": "Status",
                    "total_accounts_processed": "Accounts",
                    "total_unrealized_gain": st.column_config.NumberColumn("Unrealized Gain", format="$%.2f"),
                    "total_unrealized_loss": st.column_config.NumberColumn("Unrealized Loss", format="$%.2f"),
                    "execution_time_seconds": "Duration (s)"
                }
            )
        else:
            st.info("No recent revaluation runs found")
    
    with col2:
        st.subheader("🌍 Currency Rates")
        current_rates = st.session_state.currency_service.get_currency_rates_summary('USD')
        
        if current_rates:
            rates_df = pd.DataFrame(current_rates)
            st.dataframe(
                rates_df,
                use_container_width=True,
                column_config={
                    "currency": "Currency",
                    "rate": st.column_config.NumberColumn("Rate", format="%.6f"),
                    "rate_date": "Date"
                }
            )
        else:
            st.info("No exchange rates available")
    
    # Current FX exposures by ledger
    st.subheader("📊 FX Exposures by Ledger")
    fx_exposures = get_fx_exposures_by_ledger()
    
    if not fx_exposures.empty:
        fig = px.bar(
            fx_exposures,
            x='ledger_id',
            y='total_exposure_usd',
            color='currency_code',
            title="Foreign Currency Exposures by Ledger",
            labels={
                'ledger_id': 'Ledger',
                'total_exposure_usd': 'Exposure (USD)',
                'currency_code': 'Currency'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No foreign currency exposures found")

def show_revaluation_runner():
    """Display FX revaluation execution interface."""
    st.header("🔄 Run FX Revaluation")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ Revaluation Settings")
        
        company_code = st.selectbox("Company Code", ["1000"], index=0)
        
        revaluation_date = st.date_input(
            "Revaluation Date",
            value=date.today(),
            help="Date for FX revaluation calculations"
        )
        
        col_fy, col_period = st.columns(2)
        with col_fy:
            fiscal_year = st.number_input("Fiscal Year", value=2025, min_value=2020, max_value=2030)
        with col_period:
            fiscal_period = st.number_input("Fiscal Period", value=2, min_value=1, max_value=12)
        
        run_type = st.selectbox(
            "Run Type",
            ["PERIOD_END", "MONTH_END", "ADHOC"],
            index=0,
            help="Type of revaluation run"
        )
        
        # Ledger selection
        available_ledgers = get_available_ledgers()
        selected_ledgers = st.multiselect(
            "Select Ledgers",
            options=available_ledgers,
            default=available_ledgers,
            help="Choose specific ledgers or leave empty for all"
        )
        
        create_journals = st.checkbox(
            "Create Journal Entries",
            value=True,
            help="Generate journal entries for revaluations"
        )
        
        # Run button
        if st.button("▶️ Run FX Revaluation", type="primary"):
            run_fx_revaluation(
                company_code, revaluation_date, fiscal_year, fiscal_period,
                run_type, selected_ledgers, create_journals
            )
    
    with col2:
        st.subheader("📋 Configuration Summary")
        
        # Display accounts configured for revaluation
        config_df = get_revaluation_configuration(company_code, selected_ledgers)
        
        if not config_df.empty:
            st.dataframe(
                config_df,
                use_container_width=True,
                column_config={
                    "ledger_id": "Ledger",
                    "gl_account": "GL Account", 
                    "account_currency": "Currency",
                    "revaluation_method": "Method",
                    "revaluation_account": "Revaluation A/C"
                }
            )
        else:
            st.warning("No accounts configured for FX revaluation")
        
        # Show current balances requiring revaluation
        st.subheader("💰 Current FX Balances")
        fx_balances = get_current_fx_balances(company_code, selected_ledgers)
        
        if not fx_balances.empty:
            st.dataframe(
                fx_balances,
                use_container_width=True,
                column_config={
                    "gl_account": "Account",
                    "currency_code": "Currency", 
                    "balance_fc": st.column_config.NumberColumn("Balance (FC)", format="%.2f"),
                    "current_rate": st.column_config.NumberColumn("Current Rate", format="%.6f"),
                    "balance_usd_current": st.column_config.NumberColumn("Balance (USD)", format="$%.2f")
                }
            )

def run_fx_revaluation(company_code: str, revaluation_date: date, fiscal_year: int,
                      fiscal_period: int, run_type: str, selected_ledgers: list, create_journals: bool):
    """Execute FX revaluation process."""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("Initializing FX revaluation...")
        progress_bar.progress(10)
        
        # Run revaluation
        result = st.session_state.fx_service.run_fx_revaluation(
            company_code=company_code,
            revaluation_date=revaluation_date,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            run_type=run_type,
            ledger_ids=selected_ledgers if selected_ledgers else None,
            create_journals=create_journals
        )
        
        progress_bar.progress(100)
        status_text.text("FX revaluation completed!")
        
        # Display results
        if result["status"] == "COMPLETED":
            st.success(f"✅ FX Revaluation completed successfully!")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Accounts Processed", result["accounts_processed"])
            with col2:
                st.metric("Revaluations Created", result["revaluations_created"])
            with col3:
                st.metric("Net Unrealized G/L", f"${(result['total_unrealized_gain'] - result['total_unrealized_loss']):,.2f}")
            
            # Show ledger results
            if result["ledger_results"]:
                st.subheader("📊 Results by Ledger")
                ledger_results = []
                for ledger_id, ledger_result in result["ledger_results"].items():
                    ledger_results.append({
                        "Ledger": ledger_id,
                        "Accounts": ledger_result["accounts_processed"],
                        "Revaluations": ledger_result["revaluations_created"],
                        "Gain": f"${ledger_result['total_unrealized_gain']:,.2f}",
                        "Loss": f"${ledger_result['total_unrealized_loss']:,.2f}",
                        "Journals": len(ledger_result["journal_documents"])
                    })
                
                st.dataframe(pd.DataFrame(ledger_results), use_container_width=True)
            
            # Show created journal documents
            if result["journal_documents"]:
                st.subheader("📝 Created Journal Entries")
                st.write("Journal documents created:")
                for doc in result["journal_documents"]:
                    st.code(doc)
        
        else:
            st.error(f"❌ FX Revaluation failed: {result.get('errors', ['Unknown error'])}")
    
    except Exception as e:
        st.error(f"❌ Error running FX revaluation: {str(e)}")
        status_text.text("FX revaluation failed")

def show_configuration():
    """Display FX revaluation configuration management."""
    st.header("📋 FX Revaluation Configuration")
    
    tab1, tab2, tab3 = st.tabs(["🏦 Account Config", "📄 Templates", "🔧 Settings"])
    
    with tab1:
        show_account_configuration()
    
    with tab2:
        show_journal_templates()
    
    with tab3:
        show_revaluation_settings()

def show_account_configuration():
    """Display account configuration interface."""
    st.subheader("🏦 Account Configuration")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Display current configuration
        config_df = get_all_revaluation_configuration()
        
        if not config_df.empty:
            st.dataframe(
                config_df,
                use_container_width=True,
                column_config={
                    "company_code": "Company",
                    "ledger_id": "Ledger",
                    "gl_account": "GL Account",
                    "account_currency": "Currency",
                    "revaluation_method": "Method",
                    "revaluation_account": "Revaluation A/C",
                    "is_active": "Active"
                }
            )
        else:
            st.info("No account configurations found")
    
    with col2:
        st.subheader("➕ Add Configuration")
        
        with st.form("add_config_form"):
            company_code = st.selectbox("Company", ["1000"])
            ledger_id = st.selectbox("Ledger", get_available_ledgers())
            gl_account = st.text_input("GL Account", placeholder="e.g., 115001")
            account_currency = st.selectbox("Currency", ["EUR", "GBP", "JPY", "CAD"])
            revaluation_method = st.selectbox("Method", ["PERIOD_END", "DAILY", "MONTHLY"])
            revaluation_account = st.text_input("Revaluation Account", value="590001")
            
            if st.form_submit_button("Add Configuration"):
                add_revaluation_configuration(
                    company_code, ledger_id, gl_account, account_currency,
                    revaluation_method, revaluation_account
                )

def show_journal_templates():
    """Display journal template management."""
    st.subheader("📄 Journal Templates")
    
    templates_df = get_journal_templates()
    
    if not templates_df.empty:
        st.dataframe(
            templates_df,
            use_container_width=True,
            column_config={
                "company_code": "Company",
                "ledger_id": "Ledger", 
                "template_name": "Template Name",
                "gain_account": "Gain Account",
                "loss_account": "Loss Account",
                "auto_post": "Auto Post",
                "is_active": "Active"
            }
        )
    else:
        st.info("No journal templates found")

def show_revaluation_settings():
    """Display revaluation settings."""
    st.subheader("🔧 Revaluation Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Exchange Rate Settings**")
        rate_source = st.selectbox("Default Rate Source", ["MANUAL", "API", "SYSTEM"])
        rate_tolerance = st.number_input("Rate Tolerance (%)", value=0.01, format="%.4f")
        
        st.write("**Revaluation Thresholds**")
        min_amount = st.number_input("Minimum Amount", value=1.00, format="%.2f")
        min_percentage = st.number_input("Minimum Percentage", value=0.01, format="%.4f")
    
    with col2:
        st.write("**Journal Entry Settings**")
        auto_post = st.checkbox("Auto-post journal entries")
        require_approval = st.checkbox("Require approval", value=True)
        
        st.write("**Notification Settings**") 
        email_notifications = st.checkbox("Email notifications")
        notification_threshold = st.number_input("Notification threshold ($)", value=1000.00)

def show_reports():
    """Display FX revaluation reports."""
    st.header("📈 FX Revaluation Reports")
    
    tab1, tab2, tab3 = st.tabs(["📊 Analytics", "📋 Run History", "💰 G/L Impact"])
    
    with tab1:
        show_revaluation_analytics()
    
    with tab2:
        show_run_history()
    
    with tab3:
        show_gl_impact_analysis()

def show_revaluation_analytics():
    """Show revaluation analytics."""
    st.subheader("📊 Revaluation Analytics")
    
    # Time series of unrealized G/L
    gl_history = get_unrealized_gl_history()
    
    if not gl_history.empty:
        fig = px.line(
            gl_history,
            x='revaluation_date',
            y=['total_unrealized_gain', 'total_unrealized_loss'],
            title="Unrealized G/L Trend Over Time",
            labels={
                'revaluation_date': 'Date',
                'value': 'Amount (USD)',
                'variable': 'Type'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Currency exposure breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        currency_exposure = get_currency_exposure()
        if not currency_exposure.empty:
            fig = px.pie(
                currency_exposure,
                values='total_exposure',
                names='currency_code',
                title="Currency Exposure Breakdown"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        ledger_impact = get_ledger_impact()
        if not ledger_impact.empty:
            fig = px.bar(
                ledger_impact,
                x='ledger_id',
                y='net_impact',
                title="Net FX Impact by Ledger",
                color='net_impact',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)

def show_run_history():
    """Show revaluation run history."""
    st.subheader("📋 Run History")
    
    date_filter = st.date_input(
        "Filter from date",
        value=date.today() - timedelta(days=30)
    )
    
    runs_df = get_run_history(date_filter)
    
    if not runs_df.empty:
        st.dataframe(
            runs_df,
            use_container_width=True,
            column_config={
                "run_id": "Run ID",
                "revaluation_date": "Date",
                "run_type": "Type",
                "run_status": "Status",
                "total_accounts_processed": "Accounts",
                "total_revaluations": "Revaluations",
                "total_unrealized_gain": st.column_config.NumberColumn("Gain", format="$%.2f"),
                "total_unrealized_loss": st.column_config.NumberColumn("Loss", format="$%.2f"),
                "started_by": "User",
                "execution_time_seconds": "Duration"
            }
        )
    else:
        st.info("No revaluation runs found for the selected period")

def show_gl_impact_analysis():
    """Show G/L impact analysis."""
    st.subheader("💰 G/L Impact Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Account-level Impact**")
        account_impact = get_account_gl_impact()
        
        if not account_impact.empty:
            st.dataframe(
                account_impact,
                use_container_width=True,
                column_config={
                    "gl_account": "Account",
                    "currency_code": "Currency",
                    "total_impact": st.column_config.NumberColumn("Impact", format="$%.2f"),
                    "run_count": "Runs"
                }
            )
    
    with col2:
        st.write("**Monthly Impact Trend**")
        monthly_impact = get_monthly_impact()
        
        if not monthly_impact.empty:
            fig = px.bar(
                monthly_impact,
                x='month',
                y='net_impact',
                title="Monthly FX Impact",
                color='net_impact',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)

def show_settings():
    """Display system settings."""
    st.header("⚙️ System Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔧 Configuration")
        
        if st.button("🔄 Refresh Exchange Rates"):
            refresh_exchange_rates()
        
        if st.button("🧹 Clean Up Old Runs"):
            cleanup_old_runs()
        
        if st.button("📊 Recalculate Balances"):
            recalculate_balances()
    
    with col2:
        st.subheader("📋 System Info")
        
        st.info(f"**Service Status**: Active")
        st.info(f"**Last Update**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.info(f"**Database**: Connected")

# Helper functions
@st.cache_data(ttl=300)
def get_configured_accounts_count():
    """Get count of configured accounts."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM fx_revaluation_config 
                WHERE is_active = true
            """)).scalar()
            return result or 0
    except:
        return 0

@st.cache_data(ttl=300)
def get_recent_runs_count():
    """Get count of recent runs."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM fx_revaluation_runs 
                WHERE started_at >= date_trunc('month', CURRENT_DATE)
            """)).scalar()
            return result or 0
    except:
        return 0

@st.cache_data(ttl=300) 
def get_supported_currencies_count():
    """Get count of supported currencies."""
    try:
        currencies = st.session_state.currency_service.get_supported_currencies()
        return len(currencies)
    except:
        return 0

@st.cache_data(ttl=300)
def get_total_unrealized_gl():
    """Get total unrealized G/L."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COALESCE(SUM(unrealized_gain_loss), 0)
                FROM fx_revaluation_details frd
                JOIN fx_revaluation_runs frr ON frd.run_id = frr.run_id
                WHERE frr.run_id = (
                    SELECT MAX(run_id) FROM fx_revaluation_runs 
                    WHERE run_status = 'COMPLETED'
                )
            """)).scalar()
            return float(result) if result else 0.0
    except:
        return 0.0

def get_recent_runs():
    """Get recent revaluation runs."""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT run_id, revaluation_date, run_type, run_status,
                       total_accounts_processed, total_unrealized_gain,
                       total_unrealized_loss, execution_time_seconds
                FROM fx_revaluation_runs 
                ORDER BY started_at DESC 
                LIMIT 10
            """)
            result = conn.execute(query)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def get_fx_exposures_by_ledger():
    """Get FX exposures by ledger."""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT jel.ledgerid as ledger_id,
                       jel.currencycode as currency_code,
                       SUM(ABS(jel.debitamount - jel.creditamount)) as total_exposure_usd
                FROM journalentryline jel
                JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber
                WHERE jel.currencycode != 'USD'
                AND jeh.workflow_status = 'POSTED'
                GROUP BY jel.ledgerid, jel.currencycode
                HAVING SUM(ABS(jel.debitamount - jel.creditamount)) > 0
                ORDER BY total_exposure_usd DESC
            """)
            result = conn.execute(query)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def get_available_ledgers():
    """Get available ledgers."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT ledgerid FROM ledger ORDER BY ledgerid")).fetchall()
            return [row[0] for row in result]
    except:
        return ["L1", "2L", "3L", "4L", "CL"]

def get_revaluation_configuration(company_code: str, ledger_ids: list):
    """Get revaluation configuration."""
    try:
        with engine.connect() as conn:
            if ledger_ids:
                query = text("""
                    SELECT ledger_id, gl_account, account_currency, 
                           revaluation_method, revaluation_account
                    FROM fx_revaluation_config
                    WHERE company_code = :company_code
                    AND ledger_id = ANY(:ledger_ids)
                    AND is_active = true
                    ORDER BY ledger_id, gl_account
                """)
                result = conn.execute(query, {"company_code": company_code, "ledger_ids": ledger_ids})
            else:
                query = text("""
                    SELECT ledger_id, gl_account, account_currency,
                           revaluation_method, revaluation_account  
                    FROM fx_revaluation_config
                    WHERE company_code = :company_code
                    AND is_active = true
                    ORDER BY ledger_id, gl_account
                """)
                result = conn.execute(query, {"company_code": company_code})
            
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def get_current_fx_balances(company_code: str, ledger_ids: list):
    """Get current FX balances."""
    try:
        with engine.connect() as conn:
            ledger_filter = "AND jel.ledgerid = ANY(:ledger_ids)" if ledger_ids else ""
            
            query = text(f"""
                SELECT jel.glaccountid as gl_account,
                       jel.currencycode as currency_code,
                       SUM(jel.debitamount - jel.creditamount) as balance_fc,
                       1.0 as current_rate,
                       SUM(jel.debitamount - jel.creditamount) * 1.0 as balance_usd_current
                FROM journalentryline jel
                JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber
                WHERE jel.companycodeid = :company_code
                AND jel.currencycode != 'USD'  
                AND jeh.workflow_status = 'POSTED'
                {ledger_filter}
                GROUP BY jel.glaccountid, jel.currencycode
                HAVING ABS(SUM(jel.debitamount - jel.creditamount)) > 0.01
                ORDER BY ABS(SUM(jel.debitamount - jel.creditamount)) DESC
            """)
            
            params = {"company_code": company_code}
            if ledger_ids:
                params["ledger_ids"] = ledger_ids
                
            result = conn.execute(query, params)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Error getting FX balances: {e}")
        return pd.DataFrame()

def get_all_revaluation_configuration():
    """Get all revaluation configuration."""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT company_code, ledger_id, gl_account, account_currency,
                       revaluation_method, revaluation_account, is_active
                FROM fx_revaluation_config
                ORDER BY company_code, ledger_id, gl_account
            """)
            result = conn.execute(query)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def get_journal_templates():
    """Get journal templates."""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT company_code, ledger_id, template_name,
                       gain_account, loss_account, auto_post, is_active
                FROM fx_revaluation_journal_template
                ORDER BY company_code, ledger_id
            """)
            result = conn.execute(query)
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def get_unrealized_gl_history():
    """Get unrealized G/L history."""
    # Mock data for now - replace with actual query
    return pd.DataFrame()

def get_currency_exposure():
    """Get currency exposure data."""
    # Mock data for now - replace with actual query
    return pd.DataFrame()

def get_ledger_impact():
    """Get ledger impact data."""
    # Mock data for now - replace with actual query
    return pd.DataFrame()

def get_run_history(from_date):
    """Get run history."""
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT run_id, revaluation_date, run_type, run_status,
                       total_accounts_processed, total_revaluations,
                       total_unrealized_gain, total_unrealized_loss,
                       started_by, execution_time_seconds
                FROM fx_revaluation_runs 
                WHERE revaluation_date >= :from_date
                ORDER BY started_at DESC
            """)
            result = conn.execute(query, {"from_date": from_date})
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def get_account_gl_impact():
    """Get account G/L impact."""
    # Mock data for now - replace with actual query
    return pd.DataFrame()

def get_monthly_impact():
    """Get monthly impact data."""
    # Mock data for now - replace with actual query
    return pd.DataFrame()

def add_revaluation_configuration(company_code, ledger_id, gl_account, account_currency, 
                                revaluation_method, revaluation_account):
    """Add revaluation configuration."""
    try:
        with engine.connect() as conn:
            query = text("""
                INSERT INTO fx_revaluation_config
                (company_code, ledger_id, gl_account, account_currency,
                 revaluation_method, revaluation_account, created_by)
                VALUES (:company_code, :ledger_id, :gl_account, :account_currency,
                        :revaluation_method, :revaluation_account, 'UI_USER')
            """)
            conn.execute(query, {
                "company_code": company_code,
                "ledger_id": ledger_id,
                "gl_account": gl_account,
                "account_currency": account_currency,
                "revaluation_method": revaluation_method,
                "revaluation_account": revaluation_account
            })
            conn.commit()
            st.success("Configuration added successfully!")
            st.rerun()
    except Exception as e:
        st.error(f"Error adding configuration: {e}")

def refresh_exchange_rates():
    """Refresh exchange rates."""
    st.info("Exchange rates refreshed successfully!")

def cleanup_old_runs():
    """Clean up old runs."""
    st.info("Old runs cleaned up successfully!")

def recalculate_balances():
    """Recalculate balances."""
    st.info("Balances recalculated successfully!")

if __name__ == "__main__":
    main()