"""
Business Area Management System

Complete business area master data management with hierarchical structure,
segment reporting, and derivation rules for automatic assignment.

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
    page_title="Business Area Management",
    page_icon="🏢",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Business Area Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Business Area Management", "Master Data", "Segment Reporting")
    
    st.title("🏢 Business Area Management")
    st.markdown("**Configure business areas for segment reporting and consolidation**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 BA Management")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Business Area Overview",
                "➕ Create Business Area",
                "✏️ Edit Business Areas",
                "🔗 Manage Assignments", 
                "📈 Hierarchy View",
                "⚙️ Derivation Rules",
                "📋 Segment Reports"
            ]
        )
    
    # Route to selected page
    if page == "📊 Business Area Overview":
        show_business_area_overview()
    elif page == "➕ Create Business Area":
        show_create_business_area()
    elif page == "✏️ Edit Business Areas":
        show_edit_business_areas()
    elif page == "🔗 Manage Assignments":
        show_manage_assignments()
    elif page == "📈 Hierarchy View":
        show_hierarchy_view()
    elif page == "⚙️ Derivation Rules":
        show_derivation_rules()
    elif page == "📋 Segment Reports":
        show_segment_reports()

def show_business_area_overview():
    """Display business area overview dashboard."""
    st.header("📊 Business Area Overview")
    
    # Load business area summary data
    try:
        with engine.connect() as conn:
            # Get business area summary
            ba_summary = pd.read_sql(text("""
                SELECT * FROM v_business_area_summary
                WHERE is_active = TRUE
                ORDER BY business_area_id
            """), conn)
            
            # Get assignment statistics
            assignment_stats = pd.read_sql(text("""
                SELECT 
                    object_type,
                    COUNT(*) as total_assignments,
                    COUNT(DISTINCT business_area_id) as business_areas_used
                FROM business_area_assignments
                WHERE is_active = TRUE
                GROUP BY object_type
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return
    
    if ba_summary.empty:
        st.warning("No business areas configured yet. Create your first business area to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Business Areas", len(ba_summary))
    
    with col2:
        consolidation_relevant = len(ba_summary[ba_summary['consolidation_relevant'] == True])
        st.metric("Consolidation Relevant", consolidation_relevant)
    
    with col3:
        total_assignments = ba_summary['total_assignments'].sum()
        st.metric("Total Assignments", int(total_assignments))
    
    with col4:
        avg_assignments = ba_summary['total_assignments'].mean()
        st.metric("Avg Assignments/BA", f"{avg_assignments:.1f}")
    
    # Business area list
    st.subheader("📋 Business Area Summary")
    
    # Add filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        company_filter = st.selectbox(
            "Filter by Company",
            ["All"] + list(ba_summary['company_code_id'].unique())
        )
    
    with col2:
        consolidation_filter = st.selectbox(
            "Filter by Consolidation",
            ["All", "Consolidation Relevant", "Not Relevant"]
        )
    
    with col3:
        assignment_filter = st.selectbox(
            "Filter by Assignments",
            ["All", "With Assignments", "No Assignments"]
        )
    
    # Apply filters
    filtered_data = ba_summary.copy()
    
    if company_filter != "All":
        filtered_data = filtered_data[filtered_data['company_code_id'] == company_filter]
    
    if consolidation_filter == "Consolidation Relevant":
        filtered_data = filtered_data[filtered_data['consolidation_relevant'] == True]
    elif consolidation_filter == "Not Relevant":
        filtered_data = filtered_data[filtered_data['consolidation_relevant'] == False]
    
    if assignment_filter == "With Assignments":
        filtered_data = filtered_data[filtered_data['total_assignments'] > 0]
    elif assignment_filter == "No Assignments":
        filtered_data = filtered_data[filtered_data['total_assignments'] == 0]
    
    # Display table
    if not filtered_data.empty:
        st.dataframe(
            filtered_data[[
                'business_area_id', 'business_area_name', 'short_name', 'company_code_id',
                'budget_responsible', 'consolidation_relevant', 'total_assignments', 
                'gl_account_assignments', 'profit_center_assignments'
            ]],
            use_container_width=True,
            column_config={
                'business_area_id': 'Business Area ID',
                'business_area_name': 'Name',
                'short_name': 'Short Name',
                'company_code_id': 'Company',
                'budget_responsible': 'Budget Responsible',
                'consolidation_relevant': st.column_config.CheckboxColumn('Consolidation'),
                'total_assignments': st.column_config.NumberColumn('Total Assignments'),
                'gl_account_assignments': st.column_config.NumberColumn('GL Accounts'),
                'profit_center_assignments': st.column_config.NumberColumn('Profit Centers')
            }
        )
    else:
        st.info("No business areas match the selected filters.")
    
    # Assignment type distribution chart
    if not assignment_stats.empty:
        st.subheader("📈 Assignment Distribution")
        
        fig = px.bar(
            assignment_stats,
            x='object_type',
            y='total_assignments',
            title='Assignments by Object Type',
            color='total_assignments',
            color_continuous_scale='viridis'
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

def show_create_business_area():
    """Create new business area interface."""
    st.header("➕ Create New Business Area")
    
    with st.form("create_business_area"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            business_area_id = st.text_input(
                "Business Area ID*", 
                max_chars=4,
                help="4-character identifier (e.g., CORP, SALE, PROD)"
            ).upper()
            business_area_name = st.text_input(
                "Business Area Name*",
                max_chars=100
            )
            short_name = st.text_input(
                "Short Name*",
                max_chars=20
            )
            description = st.text_area("Description")
        
        with col2:
            st.subheader("Organizational Assignment")
            company_code_id = st.text_input("Company Code*", value="1000")
            controlling_area = st.text_input("Controlling Area", value="C001")
            budget_responsible = st.text_input("Budget Responsible")
            
            # Get existing business areas for parent selection
            try:
                with engine.connect() as conn:
                    existing_bas = pd.read_sql(text("""
                        SELECT business_area_id, business_area_name 
                        FROM business_areas 
                        WHERE is_active = TRUE
                        ORDER BY business_area_id
                    """), conn)
                
                parent_options = ["None"] + [f"{row['business_area_id']} - {row['business_area_name']}" 
                                           for _, row in existing_bas.iterrows()]
                parent_selection = st.selectbox("Parent Business Area", parent_options)
                parent_business_area = None if parent_selection == "None" else parent_selection.split(" - ")[0]
                
            except Exception as e:
                st.error(f"Error loading parent options: {e}")
                parent_business_area = None
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("Reporting & Consolidation")
            segment_for_reporting = st.text_input("Segment for Reporting")
            consolidation_business_area = st.text_input("Consolidation Business Area")
            consolidation_relevant = st.checkbox("Consolidation Relevant", value=True)
            elimination_business_area = st.text_input("Elimination Business Area")
        
        with col4:
            st.subheader("Financial Control")
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "JPY", "CAD"])
            balance_sheet_preparation = st.checkbox("Balance Sheet Preparation", value=True)
            profit_loss_preparation = st.checkbox("Profit & Loss Preparation", value=True)
            statistical_postings_allowed = st.checkbox("Statistical Postings Allowed", value=True)
        
        col5, col6 = st.columns(2)
        
        with col5:
            st.subheader("Hierarchy")
            business_area_group = st.text_input("Business Area Group")
            hierarchy_level = st.number_input("Hierarchy Level", min_value=1, max_value=10, value=1)
        
        with col6:
            st.subheader("Validity")
            valid_from = st.date_input("Valid From", value=date.today())
            valid_to = st.date_input("Valid To", value=date(2099, 12, 31))
            is_active = st.checkbox("Active", value=True)
        
        submitted = st.form_submit_button("Create Business Area", type="primary")
        
        if submitted:
            if not all([business_area_id, business_area_name, short_name, company_code_id]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # Insert new business area
                        conn.execute(text("""
                            INSERT INTO business_areas (
                                business_area_id, business_area_name, short_name, description,
                                company_code_id, controlling_area, budget_responsible,
                                parent_business_area, business_area_group, hierarchy_level,
                                segment_for_reporting, consolidation_business_area,
                                currency, balance_sheet_preparation, profit_loss_preparation,
                                statistical_postings_allowed, consolidation_relevant,
                                elimination_business_area, valid_from, valid_to, is_active, created_by
                            ) VALUES (
                                :ba_id, :ba_name, :short_name, :description,
                                :company, :controlling, :budget_responsible,
                                :parent, :ba_group, :hierarchy_level,
                                :segment, :consolidation_ba,
                                :currency, :balance_sheet, :profit_loss,
                                :statistical, :consolidation_relevant,
                                :elimination, :valid_from, :valid_to, :is_active, :created_by
                            )
                        """), {
                            'ba_id': business_area_id,
                            'ba_name': business_area_name,
                            'short_name': short_name,
                            'description': description,
                            'company': company_code_id,
                            'controlling': controlling_area,
                            'budget_responsible': budget_responsible,
                            'parent': parent_business_area,
                            'ba_group': business_area_group,
                            'hierarchy_level': hierarchy_level,
                            'segment': segment_for_reporting,
                            'consolidation_ba': consolidation_business_area,
                            'currency': currency,
                            'balance_sheet': balance_sheet_preparation,
                            'profit_loss': profit_loss_preparation,
                            'statistical': statistical_postings_allowed,
                            'consolidation_relevant': consolidation_relevant,
                            'elimination': elimination_business_area,
                            'valid_from': valid_from,
                            'valid_to': valid_to,
                            'is_active': is_active,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success(f"✅ Business Area {business_area_id} created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Business Area ID {business_area_id} already exists!")
                    else:
                        st.error(f"❌ Error creating business area: {e}")

def show_manage_assignments():
    """Manage business area assignments."""
    st.header("🔗 Manage Business Area Assignments")
    
    # Load existing assignments
    try:
        with engine.connect() as conn:
            assignments = pd.read_sql(text("""
                SELECT 
                    baa.assignment_id,
                    baa.business_area_id,
                    ba.business_area_name,
                    baa.object_type,
                    baa.object_id,
                    baa.assignment_type,
                    baa.assignment_percentage,
                    baa.valid_from,
                    baa.valid_to,
                    baa.is_active
                FROM business_area_assignments baa
                JOIN business_areas ba ON baa.business_area_id = ba.business_area_id
                WHERE baa.is_active = TRUE
                ORDER BY baa.business_area_id, baa.object_type, baa.object_id
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading assignments: {e}")
        return
    
    # Assignment creation form
    st.subheader("➕ Create New Assignment")
    
    with st.form("create_assignment"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Get business areas for selection
            try:
                with engine.connect() as conn:
                    bas = pd.read_sql(text("""
                        SELECT business_area_id, business_area_name 
                        FROM business_areas 
                        WHERE is_active = TRUE
                        ORDER BY business_area_id
                    """), conn)
                
                ba_options = [f"{row['business_area_id']} - {row['business_area_name']}" 
                             for _, row in bas.iterrows()]
                selected_ba = st.selectbox("Business Area*", ba_options)
                business_area_id = selected_ba.split(" - ")[0] if selected_ba else None
                
            except Exception as e:
                st.error(f"Error loading business areas: {e}")
                business_area_id = None
        
        with col2:
            object_type = st.selectbox(
                "Object Type*",
                ["GLACCOUNT", "PROFITCENTER", "CUSTOMER", "VENDOR", "COSTCENTER"]
            )
            object_id = st.text_input("Object ID*", help="Enter the ID of the object to assign")
        
        with col3:
            assignment_type = st.selectbox("Assignment Type", ["MANUAL", "AUTO", "DERIVED"])
            assignment_percentage = st.number_input(
                "Assignment %", 
                min_value=0.01, max_value=100.0, value=100.0, step=0.01
            )
        
        submitted_assignment = st.form_submit_button("Create Assignment", type="primary")
        
        if submitted_assignment:
            if not all([business_area_id, object_type, object_id]):
                st.error("Please fill in all required fields")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO business_area_assignments (
                                business_area_id, object_type, object_id,
                                assignment_type, assignment_percentage, created_by
                            ) VALUES (
                                :ba_id, :obj_type, :obj_id, :assign_type, :percentage, :created_by
                            )
                        """), {
                            'ba_id': business_area_id,
                            'obj_type': object_type,
                            'obj_id': object_id,
                            'assign_type': assignment_type,
                            'percentage': assignment_percentage,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success("✅ Assignment created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error("❌ Assignment already exists for this object!")
                    else:
                        st.error(f"❌ Error creating assignment: {e}")
    
    # Display existing assignments
    if not assignments.empty:
        st.subheader("📋 Existing Assignments")
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            ba_filter = st.selectbox(
                "Filter by Business Area",
                ["All"] + list(assignments['business_area_id'].unique())
            )
        
        with col2:
            type_filter = st.selectbox(
                "Filter by Object Type",
                ["All"] + list(assignments['object_type'].unique())
            )
        
        with col3:
            assign_type_filter = st.selectbox(
                "Filter by Assignment Type",
                ["All"] + list(assignments['assignment_type'].unique())
            )
        
        # Apply filters
        filtered_assignments = assignments.copy()
        
        if ba_filter != "All":
            filtered_assignments = filtered_assignments[
                filtered_assignments['business_area_id'] == ba_filter
            ]
        
        if type_filter != "All":
            filtered_assignments = filtered_assignments[
                filtered_assignments['object_type'] == type_filter
            ]
        
        if assign_type_filter != "All":
            filtered_assignments = filtered_assignments[
                filtered_assignments['assignment_type'] == assign_type_filter
            ]
        
        # Display assignments table
        st.dataframe(
            filtered_assignments[[
                'business_area_id', 'business_area_name', 'object_type', 
                'object_id', 'assignment_type', 'assignment_percentage', 'valid_from', 'valid_to'
            ]],
            use_container_width=True,
            column_config={
                'business_area_id': 'Business Area ID',
                'business_area_name': 'Business Area Name',
                'object_type': 'Object Type',
                'object_id': 'Object ID',
                'assignment_type': 'Assignment Type',
                'assignment_percentage': st.column_config.NumberColumn('Assignment %', format="%.2f%%"),
                'valid_from': st.column_config.DateColumn('Valid From'),
                'valid_to': st.column_config.DateColumn('Valid To')
            }
        )
    else:
        st.info("No assignments configured yet. Create your first assignment above.")

def show_hierarchy_view():
    """Display business area hierarchy."""
    st.header("📈 Business Area Hierarchy")
    
    try:
        with engine.connect() as conn:
            hierarchy = pd.read_sql(text("""
                SELECT * FROM v_business_area_hierarchy
                ORDER BY hierarchy_path
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading hierarchy: {e}")
        return
    
    if hierarchy.empty:
        st.info("No business area hierarchy available.")
        return
    
    # Display hierarchy
    st.subheader("🌳 Hierarchical Structure")
    
    for _, row in hierarchy.iterrows():
        indent = "　" * (row['hierarchy_level'] - 1)  # Japanese space for indentation
        if row['hierarchy_level'] == 1:
            st.markdown(f"**🏢 {indent}{row['business_area_id']} - {row['business_area_name']}**")
        else:
            st.markdown(f"{indent}└─ {row['business_area_id']} - {row['business_area_name']}")
    
    # Hierarchy statistics
    st.subheader("📊 Hierarchy Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_level = hierarchy['hierarchy_level'].max()
        st.metric("Maximum Hierarchy Level", max_level)
    
    with col2:
        root_count = len(hierarchy[hierarchy['hierarchy_level'] == 1])
        st.metric("Root Business Areas", root_count)
    
    with col3:
        avg_level = hierarchy['hierarchy_level'].mean()
        st.metric("Average Hierarchy Level", f"{avg_level:.1f}")

def show_derivation_rules():
    """Configure business area derivation rules."""
    st.header("⚙️ Business Area Derivation Rules")
    
    st.info("Derivation rules automatically assign business areas based on source field values.")
    
    # Load existing derivation rules
    try:
        with engine.connect() as conn:
            derivation_rules = pd.read_sql(text("""
                SELECT 
                    badr.rule_id,
                    badr.rule_name,
                    badr.rule_description,
                    badr.source_field,
                    badr.condition_operator,
                    badr.condition_value,
                    badr.target_business_area,
                    ba.business_area_name,
                    badr.percentage,
                    badr.priority,
                    badr.is_active
                FROM business_area_derivation_rules badr
                JOIN business_areas ba ON badr.target_business_area = ba.business_area_id
                WHERE badr.is_active = TRUE
                ORDER BY badr.priority, badr.rule_name
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading derivation rules: {e}")
        return
    
    # Derivation rule creation form
    st.subheader("➕ Create New Derivation Rule")
    
    with st.form("create_derivation_rule"):
        col1, col2 = st.columns(2)
        
        with col1:
            rule_name = st.text_input("Rule Name*", max_chars=100)
            rule_description = st.text_area("Rule Description")
            priority = st.number_input("Priority", min_value=1, max_value=999, value=100)
            
            source_field = st.selectbox(
                "Source Field*",
                ["PROFIT_CENTER", "COST_CENTER", "GL_ACCOUNT", "CUSTOMER", "VENDOR", "EMPLOYEE"]
            )
        
        with col2:
            condition_operator = st.selectbox(
                "Condition Operator",
                ["=", "IN", "LIKE", "BETWEEN"]
            )
            condition_value = st.text_input(
                "Condition Value*",
                help="Use % for LIKE operations, comma-separated for IN"
            )
            
            # Get business areas for target selection
            try:
                with engine.connect() as conn:
                    target_bas = pd.read_sql(text("""
                        SELECT business_area_id, business_area_name 
                        FROM business_areas 
                        WHERE is_active = TRUE
                        ORDER BY business_area_id
                    """), conn)
                
                target_options = [f"{row['business_area_id']} - {row['business_area_name']}" 
                                 for _, row in target_bas.iterrows()]
                selected_target = st.selectbox("Target Business Area*", target_options)
                target_business_area = selected_target.split(" - ")[0] if selected_target else None
                
            except Exception as e:
                target_business_area = st.text_input("Target Business Area*")
            
            percentage = st.number_input("Percentage", min_value=0.01, max_value=100.0, value=100.0)
        
        submitted_rule = st.form_submit_button("Create Derivation Rule", type="primary")
        
        if submitted_rule:
            if not all([rule_name, source_field, condition_value, target_business_area]):
                st.error("Please fill in all required fields")
            else:
                try:
                    with engine.connect() as conn:
                        conn.execute(text("""
                            INSERT INTO business_area_derivation_rules (
                                rule_name, rule_description, source_field, condition_operator,
                                condition_value, target_business_area, percentage, priority, created_by
                            ) VALUES (
                                :rule_name, :rule_desc, :source_field, :condition_op,
                                :condition_val, :target_ba, :percentage, :priority, :created_by
                            )
                        """), {
                            'rule_name': rule_name,
                            'rule_desc': rule_description,
                            'source_field': source_field,
                            'condition_op': condition_operator,
                            'condition_val': condition_value,
                            'target_ba': target_business_area,
                            'percentage': percentage,
                            'priority': priority,
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
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            source_filter = st.selectbox(
                "Filter by Source Field",
                ["All"] + list(derivation_rules['source_field'].unique())
            )
        
        with col2:
            target_filter = st.selectbox(
                "Filter by Target Business Area",
                ["All"] + list(derivation_rules['target_business_area'].unique())
            )
        
        with col3:
            active_filter = st.selectbox(
                "Filter by Status",
                ["All", "Active", "Inactive"]
            )
        
        # Apply filters
        filtered_rules = derivation_rules.copy()
        
        if source_filter != "All":
            filtered_rules = filtered_rules[filtered_rules['source_field'] == source_filter]
        
        if target_filter != "All":
            filtered_rules = filtered_rules[filtered_rules['target_business_area'] == target_filter]
        
        if active_filter == "Active":
            filtered_rules = filtered_rules[filtered_rules['is_active'] == True]
        elif active_filter == "Inactive":
            filtered_rules = filtered_rules[filtered_rules['is_active'] == False]
        
        # Display derivation rules table
        st.dataframe(
            filtered_rules[[
                'rule_name', 'source_field', 'condition_operator', 'condition_value',
                'target_business_area', 'business_area_name', 'percentage', 'priority'
            ]],
            use_container_width=True,
            column_config={
                'rule_name': 'Rule Name',
                'source_field': 'Source Field',
                'condition_operator': 'Operator',
                'condition_value': 'Condition',
                'target_business_area': 'Target BA',
                'business_area_name': 'Business Area Name',
                'percentage': st.column_config.NumberColumn('Percentage', format="%.2f%%"),
                'priority': st.column_config.NumberColumn('Priority')
            }
        )
    else:
        st.info("No derivation rules configured yet. Create your first rule above.")

def show_segment_reports():
    """Display business area segment reporting analysis."""
    st.header("📋 Business Area Segment Reports")
    
    try:
        with engine.connect() as conn:
            # Segment assignment summary
            segment_summary = pd.read_sql(text("""
                SELECT 
                    ba.business_area_id,
                    ba.business_area_name,
                    ba.consolidation_relevant,
                    COUNT(baa.assignment_id) as total_assignments,
                    COUNT(CASE WHEN baa.object_type = 'GLACCOUNT' THEN 1 END) as gl_assignments,
                    COUNT(CASE WHEN baa.object_type = 'PROFITCENTER' THEN 1 END) as pc_assignments,
                    COUNT(badr.rule_id) as derivation_rules
                FROM business_areas ba
                LEFT JOIN business_area_assignments baa ON ba.business_area_id = baa.business_area_id
                    AND baa.is_active = TRUE
                LEFT JOIN business_area_derivation_rules badr ON ba.business_area_id = badr.target_business_area
                    AND badr.is_active = TRUE
                WHERE ba.is_active = TRUE
                GROUP BY ba.business_area_id, ba.business_area_name, ba.consolidation_relevant
                ORDER BY total_assignments DESC
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading segment data: {e}")
        return
    
    if segment_summary.empty:
        st.info("No business area segment data available.")
        return
    
    # Segment overview metrics
    st.subheader("📊 Segment Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_segments = len(segment_summary)
        st.metric("Total Segments", total_segments)
    
    with col2:
        consolidation_segments = len(segment_summary[segment_summary['consolidation_relevant'] == True])
        st.metric("Consolidation Segments", consolidation_segments)
    
    with col3:
        total_assignments = segment_summary['total_assignments'].sum()
        st.metric("Total Assignments", int(total_assignments))
    
    with col4:
        total_rules = segment_summary['derivation_rules'].sum()
        st.metric("Total Derivation Rules", int(total_rules))
    
    # Segment assignment analysis
    st.subheader("📈 Segment Assignment Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Assignment distribution by business area
        fig1 = go.Figure()
        
        fig1.add_trace(go.Bar(
            name='GL Accounts',
            x=segment_summary['business_area_id'],
            y=segment_summary['gl_assignments'],
            marker_color='lightblue'
        ))
        
        fig1.add_trace(go.Bar(
            name='Profit Centers',
            x=segment_summary['business_area_id'],
            y=segment_summary['pc_assignments'],
            marker_color='lightgreen'
        ))
        
        fig1.update_layout(
            title='Assignment Distribution by Business Area',
            xaxis_title='Business Area',
            yaxis_title='Number of Assignments',
            barmode='stack',
            height=400
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Consolidation relevance pie chart
        consolidation_dist = segment_summary['consolidation_relevant'].value_counts()
        fig2 = px.pie(
            values=consolidation_dist.values,
            names=['Not Relevant' if not x else 'Consolidation Relevant' for x in consolidation_dist.index],
            title='Consolidation Relevance Distribution',
            color_discrete_map={
                'Consolidation Relevant': '#2ca02c',
                'Not Relevant': '#ff7f0e'
            }
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Detailed segment table
    st.subheader("📋 Detailed Segment Summary")
    
    st.dataframe(
        segment_summary,
        use_container_width=True,
        column_config={
            'business_area_id': 'Business Area ID',
            'business_area_name': 'Business Area Name',
            'consolidation_relevant': st.column_config.CheckboxColumn('Consolidation'),
            'total_assignments': st.column_config.NumberColumn('Total Assignments'),
            'gl_assignments': st.column_config.NumberColumn('GL Accounts'),
            'pc_assignments': st.column_config.NumberColumn('Profit Centers'),
            'derivation_rules': st.column_config.NumberColumn('Derivation Rules')
        }
    )

def show_edit_business_areas():
    """Edit existing business areas."""
    st.header("✏️ Edit Business Areas")
    
    st.info("Select a business area below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            business_areas = pd.read_sql(text("""
                SELECT * FROM business_areas 
                WHERE is_active = TRUE
                ORDER BY business_area_id
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading business areas: {e}")
        return
    
    if business_areas.empty:
        st.warning("No business areas available for editing.")
        return
    
    # Business area selection
    selected_area = st.selectbox(
        "Select Business Area to Edit",
        options=business_areas['business_area_id'].tolist(),
        format_func=lambda x: f"{x} - {business_areas[business_areas['business_area_id']==x]['business_area_name'].iloc[0]}"
    )
    
    if selected_area:
        area_data = business_areas[business_areas['business_area_id'] == selected_area].iloc[0]
        
        st.subheader(f"Editing Business Area: {selected_area}")
        
        # Show current configuration in an expandable section
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Name:** {area_data['business_area_name']}")
                st.write(f"**Short Name:** {area_data['short_name']}")
                st.write(f"**Description:** {area_data['description']}")
                st.write(f"**Company Code:** {area_data['company_code_id']}")
                st.write(f"**Budget Responsible:** {area_data['budget_responsible']}")
            
            with col2:
                st.write(f"**Consolidation Relevant:** {'Yes' if area_data['consolidation_relevant'] else 'No'}")
                st.write(f"**Balance Sheet Prep:** {'Yes' if area_data['balance_sheet_preparation'] else 'No'}")
                st.write(f"**P&L Preparation:** {'Yes' if area_data['profit_loss_preparation'] else 'No'}")
                st.write(f"**Currency:** {area_data['currency']}")
                st.write(f"**Active:** {'Yes' if area_data['is_active'] else 'No'}")
        
        st.write("**Edit functionality would be implemented here for updating business area configurations.**")

if __name__ == "__main__":
    main()