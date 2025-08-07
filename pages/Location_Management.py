"""
Location Management System

Complete location master data management for hierarchical organizational structure,
geographic reporting, and site management.

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
    page_title="Location Management",
    page_icon="🌍",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Location Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Location Management", "Master Data", "Locations")
    
    st.title("🌍 Location Management")
    st.markdown("**Manage hierarchical location structure for reporting and organizational management**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🗺️ Location Functions")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Location Overview",
                "➕ Create Location",
                "✏️ Edit Locations", 
                "🌳 Location Hierarchy",
                "📈 Location Analytics",
                "📋 Location Reports",
                "⚙️ Advanced Operations"
            ]
        )
    
    # Route to selected page
    if page == "📊 Location Overview":
        show_location_overview()
    elif page == "➕ Create Location":
        show_create_location()
    elif page == "✏️ Edit Locations":
        show_edit_locations()
    elif page == "🌳 Location Hierarchy":
        show_location_hierarchy()
    elif page == "📈 Location Analytics":
        show_location_analytics()
    elif page == "📋 Location Reports":
        show_location_reports()
    elif page == "⚙️ Advanced Operations":
        show_advanced_operations()

def show_location_overview():
    """Display location overview dashboard."""
    st.header("📊 Location Overview")
    
    # Load location data
    try:
        with engine.connect() as conn:
            # Get location summary
            locations = pd.read_sql(text("""
                SELECT 
                    rl.location_code,
                    rl.location_name,
                    rl.location_level,
                    rl.parent_location,
                    rl.country_code,
                    rl.location_type,
                    rl.business_area_id,
                    ba.business_area_name,
                    rl.is_manufacturing,
                    rl.is_sales,
                    rl.is_distribution,
                    rl.is_service,
                    rl.is_administrative,
                    rl.is_active,
                    rl.created_by,
                    rl.created_at
                FROM reporting_locations rl
                LEFT JOIN business_areas ba ON rl.business_area_id = ba.business_area_id
                ORDER BY rl.location_code
            """), conn)
            
            # Get location statistics by level
            level_stats = pd.read_sql(text("""
                SELECT 
                    location_level,
                    COUNT(*) as count,
                    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_count
                FROM reporting_locations
                GROUP BY location_level
                ORDER BY 
                    CASE location_level 
                        WHEN 'GLOBAL' THEN 1
                        WHEN 'REGION' THEN 2
                        WHEN 'COUNTRY' THEN 3
                        WHEN 'STATE' THEN 4
                        WHEN 'CITY' THEN 5
                        WHEN 'SITE' THEN 6
                        WHEN 'BUILDING' THEN 7
                        WHEN 'FLOOR' THEN 8
                        ELSE 9
                    END
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading location data: {e}")
        return
    
    if locations.empty:
        st.warning("No locations configured yet. Create your first location to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Locations", len(locations))
    
    with col2:
        active_locations = len(locations[locations['is_active'] == True])
        st.metric("Active Locations", active_locations)
    
    with col3:
        countries = locations['country_code'].nunique() if 'country_code' in locations.columns else 0
        st.metric("Countries", countries)
    
    with col4:
        manufacturing_sites = len(locations[locations['is_manufacturing'] == True])
        st.metric("Manufacturing Sites", manufacturing_sites)
    
    # Location level breakdown
    st.subheader("📈 Location Structure by Level")
    
    if not level_stats.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                level_stats,
                x='location_level',
                y='count',
                title='Locations by Organizational Level',
                color='count',
                color_continuous_scale='viridis',
                text='count'
            )
            fig1.update_traces(textposition='auto')
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Location type distribution
            type_dist = locations['location_type'].value_counts()
            fig2 = px.pie(
                values=type_dist.values,
                names=type_dist.index,
                title='Distribution by Location Type'
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # Location capabilities analysis
    st.subheader("🏭 Location Capabilities")
    
    capabilities = {
        'Manufacturing': locations['is_manufacturing'].sum(),
        'Sales': locations['is_sales'].sum(),
        'Distribution': locations['is_distribution'].sum(),
        'Service': locations['is_service'].sum(),
        'Administrative': locations['is_administrative'].sum()
    }
    
    cap_df = pd.DataFrame(list(capabilities.items()), columns=['Capability', 'Count'])
    
    fig3 = px.bar(
        cap_df,
        x='Capability',
        y='Count',
        title='Location Capabilities Distribution',
        color='Count',
        color_continuous_scale='blues'
    )
    st.plotly_chart(fig3, use_container_width=True)
    
    # Recent locations
    st.subheader("🆕 Recently Created Locations")
    
    recent_locations = locations.nlargest(10, 'created_at')
    st.dataframe(
        recent_locations[[
            'location_code', 'location_name', 'location_level', 
            'location_type', 'country_code', 'business_area_name',
            'created_by', 'created_at'
        ]],
        use_container_width=True,
        column_config={
            'location_code': 'Code',
            'location_name': 'Location Name',
            'location_level': 'Level',
            'location_type': 'Type',
            'country_code': 'Country',
            'business_area_name': 'Business Area',
            'created_by': 'Created By',
            'created_at': st.column_config.DatetimeColumn('Created At')
        }
    )

def show_create_location():
    """Create new location interface."""
    st.header("➕ Create New Location")
    
    with st.form("create_location"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            location_code = st.text_input(
                "Location Code*", 
                max_chars=6,
                help="6-digit unique location identifier"
            ).upper()
            
            location_name = st.text_input(
                "Location Name*",
                max_chars=100,
                help="Full name of the location"
            )
            
            # Load parent locations for dropdown
            try:
                with engine.connect() as conn:
                    parent_locations = pd.read_sql(text("""
                        SELECT location_code, location_name, location_level
                        FROM reporting_locations 
                        WHERE is_active = TRUE
                        ORDER BY location_code
                    """), conn)
                
                parent_options = ["None"] + [
                    f"{row['location_code']} - {row['location_name']} ({row['location_level']})"
                    for _, row in parent_locations.iterrows()
                ]
                
                parent_selection = st.selectbox("Parent Location", parent_options)
                parent_location = None if parent_selection == "None" else parent_selection.split(" - ")[0]
                
            except Exception as e:
                st.error(f"Error loading parent locations: {e}")
                parent_location = None
            
            location_level = st.selectbox(
                "Location Level*",
                ["GLOBAL", "REGION", "COUNTRY", "STATE", "CITY", "SITE", "BUILDING", "FLOOR"]
            )
            
            location_type = st.selectbox(
                "Location Type*",
                ["HEADQUARTERS", "OFFICE", "PLANT", "WAREHOUSE", "STORE", "DC", "BRANCH", "OTHER"]
            )
        
        with col2:
            st.subheader("Geographic Information")
            country_code = st.text_input("Country Code", max_chars=3, help="3-letter ISO country code")
            state_province = st.text_input("State/Province", max_chars=50)
            city = st.text_input("City", max_chars=50)
            address_line_1 = st.text_input("Address Line 1", max_chars=100)
            address_line_2 = st.text_input("Address Line 2", max_chars=100)
            postal_code = st.text_input("Postal Code", max_chars=20)
            
            col2a, col2b = st.columns(2)
            with col2a:
                latitude = st.number_input("Latitude", min_value=-90.0, max_value=90.0, format="%.6f")
            with col2b:
                longitude = st.number_input("Longitude", min_value=-180.0, max_value=180.0, format="%.6f")
        
        st.subheader("Business Attributes")
        col3, col4 = st.columns(2)
        
        with col3:
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
            
            is_consolidation_unit = st.checkbox("Consolidation Unit")
            consolidation_currency = st.text_input("Consolidation Currency", max_chars=3)
        
        with col4:
            st.markdown("**Operational Capabilities**")
            is_manufacturing = st.checkbox("Manufacturing")
            is_sales = st.checkbox("Sales")
            is_distribution = st.checkbox("Distribution")
            is_service = st.checkbox("Service")
            is_administrative = st.checkbox("Administrative")
        
        st.subheader("Contact Information")
        col5, col6 = st.columns(2)
        
        with col5:
            location_manager = st.text_input("Location Manager", max_chars=100)
            contact_phone = st.text_input("Contact Phone", max_chars=30)
        
        with col6:
            contact_email = st.text_input("Contact Email", max_chars=100)
            timezone = st.text_input("Timezone", max_chars=50, help="e.g., America/New_York")
        
        col7, col8 = st.columns(2)
        with col7:
            is_active = st.checkbox("Active", value=True)
        with col8:
            valid_from = st.date_input("Valid From", value=date.today())
        
        submitted = st.form_submit_button("Create Location", type="primary")
        
        if submitted:
            if not all([location_code, location_name, location_level, location_type]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # Insert new location
                        conn.execute(text("""
                            INSERT INTO reporting_locations (
                                location_code, location_name, location_level, parent_location,
                                country_code, state_province, city, address_line_1, address_line_2,
                                postal_code, latitude, longitude, timezone, business_area_id,
                                location_type, is_consolidation_unit, consolidation_currency,
                                is_manufacturing, is_sales, is_distribution, is_service, is_administrative,
                                location_manager, contact_phone, contact_email, is_active, valid_from,
                                created_by
                            ) VALUES (
                                :location_code, :location_name, :location_level, :parent_location,
                                :country_code, :state_province, :city, :address_line_1, :address_line_2,
                                :postal_code, :latitude, :longitude, :timezone, :business_area_id,
                                :location_type, :is_consolidation_unit, :consolidation_currency,
                                :is_manufacturing, :is_sales, :is_distribution, :is_service, :is_administrative,
                                :location_manager, :contact_phone, :contact_email, :is_active, :valid_from,
                                :created_by
                            )
                        """), {
                            'location_code': location_code,
                            'location_name': location_name,
                            'location_level': location_level,
                            'parent_location': parent_location,
                            'country_code': country_code or None,
                            'state_province': state_province or None,
                            'city': city or None,
                            'address_line_1': address_line_1 or None,
                            'address_line_2': address_line_2 or None,
                            'postal_code': postal_code or None,
                            'latitude': latitude if latitude != 0.0 else None,
                            'longitude': longitude if longitude != 0.0 else None,
                            'timezone': timezone or None,
                            'business_area_id': business_area_id,
                            'location_type': location_type,
                            'is_consolidation_unit': is_consolidation_unit,
                            'consolidation_currency': consolidation_currency or None,
                            'is_manufacturing': is_manufacturing,
                            'is_sales': is_sales,
                            'is_distribution': is_distribution,
                            'is_service': is_service,
                            'is_administrative': is_administrative,
                            'location_manager': location_manager or None,
                            'contact_phone': contact_phone or None,
                            'contact_email': contact_email or None,
                            'is_active': is_active,
                            'valid_from': valid_from,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success(f"✅ Location {location_code} created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Location code {location_code} already exists!")
                    else:
                        st.error(f"❌ Error creating location: {e}")

def show_location_hierarchy():
    """Display location hierarchy visualization."""
    st.header("🌳 Location Hierarchy")
    
    try:
        with engine.connect() as conn:
            # Get hierarchy data
            hierarchy = pd.read_sql(text("""
                SELECT 
                    location_code,
                    location_name,
                    location_level,
                    parent_location,
                    full_path,
                    level
                FROM v_location_hierarchy
                ORDER BY path
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading hierarchy: {e}")
        return
    
    if hierarchy.empty:
        st.info("No location hierarchy available.")
        return
    
    # Display hierarchy as expandable tree
    st.subheader("📋 Hierarchical Location Structure")
    
    # Group by level for display
    max_level = hierarchy['level'].max()
    
    for current_level in range(max_level + 1):
        level_locations = hierarchy[hierarchy['level'] == current_level]
        
        if not level_locations.empty:
            level_name = level_locations.iloc[0]['location_level']
            st.markdown(f"**Level {current_level}: {level_name}**")
            
            for _, location in level_locations.iterrows():
                indent = "　" * current_level  # Japanese full-width space for indentation
                st.write(f"{indent}🏢 {location['location_code']} - {location['location_name']}")
    
    # Hierarchy statistics
    st.subheader("📊 Hierarchy Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        level_counts = hierarchy['location_level'].value_counts()
        fig = px.bar(
            x=level_counts.index,
            y=level_counts.values,
            title='Locations by Level',
            labels={'x': 'Location Level', 'y': 'Count'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Show deepest paths
        deepest = hierarchy.nlargest(5, 'level')[['location_code', 'location_name', 'level', 'full_path']]
        st.markdown("**Deepest Location Paths:**")
        for _, row in deepest.iterrows():
            st.write(f"**Level {row['level']}:** {row['full_path']}")

def show_location_analytics():
    """Location analytics and insights."""
    st.header("📈 Location Analytics")
    
    try:
        with engine.connect() as conn:
            # Geographic distribution
            geo_data = pd.read_sql(text("""
                SELECT 
                    country_code,
                    COUNT(*) as location_count,
                    COUNT(CASE WHEN is_manufacturing = TRUE THEN 1 END) as manufacturing_count,
                    COUNT(CASE WHEN is_sales = TRUE THEN 1 END) as sales_count,
                    COUNT(CASE WHEN is_distribution = TRUE THEN 1 END) as distribution_count
                FROM reporting_locations
                WHERE country_code IS NOT NULL
                GROUP BY country_code
                ORDER BY location_count DESC
            """), conn)
            
            # Business area distribution
            ba_data = pd.read_sql(text("""
                SELECT 
                    rl.business_area_id,
                    ba.business_area_name,
                    COUNT(*) as location_count,
                    COUNT(CASE WHEN rl.is_active = TRUE THEN 1 END) as active_count
                FROM reporting_locations rl
                LEFT JOIN business_areas ba ON rl.business_area_id = ba.business_area_id
                WHERE rl.business_area_id IS NOT NULL
                GROUP BY rl.business_area_id, ba.business_area_name
                ORDER BY location_count DESC
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading analytics data: {e}")
        return
    
    # Geographic analysis
    if not geo_data.empty:
        st.subheader("🌍 Geographic Distribution")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                geo_data.head(10),
                x='country_code',
                y='location_count',
                title='Locations by Country',
                text='location_count'
            )
            fig1.update_traces(textposition='auto')
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Capability heatmap by country
            capability_cols = ['manufacturing_count', 'sales_count', 'distribution_count']
            heatmap_data = geo_data[['country_code'] + capability_cols].set_index('country_code')
            
            if not heatmap_data.empty:
                fig2 = px.imshow(
                    heatmap_data.T,
                    title='Capabilities by Country',
                    aspect="auto",
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig2, use_container_width=True)
    
    # Business area analysis
    if not ba_data.empty:
        st.subheader("🏢 Business Area Distribution")
        
        fig3 = px.pie(
            ba_data,
            values='location_count',
            names='business_area_name',
            title='Location Distribution by Business Area'
        )
        st.plotly_chart(fig3, use_container_width=True)
        
        # Business area table
        st.dataframe(
            ba_data,
            use_container_width=True,
            column_config={
                'business_area_id': 'BA Code',
                'business_area_name': 'Business Area',
                'location_count': st.column_config.NumberColumn('Total Locations'),
                'active_count': st.column_config.NumberColumn('Active Locations')
            }
        )

def show_location_reports():
    """Location reporting interface."""
    st.header("📋 Location Reports")
    
    # Report selection
    report_type = st.selectbox(
        "Select Report Type",
        [
            "📊 Location Summary Report",
            "🗺️ Geographic Distribution Report", 
            "🏭 Capability Analysis Report",
            "📈 Location Hierarchy Report"
        ]
    )
    
    try:
        with engine.connect() as conn:
            if report_type == "📊 Location Summary Report":
                report_data = pd.read_sql(text("""
                    SELECT 
                        rl.location_code,
                        rl.location_name,
                        rl.location_level,
                        rl.location_type,
                        rl.country_code,
                        rl.state_province,
                        rl.city,
                        ba.business_area_name,
                        rl.is_manufacturing,
                        rl.is_sales,
                        rl.is_distribution,
                        rl.is_service,
                        rl.is_administrative,
                        rl.location_manager,
                        rl.is_active,
                        rl.created_at
                    FROM reporting_locations rl
                    LEFT JOIN business_areas ba ON rl.business_area_id = ba.business_area_id
                    ORDER BY rl.location_code
                """), conn)
                
                st.subheader("📊 Complete Location Summary")
                st.dataframe(report_data, use_container_width=True)
                
                # Download option
                csv = report_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"location_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            elif report_type == "🗺️ Geographic Distribution Report":
                geo_report = pd.read_sql(text("""
                    SELECT 
                        COALESCE(country_code, 'Unknown') as country,
                        COUNT(*) as total_locations,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_locations,
                        COUNT(CASE WHEN is_manufacturing = TRUE THEN 1 END) as manufacturing_sites,
                        COUNT(CASE WHEN is_sales = TRUE THEN 1 END) as sales_locations,
                        COUNT(CASE WHEN is_distribution = TRUE THEN 1 END) as distribution_centers,
                        STRING_AGG(DISTINCT location_type, ', ') as location_types
                    FROM reporting_locations
                    GROUP BY country_code
                    ORDER BY total_locations DESC
                """), conn)
                
                st.subheader("🗺️ Geographic Distribution Analysis")
                st.dataframe(geo_report, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error generating report: {e}")

def show_advanced_operations():
    """Advanced location operations."""
    st.header("⚙️ Advanced Location Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔧 Bulk Operations")
        
        st.markdown("**Activate/Deactivate Locations**")
        operation = st.selectbox("Operation", ["Activate", "Deactivate"])
        location_type_filter = st.selectbox(
            "Filter by Location Type",
            ["All", "HEADQUARTERS", "OFFICE", "PLANT", "WAREHOUSE", "STORE", "DC", "BRANCH", "OTHER"]
        )
        
        if st.button(f"{operation} Locations"):
            try:
                with engine.connect() as conn:
                    where_clause = ""
                    params = {'is_active': operation == "Activate", 'user': user.username}
                    
                    if location_type_filter != "All":
                        where_clause = "WHERE location_type = :location_type"
                        params['location_type'] = location_type_filter
                    
                    result = conn.execute(text(f"""
                        UPDATE reporting_locations 
                        SET is_active = :is_active,
                            modified_by = :user,
                            modified_at = CURRENT_TIMESTAMP
                        {where_clause}
                    """), params)
                    
                    affected = result.rowcount
                    conn.commit()
                    
                st.success(f"✅ {operation}d {affected} locations")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error during bulk operation: {e}")
    
    with col2:
        st.subheader("📊 Data Validation")
        
        if st.button("Validate Location Data"):
            try:
                with engine.connect() as conn:
                    # Check for orphaned locations
                    orphans = pd.read_sql(text("""
                        SELECT location_code, location_name, parent_location
                        FROM reporting_locations
                        WHERE parent_location IS NOT NULL 
                        AND parent_location NOT IN (
                            SELECT location_code FROM reporting_locations
                        )
                    """), conn)
                    
                    # Check for circular references (basic)
                    circular = pd.read_sql(text("""
                        SELECT location_code, location_name
                        FROM reporting_locations
                        WHERE location_code = parent_location
                    """), conn)
                    
                if not orphans.empty:
                    st.error("❌ Found orphaned locations:")
                    st.dataframe(orphans)
                else:
                    st.success("✅ No orphaned locations found")
                
                if not circular.empty:
                    st.error("❌ Found circular references:")
                    st.dataframe(circular)
                else:
                    st.success("✅ No circular references found")
                    
            except Exception as e:
                st.error(f"❌ Validation error: {e}")

def show_edit_locations():
    """Edit existing locations."""
    st.header("✏️ Edit Locations")
    
    st.info("Select a location below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            locations = pd.read_sql(text("""
                SELECT location_code, location_name, location_level, location_type, is_active
                FROM reporting_locations 
                ORDER BY location_code
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading locations: {e}")
        return
    
    if locations.empty:
        st.warning("No locations available for editing.")
        return
    
    # Location selection
    selected_location = st.selectbox(
        "Select Location to Edit",
        options=locations['location_code'].tolist(),
        format_func=lambda x: f"{x} - {locations[locations['location_code']==x]['location_name'].iloc[0]} ({locations[locations['location_code']==x]['location_level'].iloc[0]})"
    )
    
    if selected_location:
        # Show current configuration
        location_data = locations[locations['location_code'] == selected_location].iloc[0]
        
        st.subheader(f"Editing Location: {selected_location}")
        
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Location Code:** {location_data['location_code']}")
                st.write(f"**Location Name:** {location_data['location_name']}")
                st.write(f"**Level:** {location_data['location_level']}")
            
            with col2:
                st.write(f"**Type:** {location_data['location_type']}")
                st.write(f"**Active:** {'Yes' if location_data['is_active'] else 'No'}")
        
        st.write("**Full edit functionality would be implemented here for updating location configurations.**")

if __name__ == "__main__":
    main()