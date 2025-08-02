import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb

# Configure page
st.set_page_config(page_title="📊 Revenue & Expenses Trend", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Revenue & Expenses Trend", "Financial Reports", "Analytics")

st.title("📊 Revenue & Total Expenses Trend Analysis")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        cost_centers = [row[0] for row in conn.execute(text("SELECT DISTINCT ledgerid FROM journalentryline WHERE ledgerid IS NOT NULL ORDER BY ledgerid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
    
    return companies, cost_centers, years

def get_monthly_data(companies, cost_centers, years):
    """Get monthly revenue and expense data"""
    
    # Build query conditions
    where_conditions = ["1=1"]
    params = {}
    
    if companies and "All" not in companies:
        comp_ph = ", ".join([f":comp{i}" for i in range(len(companies))])
        where_conditions.append(f"jeh.companycodeid IN ({comp_ph})")
        params.update({f"comp{i}": v for i, v in enumerate(companies)})
    
    if cost_centers and "All" not in cost_centers:
        cc_ph = ", ".join([f":cc{i}" for i in range(len(cost_centers))])
        where_conditions.append(f"jel.ledgerid IN ({cc_ph})")
        params.update({f"cc{i}": v for i, v in enumerate(cost_centers)})
    
    if years and "All" not in years:
        year_ph = ", ".join([f":year{i}" for i in range(len(years))])
        where_conditions.append(f"jeh.fiscalyear IN ({year_ph})")
        params.update({f"year{i}": v for i, v in enumerate(years)})
    
    query = f"""
    WITH monthly_data AS (
        SELECT 
            jeh.fiscalyear,
            jeh.period,
            CONCAT(jeh.fiscalyear, '-', LPAD(jeh.period::text, 2, '0')) as year_month,
            coa.accounttype,
            CASE 
                WHEN coa.accounttype = 'Revenue' THEN 
                    SUM(COALESCE(jel.creditamount, 0) - COALESCE(jel.debitamount, 0))
                WHEN coa.accounttype IN ('Expense', 'Expenses') THEN 
                    SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0))
                ELSE 0
            END as amount,
            -- Categorize expenses
            CASE 
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%cost of goods%' 
                    OR LOWER(coa.accountname) LIKE '%cogs%'
                    OR LOWER(coa.accountname) LIKE '%direct cost%'
                    OR LOWER(coa.accountname) LIKE '%cost of sales%'
                ) THEN 'Cost of Goods Sold'
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%salary%' 
                    OR LOWER(coa.accountname) LIKE '%wage%'
                    OR LOWER(coa.accountname) LIKE '%payroll%'
                    OR LOWER(coa.accountname) LIKE '%compensation%'
                ) THEN 'Personnel Expenses'
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%marketing%' 
                    OR LOWER(coa.accountname) LIKE '%advertising%'
                    OR LOWER(coa.accountname) LIKE '%promotion%'
                ) THEN 'Marketing Expenses'
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%rent%' 
                    OR LOWER(coa.accountname) LIKE '%utilities%'
                    OR LOWER(coa.accountname) LIKE '%office%'
                    OR LOWER(coa.accountname) LIKE '%facility%'
                ) THEN 'Facilities Expenses'
                WHEN coa.accounttype IN ('Expense', 'Expenses') THEN 'Other Operating Expenses'
                ELSE coa.accounttype
            END as category
        FROM journalentryline jel
        JOIN glaccount coa ON coa.glaccountid = jel.glaccountid
        JOIN journalentryheader jeh ON jeh.documentnumber = jel.documentnumber 
            AND jeh.companycodeid = jel.companycodeid
        WHERE {' AND '.join(where_conditions)}
            AND coa.accounttype IN ('Revenue', 'Expense')
        GROUP BY jeh.fiscalyear, jeh.period, year_month, coa.accounttype, category
    )
    SELECT 
        year_month,
        fiscalyear,
        period,
        category,
        SUM(amount) as total_amount
    FROM monthly_data
    GROUP BY year_month, fiscalyear, period, category
    ORDER BY fiscalyear, period
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    
    return df

# Get filter options
companies, cost_centers, years = get_filter_options()

# Filter Section
with st.expander("🔍 Filter Options", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🏢 Company")
        selected_companies = st.multiselect("Company Code(s)", ["All"] + companies, default=["All"])
    
    with col2:
        st.subheader("🏷️ Cost Center")
        selected_cost_centers = st.multiselect("Cost Center(s)", ["All"] + cost_centers, default=["All"])
    
    with col3:
        st.subheader("📅 Fiscal Year")
        selected_years = st.multiselect("Fiscal Year(s)", ["All"] + years, default=["All"])

# Chart Options
with st.expander("📊 Chart Options", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        show_expense_breakdown = st.checkbox("Show Expense Categories Breakdown", value=True)
        show_net_income = st.checkbox("Show Net Income Line", value=True)
    with col2:
        chart_type = st.selectbox("Chart Type for Revenue", ["Bar", "Line"], index=0)
        expense_chart_type = st.selectbox("Chart Type for Expenses", ["Line", "Stacked Bar"], index=0)

# Generate Report Button
if st.button("📊 Generate Trend Analysis", type="primary"):
    with st.spinner("Generating trend analysis..."):
        try:
            # Get data
            df = get_monthly_data(selected_companies, selected_cost_centers, selected_years)
            
            if df.empty:
                st.warning("No data found for the selected filters.")
            else:
                # Pivot data for easier processing
                pivot_df = df.pivot_table(
                    index=['year_month', 'fiscalyear', 'period'], 
                    columns='category', 
                    values='total_amount', 
                    fill_value=0
                ).reset_index()
                
                # Calculate total expenses and net income
                expense_columns = [col for col in pivot_df.columns if 'Expenses' in col or col == 'Cost of Goods Sold']
                if expense_columns:
                    pivot_df['Total Expenses'] = pivot_df[expense_columns].sum(axis=1)
                else:
                    pivot_df['Total Expenses'] = 0
                
                revenue = pivot_df.get('Revenue', pd.Series([0] * len(pivot_df)))
                pivot_df['Net Income'] = revenue - pivot_df['Total Expenses']
                
                # Sort by year and period
                pivot_df = pivot_df.sort_values(['fiscalyear', 'period'])
                
                # Create the main chart
                st.subheader("📊 Revenue & Total Expenses Trend by Month")
                
                # Create subplot with secondary y-axis
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Add Revenue
                if chart_type == "Bar":
                    fig.add_trace(
                        go.Bar(
                            x=pivot_df['year_month'],
                            y=pivot_df.get('Revenue', [0] * len(pivot_df)),
                            name='Revenue',
                            marker_color='#1f77b4',
                            opacity=0.7
                        ),
                        secondary_y=False
                    )
                else:
                    fig.add_trace(
                        go.Scatter(
                            x=pivot_df['year_month'],
                            y=pivot_df.get('Revenue', [0] * len(pivot_df)),
                            mode='lines+markers',
                            name='Revenue',
                            line=dict(color='#1f77b4', width=3),
                            marker=dict(size=8)
                        ),
                        secondary_y=False
                    )
                
                # Add Total Expenses
                fig.add_trace(
                    go.Scatter(
                        x=pivot_df['year_month'],
                        y=pivot_df['Total Expenses'],
                        mode='lines+markers',
                        name='Total Expenses',
                        line=dict(color='#ff7f0e', width=3),
                        marker=dict(size=8)
                    ),
                    secondary_y=True
                )
                
                # Add Net Income if requested
                if show_net_income:
                    fig.add_trace(
                        go.Scatter(
                            x=pivot_df['year_month'],
                            y=pivot_df['Net Income'],
                            mode='lines+markers',
                            name='Net Income',
                            line=dict(color='#2ca02c', width=3, dash='dash'),
                            marker=dict(size=8)
                        ),
                        secondary_y=True
                    )
                
                # Update layout
                chart_title = f"Revenue ({chart_type}) & Total Expenses (Line) Trend by Month"
                if show_net_income:
                    chart_title += " with Net Income"
                
                fig.update_layout(
                    title=chart_title,
                    xaxis_title="Year-Month",
                    height=600,
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                # Set y-axes titles
                fig.update_yaxes(title_text="Revenue", secondary_y=False)
                fig.update_yaxes(title_text="Expenses & Net Income", secondary_y=True)
                
                # Display chart
                st.plotly_chart(fig, use_container_width=True)
                
                # Expense Breakdown Chart
                if show_expense_breakdown and expense_columns:
                    st.subheader("💸 Expense Categories Breakdown")
                    
                    if expense_chart_type == "Stacked Bar":
                        fig2 = go.Figure()
                        colors = px.colors.qualitative.Set3
                        
                        for i, col in enumerate(expense_columns):
                            if col in pivot_df.columns:
                                fig2.add_trace(go.Bar(
                                    x=pivot_df['year_month'],
                                    y=pivot_df[col],
                                    name=col,
                                    marker_color=colors[i % len(colors)]
                                ))
                        
                        fig2.update_layout(
                            title="Monthly Expense Categories (Stacked)",
                            xaxis_title="Year-Month",
                            yaxis_title="Expense Amount",
                            barmode='stack',
                            height=500
                        )
                    else:
                        fig2 = go.Figure()
                        colors = px.colors.qualitative.Set3
                        
                        for i, col in enumerate(expense_columns):
                            if col in pivot_df.columns:
                                fig2.add_trace(go.Scatter(
                                    x=pivot_df['year_month'],
                                    y=pivot_df[col],
                                    mode='lines+markers',
                                    name=col,
                                    line=dict(color=colors[i % len(colors)], width=2),
                                    marker=dict(size=6)
                                ))
                        
                        fig2.update_layout(
                            title="Monthly Expense Categories (Lines)",
                            xaxis_title="Year-Month",
                            yaxis_title="Expense Amount",
                            height=500
                        )
                    
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Summary metrics
                st.subheader("📋 Summary Metrics")
                col1, col2, col3, col4 = st.columns(4)
                
                total_revenue = pivot_df.get('Revenue', pd.Series([0])).sum()
                total_expenses = pivot_df['Total Expenses'].sum()
                total_net_income = pivot_df['Net Income'].sum()
                avg_monthly_revenue = pivot_df.get('Revenue', pd.Series([0])).mean()
                
                with col1:
                    st.metric("Total Revenue", f"{total_revenue:,.2f}")
                with col2:
                    st.metric("Total Expenses", f"{total_expenses:,.2f}")
                with col3:
                    st.metric("Total Net Income", f"{total_net_income:,.2f}")
                with col4:
                    st.metric("Avg Monthly Revenue", f"{avg_monthly_revenue:,.2f}")
                
                # Financial ratios
                col1, col2, col3 = st.columns(3)
                with col1:
                    if total_revenue != 0:
                        expense_ratio = (total_expenses / total_revenue) * 100
                        st.metric("Expense Ratio", f"{expense_ratio:.2f}%")
                
                with col2:
                    if total_revenue != 0:
                        net_margin = (total_net_income / total_revenue) * 100
                        st.metric("Net Margin", f"{net_margin:.2f}%")
                
                with col3:
                    avg_monthly_expenses = pivot_df['Total Expenses'].mean()
                    st.metric("Avg Monthly Expenses", f"{avg_monthly_expenses:,.2f}")
                
                # Data table
                st.subheader("📊 Monthly Data Table")
                
                # Prepare display dataframe
                display_df = pivot_df.copy()
                
                # Format numeric columns
                numeric_columns = ['Revenue', 'Total Expenses', 'Net Income'] + expense_columns
                for col in numeric_columns:
                    if col in display_df.columns:
                        display_df[f'{col}_formatted'] = display_df[col].apply(lambda x: f"{x:,.2f}")
                
                # Select and rename columns for display
                display_columns = ['year_month', 'fiscalyear', 'period']
                display_names = ['Year-Month', 'Fiscal Year', 'Period']
                
                for col in ['Revenue', 'Total Expenses', 'Net Income']:
                    if col in display_df.columns:
                        display_columns.append(f'{col}_formatted')
                        display_names.append(col)
                
                if len(display_columns) > 3:  # Only show if we have data
                    final_df = display_df[display_columns].copy()
                    final_df.columns = display_names
                    
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                
                # Growth Analysis
                if len(pivot_df) > 1:
                    st.subheader("📈 Growth Analysis")
                    
                    # Calculate month-over-month growth
                    revenue_growth = ((pivot_df.get('Revenue', pd.Series([0])).iloc[-1] - 
                                     pivot_df.get('Revenue', pd.Series([0])).iloc[-2]) / 
                                    pivot_df.get('Revenue', pd.Series([1])).iloc[-2] * 100) if len(pivot_df) >= 2 else 0
                    
                    expense_growth = ((pivot_df['Total Expenses'].iloc[-1] - pivot_df['Total Expenses'].iloc[-2]) / 
                                    pivot_df['Total Expenses'].iloc[-2] * 100) if len(pivot_df) >= 2 and pivot_df['Total Expenses'].iloc[-2] != 0 else 0
                    
                    net_income_growth = ((pivot_df['Net Income'].iloc[-1] - pivot_df['Net Income'].iloc[-2]) / 
                                       abs(pivot_df['Net Income'].iloc[-2]) * 100) if len(pivot_df) >= 2 and pivot_df['Net Income'].iloc[-2] != 0 else 0
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Revenue Growth (MoM)", f"{revenue_growth:.2f}%")
                    with col2:
                        st.metric("Expense Growth (MoM)", f"{expense_growth:.2f}%")
                    with col3:
                        st.metric("Net Income Growth (MoM)", f"{net_income_growth:.2f}%")
                
                # Export functionality
                st.subheader("📤 Export Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    csv_data = final_df.to_csv(index=False) if 'final_df' in locals() else pivot_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv_data,
                        file_name=f"Revenue_Expenses_Trend_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    # Excel export would go here
                    st.info("Excel export - feature coming soon")
                
        except Exception as e:
            st.error(f"Error generating trend analysis: {str(e)}")

# Information panel
with st.expander("ℹ️ About Revenue & Total Expenses Trend Analysis"):
    st.markdown("""
    **Revenue & Total Expenses Trend Analysis** shows the monthly trend of revenue, expenses, and net income with detailed expense categorization.
    
    **Key Metrics:**
    - **Revenue**: Total income from business operations (Credit balances from Revenue accounts)
    - **Total Expenses**: Sum of all expense categories
    - **Net Income**: Revenue - Total Expenses
    - **Expense Ratio**: Total Expenses ÷ Revenue × 100
    - **Net Margin**: Net Income ÷ Revenue × 100
    
    **Expense Categories:**
    - **Cost of Goods Sold**: Direct costs related to production/sales
    - **Personnel Expenses**: Salaries, wages, payroll, compensation
    - **Marketing Expenses**: Advertising, promotion, marketing costs
    - **Facilities Expenses**: Rent, utilities, office, facility costs
    - **Other Operating Expenses**: All other operating expenses
    
    **Chart Features:**
    - **Revenue**: Configurable as bars or lines
    - **Total Expenses**: Line chart with markers
    - **Net Income**: Optional dashed line showing profitability
    - **Expense Breakdown**: Separate chart showing expense categories
    
    **Growth Analysis:**
    - Month-over-month percentage changes
    - Trend identification for revenue, expenses, and profitability
    
    **Use Cases:**
    - Monitor financial performance trends
    - Identify cost control opportunities
    - Track profitability over time
    - Analyze expense category patterns
    - Compare revenue vs. expense growth rates
    """)

# Navigation is now handled by the SAP-style sidebar