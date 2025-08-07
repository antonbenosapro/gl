"""
Field Status Groups Management System

Complete field status group master data management for document posting controls,
field validation, and posting key configuration.

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
    page_title="Field Status Groups Management",
    page_icon="🛡️",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Field Status Groups Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Field Status Groups Management", "Master Data", "Controls")
    
    st.title("🛡️ Field Status Groups Management")
    st.markdown("**Configure and manage field status groups for posting controls and validation**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 Field Controls")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Groups Overview",
                "➕ Create Field Status Group",
                "✏️ Edit Field Status Groups",
                "🔍 Field Status Analysis",
                "📋 Usage Reports",
                "⚙️ Advanced Configuration"
            ]
        )
    
    # Route to selected page
    if page == "📊 Groups Overview":
        show_groups_overview()
    elif page == "➕ Create Field Status Group":
        show_create_field_status_group()
    elif page == "✏️ Edit Field Status Groups":
        show_edit_field_status_groups()
    elif page == "🔍 Field Status Analysis":
        show_field_status_analysis()
    elif page == "📋 Usage Reports":
        show_usage_reports()
    elif page == "⚙️ Advanced Configuration":
        show_advanced_configuration()

def show_groups_overview():
    """Display field status groups overview dashboard."""
    st.header("📊 Field Status Groups Overview")
    
    # Load field status groups data
    try:
        with engine.connect() as conn:
            # Get field status groups
            groups = pd.read_sql(text("""
                SELECT 
                    fsg.group_id,
                    fsg.group_name,
                    fsg.group_description,
                    fsg.is_active,
                    fsg.allow_negative_postings,
                    fsg.created_by,
                    fsg.created_at,
                    fsg.modified_by,
                    fsg.modified_at
                FROM field_status_groups fsg
                ORDER BY fsg.group_id
            """), conn)
            
            # Get usage statistics
            usage_stats = pd.read_sql(text("""
                SELECT 
                    fsg.group_id,
                    fsg.group_name,
                    COUNT(DISTINCT dt.document_type) as document_types_using,
                    COUNT(DISTINCT jeh.companycodeid) as companies_using
                FROM field_status_groups fsg
                LEFT JOIN document_types dt ON fsg.group_id = dt.field_status_group
                LEFT JOIN journalentryheader jeh ON dt.document_type = jeh.document_type
                GROUP BY fsg.group_id, fsg.group_name
                ORDER BY fsg.group_id
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    if groups.empty:
        st.warning("No field status groups configured yet. Create your first group to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Groups", len(groups))
    
    with col2:
        active_groups = len(groups[groups['is_active'] == True])
        st.metric("Active Groups", active_groups)
    
    with col3:
        allow_negative = len(groups[groups['allow_negative_postings'] == True])
        st.metric("Allow Negative Postings", allow_negative)
    
    with col4:
        # Calculate total document types usage
        if not usage_stats.empty:
            total_usage = usage_stats['document_types_using'].sum()
            st.metric("Document Types Using", int(total_usage))
        else:
            st.metric("Document Types Using", 0)
    
    # Groups list
    st.subheader("📋 Field Status Groups Configuration")
    
    # Add filters
    col1, col2 = st.columns(2)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Active", "Inactive"]
        )
    
    with col2:
        negative_filter = st.selectbox(
            "Filter by Negative Postings",
            ["All", "Allowed", "Not Allowed"]
        )
    
    # Apply filters
    filtered_data = groups.copy()
    
    if status_filter == "Active":
        filtered_data = filtered_data[filtered_data['is_active'] == True]
    elif status_filter == "Inactive":
        filtered_data = filtered_data[filtered_data['is_active'] == False]
    
    if negative_filter == "Allowed":
        filtered_data = filtered_data[filtered_data['allow_negative_postings'] == True]
    elif negative_filter == "Not Allowed":
        filtered_data = filtered_data[filtered_data['allow_negative_postings'] == False]
    
    # Display table
    if not filtered_data.empty:
        st.dataframe(
            filtered_data[[
                'group_id', 'group_name', 'group_description', 'is_active',
                'allow_negative_postings', 'created_by', 'created_at'
            ]],
            use_container_width=True,
            column_config={
                'group_id': 'Group ID',
                'group_name': 'Group Name',
                'group_description': 'Description',
                'is_active': st.column_config.CheckboxColumn('Active'),
                'allow_negative_postings': st.column_config.CheckboxColumn('Allow Negative'),
                'created_by': 'Created By',
                'created_at': st.column_config.DatetimeColumn('Created At')
            }
        )
    else:
        st.info("No field status groups match the selected filters.")
    
    # Usage analytics
    if not usage_stats.empty:
        st.subheader("📈 Field Status Group Usage Analytics")
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Document Types Using',
            x=usage_stats['group_id'],
            y=usage_stats['document_types_using'],
            marker_color='lightblue',
            text=usage_stats['document_types_using'],
            textposition='auto'
        ))
        
        fig.update_layout(
            title='Document Type Usage by Field Status Group',
            xaxis_title='Field Status Group ID',
            yaxis_title='Number of Document Types',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

def show_create_field_status_group():
    """Create new field status group interface."""
    st.header("➕ Create New Field Status Group")
    
    with st.form("create_field_status_group"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            group_id = st.text_input(
                "Group ID*", 
                max_chars=10,
                help="Unique field status group identifier (e.g., ASSET01, REV01)"
            ).upper()
            group_name = st.text_input(
                "Group Name*",
                max_chars=100,
                help="Descriptive name for the field status group"
            )
            group_description = st.text_area(
                "Description",
                help="Detailed description of the field status group purpose"
            )
        
        with col2:
            st.subheader("General Settings")
            is_active = st.checkbox("Active", value=True)
            allow_negative_postings = st.checkbox(
                "Allow Negative Postings", 
                value=True,
                help="Allow negative amounts in postings for this group"
            )
        
        # Field Status Configuration
        st.subheader("📝 Field Status Configuration")
        st.markdown("""
        **Field Status Codes:**
        - **SUP** (Suppress): Field is hidden/not displayed
        - **REQ** (Required): Field must be filled (mandatory)
        - **OPT** (Optional): Field can be filled (optional)
        - **DIS** (Display): Field is displayed but not editable
        """)
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            st.markdown("**📋 Basic Fields**")
            reference_field_status = st.selectbox("Reference Field", ["SUP", "REQ", "OPT", "DIS"], index=2)
            document_header_text_status = st.selectbox("Document Header Text", ["SUP", "REQ", "OPT", "DIS"], index=2)
            assignment_field_status = st.selectbox("Assignment Field", ["SUP", "REQ", "OPT", "DIS"], index=2)
            text_field_status = st.selectbox("Text Field", ["SUP", "REQ", "OPT", "DIS"], index=2)
        
        with col4:
            st.markdown("**🏢 Organizational Fields**")
            business_unit_status = st.selectbox("Business Unit", ["SUP", "REQ", "OPT", "DIS"], index=2)
            business_area_status = st.selectbox("Business Area", ["SUP", "REQ", "OPT", "DIS"], index=2)
            trading_partner_status = st.selectbox("Trading Partner", ["SUP", "REQ", "OPT", "DIS"], index=0)
            partner_company_status = st.selectbox("Partner Company", ["SUP", "REQ", "OPT", "DIS"], index=0)
        
        with col5:
            st.markdown("**💰 Financial Fields**")
            tax_code_status = st.selectbox("Tax Code", ["SUP", "REQ", "OPT", "DIS"], index=2)
            payment_terms_status = st.selectbox("Payment Terms", ["SUP", "REQ", "OPT", "DIS"], index=0)
            baseline_date_status = st.selectbox("Baseline Date", ["SUP", "REQ", "OPT", "DIS"], index=0)
            amount_in_local_currency_status = st.selectbox("Amount in Local Currency", ["SUP", "REQ", "OPT", "DIS"], index=3)
            exchange_rate_status = st.selectbox("Exchange Rate", ["SUP", "REQ", "OPT", "DIS"], index=2)
        
        col6, col7 = st.columns(2)
        
        with col6:
            st.markdown("**📊 Quantity Fields**")
            quantity_status = st.selectbox("Quantity", ["SUP", "REQ", "OPT", "DIS"], index=0)
            base_unit_status = st.selectbox("Base Unit", ["SUP", "REQ", "OPT", "DIS"], index=0)
        
        with col7:
            st.markdown("**🏦 Banking Fields**")
            house_bank_status = st.selectbox("House Bank", ["SUP", "REQ", "OPT", "DIS"], index=0)
            account_id_status = st.selectbox("Account ID", ["SUP", "REQ", "OPT", "DIS"], index=0)
        
        submitted = st.form_submit_button("Create Field Status Group", type="primary")
        
        if submitted:
            if not all([group_id, group_name]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # Insert new field status group
                        conn.execute(text("""
                            INSERT INTO field_status_groups (
                                group_id, group_name, group_description, is_active, allow_negative_postings,
                                reference_field_status, document_header_text_status, assignment_field_status,
                                text_field_status, business_unit_status, business_area_status,
                                trading_partner_status, partner_company_status, tax_code_status, payment_terms_status,
                                baseline_date_status, amount_in_local_currency_status, exchange_rate_status,
                                quantity_status, base_unit_status, house_bank_status, account_id_status,
                                created_by
                            ) VALUES (
                                :group_id, :group_name, :description, :is_active, :allow_negative,
                                :ref_field, :doc_header, :assignment, :text_field, :business_unit,
                                :business_area, :trading_partner, :partner_company, :tax_code, :payment_terms,
                                :baseline_date, :local_currency, :exchange_rate, :quantity, :base_unit,
                                :house_bank, :account_id, :created_by
                            )
                        """), {
                            'group_id': group_id,
                            'group_name': group_name,
                            'description': group_description,
                            'is_active': is_active,
                            'allow_negative': allow_negative_postings,
                            'ref_field': reference_field_status,
                            'doc_header': document_header_text_status,
                            'assignment': assignment_field_status,
                            'text_field': text_field_status,
                            'business_unit': business_unit_status,
                            'business_area': business_area_status,
                            'trading_partner': trading_partner_status,
                            'partner_company': partner_company_status,
                            'tax_code': tax_code_status,
                            'payment_terms': payment_terms_status,
                            'baseline_date': baseline_date_status,
                            'local_currency': amount_in_local_currency_status,
                            'exchange_rate': exchange_rate_status,
                            'quantity': quantity_status,
                            'base_unit': base_unit_status,
                            'house_bank': house_bank_status,
                            'account_id': account_id_status,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success(f"✅ Field Status Group {group_id} created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Field Status Group ID {group_id} already exists!")
                    else:
                        st.error(f"❌ Error creating field status group: {e}")

def show_field_status_analysis():
    """Analyze field status configurations."""
    st.header("🔍 Field Status Analysis")
    
    try:
        with engine.connect() as conn:
            # Get field status configurations
            field_analysis = pd.read_sql(text("""
                SELECT 
                    group_id, group_name,
                    reference_field_status, document_header_text_status, assignment_field_status,
                    text_field_status, business_unit_status, business_area_status,
                    trading_partner_status, partner_company_status, tax_code_status, payment_terms_status,
                    baseline_date_status, amount_in_local_currency_status, exchange_rate_status,
                    quantity_status, base_unit_status, house_bank_status, account_id_status
                FROM field_status_groups
                WHERE is_active = TRUE
                ORDER BY group_id
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading analysis data: {e}")
        return
    
    if field_analysis.empty:
        st.info("No field status groups available for analysis.")
        return
    
    st.subheader("📊 Field Status Distribution Analysis")
    
    # Prepare data for analysis
    field_columns = [
        'reference_field_status', 'document_header_text_status', 'assignment_field_status',
        'text_field_status', 'business_unit_status', 'business_area_status',
        'trading_partner_status', 'partner_company_status', 'tax_code_status', 'payment_terms_status',
        'baseline_date_status', 'amount_in_local_currency_status', 'exchange_rate_status',
        'quantity_status', 'base_unit_status', 'house_bank_status', 'account_id_status'
    ]
    
    # Count field status values
    status_counts = {}
    for status in ['SUP', 'REQ', 'OPT', 'DIS']:
        status_counts[status] = sum((field_analysis[col] == status).sum() for col in field_columns)
    
    # Field status distribution chart
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            title='Overall Field Status Distribution',
            color_discrete_map={
                'SUP': '#ff7f7f',  # Light red
                'REQ': '#87ceeb',  # Light blue  
                'OPT': '#98fb98',  # Light green
                'DIS': '#dda0dd'   # Light purple
            }
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Required fields analysis
        required_fields_count = {}
        for col in field_columns:
            field_name = col.replace('_status', '').replace('_', ' ').title()
            required_fields_count[field_name] = (field_analysis[col] == 'REQ').sum()
        
        # Top required fields
        required_df = pd.DataFrame(
            list(required_fields_count.items()), 
            columns=['Field', 'Required_Count']
        ).sort_values('Required_Count', ascending=False).head(10)
        
        fig2 = px.bar(
            required_df,
            x='Required_Count',
            y='Field',
            orientation='h',
            title='Most Required Fields Across Groups',
            color='Required_Count',
            color_continuous_scale='blues'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Field status matrix
    st.subheader("🔍 Field Status Matrix")
    
    # Create a matrix showing field status for each group
    matrix_data = field_analysis[['group_id', 'group_name'] + field_columns].set_index(['group_id', 'group_name'])
    
    # Display as a heatmap-style matrix
    st.dataframe(
        matrix_data,
        use_container_width=True,
        column_config={
            col: st.column_config.SelectboxColumn(
                col.replace('_status', '').replace('_', ' ').title(),
                options=['SUP', 'REQ', 'OPT', 'DIS']
            ) for col in field_columns
        }
    )
    
    # Field usage recommendations
    st.subheader("💡 Configuration Recommendations")
    
    recommendations = []
    
    # Check for groups with too many required fields
    for _, row in field_analysis.iterrows():
        required_count = sum(row[col] == 'REQ' for col in field_columns)
        if required_count > 8:
            recommendations.append(f"⚠️ Group {row['group_id']} has {required_count} required fields - consider reducing for better user experience")
    
    # Check for groups with too many suppressed fields
    for _, row in field_analysis.iterrows():
        suppressed_count = sum(row[col] == 'SUP' for col in field_columns)
        if suppressed_count > 12:
            recommendations.append(f"💡 Group {row['group_id']} suppresses {suppressed_count} fields - ensure necessary fields are available")
    
    # Check for consistent organizational field settings
    org_fields = ['business_unit_status', 'business_area_status']
    for _, row in field_analysis.iterrows():
        org_statuses = [row[field] for field in org_fields]
        if len(set(org_statuses)) > 2:
            recommendations.append(f"🔄 Group {row['group_id']} has inconsistent organizational field settings - consider standardizing")
    
    if recommendations:
        for rec in recommendations:
            st.write(rec)
    else:
        st.success("✅ All field status group configurations look good!")

def show_usage_reports():
    """Display usage reports for field status groups."""
    st.header("📋 Field Status Group Usage Reports")
    
    try:
        with engine.connect() as conn:
            # Get usage by document types
            document_type_usage = pd.read_sql(text("""
                SELECT 
                    fsg.group_id,
                    fsg.group_name,
                    dt.document_type,
                    dt.document_type_name,
                    jeh.companycodeid as company_code,
                    cc.name as company_name
                FROM field_status_groups fsg
                INNER JOIN document_types dt ON fsg.group_id = dt.field_status_group
                LEFT JOIN journalentryheader jeh ON dt.document_type = jeh.document_type
                LEFT JOIN companycode cc ON jeh.companycodeid = cc.companycodeid
                WHERE fsg.is_active = TRUE
                ORDER BY fsg.group_id, dt.document_type
            """), conn)
            
            # Get field status group statistics
            group_stats = pd.read_sql(text("""
                SELECT 
                    fsg.group_id,
                    fsg.group_name,
                    fsg.is_active,
                    COUNT(DISTINCT dt.document_type) as document_types_count,
                    COUNT(DISTINCT jeh.companycodeid) as companies_count
                FROM field_status_groups fsg
                LEFT JOIN document_types dt ON fsg.group_id = dt.field_status_group
                LEFT JOIN journalentryheader jeh ON dt.document_type = jeh.document_type
                GROUP BY fsg.group_id, fsg.group_name, fsg.is_active
                ORDER BY document_types_count DESC
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading usage data: {e}")
        return
    
    st.subheader("📊 Usage Statistics")
    
    if not group_stats.empty:
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_assignments = group_stats['document_types_count'].sum()
            st.metric("Total Document Type Assignments", int(total_assignments))
        
        with col2:
            used_groups = len(group_stats[group_stats['document_types_count'] > 0])
            st.metric("Groups in Use", used_groups)
        
        with col3:
            unused_groups = len(group_stats[group_stats['document_types_count'] == 0])
            st.metric("Unused Groups", unused_groups)
        
        # Usage by group chart
        fig1 = px.bar(
            group_stats,
            x='group_id',
            y='document_types_count',
            title='Document Types Using Each Field Status Group',
            color='document_types_count',
            color_continuous_scale='viridis',
            text='document_types_count'
        )
        fig1.update_traces(textposition='auto')
        st.plotly_chart(fig1, use_container_width=True)
        
        # Detailed usage table
        st.subheader("📋 Detailed Usage Breakdown")
        
        st.dataframe(
            group_stats,
            use_container_width=True,
            column_config={
                'group_id': 'Group ID',
                'group_name': 'Group Name',
                'is_active': st.column_config.CheckboxColumn('Active'),
                'document_types_count': st.column_config.NumberColumn('Document Types'),
                'companies_count': st.column_config.NumberColumn('Companies')
            }
        )
    
    if not document_type_usage.empty:
        st.subheader("🔍 Document Type Assignments")
        
        # Document type assignments
        st.dataframe(
            document_type_usage,
            use_container_width=True,
            column_config={
                'group_id': 'Field Status Group',
                'group_name': 'Group Name',
                'document_type': 'Document Type',
                'document_type_name': 'Document Type Name',
                'company_code': 'Company Code',
                'company_name': 'Company Name'
            }
        )
    else:
        st.info("No document type assignments found.")

def show_advanced_configuration():
    """Advanced configuration options."""
    st.header("⚙️ Advanced Configuration")
    
    st.subheader("🔧 Field Status Group Utilities")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Clone Field Status Group")
        
        try:
            with engine.connect() as conn:
                groups = pd.read_sql(text("""
                    SELECT group_id, group_name 
                    FROM field_status_groups 
                    WHERE is_active = TRUE
                    ORDER BY group_id
                """), conn)
            
            if not groups.empty:
                source_group = st.selectbox(
                    "Source Group to Clone",
                    groups['group_id'].tolist(),
                    format_func=lambda x: f"{x} - {groups[groups['group_id']==x]['group_name'].iloc[0]}"
                )
                
                new_group_id = st.text_input("New Group ID", max_chars=10).upper()
                new_group_name = st.text_input("New Group Name")
                
                if st.button("Clone Group"):
                    if new_group_id and new_group_name and source_group:
                        try:
                            with engine.connect() as conn:
                                # Get source group data
                                source_data = pd.read_sql(text("""
                                    SELECT * FROM field_status_groups 
                                    WHERE group_id = :source_id
                                """), conn, params={'source_id': source_group}).iloc[0]
                                
                                # Insert cloned group
                                conn.execute(text("""
                                    INSERT INTO field_status_groups (
                                        group_id, group_name, group_description, is_active, allow_negative_postings,
                                        reference_field_status, document_header_text_status, assignment_field_status,
                                        text_field_status, business_unit_status, business_area_status,
                                        trading_partner_status, partner_company_status, tax_code_status, payment_terms_status,
                                        baseline_date_status, amount_in_local_currency_status, exchange_rate_status,
                                        quantity_status, base_unit_status, house_bank_status, account_id_status,
                                        created_by
                                    ) SELECT 
                                        :new_id, :new_name, :new_desc, is_active, allow_negative_postings,
                                        reference_field_status, document_header_text_status, assignment_field_status,
                                        text_field_status, business_unit_status, business_area_status,
                                        trading_partner_status, partner_company_status, tax_code_status, payment_terms_status,
                                        baseline_date_status, amount_in_local_currency_status, exchange_rate_status,
                                        quantity_status, base_unit_status, house_bank_status, account_id_status,
                                        :created_by
                                    FROM field_status_groups 
                                    WHERE group_id = :source_id
                                """), {
                                    'new_id': new_group_id,
                                    'new_name': new_group_name,
                                    'new_desc': f"Cloned from {source_group}",
                                    'source_id': source_group,
                                    'created_by': user.username
                                })
                                conn.commit()
                                
                            st.success(f"✅ Field Status Group {new_group_id} cloned from {source_group}!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error cloning group: {e}")
                    else:
                        st.error("Please fill in all required fields")
            
        except Exception as e:
            st.error(f"Error loading groups for cloning: {e}")
    
    with col2:
        st.subheader("📊 Bulk Operations")
        
        st.markdown("**Deactivate Unused Groups**")
        if st.button("Deactivate Groups with No Usage"):
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        UPDATE field_status_groups 
                        SET is_active = FALSE, 
                            modified_by = :user,
                            modified_at = CURRENT_TIMESTAMP
                        WHERE group_id NOT IN (
                            SELECT DISTINCT field_status_group 
                            FROM document_types 
                            WHERE field_status_group IS NOT NULL
                        )
                        AND is_active = TRUE
                    """), {'user': user.username})
                    
                    rows_updated = result.rowcount
                    conn.commit()
                    
                st.success(f"✅ Deactivated {rows_updated} unused field status groups")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error during bulk operation: {e}")
        
        st.markdown("**Reset Modified Timestamps**")
        if st.button("Update All Modified Timestamps"):
            try:
                with engine.connect() as conn:
                    conn.execute(text("""
                        UPDATE field_status_groups 
                        SET modified_at = CURRENT_TIMESTAMP,
                            modified_by = :user
                        WHERE modified_at IS NULL
                    """), {'user': user.username})
                    conn.commit()
                    
                st.success("✅ Updated all modified timestamps")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error updating timestamps: {e}")

def show_edit_field_status_groups():
    """Edit existing field status groups."""
    st.header("✏️ Edit Field Status Groups")
    
    st.info("Select a field status group below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            groups = pd.read_sql(text("""
                SELECT * FROM field_status_groups 
                ORDER BY group_id
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading groups: {e}")
        return
    
    if groups.empty:
        st.warning("No field status groups available for editing.")
        return
    
    # Group selection
    selected_group = st.selectbox(
        "Select Field Status Group to Edit",
        options=groups['group_id'].tolist(),
        format_func=lambda x: f"{x} - {groups[groups['group_id']==x]['group_name'].iloc[0]}"
    )
    
    if selected_group:
        group_data = groups[groups['group_id'] == selected_group].iloc[0]
        
        st.subheader(f"Editing Field Status Group: {selected_group}")
        
        # Show current configuration
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Group ID:** {group_data['group_id']}")
                st.write(f"**Group Name:** {group_data['group_name']}")
                st.write(f"**Description:** {group_data['group_description']}")
                st.write(f"**Active:** {'Yes' if group_data['is_active'] else 'No'}")
            
            with col2:
                st.write(f"**Allow Negative Postings:** {'Yes' if group_data['allow_negative_postings'] else 'No'}")
                st.write(f"**Created By:** {group_data['created_by']}")
                st.write(f"**Created At:** {group_data['created_at']}")
                st.write(f"**Modified By:** {group_data.get('modified_by', 'N/A')}")
        
        # Field status configuration display
        with st.expander("Field Status Configuration", expanded=False):
            field_status_columns = [
                'reference_field_status', 'document_header_text_status', 'assignment_field_status',
                'text_field_status', 'business_unit_status', 'business_area_status',
                'trading_partner_status', 'partner_company_status', 'tax_code_status', 'payment_terms_status',
                'baseline_date_status', 'amount_in_local_currency_status', 'exchange_rate_status',
                'quantity_status', 'base_unit_status', 'house_bank_status', 'account_id_status'
            ]
            
            for i in range(0, len(field_status_columns), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(field_status_columns):
                        field_name = field_status_columns[i + j]
                        display_name = field_name.replace('_status', '').replace('_', ' ').title()
                        col.write(f"**{display_name}:** {group_data[field_name]}")
        
        st.write("**Full edit functionality would be implemented here for updating field status group configurations.**")

if __name__ == "__main__":
    main()