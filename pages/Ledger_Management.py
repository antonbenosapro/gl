"""
Ledger Management System

Complete ledger master data management for parallel ledger configuration,
accounting principles, and multi-currency ledger setup.

Author: Claude Code Assistant  
Date: August 7, 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from sqlalchemy import text
import json

# Add project root to path
import sys
sys.path.append('/home/anton/erp/gl')

from db_config import engine
from utils.navigation import show_breadcrumb
from auth.optimized_middleware import optimized_authenticator as authenticator

# Page configuration
st.set_page_config(
    page_title="Ledger Management",
    page_icon="📚",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Ledger Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Ledger Management", "Master Data", "Accounting")
    
    st.title("📚 Ledger Management")
    st.markdown("**Configure and manage ledgers for parallel accounting and reporting**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 Ledger Config")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Ledger Overview",
                "➕ Create Ledger",
                "✏️ Edit Ledgers", 
                "🔄 Derivation Rules",
                "💱 Currency Setup",
                "📋 Ledger Reports"
            ]
        )
    
    # Route to selected page
    if page == "📊 Ledger Overview":
        show_ledger_overview()
    elif page == "➕ Create Ledger":
        show_create_ledger()
    elif page == "✏️ Edit Ledgers":
        show_edit_ledgers()
    elif page == "🔄 Derivation Rules":
        show_derivation_rules()
    elif page == "💱 Currency Setup":
        show_currency_setup()
    elif page == "📋 Ledger Reports":
        show_ledger_reports()

def show_ledger_overview():
    """Display ledger overview dashboard."""
    st.header("📊 Ledger Overview")
    
    # Load ledger data
    try:
        with engine.connect() as conn:
            # Get ledgers with enhanced information
            ledgers = pd.read_sql(text("""
                SELECT 
                    l.ledgerid,
                    l.description,
                    l.isleadingledger,
                    l.currencycode,
                    l.accounting_principle,
                    l.parallel_currency_1,
                    l.parallel_currency_2,
                    l.consolidation_ledger,
                    l.created_at,
                    l.updated_at,
                    cur.currency_name,
                    cur.currency_symbol
                FROM ledger l
                LEFT JOIN currencies cur ON l.currencycode = cur.currency_code
                ORDER BY l.ledgerid
            """), conn)
            
            # Get usage statistics
            usage_stats = pd.read_sql(text("""
                SELECT 
                    l.ledgerid,
                    l.description,
                    COUNT(jel.docid) as journal_line_count,
                    COUNT(gt.transaction_id) as gl_transaction_count
                FROM ledger l
                LEFT JOIN journalentryline jel ON l.ledgerid = jel.ledgerid
                LEFT JOIN gl_transactions gt ON l.ledgerid = gt.ledger_id
                GROUP BY l.ledgerid, l.description
                ORDER BY l.ledgerid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    if ledgers.empty:
        st.warning("No ledgers configured yet. Create your first ledger to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Ledgers", len(ledgers))
    
    with col2:
        leading_ledgers = len(ledgers[ledgers['isleadingledger'] == True])
        st.metric("Leading Ledgers", leading_ledgers)
    
    with col3:
        consolidation_ledgers = len(ledgers[ledgers['consolidation_ledger'] == True])
        st.metric("Consolidation Ledgers", consolidation_ledgers)
    
    with col4:
        unique_currencies = ledgers['currencycode'].nunique()
        st.metric("Currencies Used", unique_currencies)
    
    # Ledger list
    st.subheader("📋 Ledger Configuration")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        currency_filter = st.selectbox(
            "Filter by Currency",
            ["All"] + list(ledgers['currencycode'].dropna().unique())
        )
    
    with col2:
        principle_filter = st.selectbox(
            "Filter by Accounting Principle",
            ["All"] + list(ledgers['accounting_principle'].dropna().unique())
        )
    
    with col3:
        type_filter = st.selectbox(
            "Filter by Type",
            ["All", "Leading Ledger", "Parallel Ledger", "Consolidation Ledger"]
        )
    
    # Apply filters
    filtered_data = ledgers.copy()
    
    if currency_filter != "All":
        filtered_data = filtered_data[filtered_data['currencycode'] == currency_filter]
    
    if principle_filter != "All":
        filtered_data = filtered_data[filtered_data['accounting_principle'] == principle_filter]
    
    if type_filter == "Leading Ledger":
        filtered_data = filtered_data[filtered_data['isleadingledger'] == True]
    elif type_filter == "Parallel Ledger":
        filtered_data = filtered_data[filtered_data['isleadingledger'] == False]
    elif type_filter == "Consolidation Ledger":
        filtered_data = filtered_data[filtered_data['consolidation_ledger'] == True]
    
    # Display table
    if not filtered_data.empty:
        st.dataframe(
            filtered_data[[
                'ledgerid', 'description', 'isleadingledger', 'currencycode',
                'currency_name', 'accounting_principle', 'parallel_currency_1', 
                'parallel_currency_2', 'consolidation_ledger'
            ]],
            use_container_width=True,
            column_config={
                'ledgerid': 'Ledger ID',
                'description': 'Description',
                'isleadingledger': st.column_config.CheckboxColumn('Leading'),
                'currencycode': 'Currency',
                'currency_name': 'Currency Name',
                'accounting_principle': 'Accounting Principle',
                'parallel_currency_1': 'Parallel Currency 1',
                'parallel_currency_2': 'Parallel Currency 2',
                'consolidation_ledger': st.column_config.CheckboxColumn('Consolidation')
            }
        )
    else:
        st.info("No ledgers match the selected filters.")
    
    # Usage analytics
    if not usage_stats.empty:
        st.subheader("📈 Ledger Usage Analytics")
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Journal Entry Lines',
            x=usage_stats['ledgerid'],
            y=usage_stats['journal_line_count'],
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='GL Transactions',
            x=usage_stats['ledgerid'],
            y=usage_stats['gl_transaction_count'],
            marker_color='lightgreen'
        ))
        
        fig.update_layout(
            title='Transaction Volume by Ledger',
            xaxis_title='Ledger ID',
            yaxis_title='Number of Transactions',
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def show_create_ledger():
    """Create new ledger interface."""
    st.header("➕ Create New Ledger")
    
    with st.form("create_ledger"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            ledgerid = st.text_input(
                "Ledger ID*", 
                max_chars=10,
                help="Unique ledger identifier (e.g., L1, 0L, 2L)"
            ).upper()
            description = st.text_input(
                "Description*",
                max_chars=100,
                help="Descriptive name for the ledger"
            )
            
            isleadingledger = st.checkbox(
                "Leading Ledger", 
                value=False,
                help="Leading ledger is the primary ledger for legal reporting"
            )
            
            consolidation_ledger = st.checkbox(
                "Consolidation Ledger",
                value=False,
                help="Used for group consolidation reporting"
            )
        
        with col2:
            st.subheader("Accounting Configuration")
            
            accounting_principle = st.selectbox(
                "Accounting Principle*",
                [
                    "US_GAAP", "IFRS", "LOCAL_GAAP", "TAX", "MANAGEMENT",
                    "STATISTICAL", "BUDGET", "FORECAST"
                ],
                help="Accounting standards applied to this ledger"
            )
            
            # Get available currencies
            try:
                with engine.connect() as conn:
                    currencies = pd.read_sql(text("""
                        SELECT currency_code, currency_name 
                        FROM currencies 
                        WHERE is_active = TRUE
                        ORDER BY currency_code
                    """), conn)
                
                currency_codes = currencies['currency_code'].tolist() if not currencies.empty else ['USD', 'EUR', 'GBP']
                
            except Exception as e:
                currency_codes = ['USD', 'EUR', 'GBP', 'JPY', 'CAD']
            
            currencycode = st.selectbox("Ledger Currency*", currency_codes)
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("Parallel Currencies")
            parallel_currency_1 = st.selectbox(
                "Parallel Currency 1", 
                ["None"] + currency_codes,
                help="First parallel currency for currency translation"
            )
            parallel_currency_1 = None if parallel_currency_1 == "None" else parallel_currency_1
            
            parallel_currency_2 = st.selectbox(
                "Parallel Currency 2",
                ["None"] + currency_codes,
                help="Second parallel currency for currency translation"
            )
            parallel_currency_2 = None if parallel_currency_2 == "None" else parallel_currency_2
        
        with col4:
            st.subheader("Advanced Settings")
            
            fiscal_year_variant = st.selectbox(
                "Fiscal Year Variant",
                ["K4", "V3", "K1", "V1", "V4", "US", "UK", "DE", "FR", "JP"],
                help="Fiscal year calendar for this ledger"
            )
            
            posting_period_variant = st.selectbox(
                "Posting Period Variant",
                ["000", "001", "002", "US1", "CAL"],
                help="Posting period configuration"
            )
            
            currency_translation_method = st.selectbox(
                "Currency Translation Method",
                ["CURRENT_RATE", "HISTORICAL_RATE", "AVERAGE_RATE", "MONETARY_NONMONETARY"],
                help="Method for translating foreign currency amounts"
            )
        
        submitted = st.form_submit_button("Create Ledger", type="primary")
        
        if submitted:
            if not all([ledgerid, description, accounting_principle, currencycode]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # First enhance the ledger table if needed
                        enhancement_columns = {
                            'fiscal_year_variant': 'VARCHAR(5)',
                            'posting_period_variant': 'VARCHAR(5)', 
                            'currency_translation_method': 'VARCHAR(30)'
                        }
                        
                        for col_name, col_type in enhancement_columns.items():
                            try:
                                conn.execute(text(f"ALTER TABLE ledger ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                            except:
                                pass
                        
                        # Insert new ledger
                        conn.execute(text("""
                            INSERT INTO ledger (
                                ledgerid, description, isleadingledger, currencycode, 
                                accounting_principle, parallel_currency_1, parallel_currency_2,
                                consolidation_ledger, fiscal_year_variant, posting_period_variant,
                                currency_translation_method
                            ) VALUES (
                                :ledger_id, :desc, :is_leading, :currency,
                                :principle, :par_curr1, :par_curr2,
                                :consolidation, :fiscal_variant, :period_variant,
                                :translation_method
                            )
                        """), {
                            'ledger_id': ledgerid,
                            'desc': description,
                            'is_leading': isleadingledger,
                            'currency': currencycode,
                            'principle': accounting_principle,
                            'par_curr1': parallel_currency_1,
                            'par_curr2': parallel_currency_2,
                            'consolidation': consolidation_ledger,
                            'fiscal_variant': fiscal_year_variant,
                            'period_variant': posting_period_variant,
                            'translation_method': currency_translation_method
                        })
                        conn.commit()
                    
                    st.success(f"✅ Ledger {ledgerid} created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Ledger ID {ledgerid} already exists!")
                    else:
                        st.error(f"❌ Error creating ledger: {e}")

def show_derivation_rules():
    """Manage ledger derivation rules."""
    st.header("🔄 Ledger Derivation Rules")
    
    st.info("Derivation rules determine how transactions are automatically posted to multiple ledgers.")
    
    # Load existing derivation rules
    try:
        with engine.connect() as conn:
            derivation_rules = pd.read_sql(text("""
                SELECT 
                    ldr.rule_id,
                    ldr.rule_name,
                    ldr.source_ledger,
                    sl.description as source_description,
                    ldr.target_ledger,
                    tl.description as target_description,
                    ldr.condition_field,
                    ldr.condition_value,
                    ldr.is_active,
                    ldr.created_at
                FROM ledger_derivation_rules ldr
                LEFT JOIN ledger sl ON ldr.source_ledger = sl.ledgerid
                LEFT JOIN ledger tl ON ldr.target_ledger = tl.ledgerid
                WHERE ldr.is_active = TRUE
                ORDER BY ldr.rule_name
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading derivation rules: {e}")
        return
    
    # Derivation rule creation form
    st.subheader("➕ Create New Derivation Rule")
    
    with st.form("create_derivation_rule"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rule_name = st.text_input("Rule Name*", max_chars=100)
            rule_description = st.text_area("Rule Description")
            
            # Get ledgers for selection
            try:
                with engine.connect() as conn:
                    ledgers = pd.read_sql(text("""
                        SELECT ledgerid, description 
                        FROM ledger 
                        ORDER BY ledgerid
                    """), conn)
                
                ledger_options = [f"{row['ledgerid']} - {row['description']}" 
                                 for _, row in ledgers.iterrows()]
                
            except Exception as e:
                ledger_options = ["L1 - Leading Ledger"]
            
            source_ledger_selection = st.selectbox("Source Ledger*", ledger_options)
            source_ledger = source_ledger_selection.split(" - ")[0] if source_ledger_selection else None
        
        with col2:
            target_ledger_selection = st.selectbox("Target Ledger*", ledger_options)
            target_ledger = target_ledger_selection.split(" - ")[0] if target_ledger_selection else None
            
            condition_field = st.selectbox(
                "Condition Field*",
                ["GL_ACCOUNT", "COST_CENTER", "DOCUMENT_TYPE", "AMOUNT", "CURRENCY", "POSTING_KEY"]
            )
            condition_value = st.text_input(
                "Condition Value*",
                help="Value to match (e.g., 4* for revenue accounts)"
            )
        
        with col3:
            condition_operator = st.selectbox(
                "Condition Operator",
                ["=", "LIKE", "IN", "BETWEEN", ">=", "<="]
            )
            priority = st.number_input("Priority", min_value=1, max_value=999, value=100)
            percentage = st.number_input("Percentage", min_value=0.01, max_value=100.0, value=100.0)
        
        submitted_rule = st.form_submit_button("Create Derivation Rule", type="primary")
        
        if submitted_rule:
            if not all([rule_name, source_ledger, target_ledger, condition_field, condition_value]):
                st.error("Please fill in all required fields")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO ledger_derivation_rules (
                                rule_name, rule_description, source_ledger, target_ledger,
                                condition_field, condition_operator, condition_value,
                                priority, percentage, created_by
                            ) VALUES (
                                :rule_name, :rule_desc, :source_ledger, :target_ledger,
                                :condition_field, :condition_op, :condition_value,
                                :priority, :percentage, :created_by
                            )
                        """), {
                            'rule_name': rule_name,
                            'rule_desc': rule_description,
                            'source_ledger': source_ledger,
                            'target_ledger': target_ledger,
                            'condition_field': condition_field,
                            'condition_op': condition_operator,
                            'condition_value': condition_value,
                            'priority': priority,
                            'percentage': percentage,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success("✅ Derivation rule created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error creating derivation rule: {e}")
    
    # Display existing derivation rules
    if not derivation_rules.empty:
        st.subheader("📋 Existing Derivation Rules")
        
        st.dataframe(
            derivation_rules[[
                'rule_name', 'source_ledger', 'source_description', 
                'target_ledger', 'target_description', 'condition_field',
                'condition_value', 'created_at'
            ]],
            use_container_width=True,
            column_config={
                'rule_name': 'Rule Name',
                'source_ledger': 'Source Ledger',
                'source_description': 'Source Description',
                'target_ledger': 'Target Ledger', 
                'target_description': 'Target Description',
                'condition_field': 'Condition Field',
                'condition_value': 'Condition Value',
                'created_at': st.column_config.DatetimeColumn('Created At')
            }
        )
    else:
        st.info("No derivation rules configured yet. Create your first rule above.")

def show_currency_setup():
    """Configure currency settings for ledgers."""
    st.header("💱 Currency Setup")
    
    try:
        with engine.connect() as conn:
            # Get ledger currency configurations
            ledger_currencies = pd.read_sql(text("""
                SELECT 
                    l.ledgerid,
                    l.description,
                    l.currencycode,
                    c1.currency_name as primary_currency_name,
                    l.parallel_currency_1,
                    c2.currency_name as parallel_1_name,
                    l.parallel_currency_2,
                    c3.currency_name as parallel_2_name,
                    l.accounting_principle,
                    l.isleadingledger
                FROM ledger l
                LEFT JOIN currencies c1 ON l.currencycode = c1.currency_code
                LEFT JOIN currencies c2 ON l.parallel_currency_1 = c2.currency_code
                LEFT JOIN currencies c3 ON l.parallel_currency_2 = c3.currency_code
                ORDER BY l.ledgerid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading ledger currency data: {e}")
        return
    
    if ledger_currencies.empty:
        st.info("No ledgers configured yet.")
        return
    
    st.subheader("💰 Current Currency Configuration")
    
    st.dataframe(
        ledger_currencies,
        use_container_width=True,
        column_config={
            'ledgerid': 'Ledger ID',
            'description': 'Description',
            'currencycode': 'Primary Currency',
            'primary_currency_name': 'Primary Currency Name',
            'parallel_currency_1': 'Parallel Currency 1',
            'parallel_1_name': 'Parallel 1 Name',
            'parallel_currency_2': 'Parallel Currency 2', 
            'parallel_2_name': 'Parallel 2 Name',
            'accounting_principle': 'Accounting Principle',
            'isleadingledger': st.column_config.CheckboxColumn('Leading')
        }
    )
    
    # Currency assignment analysis
    st.subheader("📊 Currency Usage Analysis")
    
    # Primary currency distribution
    primary_currencies = ledger_currencies['currencycode'].value_counts()
    if not primary_currencies.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.pie(
                values=primary_currencies.values,
                names=primary_currencies.index,
                title='Primary Currency Distribution'
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Parallel currency usage
            parallel_usage = []
            for _, row in ledger_currencies.iterrows():
                if row['parallel_currency_1']:
                    parallel_usage.append(row['parallel_currency_1'])
                if row['parallel_currency_2']:
                    parallel_usage.append(row['parallel_currency_2'])
            
            if parallel_usage:
                parallel_counts = pd.Series(parallel_usage).value_counts()
                fig2 = px.bar(
                    x=parallel_counts.index,
                    y=parallel_counts.values,
                    title='Parallel Currency Usage',
                    color=parallel_counts.values,
                    color_continuous_scale='viridis'
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No parallel currencies configured")

def show_ledger_reports():
    """Display ledger analysis and reports."""
    st.header("📋 Ledger Reports & Analysis")
    
    try:
        with engine.connect() as conn:
            # Comprehensive ledger analysis
            ledger_analysis = pd.read_sql(text("""
                SELECT 
                    l.ledgerid,
                    l.description,
                    l.accounting_principle,
                    l.isleadingledger,
                    l.consolidation_ledger,
                    COUNT(DISTINCT jel.docid) as journal_entries,
                    COUNT(DISTINCT gt.transaction_id) as gl_transactions,
                    SUM(CASE WHEN gt.debit_amount IS NOT NULL THEN gt.debit_amount ELSE 0 END) as total_debits,
                    SUM(CASE WHEN gt.credit_amount IS NOT NULL THEN gt.credit_amount ELSE 0 END) as total_credits,
                    l.created_at as ledger_created
                FROM ledger l
                LEFT JOIN journalentryline jel ON l.ledgerid = jel.ledgerid
                LEFT JOIN gl_transactions gt ON l.ledgerid = gt.ledger_id
                GROUP BY l.ledgerid, l.description, l.accounting_principle, 
                         l.isleadingledger, l.consolidation_ledger, l.created_at
                ORDER BY l.ledgerid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading analysis data: {e}")
        return
    
    if ledger_analysis.empty:
        st.info("No ledger data available for analysis.")
        return
    
    # Ledger performance analysis
    st.subheader("📊 Ledger Performance Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Transaction volume by ledger
        fig1 = px.bar(
            ledger_analysis,
            x='ledgerid',
            y='gl_transactions',
            title='GL Transaction Volume by Ledger',
            color='accounting_principle',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Journal entry distribution
        fig2 = px.bar(
            ledger_analysis,
            x='ledgerid', 
            y='journal_entries',
            title='Journal Entry Volume by Ledger',
            color='isleadingledger',
            color_discrete_map={True: 'gold', False: 'lightblue'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Accounting principle distribution
    st.subheader("📈 Accounting Principle Distribution")
    
    principle_stats = ledger_analysis['accounting_principle'].value_counts()
    if not principle_stats.empty:
        fig3 = px.pie(
            values=principle_stats.values,
            names=principle_stats.index,
            title='Ledgers by Accounting Principle'
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # Financial summary
    st.subheader("💰 Financial Summary by Ledger")
    
    # Calculate balances
    ledger_analysis['net_balance'] = ledger_analysis['total_debits'] - ledger_analysis['total_credits']
    
    st.dataframe(
        ledger_analysis,
        use_container_width=True,
        column_config={
            'ledgerid': 'Ledger ID',
            'description': 'Description', 
            'accounting_principle': 'Accounting Principle',
            'isleadingledger': st.column_config.CheckboxColumn('Leading'),
            'consolidation_ledger': st.column_config.CheckboxColumn('Consolidation'),
            'journal_entries': st.column_config.NumberColumn('Journal Entries'),
            'gl_transactions': st.column_config.NumberColumn('GL Transactions'),
            'total_debits': st.column_config.NumberColumn('Total Debits', format="$%.2f"),
            'total_credits': st.column_config.NumberColumn('Total Credits', format="$%.2f"),
            'net_balance': st.column_config.NumberColumn('Net Balance', format="$%.2f"),
            'ledger_created': st.column_config.DatetimeColumn('Created At')
        }
    )

def show_edit_ledgers():
    """Edit existing ledgers."""
    st.header("✏️ Edit Ledgers")
    
    st.info("Select a ledger below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            ledgers = pd.read_sql(text("""
                SELECT * FROM ledger 
                ORDER BY ledgerid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading ledgers: {e}")
        return
    
    if ledgers.empty:
        st.warning("No ledgers available for editing.")
        return
    
    # Ledger selection
    selected_ledger = st.selectbox(
        "Select Ledger to Edit",
        options=ledgers['ledgerid'].tolist(),
        format_func=lambda x: f"{x} - {ledgers[ledgers['ledgerid']==x]['description'].iloc[0]}"
    )
    
    if selected_ledger:
        ledger_data = ledgers[ledgers['ledgerid'] == selected_ledger].iloc[0]
        
        st.subheader(f"Editing Ledger: {selected_ledger}")
        
        # Show current configuration
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Ledger ID:** {ledger_data['ledgerid']}")
                st.write(f"**Description:** {ledger_data['description']}")
                st.write(f"**Currency:** {ledger_data['currencycode']}")
                st.write(f"**Accounting Principle:** {ledger_data['accounting_principle']}")
            
            with col2:
                st.write(f"**Leading Ledger:** {'Yes' if ledger_data['isleadingledger'] else 'No'}")
                st.write(f"**Consolidation Ledger:** {'Yes' if ledger_data['consolidation_ledger'] else 'No'}")
                st.write(f"**Parallel Currency 1:** {ledger_data.get('parallel_currency_1', 'None')}")
                st.write(f"**Parallel Currency 2:** {ledger_data.get('parallel_currency_2', 'None')}")
        
        st.write("**Full edit functionality would be implemented here for updating ledger configurations.**")

if __name__ == "__main__":
    main()