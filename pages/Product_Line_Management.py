"""
Product Line Management System

Complete product line master data management for industry-specific product portfolio,
lifecycle management, and profitability analysis.

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
    page_title="Product Line Management",
    page_icon="📦",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Product Line Management application."""
    # Show breadcrumb with user info
    show_breadcrumb("Product Line Management", "Master Data", "Products")
    
    st.title("📦 Product Line Management")
    st.markdown("**Manage product line portfolio for multi-industry business operations**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🛍️ Product Functions")
        
        page = st.selectbox(
            "Select Function",
            [
                "📊 Product Overview",
                "➕ Create Product Line",
                "✏️ Edit Product Lines",
                "🌳 Product Hierarchy",
                "📈 Lifecycle Analytics",
                "🎯 Industry Analysis",
                "📋 Product Reports",
                "⚙️ Advanced Operations"
            ]
        )
    
    # Route to selected page
    if page == "📊 Product Overview":
        show_product_overview()
    elif page == "➕ Create Product Line":
        show_create_product_line()
    elif page == "✏️ Edit Product Lines":
        show_edit_product_lines()
    elif page == "🌳 Product Hierarchy":
        show_product_hierarchy()
    elif page == "📈 Lifecycle Analytics":
        show_lifecycle_analytics()
    elif page == "🎯 Industry Analysis":
        show_industry_analysis()
    elif page == "📋 Product Reports":
        show_product_reports()
    elif page == "⚙️ Advanced Operations":
        show_advanced_operations()

def show_product_overview():
    """Display product line overview dashboard."""
    st.header("📊 Product Line Overview")
    
    # Load product line data
    try:
        with engine.connect() as conn:
            # Get product line summary
            products = pd.read_sql(text("""
                SELECT 
                    pl.product_line_id,
                    pl.product_line_name,
                    pl.short_name,
                    pl.product_category,
                    pl.product_family,
                    pl.lifecycle_stage,
                    pl.industry_sector,
                    pl.business_area_id,
                    ba.business_area_name,
                    pl.is_manufactured,
                    pl.is_purchased,
                    pl.is_service,
                    pl.is_digital,
                    pl.requires_serialization,
                    pl.requires_lot_tracking,
                    pl.is_active,
                    pl.created_by,
                    pl.created_at
                FROM product_lines pl
                LEFT JOIN business_areas ba ON pl.business_area_id = ba.business_area_id
                ORDER BY pl.product_line_id
            """), conn)
            
            # Get lifecycle distribution
            lifecycle_stats = pd.read_sql(text("""
                SELECT 
                    lifecycle_stage,
                    COUNT(*) as count,
                    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_count
                FROM product_lines
                WHERE lifecycle_stage IS NOT NULL
                GROUP BY lifecycle_stage
                ORDER BY 
                    CASE lifecycle_stage 
                        WHEN 'DEVELOPMENT' THEN 1
                        WHEN 'INTRODUCTION' THEN 2
                        WHEN 'GROWTH' THEN 3
                        WHEN 'MATURITY' THEN 4
                        WHEN 'DECLINE' THEN 5
                        WHEN 'END_OF_LIFE' THEN 6
                        ELSE 7
                    END
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading product data: {e}")
        return
    
    if products.empty:
        st.warning("No product lines configured yet. Create your first product line to get started.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Product Lines", len(products))
    
    with col2:
        active_products = len(products[products['is_active'] == True])
        st.metric("Active Product Lines", active_products)
    
    with col3:
        industries = products['industry_sector'].nunique()
        st.metric("Industry Sectors", industries)
    
    with col4:
        manufactured = len(products[products['is_manufactured'] == True])
        st.metric("Manufactured Products", manufactured)
    
    # Product lifecycle analysis
    st.subheader("🔄 Product Lifecycle Distribution")
    
    if not lifecycle_stats.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig1 = px.bar(
                lifecycle_stats,
                x='lifecycle_stage',
                y='count',
                title='Products by Lifecycle Stage',
                color='count',
                color_continuous_scale='viridis',
                text='count'
            )
            fig1.update_traces(textposition='auto')
            fig1.update_layout(showlegend=False)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Industry sector distribution
            industry_dist = products['industry_sector'].value_counts()
            fig2 = px.pie(
                values=industry_dist.values,
                names=industry_dist.index,
                title='Distribution by Industry Sector'
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # Product characteristics analysis
    st.subheader("🏭 Product Characteristics")
    
    characteristics = {
        'Manufactured': products['is_manufactured'].sum(),
        'Purchased': products['is_purchased'].sum(),
        'Service': products['is_service'].sum(),
        'Digital': products['is_digital'].sum(),
        'Requires Serialization': products['requires_serialization'].sum(),
        'Requires Lot Tracking': products['requires_lot_tracking'].sum()
    }
    
    char_df = pd.DataFrame(list(characteristics.items()), columns=['Characteristic', 'Count'])
    
    fig3 = px.bar(
        char_df,
        x='Characteristic',
        y='Count',
        title='Product Characteristics Distribution',
        color='Count',
        color_continuous_scale='blues'
    )
    fig3.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig3, use_container_width=True)
    
    # Recent product lines
    st.subheader("🆕 Recently Created Product Lines")
    
    recent_products = products.nlargest(10, 'created_at')
    st.dataframe(
        recent_products[[
            'product_line_id', 'product_line_name', 'product_category', 
            'lifecycle_stage', 'industry_sector', 'business_area_name',
            'created_by', 'created_at'
        ]],
        use_container_width=True,
        column_config={
            'product_line_id': 'Product ID',
            'product_line_name': 'Product Line Name',
            'product_category': 'Category',
            'lifecycle_stage': 'Lifecycle',
            'industry_sector': 'Industry',
            'business_area_name': 'Business Area',
            'created_by': 'Created By',
            'created_at': st.column_config.DatetimeColumn('Created At')
        }
    )

def show_create_product_line():
    """Create new product line interface."""
    st.header("➕ Create New Product Line")
    
    with st.form("create_product_line"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Basic Information")
            product_line_id = st.text_input(
                "Product Line ID*", 
                max_chars=4,
                help="4-digit unique product line identifier"
            ).upper()
            
            product_line_name = st.text_input(
                "Product Line Name*",
                max_chars=100,
                help="Full name of the product line"
            )
            
            short_name = st.text_input(
                "Short Name",
                max_chars=20,
                help="Abbreviated name for reports"
            )
            
            description = st.text_area(
                "Description",
                help="Detailed description of the product line"
            )
            
            # Load parent product lines for dropdown
            try:
                with engine.connect() as conn:
                    parent_products = pd.read_sql(text("""
                        SELECT product_line_id, product_line_name, product_category
                        FROM product_lines 
                        WHERE is_active = TRUE
                        ORDER BY product_line_id
                    """), conn)
                
                parent_options = ["None"] + [
                    f"{row['product_line_id']} - {row['product_line_name']} ({row['product_category']})"
                    for _, row in parent_products.iterrows()
                ]
                
                parent_selection = st.selectbox("Parent Product Line", parent_options)
                parent_product_line = None if parent_selection == "None" else parent_selection.split(" - ")[0]
                
            except Exception as e:
                st.error(f"Error loading parent product lines: {e}")
                parent_product_line = None
        
        with col2:
            st.subheader("Product Classification")
            product_category = st.text_input(
                "Product Category",
                max_chars=50,
                help="e.g., Electronics, Software, Healthcare"
            )
            
            product_family = st.text_input(
                "Product Family",
                max_chars=50,
                help="e.g., Smartphones, Enterprise, Pharmaceuticals"
            )
            
            product_group = st.text_input(
                "Product Group",
                max_chars=50,
                help="Specific grouping within family"
            )
            
            industry_sector = st.selectbox(
                "Industry Sector",
                ["", "TECHNOLOGY", "CPG", "PHARMA", "MANUFACTURING", "AUTOMOTIVE", 
                 "AEROSPACE", "SERVICES", "FINANCE", "RETAIL", "ENERGY", "OTHER"]
            )
            
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
        
        st.subheader("Business Attributes")
        col3, col4 = st.columns(2)
        
        with col3:
            product_manager = st.text_input("Product Manager", max_chars=100)
            product_manager_email = st.text_input("Product Manager Email", max_chars=100)
            
            default_profit_center = st.text_input(
                "Default Profit Center",
                max_chars=20,
                help="Default profit center for this product line"
            )
            
            revenue_recognition = st.selectbox(
                "Revenue Recognition Method",
                ["", "POINT_IN_TIME", "OVER_TIME", "COMPLETED_CONTRACT", "PERCENTAGE_COMPLETION"]
            )
        
        with col4:
            standard_margin = st.number_input(
                "Standard Margin %",
                min_value=0.0,
                max_value=100.0,
                format="%.2f"
            )
            
            target_margin = st.number_input(
                "Target Margin %",
                min_value=0.0,
                max_value=100.0,
                format="%.2f"
            )
            
            annual_revenue_target = st.number_input(
                "Annual Revenue Target",
                min_value=0.0,
                format="%.2f"
            )
            
            annual_volume_target = st.number_input(
                "Annual Volume Target",
                min_value=0.0,
                format="%.2f"
            )
        
        st.subheader("Lifecycle Management")
        col5, col6 = st.columns(2)
        
        with col5:
            lifecycle_stage = st.selectbox(
                "Lifecycle Stage*",
                ["DEVELOPMENT", "INTRODUCTION", "GROWTH", "MATURITY", "DECLINE", "END_OF_LIFE"]
            )
            
            launch_date = st.date_input("Launch Date")
            sunset_date = st.date_input("Sunset Date", value=None)
            
        with col6:
            market_share_target = st.number_input(
                "Market Share Target %",
                min_value=0.0,
                max_value=100.0,
                format="%.2f"
            )
            
            regulatory_classification = st.text_input(
                "Regulatory Classification",
                max_chars=50,
                help="e.g., FDA Class II, PRESCRIPTION, OTC"
            )
        
        st.subheader("Product Characteristics")
        col7, col8 = st.columns(2)
        
        with col7:
            st.markdown("**Product Type**")
            is_manufactured = st.checkbox("Manufactured Product")
            is_purchased = st.checkbox("Purchased Product")
            is_service = st.checkbox("Service Product")
            is_digital = st.checkbox("Digital Product")
        
        with col8:
            st.markdown("**Compliance Requirements**")
            requires_serialization = st.checkbox("Requires Serialization")
            requires_lot_tracking = st.checkbox("Requires Lot Tracking")
        
        col9, col10 = st.columns(2)
        with col9:
            is_active = st.checkbox("Active", value=True)
        with col10:
            valid_from = st.date_input("Valid From", value=date.today())
        
        submitted = st.form_submit_button("Create Product Line", type="primary")
        
        if submitted:
            if not all([product_line_id, product_line_name, lifecycle_stage]):
                st.error("Please fill in all required fields (marked with *)")
            else:
                try:
                    with engine.connect() as conn:
                        # Insert new product line
                        conn.execute(text("""
                            INSERT INTO product_lines (
                                product_line_id, product_line_name, short_name, description,
                                parent_product_line, product_category, product_family, product_group,
                                business_area_id, product_manager, product_manager_email,
                                default_profit_center, revenue_recognition_method,
                                standard_margin_percentage, target_margin_percentage,
                                lifecycle_stage, launch_date, sunset_date, industry_sector,
                                regulatory_classification, requires_serialization, requires_lot_tracking,
                                is_manufactured, is_purchased, is_service, is_digital,
                                annual_revenue_target, annual_volume_target, market_share_target,
                                is_active, valid_from, created_by
                            ) VALUES (
                                :product_line_id, :product_line_name, :short_name, :description,
                                :parent_product_line, :product_category, :product_family, :product_group,
                                :business_area_id, :product_manager, :product_manager_email,
                                :default_profit_center, :revenue_recognition_method,
                                :standard_margin_percentage, :target_margin_percentage,
                                :lifecycle_stage, :launch_date, :sunset_date, :industry_sector,
                                :regulatory_classification, :requires_serialization, :requires_lot_tracking,
                                :is_manufactured, :is_purchased, :is_service, :is_digital,
                                :annual_revenue_target, :annual_volume_target, :market_share_target,
                                :is_active, :valid_from, :created_by
                            )
                        """), {
                            'product_line_id': product_line_id,
                            'product_line_name': product_line_name,
                            'short_name': short_name or None,
                            'description': description or None,
                            'parent_product_line': parent_product_line,
                            'product_category': product_category or None,
                            'product_family': product_family or None,
                            'product_group': product_group or None,
                            'business_area_id': business_area_id,
                            'product_manager': product_manager or None,
                            'product_manager_email': product_manager_email or None,
                            'default_profit_center': default_profit_center or None,
                            'revenue_recognition_method': revenue_recognition or None,
                            'standard_margin_percentage': standard_margin if standard_margin > 0 else None,
                            'target_margin_percentage': target_margin if target_margin > 0 else None,
                            'lifecycle_stage': lifecycle_stage,
                            'launch_date': launch_date if launch_date != date.today() else None,
                            'sunset_date': sunset_date,
                            'industry_sector': industry_sector or None,
                            'regulatory_classification': regulatory_classification or None,
                            'requires_serialization': requires_serialization,
                            'requires_lot_tracking': requires_lot_tracking,
                            'is_manufactured': is_manufactured,
                            'is_purchased': is_purchased,
                            'is_service': is_service,
                            'is_digital': is_digital,
                            'annual_revenue_target': annual_revenue_target if annual_revenue_target > 0 else None,
                            'annual_volume_target': annual_volume_target if annual_volume_target > 0 else None,
                            'market_share_target': market_share_target if market_share_target > 0 else None,
                            'is_active': is_active,
                            'valid_from': valid_from,
                            'created_by': user.username
                        })
                        conn.commit()
                    
                    st.success(f"✅ Product Line {product_line_id} created successfully!")
                    st.rerun()
                    
                except Exception as e:
                    if "duplicate key" in str(e).lower():
                        st.error(f"❌ Product Line ID {product_line_id} already exists!")
                    else:
                        st.error(f"❌ Error creating product line: {e}")

def show_product_hierarchy():
    """Display product line hierarchy visualization."""
    st.header("🌳 Product Line Hierarchy")
    
    try:
        with engine.connect() as conn:
            # Get hierarchy data
            hierarchy = pd.read_sql(text("""
                SELECT 
                    product_line_id,
                    product_line_name,
                    parent_product_line,
                    product_category,
                    full_path,
                    level
                FROM v_product_line_hierarchy
                ORDER BY path
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading hierarchy: {e}")
        return
    
    if hierarchy.empty:
        st.info("No product hierarchy available.")
        return
    
    # Display hierarchy as expandable tree
    st.subheader("📋 Hierarchical Product Structure")
    
    # Group by level for display
    max_level = hierarchy['level'].max()
    
    for current_level in range(max_level + 1):
        level_products = hierarchy[hierarchy['level'] == current_level]
        
        if not level_products.empty:
            st.markdown(f"**Level {current_level} Products**")
            
            for _, product in level_products.iterrows():
                indent = "　" * current_level  # Japanese full-width space for indentation
                category = f" ({product['product_category']})" if product['product_category'] else ""
                st.write(f"{indent}📦 {product['product_line_id']} - {product['product_line_name']}{category}")
    
    # Hierarchy statistics
    st.subheader("📊 Hierarchy Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        level_counts = hierarchy['level'].value_counts().sort_index()
        fig = px.bar(
            x=[f"Level {i}" for i in level_counts.index],
            y=level_counts.values,
            title='Products by Hierarchy Level',
            labels={'x': 'Hierarchy Level', 'y': 'Count'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Show deepest product paths
        deepest = hierarchy.nlargest(5, 'level')[['product_line_id', 'product_line_name', 'level', 'full_path']]
        st.markdown("**Deepest Product Paths:**")
        for _, row in deepest.iterrows():
            st.write(f"**Level {row['level']}:** {row['full_path']}")

def show_lifecycle_analytics():
    """Product lifecycle analytics."""
    st.header("📈 Product Lifecycle Analytics")
    
    try:
        with engine.connect() as conn:
            # Lifecycle analysis
            lifecycle_data = pd.read_sql(text("""
                SELECT 
                    lifecycle_stage,
                    industry_sector,
                    COUNT(*) as product_count,
                    AVG(standard_margin_percentage) as avg_margin,
                    AVG(target_margin_percentage) as avg_target_margin,
                    AVG(annual_revenue_target) as avg_revenue_target
                FROM product_lines
                WHERE is_active = TRUE
                GROUP BY lifecycle_stage, industry_sector
                ORDER BY lifecycle_stage, industry_sector
            """), conn)
            
            # Performance targets
            targets_data = pd.read_sql(text("""
                SELECT 
                    product_line_id,
                    product_line_name,
                    lifecycle_stage,
                    industry_sector,
                    standard_margin_percentage,
                    target_margin_percentage,
                    annual_revenue_target,
                    market_share_target
                FROM product_lines
                WHERE is_active = TRUE 
                AND (annual_revenue_target > 0 OR market_share_target > 0)
                ORDER BY annual_revenue_target DESC NULLS LAST
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading analytics data: {e}")
        return
    
    # Lifecycle stage analysis
    if not lifecycle_data.empty:
        st.subheader("🔄 Lifecycle Stage Analysis")
        
        # Lifecycle distribution by industry
        fig1 = px.bar(
            lifecycle_data,
            x='lifecycle_stage',
            y='product_count',
            color='industry_sector',
            title='Product Count by Lifecycle Stage and Industry',
            barmode='stack'
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # Margin analysis by lifecycle
        lifecycle_margins = lifecycle_data.groupby('lifecycle_stage').agg({
            'avg_margin': 'mean',
            'avg_target_margin': 'mean'
        }).reset_index()
        
        if not lifecycle_margins.empty:
            fig2 = go.Figure()
            
            fig2.add_trace(go.Bar(
                name='Standard Margin',
                x=lifecycle_margins['lifecycle_stage'],
                y=lifecycle_margins['avg_margin'],
                marker_color='lightblue'
            ))
            
            fig2.add_trace(go.Bar(
                name='Target Margin',
                x=lifecycle_margins['lifecycle_stage'],
                y=lifecycle_margins['avg_target_margin'],
                marker_color='darkblue'
            ))
            
            fig2.update_layout(
                title='Average Margins by Lifecycle Stage',
                xaxis_title='Lifecycle Stage',
                yaxis_title='Margin Percentage',
                barmode='group'
            )
            
            st.plotly_chart(fig2, use_container_width=True)
    
    # Performance targets analysis
    if not targets_data.empty:
        st.subheader("🎯 Performance Targets Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Revenue targets by lifecycle
            revenue_by_stage = targets_data.groupby('lifecycle_stage')['annual_revenue_target'].sum().reset_index()
            fig3 = px.pie(
                revenue_by_stage,
                values='annual_revenue_target',
                names='lifecycle_stage',
                title='Revenue Targets by Lifecycle Stage'
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            # Market share targets
            market_share_data = targets_data[targets_data['market_share_target'] > 0]
            if not market_share_data.empty:
                fig4 = px.scatter(
                    market_share_data,
                    x='annual_revenue_target',
                    y='market_share_target',
                    color='lifecycle_stage',
                    size='target_margin_percentage',
                    title='Revenue vs Market Share Targets',
                    hover_data=['product_line_name']
                )
                st.plotly_chart(fig4, use_container_width=True)

def show_industry_analysis():
    """Industry sector analysis."""
    st.header("🎯 Industry Sector Analysis")
    
    try:
        with engine.connect() as conn:
            # Industry analysis
            industry_data = pd.read_sql(text("""
                SELECT 
                    industry_sector,
                    COUNT(*) as product_count,
                    COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_count,
                    COUNT(CASE WHEN lifecycle_stage = 'GROWTH' THEN 1 END) as growth_stage_count,
                    COUNT(CASE WHEN is_manufactured = TRUE THEN 1 END) as manufactured_count,
                    COUNT(CASE WHEN is_service = TRUE THEN 1 END) as service_count,
                    COUNT(CASE WHEN is_digital = TRUE THEN 1 END) as digital_count,
                    AVG(standard_margin_percentage) as avg_margin
                FROM product_lines
                WHERE industry_sector IS NOT NULL
                GROUP BY industry_sector
                ORDER BY product_count DESC
            """), conn)
            
            # Compliance requirements by industry
            compliance_data = pd.read_sql(text("""
                SELECT 
                    industry_sector,
                    COUNT(CASE WHEN requires_serialization = TRUE THEN 1 END) as serialization_required,
                    COUNT(CASE WHEN requires_lot_tracking = TRUE THEN 1 END) as lot_tracking_required,
                    COUNT(*) as total_products
                FROM product_lines
                WHERE industry_sector IS NOT NULL
                GROUP BY industry_sector
                ORDER BY industry_sector
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading industry data: {e}")
        return
    
    if industry_data.empty:
        st.info("No industry-specific data available.")
        return
    
    # Industry overview
    st.subheader("🏭 Industry Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = px.bar(
            industry_data,
            x='industry_sector',
            y='product_count',
            title='Product Lines by Industry Sector',
            color='avg_margin',
            color_continuous_scale='viridis',
            text='product_count'
        )
        fig1.update_traces(textposition='auto')
        fig1.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # Product type distribution by industry
        type_data = industry_data[['industry_sector', 'manufactured_count', 'service_count', 'digital_count']]
        type_melted = type_data.melt(
            id_vars='industry_sector',
            value_vars=['manufactured_count', 'service_count', 'digital_count'],
            var_name='product_type',
            value_name='count'
        )
        
        fig2 = px.bar(
            type_melted,
            x='industry_sector',
            y='count',
            color='product_type',
            title='Product Types by Industry',
            barmode='stack'
        )
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Compliance requirements
    if not compliance_data.empty:
        st.subheader("📋 Compliance Requirements by Industry")
        
        compliance_melted = compliance_data.melt(
            id_vars='industry_sector',
            value_vars=['serialization_required', 'lot_tracking_required'],
            var_name='requirement_type',
            value_name='count'
        )
        
        fig3 = px.bar(
            compliance_melted,
            x='industry_sector',
            y='count',
            color='requirement_type',
            title='Compliance Requirements Distribution',
            barmode='group'
        )
        fig3.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)
    
    # Industry performance table
    st.subheader("📊 Industry Performance Summary")
    
    st.dataframe(
        industry_data,
        use_container_width=True,
        column_config={
            'industry_sector': 'Industry',
            'product_count': st.column_config.NumberColumn('Total Products'),
            'active_count': st.column_config.NumberColumn('Active Products'),
            'growth_stage_count': st.column_config.NumberColumn('Growth Stage'),
            'manufactured_count': st.column_config.NumberColumn('Manufactured'),
            'service_count': st.column_config.NumberColumn('Services'),
            'digital_count': st.column_config.NumberColumn('Digital'),
            'avg_margin': st.column_config.NumberColumn('Avg Margin %', format="%.2f")
        }
    )

def show_product_reports():
    """Product line reporting interface."""
    st.header("📋 Product Line Reports")
    
    # Report selection
    report_type = st.selectbox(
        "Select Report Type",
        [
            "📊 Product Line Summary Report",
            "🔄 Lifecycle Status Report", 
            "🎯 Industry Analysis Report",
            "📈 Performance Targets Report"
        ]
    )
    
    try:
        with engine.connect() as conn:
            if report_type == "📊 Product Line Summary Report":
                report_data = pd.read_sql(text("""
                    SELECT 
                        pl.product_line_id,
                        pl.product_line_name,
                        pl.short_name,
                        pl.product_category,
                        pl.lifecycle_stage,
                        pl.industry_sector,
                        ba.business_area_name,
                        pl.product_manager,
                        pl.standard_margin_percentage,
                        pl.target_margin_percentage,
                        pl.annual_revenue_target,
                        pl.is_active,
                        pl.created_at
                    FROM product_lines pl
                    LEFT JOIN business_areas ba ON pl.business_area_id = ba.business_area_id
                    ORDER BY pl.product_line_id
                """), conn)
                
                st.subheader("📊 Complete Product Line Summary")
                st.dataframe(report_data, use_container_width=True)
                
                # Download option
                csv = report_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"product_line_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    except Exception as e:
        st.error(f"Error generating report: {e}")

def show_advanced_operations():
    """Advanced product line operations."""
    st.header("⚙️ Advanced Product Line Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔧 Bulk Operations")
        
        st.markdown("**Lifecycle Stage Updates**")
        from_stage = st.selectbox("From Lifecycle Stage", 
                                 ["DEVELOPMENT", "INTRODUCTION", "GROWTH", "MATURITY", "DECLINE", "END_OF_LIFE"])
        to_stage = st.selectbox("To Lifecycle Stage",
                               ["DEVELOPMENT", "INTRODUCTION", "GROWTH", "MATURITY", "DECLINE", "END_OF_LIFE"])
        
        if st.button("Update Lifecycle Stages"):
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        UPDATE product_lines 
                        SET lifecycle_stage = :to_stage,
                            modified_by = :user,
                            modified_at = CURRENT_TIMESTAMP
                        WHERE lifecycle_stage = :from_stage
                        AND is_active = TRUE
                    """), {
                        'from_stage': from_stage,
                        'to_stage': to_stage,
                        'user': user.username
                    })
                    
                    affected = result.rowcount
                    conn.commit()
                    
                st.success(f"✅ Updated {affected} product lines from {from_stage} to {to_stage}")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error during bulk operation: {e}")
    
    with col2:
        st.subheader("📊 Data Validation")
        
        if st.button("Validate Product Data"):
            try:
                with engine.connect() as conn:
                    # Check for orphaned product lines
                    orphans = pd.read_sql(text("""
                        SELECT product_line_id, product_line_name, parent_product_line
                        FROM product_lines
                        WHERE parent_product_line IS NOT NULL 
                        AND parent_product_line NOT IN (
                            SELECT product_line_id FROM product_lines
                        )
                    """), conn)
                    
                    # Check for missing business areas
                    missing_ba = pd.read_sql(text("""
                        SELECT product_line_id, product_line_name
                        FROM product_lines
                        WHERE business_area_id IS NULL AND is_active = TRUE
                    """), conn)
                    
                if not orphans.empty:
                    st.error("❌ Found orphaned product lines:")
                    st.dataframe(orphans)
                else:
                    st.success("✅ No orphaned product lines found")
                
                if not missing_ba.empty:
                    st.warning("⚠️ Active product lines without business area:")
                    st.dataframe(missing_ba)
                else:
                    st.success("✅ All active products have business areas assigned")
                    
            except Exception as e:
                st.error(f"❌ Validation error: {e}")

def show_edit_product_lines():
    """Edit existing product lines."""
    st.header("✏️ Edit Product Lines")
    
    st.info("Select a product line below to modify its configuration.")
    
    try:
        with engine.connect() as conn:
            products = pd.read_sql(text("""
                SELECT product_line_id, product_line_name, product_category, lifecycle_stage, is_active
                FROM product_lines 
                ORDER BY product_line_id
            """), conn)
    
    except Exception as e:
        st.error(f"Error loading product lines: {e}")
        return
    
    if products.empty:
        st.warning("No product lines available for editing.")
        return
    
    # Product selection
    selected_product = st.selectbox(
        "Select Product Line to Edit",
        options=products['product_line_id'].tolist(),
        format_func=lambda x: f"{x} - {products[products['product_line_id']==x]['product_line_name'].iloc[0]} ({products[products['product_line_id']==x]['lifecycle_stage'].iloc[0]})"
    )
    
    if selected_product:
        # Show current configuration
        product_data = products[products['product_line_id'] == selected_product].iloc[0]
        
        st.subheader(f"Editing Product Line: {selected_product}")
        
        with st.expander("Current Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Product Line ID:** {product_data['product_line_id']}")
                st.write(f"**Product Name:** {product_data['product_line_name']}")
                st.write(f"**Category:** {product_data['product_category']}")
            
            with col2:
                st.write(f"**Lifecycle Stage:** {product_data['lifecycle_stage']}")
                st.write(f"**Active:** {'Yes' if product_data['is_active'] else 'No'}")
        
        st.write("**Full edit functionality would be implemented here for updating product line configurations.**")

if __name__ == "__main__":
    main()