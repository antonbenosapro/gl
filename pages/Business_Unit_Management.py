"""
Business Unit Management System

Comprehensive unified business unit management combining cost centers and profit centers
with integrated Product Line and Location capabilities.

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
    page_title="Business Unit Management",
    page_icon="🏢",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Business Unit Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Business Unit Management", "Master Data", "Business Units")
    
    st.title("🏢 Business Unit Management")
    st.markdown("**Unified management of cost centers, profit centers, and organizational units**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🏗️ Business Unit Functions")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Business Unit Overview",
                "➕ Create Business Unit", 
                "✏️ Edit Business Units",
                "🌳 Organizational Hierarchy",
                "📈 Performance Analytics",
                "🔗 Integration Dashboard",
                "📋 Business Unit Reports",
                "⚙️ Advanced Operations"
            ]
        )
    
    # Route to selected page
    if page == "📊 Business Unit Overview":
        show_business_unit_overview()
    elif page == "➕ Create Business Unit":
        show_create_business_unit()
    elif page == "✏️ Edit Business Units":
        show_edit_business_units()
    elif page == "🌳 Organizational Hierarchy":
        show_organizational_hierarchy()
    elif page == "📈 Performance Analytics":
        show_performance_analytics()
    elif page == "🔗 Integration Dashboard":
        show_integration_dashboard()
    elif page == "📋 Business Unit Reports":
        show_business_unit_reports()
    elif page == "⚙️ Advanced Operations":
        show_advanced_operations()

def show_business_unit_overview():
    """Display business unit overview dashboard."""
    st.header("📊 Business Unit Overview")
    
    # Load business unit data
    try:
        with engine.connect() as conn:
            # Get business unit summary
            units = pd.read_sql(text("""
                SELECT 
                    bu.unit_id,
                    bu.unit_name,
                    bu.short_name,
                    bu.unit_type,
                    bu.responsibility_type,
                    bu.unit_category,
                    bu.business_area_id,
                    ba.business_area_name,
                    bu.product_line_id,
                    pl.product_line_name,
                    pl.industry_sector,
                    bu.location_code,
                    rl.location_name,
                    rl.country_code,
                    bu.generated_code_8digit as generated_code,
                    bu.person_responsible,
                    bu.department,
                    bu.is_active,
                    bu.status,
                    bu.created_by,
                    bu.created_at
                FROM business_units bu
                LEFT JOIN business_areas ba ON bu.business_area_id = ba.business_area_id
                LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
                LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
                ORDER BY bu.unit_id
            """), conn)
            
            # Get type distribution
            type_stats = pd.read_sql(text("""
                SELECT 
                    unit_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_count,
                    COUNT(CASE WHEN generated_code_8digit IS NOT NULL THEN 1 END) as coded_count
                FROM business_units
                GROUP BY unit_type
                ORDER BY count DESC
            """), conn)
            
    except Exception as e:
        st.error(f"Error loading business unit data: {e}")
        return
    
    if units.empty:
        st.warning("No business units found. Create your first business unit to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Business Units", len(units))
    
    with col2:
        active_units = len(units[units['is_active'] == True])
        st.metric("Active Units", active_units)
    
    with col3:
        coded_units = len(units[units['generated_code'].notna()])
        st.metric("Product-Location Units", coded_units)
    
    with col4:
        industries = units['industry_sector'].nunique()
        st.metric("Industry Sectors", industries if industries > 0 else 0)
    
    # Unit type analysis
    st.subheader("🏗️ Business Unit Type Distribution")
    
    if not type_stats.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                type_stats,
                x='unit_type',
                y='count',
                title='Business Units by Type',
                color='count',
                color_continuous_scale='viridis',
                text='count'
            )
            fig1.update_traces(textposition='auto')
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Show coded vs non-coded units
            coded_data = type_stats.copy()
            coded_data['non_coded'] = coded_data['count'] - coded_data['coded_count']
            
            fig2 = go.Figure(data=[
                go.Bar(name='Product-Location Coded', x=coded_data['unit_type'], y=coded_data['coded_count']),
                go.Bar(name='Standard Units', x=coded_data['unit_type'], y=coded_data['non_coded'])
            ])
            fig2.update_layout(
                barmode='stack',
                title='Coded vs Standard Units by Type'
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # Industry and location analysis
    if coded_units > 0:
        st.subheader("🌍 Multi-Dimensional Analysis")
        
        coded_units_df = units[units['generated_code'].notna()]
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'industry_sector' in coded_units_df.columns and not coded_units_df['industry_sector'].isna().all():
                industry_dist = coded_units_df['industry_sector'].value_counts()
                fig3 = px.pie(
                    values=industry_dist.values,
                    names=industry_dist.index,
                    title='Product-Location Units by Industry'
                )
                st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            if 'country_code' in coded_units_df.columns and not coded_units_df['country_code'].isna().all():
                country_dist = coded_units_df['country_code'].value_counts()
                fig4 = px.bar(
                    x=country_dist.index,
                    y=country_dist.values,
                    title='Product-Location Units by Country',
                    labels={'x': 'Country', 'y': 'Count'}
                )
                st.plotly_chart(fig4, use_container_width=True)
    
    # Recent business units
    st.subheader("🆕 Recently Created Business Units")
    
    recent_units = units.nlargest(10, 'created_at')
    
    # Display with enhanced information
    display_cols = [
        'unit_id', 'unit_name', 'unit_type', 'responsibility_type',
        'product_line_name', 'location_name', 'generated_code',
        'person_responsible', 'created_by', 'created_at'
    ]
    
    # Only show columns that exist and have data
    available_cols = [col for col in display_cols if col in recent_units.columns]
    
    st.dataframe(
        recent_units[available_cols],
        use_container_width=True,
        column_config={
            'unit_id': 'Unit ID',
            'unit_name': 'Business Unit Name', 
            'unit_type': 'Type',
            'responsibility_type': 'Responsibility',
            'product_line_name': 'Product Line',
            'location_name': 'Location',
            'generated_code': 'Generated Code',
            'person_responsible': 'Manager',
            'created_by': 'Created By',
            'created_at': st.column_config.DatetimeColumn('Created At')
        }
    )

def show_create_business_unit():
    """Create new business unit interface."""
    st.header("➕ Create New Business Unit")
    
    with st.form("create_business_unit"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            unit_id = st.text_input(
                "Unit ID*", 
                max_chars=20,
                help="Unique identifier (e.g., BU-SMART-NYC, BU-OFS-TEXAS)",
                placeholder="BU-EXAMPLE-001"
            ).upper()
            
            unit_name = st.text_input(
                "Business Unit Name*",
                max_chars=100,
                help="Full descriptive name",
                placeholder="Smartphones Development New York"
            )
            
            short_name = st.text_input(
                "Short Name*",
                max_chars=20,
                help="Abbreviated name for reports",
                placeholder="SMART-NYC"
            )
            
            description = st.text_area(
                "Description",
                help="Detailed description of the business unit"
            )
        
        with col2:
            st.subheader("Unit Classification")
            unit_type = st.selectbox(
                "Unit Type*",
                ["COST_CENTER", "PROFIT_CENTER", "BOTH"],
                help="Defines the responsibility scope"
            )
            
            unit_category = st.selectbox(
                "Unit Category",
                ["STANDARD", "OVERHEAD", "REVENUE", "INVESTMENT", "SERVICE", "AUXILIARY"]
            )
            
            responsibility_type = st.selectbox(
                "Responsibility Type",
                ["COST", "REVENUE", "PROFIT", "INVESTMENT"],
                help="Primary responsibility focus"
            )
        
        st.subheader("Product Line & Location Integration")
        col3, col4 = st.columns(2)
        
        with col3:
            # Load product lines
            try:
                with engine.connect() as conn:
                    product_lines = pd.read_sql(text("""
                        SELECT product_line_id, product_line_name, product_category, industry_sector
                        FROM product_lines 
                        WHERE is_active = TRUE
                        ORDER BY industry_sector, product_line_name
                    """), conn)
                
                if not product_lines.empty:
                    product_options = ["None"] + [
                        f"{row['product_line_id']} - {row['product_line_name']} ({row['industry_sector']})"
                        for _, row in product_lines.iterrows()
                    ]
                    
                    product_selection = st.selectbox("Product Line", product_options)
                    product_line_id = None if product_selection == "None" else product_selection.split(" - ")[0]
                else:
                    st.warning("No product lines available")
                    product_line_id = None
                    
            except Exception as e:
                st.error(f"Error loading product lines: {e}")
                product_line_id = None
        
        with col4:
            # Load locations
            try:
                with engine.connect() as conn:
                    locations = pd.read_sql(text("""
                        SELECT location_code, location_name, location_level, country_code
                        FROM reporting_locations 
                        WHERE is_active = TRUE
                        ORDER BY location_level, location_name
                    """), conn)
                
                if not locations.empty:
                    location_options = ["None"] + [
                        f"{row['location_code']} - {row['location_name']} ({row['location_level']})"
                        for _, row in locations.iterrows()
                    ]
                    
                    location_selection = st.selectbox("Location", location_options)
                    location_code = None if location_selection == "None" else location_selection.split(" - ")[0]
                else:
                    st.warning("No locations available")
                    location_code = None
                    
            except Exception as e:
                st.error(f"Error loading locations: {e}")
                location_code = None
        
        # Show generated code preview
        if product_line_id and location_code:
            generated_code = f"{product_line_id}{location_code}"
            st.success(f"🔗 Generated Code Preview: **{generated_code}**")
        
        st.subheader("Management & Organization")
        col5, col6 = st.columns(2)
        
        with col5:
            # Load business areas
            try:
                with engine.connect() as conn:
                    business_areas = pd.read_sql(text("""
                        SELECT business_area_id, business_area_name 
                        FROM business_areas 
                        ORDER BY business_area_id
                    """), conn)
                
                ba_options = [""] + [
                    f"{row['business_area_id']} - {row['business_area_name']}"
                    for _, row in business_areas.iterrows()
                ]
                
                ba_selection = st.selectbox("Business Area", ba_options)
                business_area_id = ba_selection.split(" - ")[0] if ba_selection else None
                
            except Exception as e:
                st.error(f"Error loading business areas: {e}")
                business_area_id = None
            
            person_responsible = st.text_input("Person Responsible", max_chars=100)
            person_responsible_email = st.text_input("Manager Email", max_chars=100)
        
        with col6:
            department = st.text_input("Department", max_chars=50)
            segment = st.text_input("Business Segment", max_chars=20)
            
            # Load existing units for parent selection
            try:
                with engine.connect() as conn:
                    parent_units = pd.read_sql(text("""
                        SELECT unit_id, unit_name, unit_type
                        FROM business_units 
                        WHERE is_active = TRUE
                        ORDER BY unit_name
                    """), conn)
                
                parent_options = ["None"] + [
                    f"{row['unit_id']} - {row['unit_name']} ({row['unit_type']})"
                    for _, row in parent_units.iterrows()
                ]
                
                parent_selection = st.selectbox("Parent Business Unit", parent_options)
                parent_unit_id = None if parent_selection == "None" else parent_selection.split(" - ")[0]
                
            except Exception as e:
                st.error(f"Error loading parent units: {e}")
                parent_unit_id = None
        
        st.subheader("Configuration & Status")
        col7, col8 = st.columns(2)
        
        with col7:
            planning_enabled = st.checkbox("Planning Enabled", value=True)
            margin_analysis_enabled = st.checkbox("Margin Analysis Enabled", 
                                                   value=(unit_type in ['PROFIT_CENTER', 'BOTH']))
            is_active = st.checkbox("Active", value=True)
        
        with col8:
            local_currency = st.selectbox("Local Currency", ["USD", "EUR", "GBP", "JPY", "CAD"])
            valid_from = st.date_input("Valid From", value=date.today())
        
        submitted = st.form_submit_button("Create Business Unit", type="primary")
        
        if submitted:
            if not all([unit_id, unit_name, short_name, unit_type]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # Insert new business unit
                        conn.execute(text("""
                            INSERT INTO business_units (
                                unit_id, unit_name, short_name, description,
                                unit_type, unit_category, responsibility_type,
                                company_code_id, business_area_id, parent_unit_id,
                                product_line_id, location_code,
                                person_responsible, person_responsible_email,
                                department, segment,
                                planning_enabled, margin_analysis_enabled,
                                local_currency, is_active, valid_from, created_by
                            ) VALUES (
                                :unit_id, :unit_name, :short_name, :description,
                                :unit_type, :unit_category, :responsibility_type,
                                'C001', :business_area_id, :parent_unit_id,
                                :product_line_id, :location_code,
                                :person_responsible, :person_responsible_email,
                                :department, :segment,
                                :planning_enabled, :margin_analysis_enabled,
                                :local_currency, :is_active, :valid_from, :created_by
                            )
                        """), {
                            'unit_id': unit_id,
                            'unit_name': unit_name,
                            'short_name': short_name,
                            'description': description or None,
                            'unit_type': unit_type,
                            'unit_category': unit_category,
                            'responsibility_type': responsibility_type,
                            'business_area_id': business_area_id,
                            'parent_unit_id': parent_unit_id,
                            'product_line_id': product_line_id,
                            'location_code': location_code,
                            'person_responsible': person_responsible or None,
                            'person_responsible_email': person_responsible_email or None,
                            'department': department or None,
                            'segment': segment or None,
                            'planning_enabled': planning_enabled,
                            'margin_analysis_enabled': margin_analysis_enabled,
                            'local_currency': local_currency,
                            'is_active': is_active,
                            'valid_from': valid_from,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    if product_line_id and location_code:
                        st.success(f"✅ Business Unit {unit_id} created successfully with generated code: **{product_line_id}{location_code}**")
                    else:
                        st.success(f"✅ Business Unit {unit_id} created successfully!")
                    
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Business Unit ID {unit_id} already exists!")
                    else:
                        st.error(f"❌ Error creating business unit: {e}")

def show_organizational_hierarchy():
    """Display organizational hierarchy visualization."""
    st.header("🌳 Organizational Hierarchy")
    
    try:
        with engine.connect() as conn:
            # Get hierarchy data
            hierarchy = pd.read_sql(text("""
                SELECT 
                    unit_id,
                    unit_name,
                    unit_type,
                    parent_unit_id,
                    full_path,
                    level
                FROM v_business_unit_hierarchy
                ORDER BY path
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading hierarchy: {e}")
        return
    
    if hierarchy.empty:
        st.info("No business unit hierarchy available.")
        return
    
    # Display hierarchy as expandable tree
    st.subheader("📋 Hierarchical Business Unit Structure")
    
    # Group by level for display
    max_level = hierarchy['level'].max()
    
    for current_level in range(max_level + 1):
        level_units = hierarchy[hierarchy['level'] == current_level]
        
        if not level_units.empty:
            st.markdown(f"**Level {current_level} Business Units**")
            
            for _, unit in level_units.iterrows():
                indent = "　" * current_level  # Japanese full-width space for indentation
                type_badge = f" [{unit['unit_type']}]"
                st.write(f"{indent}🏢 {unit['unit_id']} - {unit['unit_name']}{type_badge}")
    
    # Hierarchy statistics
    st.subheader("📊 Hierarchy Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        level_counts = hierarchy['level'].value_counts().sort_index()
        fig = px.bar(
            x=[f"Level {i}" for i in level_counts.index],
            y=level_counts.values,
            title='Business Units by Hierarchy Level',
            labels={'x': 'Hierarchy Level', 'y': 'Count'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Show business unit types distribution
        try:
            with engine.connect() as conn:
                type_data = pd.read_sql(text("""
                    SELECT unit_type, COUNT(*) as count
                    FROM business_units
                    WHERE is_active = TRUE
                    GROUP BY unit_type
                """), conn)
            
            if not type_data.empty:
                fig2 = px.pie(
                    type_data,
                    values='count',
                    names='unit_type',
                    title='Business Unit Types Distribution'
                )
                st.plotly_chart(fig2, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error loading type distribution: {e}")

def show_integration_dashboard():
    """Show integration status with Product Lines and Locations."""
    st.header("🔗 Integration Dashboard")
    
    st.subheader("🎯 Product Line & Location Integration Status")
    
    try:
        with engine.connect() as conn:
            # Get integration statistics
            integration_stats = pd.read_sql(text("""
                SELECT 
                    COUNT(*) as total_units,
                    COUNT(CASE WHEN product_line_id IS NOT NULL THEN 1 END) as product_linked,
                    COUNT(CASE WHEN location_code IS NOT NULL THEN 1 END) as location_linked,
                    COUNT(CASE WHEN generated_code_8digit IS NOT NULL THEN 1 END) as auto_coded,
                    COUNT(CASE WHEN unit_type = 'BOTH' THEN 1 END) as dual_purpose
                FROM business_units
                WHERE is_active = TRUE
            """), conn)
            
            # Show integration metrics
            if not integration_stats.empty:
                stats = integration_stats.iloc[0]
                
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("Total Units", int(stats['total_units']))
                
                with col2:
                    st.metric("Product-Linked", int(stats['product_linked']))
                
                with col3:
                    st.metric("Location-Linked", int(stats['location_linked']))
                
                with col4:
                    st.metric("Auto-Coded", int(stats['auto_coded']))
                
                with col5:
                    st.metric("Dual-Purpose", int(stats['dual_purpose']))
            
            # Show integrated units
            integrated_units = pd.read_sql(text("""
                SELECT 
                    bu.unit_id,
                    bu.unit_name,
                    bu.unit_type,
                    pl.product_line_name,
                    pl.industry_sector,
                    rl.location_name,
                    rl.country_code,
                    bu.generated_code_8digit as generated_code,
                    bu.person_responsible
                FROM business_units bu
                LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
                LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
                WHERE bu.generated_code_8digit IS NOT NULL
                ORDER BY bu.unit_id
            """), conn)
            
    except Exception as e:
        st.error(f"Error loading integration data: {e}")
        return
    
    if not integrated_units.empty:
        st.subheader("🌟 Fully Integrated Business Units")
        st.markdown("*Units with both Product Line and Location assignments*")
        
        st.dataframe(
            integrated_units,
            use_container_width=True,
            column_config={
                'unit_id': 'Unit ID',
                'unit_name': 'Business Unit Name',
                'unit_type': 'Type', 
                'product_line_name': 'Product Line',
                'industry_sector': 'Industry',
                'location_name': 'Location',
                'country_code': 'Country',
                'generated_code': 'Generated Code',
                'person_responsible': 'Manager'
            }
        )
        
        # Show integration visualization
        if len(integrated_units) > 0:
            st.subheader("📊 Integration Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Industry distribution of integrated units
                if 'industry_sector' in integrated_units.columns:
                    industry_counts = integrated_units['industry_sector'].value_counts()
                    fig1 = px.bar(
                        x=industry_counts.index,
                        y=industry_counts.values,
                        title='Integrated Units by Industry',
                        labels={'x': 'Industry', 'y': 'Count'}
                    )
                    st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Country distribution
                if 'country_code' in integrated_units.columns and not integrated_units['country_code'].isna().all():
                    country_counts = integrated_units['country_code'].value_counts()
                    fig2 = px.pie(
                        values=country_counts.values,
                        names=country_counts.index,
                        title='Integrated Units by Country'
                    )
                    st.plotly_chart(fig2, use_container_width=True)
    
    else:
        st.info("No fully integrated business units yet. Create units with both Product Line and Location assignments to see them here.")

def show_performance_analytics():
    """Performance analytics dashboard."""
    st.header("📈 Performance Analytics")
    st.markdown("*Business unit performance analysis and trends*")
    
    # This would integrate with GL transactions and other financial data
    st.info("📊 Performance analytics will be enhanced once GL transaction integration is complete.")
    
    # Show unit distribution analysis
    try:
        with engine.connect() as conn:
            analytics_data = pd.read_sql(text("""
                SELECT 
                    bu.unit_type,
                    bu.responsibility_type,
                    bu.unit_category,
                    pl.industry_sector,
                    rl.country_code,
                    COUNT(*) as unit_count,
                    COUNT(CASE WHEN bu.is_active = TRUE THEN 1 END) as active_count
                FROM business_units bu
                LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
                LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
                GROUP BY bu.unit_type, bu.responsibility_type, bu.unit_category, pl.industry_sector, rl.country_code
                HAVING COUNT(*) > 0
                ORDER BY unit_count DESC
            """), conn)
        
        if not analytics_data.empty:
            st.subheader("📊 Business Unit Distribution Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Unit type vs responsibility analysis
                type_resp = analytics_data.groupby(['unit_type', 'responsibility_type'])['unit_count'].sum().reset_index()
                fig1 = px.bar(
                    type_resp,
                    x='unit_type',
                    y='unit_count', 
                    color='responsibility_type',
                    title='Unit Types vs Responsibility Types',
                    barmode='stack'
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                # Category distribution
                cat_dist = analytics_data.groupby('unit_category')['unit_count'].sum().reset_index()
                fig2 = px.pie(
                    cat_dist,
                    values='unit_count',
                    names='unit_category',
                    title='Business Units by Category'
                )
                st.plotly_chart(fig2, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading analytics data: {e}")

def show_business_unit_reports():
    """Business unit reporting interface."""
    st.header("📋 Business Unit Reports")
    
    # Report selection
    report_type = st.selectbox(
        "Select Report Type",
        [
            "📊 Complete Business Unit Report",
            "🔗 Integration Status Report", 
            "🏗️ Organizational Structure Report",
            "📈 Performance Summary Report"
        ]
    )
    
    try:
        with engine.connect() as conn:
            if report_type == "📊 Complete Business Unit Report":
                report_data = pd.read_sql(text("""
                    SELECT 
                        bu.unit_id,
                        bu.unit_name,
                        bu.short_name,
                        bu.unit_type,
                        bu.responsibility_type,
                        bu.unit_category,
                        pl.product_line_name,
                        pl.industry_sector,
                        rl.location_name,
                        rl.country_code,
                        bu.generated_code_8digit as generated_code,
                        bu.person_responsible,
                        bu.department,
                        ba.business_area_name,
                        bu.is_active,
                        bu.status,
                        bu.created_at
                    FROM business_units bu
                    LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
                    LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
                    LEFT JOIN business_areas ba ON bu.business_area_id = ba.business_area_id
                    ORDER BY bu.unit_id
                """), conn)
                
                st.subheader("📊 Complete Business Unit Summary")
                st.dataframe(report_data, use_container_width=True)
                
                # Download option
                csv = report_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"business_units_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Error generating report: {e}")

def show_advanced_operations():
    """Advanced business unit operations."""
    st.header("⚙️ Advanced Business Unit Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔧 Bulk Operations")
        
        st.markdown("**Status Updates**")
        from_status = st.selectbox("From Status", 
                                 ["ACTIVE", "INACTIVE", "BLOCKED", "PLANNED"])
        to_status = st.selectbox("To Status",
                               ["ACTIVE", "INACTIVE", "BLOCKED", "PLANNED"])
        
        if st.button("Update Status"):
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        UPDATE business_units 
                        SET status = :to_status,
                            modified_by = :user,
                            modified_at = CURRENT_TIMESTAMP
                        WHERE status = :from_status
                        AND is_active = TRUE
                    """), {
                        'from_status': from_status,
                        'to_status': to_status,
                        'user': user.username
                    })
                    
                    affected = result.rowcount
                    conn.commit()
                    
                st.success(f"✅ Updated {affected} business units from {from_status} to {to_status}")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error during bulk operation: {e}")
    
    with col2:
        st.subheader("📊 Data Validation")
        
        if st.button("Validate Business Unit Data"):
            try:
                with engine.connect() as conn:
                    # Check for orphaned business units
                    orphans = pd.read_sql(text("""
                        SELECT unit_id, unit_name, parent_unit_id
                        FROM business_units
                        WHERE parent_unit_id IS NOT NULL 
                        AND parent_unit_id NOT IN (
                            SELECT unit_id FROM business_units
                        )
                    """), conn)
                    
                    # Check for missing business areas
                    missing_ba = pd.read_sql(text("""
                        SELECT unit_id, unit_name
                        FROM business_units
                        WHERE business_area_id IS NULL AND is_active = TRUE
                    """), conn)
                    
                if not orphans.empty:
                    st.error("❌ Found orphaned business units:")
                    st.dataframe(orphans)
                else:
                    st.success("✅ No orphaned business units found")
                
                if not missing_ba.empty:
                    st.warning("⚠️ Active business units without business area:")
                    st.dataframe(missing_ba)
                else:
                    st.success("✅ All active units have business areas assigned")
                    
            except Exception as e:
                st.error(f"❌ Validation error: {e}")

def show_edit_business_units():
    """Edit existing business units."""
    st.header("✏️ Edit Business Units")
    
    st.info("Select a business unit below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            units = pd.read_sql(text("""
                SELECT unit_id, unit_name, unit_type, responsibility_type, is_active
                FROM business_units 
                ORDER BY unit_id
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading business units: {e}")
        return
    
    if units.empty:
        st.warning("No business units available for editing.")
        return
    
    # Business unit selection
    selected_unit = st.selectbox(
        "Select Business Unit to Edit",
        options=units['unit_id'].tolist(),
        format_func=lambda x: f"{x} - {units[units['unit_id']==x]['unit_name'].iloc[0]} ({units[units['unit_id']==x]['unit_type'].iloc[0]})"
    )
    
    if selected_unit:
        # Show current configuration
        unit_data = units[units['unit_id'] == selected_unit].iloc[0]
        
        st.subheader(f"Editing Business Unit: {selected_unit}")
        
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Unit ID:** {unit_data['unit_id']}")
                st.write(f"**Unit Name:** {unit_data['unit_name']}")
                st.write(f"**Unit Type:** {unit_data['unit_type']}")
            
            with col2:
                st.write(f"**Responsibility:** {unit_data['responsibility_type']}")
                st.write(f"**Active:** {'Yes' if unit_data['is_active'] else 'No'}")
        
        st.write("**Full edit functionality would be implemented here for updating business unit configurations.**")

if __name__ == "__main__":
    main()