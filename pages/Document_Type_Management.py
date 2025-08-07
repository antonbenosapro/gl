"""
Document Type Management System

Complete document type configuration with field controls, number ranges,
and posting control settings for SAP-aligned document processing.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    page_title="Document Type Management",
    page_icon="📄",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Document Type Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Document Type Management", "Master Data", "Configuration")
    
    st.title("📄 Document Type Management")
    st.markdown("**Configure document types for posting control and workflow management**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 Document Config")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Document Type Overview",
                "➕ Create Document Type",
                "✏️ Edit Document Types", 
                "🔢 Number Range Config",
                "⚙️ Field Controls",
                "📋 Usage Reports"
            ]
        )
    
    # Route to selected page
    if page == "📊 Document Type Overview":
        show_document_type_overview()
    elif page == "➕ Create Document Type":
        show_create_document_type()
    elif page == "✏️ Edit Document Types":
        show_edit_document_types()
    elif page == "🔢 Number Range Config":
        show_number_range_config()
    elif page == "⚙️ Field Controls":
        show_field_controls()
    elif page == "📋 Usage Reports":
        show_usage_reports()

def show_document_type_overview():
    """Display document type overview dashboard."""
    st.header("📊 Document Type Overview")
    
    # Load document type summary data
    try:
        with engine.connect() as conn:
            # Get document type summary
            doc_type_summary = pd.read_sql(text("""
                SELECT * FROM v_document_type_summary
                WHERE is_active = TRUE
                ORDER BY document_type
            """), conn)
            
            # Get usage statistics (would be from journalentryheader when available)
            usage_stats = pd.read_sql(text("""
                SELECT 
                    'SA' as document_type,
                    COUNT(*) as usage_count
                FROM journalentryheader
                WHERE document_type IS NOT NULL
                GROUP BY document_type
                UNION ALL
                SELECT document_type, 0 as usage_count
                FROM document_types
                WHERE document_type NOT IN (
                    SELECT COALESCE(document_type, 'SA') 
                    FROM journalentryheader 
                    WHERE document_type IS NOT NULL
                )
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    if doc_type_summary.empty:
        st.warning("No document types configured yet. Create your first document type to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Document Types", len(doc_type_summary))
    
    with col2:
        workflow_required = len(doc_type_summary[doc_type_summary['workflow_required'] == True])
        st.metric("Workflow Required", workflow_required)
    
    with col3:
        approval_required = len(doc_type_summary[doc_type_summary['approval_required'] == True])
        st.metric("Approval Required", approval_required)
    
    with col4:
        avg_number_ranges = doc_type_summary['number_ranges_configured'].mean()
        st.metric("Avg Number Ranges", f"{avg_number_ranges:.1f}")
    
    # Document type list
    st.subheader("📋 Document Type Summary")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        workflow_filter = st.selectbox(
            "Filter by Workflow",
            ["All", "Workflow Required", "No Workflow"]
        )
    
    with col2:
        approval_filter = st.selectbox(
            "Filter by Approval",
            ["All", "Approval Required", "No Approval"]
        )
    
    with col3:
        field_status_filter = st.selectbox(
            "Filter by Field Status Group",
            ["All"] + list(doc_type_summary['field_status_group'].dropna().unique())
        )
    
    # Apply filters
    filtered_data = doc_type_summary.copy()
    
    if workflow_filter == "Workflow Required":
        filtered_data = filtered_data[filtered_data['workflow_required'] == True]
    elif workflow_filter == "No Workflow":
        filtered_data = filtered_data[filtered_data['workflow_required'] == False]
    
    if approval_filter == "Approval Required":
        filtered_data = filtered_data[filtered_data['approval_required'] == True]
    elif approval_filter == "No Approval":
        filtered_data = filtered_data[filtered_data['approval_required'] == False]
    
    if field_status_filter != "All":
        filtered_data = filtered_data[filtered_data['field_status_group'] == field_status_filter]
    
    # Display table
    if not filtered_data.empty:
        st.dataframe(
            filtered_data[[
                'document_type', 'document_type_name', 'description',
                'field_status_group', 'workflow_required', 'approval_required',
                'number_ranges_configured', 'field_controls_defined'
            ]],
            use_container_width=True,
            column_config={
                'document_type': 'Doc Type',
                'document_type_name': 'Name',
                'description': 'Description',
                'field_status_group': 'Field Status Group',
                'workflow_required': st.column_config.CheckboxColumn('Workflow'),
                'approval_required': st.column_config.CheckboxColumn('Approval'),
                'number_ranges_configured': st.column_config.NumberColumn('Number Ranges'),
                'field_controls_defined': st.column_config.NumberColumn('Field Controls')
            }
        )
    else:
        st.info("No document types match the selected filters.")
    
    # Workflow and approval distribution chart
    if not filtered_data.empty:
        st.subheader("📈 Document Type Configuration Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Workflow distribution pie chart
            workflow_dist = filtered_data['workflow_required'].value_counts()
            fig1 = px.pie(
                values=workflow_dist.values,
                names=['No Workflow' if not x else 'Workflow Required' for x in workflow_dist.index],
                title='Workflow Configuration Distribution',
                color_discrete_map={
                    'Workflow Required': '#ff7f0e',
                    'No Workflow': '#1f77b4'
                }
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Approval distribution pie chart
            approval_dist = filtered_data['approval_required'].value_counts()
            fig2 = px.pie(
                values=approval_dist.values,
                names=['No Approval' if not x else 'Approval Required' for x in approval_dist.index],
                title='Approval Configuration Distribution',
                color_discrete_map={
                    'Approval Required': '#d62728',
                    'No Approval': '#2ca02c'
                }
            )
            st.plotly_chart(fig2, use_container_width=True)

def show_create_document_type():
    """Create new document type interface."""
    st.header("➕ Create New Document Type")
    
    with st.form("create_document_type"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            document_type = st.text_input(
                "Document Type*", 
                max_chars=2,
                help="2-character document type code (e.g., SA, DR, KR)"
            ).upper()
            document_type_name = st.text_input(
                "Document Type Name*",
                max_chars=100
            )
            description = st.text_area("Description")
        
        with col2:
            st.subheader("Account Types & Authorization")
            account_types_allowed = st.text_input(
                "Account Types Allowed*",
                value="DKSA",
                max_chars=20,
                help="D=Customer, K=Vendor, S=GL Account, A=Asset"
            )
            authorization_group = st.text_input("Authorization Group")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("Posting Control")
            negative_postings_allowed = st.checkbox("Allow Negative Postings", value=True)
            cross_company_postings = st.checkbox("Cross Company Postings", value=False)
            foreign_currency_allowed = st.checkbox("Foreign Currency Allowed", value=True)
            reference_procedure = st.selectbox(
                "Reference Procedure", 
                ["NORMAL", "HEADER", "LINE"]
            )
        
        with col4:
            st.subheader("Workflow & Approval")
            workflow_required = st.checkbox("Workflow Required", value=False)
            automatic_workflow = st.checkbox("Automatic Workflow", value=False)
            approval_required = st.checkbox("Approval Required", value=False)
            default_approval_level = st.number_input(
                "Default Approval Level", 
                min_value=1, max_value=5, value=1
            )
        
        col5, col6 = st.columns(2)
        
        with col5:
            st.subheader("Field Status & Integration")
            # Get existing field status groups
            try:
                with engine.connect() as conn:
                    field_status_groups = pd.read_sql(text("""
                        SELECT group_id, group_name 
                        FROM field_status_groups 
                        WHERE is_active = TRUE
                        ORDER BY group_id
                    """), conn)
                
                if not field_status_groups.empty:
                    fs_options = [f"{row['group_id']} - {row['group_name']}" 
                                 for _, row in field_status_groups.iterrows()]
                    field_status_selection = st.selectbox("Field Status Group", fs_options)
                    field_status_group = field_status_selection.split(" - ")[0] if field_status_selection else None
                else:
                    field_status_group = st.text_input("Field Status Group", value="ASSET01")
                
            except Exception as e:
                field_status_group = st.text_input("Field Status Group", value="ASSET01")
            
            cash_management_integration = st.checkbox("Cash Management Integration", value=False)
            fixed_asset_integration = st.checkbox("Fixed Asset Integration", value=False)
        
        with col6:
            st.subheader("Tax & Period Control")
            input_tax_allowed = st.checkbox("Input Tax Allowed", value=True)
            output_tax_allowed = st.checkbox("Output Tax Allowed", value=True)
            posting_period_check = st.checkbox("Posting Period Check", value=True)
            exchange_rate_required = st.checkbox("Exchange Rate Required", value=False)
        
        col7, col8 = st.columns(2)
        
        with col7:
            st.subheader("Number Range")
            number_range_object = st.text_input("Number Range Object", value="JE_DOC")
            number_range_year_dependent = st.checkbox("Year Dependent", value=True)
        
        with col8:
            st.subheader("Status")
            is_active = st.checkbox("Active", value=True)
            is_system_document = st.checkbox("System Document", value=False)
        
        submitted = st.form_submit_button("Create Document Type", type="primary")
        
        if submitted:
            if not all([document_type, document_type_name, account_types_allowed]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # Insert new document type
                        conn.execute(text("""
                            INSERT INTO document_types (
                                document_type, document_type_name, description,
                                number_range_object, number_range_year_dependent,
                                authorization_group, account_types_allowed,
                                negative_postings_allowed, cross_company_postings, reference_procedure,
                                workflow_required, automatic_workflow, approval_required, default_approval_level,
                                cash_management_integration, fixed_asset_integration,
                                field_status_group, foreign_currency_allowed, exchange_rate_required,
                                input_tax_allowed, output_tax_allowed, posting_period_check,
                                is_active, is_system_document, created_by
                            ) VALUES (
                                :doc_type, :doc_name, :description,
                                :nr_object, :nr_year_dep,
                                :auth_group, :account_types,
                                :negative_post, :cross_company, :ref_proc,
                                :workflow_req, :auto_workflow, :approval_req, :approval_level,
                                :cash_mgmt, :asset_integration,
                                :field_status, :foreign_curr, :fx_required,
                                :input_tax, :output_tax, :period_check,
                                :is_active, :is_system, :created_by
                            )
                        """), {
                            'doc_type': document_type,
                            'doc_name': document_type_name,
                            'description': description,
                            'nr_object': number_range_object,
                            'nr_year_dep': number_range_year_dependent,
                            'auth_group': authorization_group,
                            'account_types': account_types_allowed,
                            'negative_post': negative_postings_allowed,
                            'cross_company': cross_company_postings,
                            'ref_proc': reference_procedure,
                            'workflow_req': workflow_required,
                            'auto_workflow': automatic_workflow,
                            'approval_req': approval_required,
                            'approval_level': default_approval_level,
                            'cash_mgmt': cash_management_integration,
                            'asset_integration': fixed_asset_integration,
                            'field_status': field_status_group,
                            'foreign_curr': foreign_currency_allowed,
                            'fx_required': exchange_rate_required,
                            'input_tax': input_tax_allowed,
                            'output_tax': output_tax_allowed,
                            'period_check': posting_period_check,
                            'is_active': is_active,
                            'is_system': is_system_document,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success(f"✅ Document Type {document_type} created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Document Type {document_type} already exists!")
                    else:
                        st.error(f"❌ Error creating document type: {e}")

def show_number_range_config():
    """Configure number ranges for document types."""
    st.header("🔢 Number Range Configuration")
    
    # Load existing number ranges
    try:
        with engine.connect() as conn:
            number_ranges = pd.read_sql(text("""
                SELECT 
                    dnr.range_id,
                    dnr.document_type,
                    dt.document_type_name,
                    dnr.company_code_id,
                    dnr.fiscal_year,
                    dnr.range_from,
                    dnr.range_to,
                    dnr.current_number,
                    dnr.external_numbering,
                    dnr.is_active,
                    dnr.range_exhausted
                FROM document_number_ranges dnr
                JOIN document_types dt ON dnr.document_type = dt.document_type
                WHERE dnr.is_active = TRUE
                ORDER BY dnr.document_type, dnr.fiscal_year
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading number ranges: {e}")
        return
    
    # Number range creation form
    st.subheader("➕ Create New Number Range")
    
    with st.form("create_number_range"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get document types for selection
            try:
                with engine.connect() as conn:
                    doc_types = pd.read_sql(text("""
                        SELECT document_type, document_type_name 
                        FROM document_types 
                        WHERE is_active = TRUE
                        ORDER BY document_type
                    """), conn)
                
                dt_options = [f"{row['document_type']} - {row['document_type_name']}" 
                             for _, row in doc_types.iterrows()]
                selected_dt = st.selectbox("Document Type*", dt_options)
                document_type = selected_dt.split(" - ")[0] if selected_dt else None
                
            except Exception as e:
                document_type = st.text_input("Document Type*")
        
        with col2:
            company_code_id = st.text_input("Company Code*", value="1000")
            fiscal_year = st.number_input(
                "Fiscal Year*", 
                min_value=2020, max_value=2030, value=2025
            )
        
        with col3:
            external_numbering = st.checkbox("External Numbering", value=False)
            number_length = st.number_input("Number Length", min_value=6, max_value=15, value=10)
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            range_from = st.number_input("Range From*", min_value=1, value=1000000000)
            range_to = st.number_input("Range To*", min_value=1, value=9999999999)
        
        with col5:
            current_number = st.number_input("Current Number", min_value=1, value=1000000001)
            interval_size = st.number_input("Interval Size", min_value=1, value=1)
        
        with col6:
            prefix = st.text_input("Prefix")
            suffix = st.text_input("Suffix")
        
        submitted_range = st.form_submit_button("Create Number Range", type="primary")
        
        if submitted_range:
            if not all([document_type, company_code_id, fiscal_year]):
                st.error("Please fill in all required fields")
            elif range_from >= range_to:
                st.error("Range From must be less than Range To")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO document_number_ranges (
                                document_type, company_code_id, fiscal_year,
                                range_from, range_to, current_number,
                                number_length, prefix, suffix,
                                external_numbering, interval_size, created_by
                            ) VALUES (
                                :doc_type, :company, :fiscal_year,
                                :range_from, :range_to, :current_number,
                                :number_length, :prefix, :suffix,
                                :external_numbering, :interval_size, :created_by
                            )
                        """), {
                            'doc_type': document_type,
                            'company': company_code_id,
                            'fiscal_year': fiscal_year,
                            'range_from': range_from,
                            'range_to': range_to,
                            'current_number': current_number,
                            'number_length': number_length,
                            'prefix': prefix,
                            'suffix': suffix,
                            'external_numbering': external_numbering,
                            'interval_size': interval_size,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success("✅ Number range created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error("❌ Number range already exists for this document type, company, and year!")
                    else:
                        st.error(f"❌ Error creating number range: {e}")
    
    # Display existing number ranges
    if not number_ranges.empty:
        st.subheader("📋 Existing Number Ranges")
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dt_filter = st.selectbox(
                "Filter by Document Type",
                ["All"] + list(number_ranges['document_type'].unique())
            )
        
        with col2:
            company_filter = st.selectbox(
                "Filter by Company",
                ["All"] + list(number_ranges['company_code_id'].unique())
            )
        
        with col3:
            year_filter = st.selectbox(
                "Filter by Fiscal Year",
                ["All"] + list(number_ranges['fiscal_year'].unique())
            )
        
        # Apply filters
        filtered_ranges = number_ranges.copy()
        
        if dt_filter != "All":
            filtered_ranges = filtered_ranges[filtered_ranges['document_type'] == dt_filter]
        
        if company_filter != "All":
            filtered_ranges = filtered_ranges[filtered_ranges['company_code_id'] == company_filter]
        
        if year_filter != "All":
            filtered_ranges = filtered_ranges[filtered_ranges['fiscal_year'] == year_filter]
        
        # Display number ranges table
        st.dataframe(
            filtered_ranges[[
                'document_type', 'document_type_name', 'company_code_id', 'fiscal_year',
                'range_from', 'range_to', 'current_number', 'external_numbering', 'range_exhausted'
            ]],
            use_container_width=True,
            column_config={
                'document_type': 'Doc Type',
                'document_type_name': 'Name',
                'company_code_id': 'Company',
                'fiscal_year': 'Fiscal Year',
                'range_from': st.column_config.NumberColumn('Range From'),
                'range_to': st.column_config.NumberColumn('Range To'),
                'current_number': st.column_config.NumberColumn('Current Number'),
                'external_numbering': st.column_config.CheckboxColumn('External'),
                'range_exhausted': st.column_config.CheckboxColumn('Exhausted')
            }
        )
    else:
        st.info("No number ranges configured yet. Create your first number range above.")

def show_field_controls():
    """Configure field controls for document types."""
    st.header("⚙️ Field Controls Configuration")
    
    st.info("Field controls determine which fields are required, optional, suppressed, or display-only for each document type.")
    
    # Load existing field controls
    try:
        with engine.connect() as conn:
            field_controls = pd.read_sql(text("""
                SELECT 
                    dtfc.control_id,
                    dtfc.document_type,
                    dt.document_type_name,
                    dtfc.field_name,
                    dtfc.field_status,
                    dtfc.field_group,
                    dtfc.validation_rule,
                    dtfc.default_value
                FROM document_type_field_controls dtfc
                JOIN document_types dt ON dtfc.document_type = dt.document_type
                WHERE dtfc.is_active = TRUE
                ORDER BY dtfc.document_type, dtfc.field_name
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading field controls: {e}")
        return
    
    # Field control creation form
    st.subheader("➕ Create Field Control")
    
    with st.form("create_field_control"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get document types for selection
            try:
                with engine.connect() as conn:
                    doc_types = pd.read_sql(text("""
                        SELECT document_type, document_type_name 
                        FROM document_types 
                        WHERE is_active = TRUE
                        ORDER BY document_type
                    """), conn)
                
                dt_options = [f"{row['document_type']} - {row['document_type_name']}" 
                             for _, row in doc_types.iterrows()]
                selected_dt = st.selectbox("Document Type*", dt_options)
                document_type = selected_dt.split(" - ")[0] if selected_dt else None
                
            except Exception as e:
                document_type = st.text_input("Document Type*")
        
        with col2:
            field_name = st.selectbox(
                "Field Name*",
                [
                    "posting_date", "document_date", "reference", "header_text",
                    "gl_account", "debit_amount", "credit_amount", "cost_center",
                    "profit_center", "business_area", "currency", "exchange_rate",
                    "tax_code", "payment_terms", "baseline_date"
                ]
            )
            field_status = st.selectbox(
                "Field Status*",
                ["REQ", "OPT", "SUP", "DIS"],
                help="REQ=Required, OPT=Optional, SUP=Suppressed, DIS=Display Only"
            )
        
        with col3:
            field_group = st.selectbox(
                "Field Group",
                ["GENERAL", "HEADER", "LINEITEM", "CURRENCY", "TAX", "PAYMENT"]
            )
            validation_rule = st.text_input("Validation Rule")
            default_value = st.text_input("Default Value")
        
        submitted_control = st.form_submit_button("Create Field Control", type="primary")
        
        if submitted_control:
            if not all([document_type, field_name, field_status]):
                st.error("Please fill in all required fields")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO document_type_field_controls (
                                document_type, field_name, field_status, field_group,
                                validation_rule, default_value, created_by
                            ) VALUES (
                                :doc_type, :field_name, :field_status, :field_group,
                                :validation_rule, :default_value, :created_by
                            )
                        """), {
                            'doc_type': document_type,
                            'field_name': field_name,
                            'field_status': field_status,
                            'field_group': field_group,
                            'validation_rule': validation_rule,
                            'default_value': default_value,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success("✅ Field control created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error("❌ Field control already exists for this document type and field!")
                    else:
                        st.error(f"❌ Error creating field control: {e}")
    
    # Display existing field controls
    if not field_controls.empty:
        st.subheader("📋 Existing Field Controls")
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dt_filter = st.selectbox(
                "Filter by Document Type",
                ["All"] + list(field_controls['document_type'].unique()),
                key="fc_dt_filter"
            )
        
        with col2:
            status_filter = st.selectbox(
                "Filter by Field Status",
                ["All"] + list(field_controls['field_status'].unique())
            )
        
        with col3:
            group_filter = st.selectbox(
                "Filter by Field Group",
                ["All"] + list(field_controls['field_group'].unique())
            )
        
        # Apply filters
        filtered_controls = field_controls.copy()
        
        if dt_filter != "All":
            filtered_controls = filtered_controls[filtered_controls['document_type'] == dt_filter]
        
        if status_filter != "All":
            filtered_controls = filtered_controls[filtered_controls['field_status'] == status_filter]
        
        if group_filter != "All":
            filtered_controls = filtered_controls[filtered_controls['field_group'] == group_filter]
        
        # Display field controls table
        st.dataframe(
            filtered_controls[[
                'document_type', 'document_type_name', 'field_name', 'field_status',
                'field_group', 'validation_rule', 'default_value'
            ]],
            use_container_width=True,
            column_config={
                'document_type': 'Doc Type',
                'document_type_name': 'Type Name',
                'field_name': 'Field Name',
                'field_status': 'Status',
                'field_group': 'Group',
                'validation_rule': 'Validation',
                'default_value': 'Default'
            }
        )
    else:
        st.info("No field controls configured yet. Create your first field control above.")

def show_usage_reports():
    """Display document type usage and analysis reports."""
    st.header("📋 Document Type Usage Reports")
    
    st.info("Usage statistics will be available once journal entries are created with document type assignments.")
    
    # Placeholder for usage statistics
    st.subheader("📊 Usage Statistics")
    st.write("Usage data will be populated from journal entry transactions.")
    
    # Document type configuration completeness
    st.subheader("🔧 Configuration Completeness")
    
    try:
        with engine.connect() as conn:
            completeness = pd.read_sql(text("""
                SELECT 
                    dt.document_type,
                    dt.document_type_name,
                    dt.is_active,
                    CASE WHEN dnr.document_type IS NOT NULL THEN 'Yes' ELSE 'No' END as has_number_range,
                    CASE WHEN dtfc.document_type IS NOT NULL THEN 'Yes' ELSE 'No' END as has_field_controls,
                    dt.field_status_group,
                    dt.workflow_required,
                    dt.approval_required
                FROM document_types dt
                LEFT JOIN (
                    SELECT DISTINCT document_type 
                    FROM document_number_ranges 
                    WHERE is_active = TRUE
                ) dnr ON dt.document_type = dnr.document_type
                LEFT JOIN (
                    SELECT DISTINCT document_type 
                    FROM document_type_field_controls 
                    WHERE is_active = TRUE
                ) dtfc ON dt.document_type = dtfc.document_type
                WHERE dt.is_active = TRUE
                ORDER BY dt.document_type
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading completeness data: {e}")
        return
    
    if not completeness.empty:
        # Configuration completeness table
        st.dataframe(
            completeness,
            use_container_width=True,
            column_config={
                'document_type': 'Doc Type',
                'document_type_name': 'Name',
                'is_active': st.column_config.CheckboxColumn('Active'),
                'has_number_range': 'Number Range',
                'has_field_controls': 'Field Controls',
                'field_status_group': 'Field Status Group',
                'workflow_required': st.column_config.CheckboxColumn('Workflow'),
                'approval_required': st.column_config.CheckboxColumn('Approval')
            }
        )
        
        # Configuration summary metrics
        st.subheader("📈 Configuration Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_types = len(completeness)
            st.metric("Total Document Types", total_types)
        
        with col2:
            with_number_ranges = len(completeness[completeness['has_number_range'] == 'Yes'])
            st.metric("With Number Ranges", f"{with_number_ranges}/{total_types}")
        
        with col3:
            with_field_controls = len(completeness[completeness['has_field_controls'] == 'Yes'])
            st.metric("With Field Controls", f"{with_field_controls}/{total_types}")
        
        with col4:
            config_complete = len(completeness[
                (completeness['has_number_range'] == 'Yes') & 
                (completeness['has_field_controls'] == 'Yes')
            ])
            st.metric("Fully Configured", f"{config_complete}/{total_types}")

def show_edit_document_types():
    """Edit existing document types."""
    st.header("✏️ Edit Document Types")
    
    st.info("Select a document type below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            doc_types = pd.read_sql(text("""
                SELECT * FROM document_types 
                WHERE is_active = TRUE
                ORDER BY document_type
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading document types: {e}")
        return
    
    if doc_types.empty:
        st.warning("No document types available for editing.")
        return
    
    # Document type selection
    selected_type = st.selectbox(
        "Select Document Type to Edit",
        options=doc_types['document_type'].tolist(),
        format_func=lambda x: f"{x} - {doc_types[doc_types['document_type']==x]['document_type_name'].iloc[0]}"
    )
    
    if selected_type:
        type_data = doc_types[doc_types['document_type'] == selected_type].iloc[0]
        
        st.subheader(f"Editing Document Type: {selected_type}")
        
        # Show current configuration in an expandable section
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Name:** {type_data['document_type_name']}")
                st.write(f"**Description:** {type_data['description']}")
                st.write(f"**Account Types:** {type_data['account_types_allowed']}")
                st.write(f"**Field Status Group:** {type_data['field_status_group']}")
            
            with col2:
                st.write(f"**Workflow Required:** {'Yes' if type_data['workflow_required'] else 'No'}")
                st.write(f"**Approval Required:** {'Yes' if type_data['approval_required'] else 'No'}")
                st.write(f"**Foreign Currency:** {'Yes' if type_data['foreign_currency_allowed'] else 'No'}")
                st.write(f"**Active:** {'Yes' if type_data['is_active'] else 'No'}")
        
        st.write("**Edit functionality would be implemented here for updating document type configurations.**")

if __name__ == "__main__":
    main()