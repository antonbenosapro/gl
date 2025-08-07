"""
Company Code Management System

Complete company code master data management for organizational structure,
fiscal year variants, and multi-company configuration.

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
    page_title="Company Code Management",
    page_icon="🏢",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Company Code Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Company Code Management", "Master Data", "Organization")
    
    st.title("🏢 Company Code Management")
    st.markdown("**Configure and manage company codes for organizational structure**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 Company Config")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Company Overview",
                "➕ Create Company Code",
                "✏️ Edit Company Codes",
                "💰 Fiscal Year Setup",
                "💱 Currency Assignment",
                "📋 Company Reports"
            ]
        )
    
    # Route to selected page
    if page == "📊 Company Overview":
        show_company_overview()
    elif page == "➕ Create Company Code":
        show_create_company_code()
    elif page == "✏️ Edit Company Codes":
        show_edit_company_codes()
    elif page == "💰 Fiscal Year Setup":
        show_fiscal_year_setup()
    elif page == "💱 Currency Assignment":
        show_currency_assignment()
    elif page == "📋 Company Reports":
        show_company_reports()

def show_company_overview():
    """Display company code overview dashboard."""
    st.header("📊 Company Code Overview")
    
    # Load company code data
    try:
        with engine.connect() as conn:
            # Get company codes
            companies = pd.read_sql(text("""
                SELECT 
                    cc.companycodeid,
                    cc.name,
                    cc.country,
                    cc.currencycode,
                    cc.fiscalyearvariant,
                    cc.createdat,
                    cur.currency_name,
                    cur.currency_symbol
                FROM companycode cc
                LEFT JOIN currencies cur ON cc.currencycode = cur.currency_code
                ORDER BY cc.companycodeid
            """), conn)
            
            # Get usage statistics
            usage_stats = pd.read_sql(text("""
                SELECT 
                    'Journal Entries' as entity_type,
                    cc.companycodeid,
                    COUNT(jeh.documentnumber) as usage_count
                FROM companycode cc
                LEFT JOIN journalentryheader jeh ON cc.companycodeid = jeh.companycodeid
                GROUP BY cc.companycodeid
                UNION ALL
                SELECT 
                    'Business Units' as entity_type,
                    cc.companycodeid,
                    COUNT(bu.unit_id) as usage_count
                FROM companycode cc
                LEFT JOIN business_units bu ON cc.companycodeid = bu.company_code_id
                GROUP BY cc.companycodeid
                UNION ALL
                SELECT 
                    'GL Transactions' as entity_type,
                    cc.companycodeid,
                    COUNT(gt.transaction_id) as usage_count
                FROM companycode cc
                LEFT JOIN gl_transactions gt ON cc.companycodeid = gt.company_code
                GROUP BY cc.companycodeid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    if companies.empty:
        st.warning("No company codes configured yet. Create your first company code to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Companies", len(companies))
    
    with col2:
        unique_countries = companies['country'].nunique()
        st.metric("Countries", unique_countries)
    
    with col3:
        unique_currencies = companies['currencycode'].nunique()
        st.metric("Currencies Used", unique_currencies)
    
    with col4:
        # Calculate total transactions across companies
        if not usage_stats.empty:
            journal_entries = usage_stats[
                (usage_stats['entity_type'] == 'Journal Entries')
            ]['usage_count'].sum()
            st.metric("Total Journal Entries", int(journal_entries))
        else:
            st.metric("Total Journal Entries", 0)
    
    # Company list
    st.subheader("📋 Company Code Summary")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        country_filter = st.selectbox(
            "Filter by Country",
            ["All"] + list(companies['country'].dropna().unique())
        )
    
    with col2:
        currency_filter = st.selectbox(
            "Filter by Currency",
            ["All"] + list(companies['currencycode'].dropna().unique())
        )
    
    with col3:
        fiscal_filter = st.selectbox(
            "Filter by Fiscal Year Variant",
            ["All"] + list(companies['fiscalyearvariant'].dropna().unique())
        )
    
    # Apply filters
    filtered_data = companies.copy()
    
    if country_filter != "All":
        filtered_data = filtered_data[filtered_data['country'] == country_filter]
    
    if currency_filter != "All":
        filtered_data = filtered_data[filtered_data['currencycode'] == currency_filter]
    
    if fiscal_filter != "All":
        filtered_data = filtered_data[filtered_data['fiscalyearvariant'] == fiscal_filter]
    
    # Display table
    if not filtered_data.empty:
        st.dataframe(
            filtered_data[[
                'companycodeid', 'name', 'country', 'currencycode', 
                'currency_name', 'fiscalyearvariant', 'createdat'
            ]],
            use_container_width=True,
            column_config={
                'companycodeid': 'Company ID',
                'name': 'Company Name',
                'country': 'Country',
                'currencycode': 'Currency',
                'currency_name': 'Currency Name',
                'fiscalyearvariant': 'Fiscal Year Variant',
                'createdat': st.column_config.DatetimeColumn('Created At')
            }
        )
    else:
        st.info("No companies match the selected filters.")
    
    # Usage analytics
    if not usage_stats.empty:
        st.subheader("📈 Company Usage Analytics")
        
        # Pivot usage stats for better visualization
        usage_pivot = usage_stats.pivot(
            index='companycodeid', 
            columns='entity_type', 
            values='usage_count'
        ).fillna(0).reset_index()
        
        fig = go.Figure()
        
        entity_types = ['Journal Entries', 'Business Units', 'GL Transactions']
        colors = ['lightblue', 'lightgreen', 'lightcoral']
        
        for i, entity_type in enumerate(entity_types):
            if entity_type in usage_pivot.columns:
                fig.add_trace(go.Bar(
                    name=entity_type,
                    x=usage_pivot['companycodeid'],
                    y=usage_pivot[entity_type],
                    marker_color=colors[i % len(colors)]
                ))
        
        fig.update_layout(
            title='Entity Usage by Company Code',
            xaxis_title='Company Code',
            yaxis_title='Count',
            barmode='group',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def show_create_company_code():
    """Create new company code interface."""
    st.header("➕ Create New Company Code")
    
    with st.form("create_company_code"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            companycodeid = st.text_input(
                "Company Code ID*", 
                max_chars=10,
                help="Unique company identifier (max 10 characters)"
            ).upper()
            name = st.text_input(
                "Company Name*",
                max_chars=100
            )
            country = st.selectbox(
                "Country*",
                [
                    "United States", "Canada", "United Kingdom", "Germany", 
                    "France", "Japan", "Australia", "Netherlands", "Switzerland",
                    "Singapore", "Hong Kong", "Sweden", "Denmark", "Norway"
                ]
            )
        
        with col2:
            st.subheader("Financial Configuration")
            
            # Get available currencies
            try:
                with engine.connect() as conn:
                    currencies = pd.read_sql(text("""
                        SELECT currency_code, currency_name, currency_symbol 
                        FROM currencies 
                        WHERE is_active = TRUE
                        ORDER BY currency_code
                    """), conn)
                
                if not currencies.empty:
                    currency_options = [
                        f"{row['currency_code']} - {row['currency_name']} ({row['currency_symbol']})"
                        for _, row in currencies.iterrows()
                    ]
                    currency_selection = st.selectbox("Company Currency*", currency_options)
                    currencycode = currency_selection.split(" - ")[0] if currency_selection else "USD"
                else:
                    currencycode = st.text_input("Company Currency*", value="USD", max_chars=3)
                    
            except Exception as e:
                st.error(f"Error loading currencies: {e}")
                currencycode = st.text_input("Company Currency*", value="USD", max_chars=3)
            
            fiscal_year_variant = st.selectbox(
                "Fiscal Year Variant",
                ["K4", "V3", "K1", "V1", "V4", "US", "UK", "DE", "FR", "JP"],
                help="K4=Calendar year, V3=April-March, etc."
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("Organizational Details")
            legal_form = st.selectbox(
                "Legal Form",
                ["Corporation", "LLC", "Partnership", "Branch", "Subsidiary", "Other"]
            )
            tax_number = st.text_input("Tax Number")
            vat_registration = st.text_input("VAT Registration Number")
        
        with col4:
            st.subheader("Address Information")
            address_line1 = st.text_input("Address Line 1")
            address_line2 = st.text_input("Address Line 2")
            city = st.text_input("City")
            postal_code = st.text_input("Postal Code")
            state_province = st.text_input("State/Province")
        
        col5, col6 = st.columns(2)
        
        with col5:
            st.subheader("Contact Information")
            phone = st.text_input("Phone Number")
            email = st.text_input("Email Address")
            website = st.text_input("Website")
        
        with col6:
            st.subheader("Settings")
            is_active = st.checkbox("Active", value=True)
            consolidation_company = st.checkbox("Consolidation Company", value=False)
            reporting_currency = st.text_input("Reporting Currency", value=currencycode)
        
        submitted = st.form_submit_button("Create Company Code", type="primary")
        
        if submitted:
            if not all([companycodeid, name, country, currencycode]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # First, enhance the companycode table if needed
                        # Check if additional columns exist
                        columns_to_add = {
                            'legal_form': 'VARCHAR(50)',
                            'tax_number': 'VARCHAR(50)',
                            'vat_registration': 'VARCHAR(50)',
                            'address_line1': 'TEXT',
                            'address_line2': 'TEXT', 
                            'city': 'VARCHAR(100)',
                            'postal_code': 'VARCHAR(20)',
                            'state_province': 'VARCHAR(100)',
                            'phone': 'VARCHAR(50)',
                            'email': 'VARCHAR(100)',
                            'website': 'VARCHAR(200)',
                            'is_active': 'BOOLEAN DEFAULT TRUE',
                            'consolidation_company': 'BOOLEAN DEFAULT FALSE',
                            'reporting_currency': 'VARCHAR(3)'
                        }
                        
                        for col_name, col_type in columns_to_add.items():
                            try:
                                conn.execute(text(f"ALTER TABLE companycode ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                            except:
                                pass  # Column might already exist
                        
                        # Insert new company code
                        conn.execute(text("""
                            INSERT INTO companycode (
                                companycodeid, name, country, currencycode, fiscalyearvariant,
                                legal_form, tax_number, vat_registration, address_line1, address_line2,
                                city, postal_code, state_province, phone, email, website,
                                is_active, consolidation_company, reporting_currency
                            ) VALUES (
                                :company_id, :company_name, :country, :currency, :fiscal_variant,
                                :legal_form, :tax_number, :vat_reg, :addr1, :addr2,
                                :city, :postal, :state, :phone, :email, :website,
                                :is_active, :consolidation, :reporting_curr
                            )
                        """), {
                            'company_id': companycodeid,
                            'company_name': name,
                            'country': country,
                            'currency': currencycode,
                            'fiscal_variant': fiscal_year_variant,
                            'legal_form': legal_form,
                            'tax_number': tax_number,
                            'vat_reg': vat_registration,
                            'addr1': address_line1,
                            'addr2': address_line2,
                            'city': city,
                            'postal': postal_code,
                            'state': state_province,
                            'phone': phone,
                            'email': email,
                            'website': website,
                            'is_active': is_active,
                            'consolidation': consolidation_company,
                            'reporting_curr': reporting_currency
                        })
                        conn.commit()
                    
                    st.success(f"✅ Company Code {companycodeid} created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Company Code {companycodeid} already exists!")
                    else:
                        st.error(f"❌ Error creating company code: {e}")

def show_fiscal_year_setup():
    """Configure fiscal year settings for companies."""
    st.header("💰 Fiscal Year Setup")
    
    try:
        with engine.connect() as conn:
            companies = pd.read_sql(text("""
                SELECT companycodeid, name, fiscalyearvariant, currencycode
                FROM companycode
                ORDER BY companycodeid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading companies: {e}")
        return
    
    if companies.empty:
        st.warning("No companies configured yet.")
        return
    
    st.subheader("📅 Fiscal Year Variants")
    
    # Show fiscal year variant explanations
    fiscal_variants = {
        'K4': 'Calendar Year (Jan-Dec)',
        'V3': 'April to March', 
        'K1': 'July to June',
        'V1': 'October to September',
        'V4': 'Custom Fiscal Year',
        'US': 'US Standard (Oct-Sep)',
        'UK': 'UK Tax Year (Apr-Mar)',
        'DE': 'German Standard (Jan-Dec)',
        'FR': 'French Standard (Jan-Dec)',
        'JP': 'Japanese Standard (Apr-Mar)'
    }
    
    for variant, description in fiscal_variants.items():
        st.write(f"**{variant}:** {description}")
    
    st.subheader("🏢 Company Fiscal Year Configuration")
    
    # Display current fiscal year settings
    for _, company in companies.iterrows():
        with st.expander(f"Company {company['companycodeid']} - {company['name']}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Current Fiscal Year Variant:** {company['fiscalyearvariant']}")
                st.write(f"**Description:** {fiscal_variants.get(company['fiscalyearvariant'], 'Unknown')}")
            
            with col2:
                st.write(f"**Company Currency:** {company['currencycode']}")
                st.write("**Status:** Active")
            
            # Allow fiscal year variant update
            new_variant = st.selectbox(
                f"Update Fiscal Year Variant for {company['companycodeid']}",
                list(fiscal_variants.keys()),
                index=list(fiscal_variants.keys()).index(company['fiscalyearvariant']) if company['fiscalyearvariant'] in fiscal_variants else 0,
                key=f"fiscal_variant_{company['companycodeid']}"
            )
            
            if st.button(f"Update {company['companycodeid']}", key=f"update_{company['companycodeid']}"):
                if new_variant != company['fiscalyearvariant']:
                    try:
                        with engine.connect() as conn:
                            conn.execute(text("""
                                UPDATE companycode 
                                SET fiscalyearvariant = :new_variant
                                WHERE companycodeid = :company_id
                            """), {
                                'new_variant': new_variant,
                                'company_id': company['companycodeid']
                            })
                            conn.commit()
                        st.success(f"✅ Updated fiscal year variant for {company['companycodeid']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error updating fiscal year variant: {e}")
                else:
                    st.info("No changes made - same variant selected")

def show_currency_assignment():
    """Manage currency assignments for companies."""
    st.header("💱 Currency Assignment")
    
    try:
        with engine.connect() as conn:
            # Get company currency assignments
            currency_assignments = pd.read_sql(text("""
                SELECT 
                    cc.companycodeid,
                    cc.name as company_name,
                    cc.currencycode,
                    cur.currency_name,
                    cur.currency_symbol,
                    cur.is_base_currency
                FROM companycode cc
                LEFT JOIN currencies cur ON cc.currencycode = cur.currency_code
                ORDER BY cc.companycodeid
            """), conn)
            
            # Get available currencies
            available_currencies = pd.read_sql(text("""
                SELECT currency_code, currency_name, currency_symbol, is_active
                FROM currencies
                WHERE is_active = TRUE
                ORDER BY currency_code
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    st.subheader("💰 Current Currency Assignments")
    
    if not currency_assignments.empty:
        st.dataframe(
            currency_assignments,
            use_container_width=True,
            column_config={
                'companycodeid': 'Company ID',
                'company_name': 'Company Name', 
                'currencycode': 'Currency Code',
                'currency_name': 'Currency Name',
                'currency_symbol': 'Symbol',
                'is_base_currency': st.column_config.CheckboxColumn('Base Currency')
            }
        )
    
    st.subheader("🔄 Update Currency Assignments")
    
    # Currency update form
    if not currency_assignments.empty and not available_currencies.empty:
        for _, company in currency_assignments.iterrows():
            with st.expander(f"Update {company['companycodeid']} - {company['company_name']}", expanded=False):
                current_currency = company['currencycode']
                
                currency_options = [
                    f"{row['currency_code']} - {row['currency_name']} ({row['currency_symbol']})"
                    for _, row in available_currencies.iterrows()
                ]
                
                # Find current selection index
                current_index = 0
                for i, option in enumerate(currency_options):
                    if option.startswith(current_currency):
                        current_index = i
                        break
                
                new_currency_selection = st.selectbox(
                    f"Currency for {company['companycodeid']}",
                    currency_options,
                    index=current_index,
                    key=f"currency_{company['companycodeid']}"
                )
                
                new_currency = new_currency_selection.split(" - ")[0]
                
                if st.button(f"Update Currency for {company['companycodeid']}", key=f"update_curr_{company['companycodeid']}"):
                    if new_currency != current_currency:
                        try:
                            with engine.connect() as conn:
                                conn.execute(text("""
                                    UPDATE companycode 
                                    SET currencycode = :new_currency
                                    WHERE companycodeid = :company_id
                                """), {
                                    'new_currency': new_currency,
                                    'company_id': company['companycodeid']
                                })
                                conn.commit()
                            st.success(f"✅ Updated currency for {company['companycodeid']} to {new_currency}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error updating currency: {e}")
                    else:
                        st.info("No changes made - same currency selected")

def show_company_reports():
    """Display company analysis and reports."""
    st.header("📋 Company Reports & Analysis")
    
    try:
        with engine.connect() as conn:
            # Comprehensive company analysis
            company_analysis = pd.read_sql(text("""
                SELECT 
                    cc.companycodeid,
                    cc.name,
                    cc.country,
                    cc.currencycode,
                    COUNT(DISTINCT jeh.documentnumber) as journal_entries,
                    COUNT(DISTINCT bu.unit_id) as business_units,
                    COUNT(DISTINCT gt.transaction_id) as gl_transactions,
                    MAX(jeh.createdat) as last_journal_entry,
                    cc.createdat as company_created
                FROM companycode cc
                LEFT JOIN journalentryheader jeh ON cc.companycodeid = jeh.companycodeid
                LEFT JOIN business_units bu ON cc.companycodeid = bu.company_code_id  
                LEFT JOIN gl_transactions gt ON cc.companycodeid = gt.company_code
                GROUP BY cc.companycodeid, cc.name, cc.country, cc.currencycode, cc.createdat
                ORDER BY cc.companycodeid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading analysis data: {e}")
        return
    
    if company_analysis.empty:
        st.info("No company data available for analysis.")
        return
    
    # Company activity analysis
    st.subheader("📊 Company Activity Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Transaction volume by company
        fig1 = px.bar(
            company_analysis,
            x='companycodeid',
            y='gl_transactions',
            title='GL Transactions by Company',
            color='gl_transactions',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Journal entries by company
        fig2 = px.bar(
            company_analysis,
            x='companycodeid',
            y='journal_entries',
            title='Journal Entries by Company',
            color='journal_entries',
            color_continuous_scale='plasma'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Geographic distribution
    st.subheader("🌍 Geographic Distribution")
    
    country_stats = company_analysis['country'].value_counts()
    if not country_stats.empty:
        fig3 = px.pie(
            values=country_stats.values,
            names=country_stats.index,
            title='Companies by Country'
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # Detailed company table
    st.subheader("📋 Detailed Company Analysis")
    
    st.dataframe(
        company_analysis,
        use_container_width=True,
        column_config={
            'companycodeid': 'Company ID',
            'name': 'Company Name',
            'country': 'Country',
            'currencycode': 'Currency',
            'journal_entries': st.column_config.NumberColumn('Journal Entries'),
            'business_units': st.column_config.NumberColumn('Business Units'),
            'gl_transactions': st.column_config.NumberColumn('GL Transactions'),
            'last_journal_entry': st.column_config.DatetimeColumn('Last Journal Entry'),
            'company_created': st.column_config.DatetimeColumn('Company Created')
        }
    )

def show_edit_company_codes():
    """Edit existing company codes."""
    st.header("✏️ Edit Company Codes")
    
    st.info("Select a company code below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            companies = pd.read_sql(text("""
                SELECT * FROM companycode 
                ORDER BY companycodeid
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading companies: {e}")
        return
    
    if companies.empty:
        st.warning("No companies available for editing.")
        return
    
    # Company selection
    selected_company = st.selectbox(
        "Select Company Code to Edit",
        options=companies['companycodeid'].tolist(),
        format_func=lambda x: f"{x} - {companies[companies['companycodeid']==x]['name'].iloc[0]}"
    )
    
    if selected_company:
        company_data = companies[companies['companycodeid'] == selected_company].iloc[0]
        
        st.subheader(f"Editing Company: {selected_company}")
        
        # Show current configuration
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Company ID:** {company_data['companycodeid']}")
                st.write(f"**Name:** {company_data['name']}")
                st.write(f"**Country:** {company_data['country']}")
                st.write(f"**Currency:** {company_data['currencycode']}")
            
            with col2:
                st.write(f"**Fiscal Year Variant:** {company_data['fiscalyearvariant']}")
                st.write(f"**Created:** {company_data['createdat']}")
                st.write("**Status:** Active" if company_data.get('is_active', True) else "**Status:** Inactive")
        
        st.write("**Full edit functionality would be implemented here for updating company configurations.**")

if __name__ == "__main__":
    main()