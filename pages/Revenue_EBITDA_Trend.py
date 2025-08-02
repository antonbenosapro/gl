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
st.set_page_config(page_title="📈 Revenue & EBITDA Trend", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Revenue & EBITDA Trend", "Financial Reports", "Analytics")

st.title("📈 Revenue & EBITDA Trend Analysis")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        cost_centers = [row[0] for row in conn.execute(text("SELECT DISTINCT ledgerid FROM journalentryline WHERE ledgerid IS NOT NULL ORDER BY ledgerid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
    
    return companies, cost_centers, years

def calculate_ebitda(net_income, interest_expense, income_taxes, depreciation, amortization):
    """Calculate EBITDA = Net Income + Interest Expense + Income Taxes + Depreciation + Amortization"""
    return net_income + interest_expense + income_taxes + depreciation + amortization

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
            CASE 
                WHEN LOWER(coa.accountname) LIKE '%depreciation%' THEN 'Depreciation'
                WHEN LOWER(coa.accountname) LIKE '%amortization%' THEN 'Amortization'
                WHEN LOWER(coa.accountname) LIKE '%interest%' AND coa.accounttype IN ('Expense', 'Expenses') THEN 'Interest Expense'
                WHEN LOWER(coa.accountname) LIKE '%tax%' AND coa.accounttype IN ('Expense', 'Expenses') THEN 'Income Taxes'
                WHEN coa.accounttype IN ('Expense', 'Expenses') THEN 'Operating Expense'
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

# Generate Report Button
if st.button("📈 Generate Trend Analysis", type="primary"):
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
                
                # Calculate Net Income first (Revenue - All Expenses)
                revenue = pivot_df.get('Revenue', pd.Series([0] * len(pivot_df)))
                operating_expenses = pivot_df.get('Operating Expense', pd.Series([0] * len(pivot_df)))
                interest_expense = pivot_df.get('Interest Expense', pd.Series([0] * len(pivot_df)))
                income_taxes = pivot_df.get('Income Taxes', pd.Series([0] * len(pivot_df)))
                depreciation = pivot_df.get('Depreciation', pd.Series([0] * len(pivot_df)))
                amortization = pivot_df.get('Amortization', pd.Series([0] * len(pivot_df)))
                
                # Net Income = Revenue - All Expenses
                total_expenses = operating_expenses + interest_expense + income_taxes + depreciation + amortization
                net_income = revenue - total_expenses
                pivot_df['Net Income'] = net_income
                
                # EBITDA = Net Income + Interest Expense + Income Taxes + Depreciation + Amortization
                pivot_df['EBITDA'] = calculate_ebitda(net_income, interest_expense, income_taxes, depreciation, amortization)
                
                # Sort by year and period
                pivot_df = pivot_df.sort_values(['fiscalyear', 'period'])
                
                # Create the chart
                st.subheader("📊 Revenue & EBITDA Trend by Month")
                
                # Create subplot with secondary y-axis
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                # Add Revenue as bar chart
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
                
                # Add EBITDA as line chart
                fig.add_trace(
                    go.Scatter(
                        x=pivot_df['year_month'],
                        y=pivot_df['EBITDA'],
                        mode='lines+markers',
                        name='EBITDA',
                        line=dict(color='#ff7f0e', width=3),
                        marker=dict(size=8)
                    ),
                    secondary_y=True
                )
                
                # Update layout
                fig.update_layout(
                    title="Revenue (Bars) & EBITDA (Line) Trend by Month",
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
                fig.update_yaxes(title_text="EBITDA", secondary_y=True)
                
                # Display chart
                st.plotly_chart(fig, use_container_width=True)
                
                # Summary metrics
                st.subheader("📋 Summary Metrics")
                col1, col2, col3, col4 = st.columns(4)
                
                total_revenue = pivot_df.get('Revenue', pd.Series([0])).sum()
                total_net_income = pivot_df['Net Income'].sum()
                total_ebitda = pivot_df['EBITDA'].sum()
                avg_monthly_revenue = pivot_df.get('Revenue', pd.Series([0])).mean()
                
                with col1:
                    st.metric("Total Revenue", f"{total_revenue:,.2f}")
                with col2:
                    st.metric("Total Net Income", f"{total_net_income:,.2f}")
                with col3:
                    st.metric("Total EBITDA", f"{total_ebitda:,.2f}")
                with col4:
                    st.metric("Avg Monthly Revenue", f"{avg_monthly_revenue:,.2f}")
                
                # Additional metrics row
                col1, col2, col3, col4 = st.columns(4)
                avg_monthly_ebitda = pivot_df['EBITDA'].mean()
                total_interest = pivot_df.get('Interest Expense', pd.Series([0])).sum()
                total_taxes = pivot_df.get('Income Taxes', pd.Series([0])).sum()
                total_depreciation = (pivot_df.get('Depreciation', pd.Series([0])).sum() + 
                                    pivot_df.get('Amortization', pd.Series([0])).sum())
                
                with col1:
                    st.metric("Avg Monthly EBITDA", f"{avg_monthly_ebitda:,.2f}")
                with col2:
                    st.metric("Total Interest Expense", f"{total_interest:,.2f}")
                with col3:
                    st.metric("Total Income Taxes", f"{total_taxes:,.2f}")
                with col4:
                    st.metric("Total Depreciation & Amortization", f"{total_depreciation:,.2f}")
                
                # Financial ratios
                if total_revenue != 0:
                    ebitda_margin = (total_ebitda / total_revenue) * 100
                    net_margin = (total_net_income / total_revenue) * 100
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("EBITDA Margin", f"{ebitda_margin:.2f}%")
                    with col2:
                        st.metric("Net Margin", f"{net_margin:.2f}%")
                
                # Data table
                st.subheader("📊 Monthly Data Table")
                
                # Prepare display dataframe
                display_df = pivot_df.copy()
                
                # Format numeric columns
                numeric_columns = ['Revenue', 'Operating Expense', 'Interest Expense', 'Income Taxes', 
                                 'Depreciation', 'Amortization', 'Net Income', 'EBITDA']
                for col in numeric_columns:
                    if col in display_df.columns:
                        display_df[f'{col}_formatted'] = display_df[col].apply(lambda x: f"{x:,.2f}")
                
                # Select and rename columns for display
                display_columns = ['year_month', 'fiscalyear', 'period']
                display_names = ['Year-Month', 'Fiscal Year', 'Period']
                
                # Add key columns for EBITDA analysis
                key_columns = ['Revenue', 'Net Income', 'EBITDA', 'Interest Expense', 'Income Taxes']
                for col in key_columns:
                    if col in display_df.columns:
                        display_columns.append(f'{col}_formatted')
                        display_names.append(col)
                
                if len(display_columns) > 3:  # Only show if we have data
                    final_df = display_df[display_columns].copy()
                    final_df.columns = display_names
                    
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                
                # Show EBITDA breakdown table
                st.subheader("🔍 EBITDA Breakdown")
                breakdown_cols = ['Interest Expense', 'Income Taxes', 'Depreciation', 'Amortization']
                breakdown_data = []
                for col in breakdown_cols:
                    if col in display_df.columns:
                        total = display_df[col].sum()
                        breakdown_data.append([col, f"{total:,.2f}"])
                
                if breakdown_data:
                    breakdown_df = pd.DataFrame(breakdown_data, columns=['Component', 'Total Amount'])
                    st.dataframe(breakdown_df, use_container_width=True, hide_index=True)
                
                # Growth Analysis
                if len(pivot_df) > 1:
                    st.subheader("📈 Growth Analysis")
                    
                    # Calculate month-over-month growth
                    revenue_growth = ((pivot_df.get('Revenue', pd.Series([0])).iloc[-1] - 
                                     pivot_df.get('Revenue', pd.Series([0])).iloc[-2]) / 
                                    pivot_df.get('Revenue', pd.Series([1])).iloc[-2] * 100) if len(pivot_df) >= 2 else 0
                    
                    ebitda_growth = ((pivot_df['EBITDA'].iloc[-1] - pivot_df['EBITDA'].iloc[-2]) / 
                                   abs(pivot_df['EBITDA'].iloc[-2]) * 100) if len(pivot_df) >= 2 and pivot_df['EBITDA'].iloc[-2] != 0 else 0
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Revenue Growth (MoM)", f"{revenue_growth:.2f}%")
                    with col2:
                        st.metric("EBITDA Growth (MoM)", f"{ebitda_growth:.2f}%")
                
                # Export functionality
                st.subheader("📤 Export Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    csv_data = final_df.to_csv(index=False) if 'final_df' in locals() else pivot_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv_data,
                        file_name=f"Revenue_EBITDA_Trend_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                with col2:
                    # Excel export would go here
                    st.info("Excel export - feature coming soon")
                
        except Exception as e:
            st.error(f"Error generating trend analysis: {str(e)}")

# Information panel
with st.expander("ℹ️ About Revenue & EBITDA Trend Analysis"):
    st.markdown("""
    **Revenue & EBITDA Trend Analysis** shows the monthly trend of revenue and EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization).
    
    **Key Metrics:**
    - **Revenue**: Total income from business operations (Credit balances from Revenue accounts)
    - **Net Income**: Revenue - All Expenses (bottom line profitability)
    - **EBITDA**: Net Income + Interest Expense + Income Taxes + Depreciation + Amortization
    - **EBITDA Margin**: EBITDA ÷ Revenue × 100
    
    **Chart Elements:**
    - **Blue Bars**: Monthly Revenue amounts
    - **Orange Line**: Monthly EBITDA trend
    - **Growth Metrics**: Month-over-month percentage changes
    
    **EBITDA Calculation Formula:**
    - **EBITDA = Net Income + Interest Expense + Income Taxes + Depreciation + Amortization**
    
    **Component Breakdown:**
    - **Net Income**: Revenue - All Expenses (the company's bottom line)
    - **Interest Expense**: Cost of borrowed money (added back to focus on operations)
    - **Income Taxes**: Tax obligations (added back to focus on pre-tax performance)
    - **Depreciation**: Non-cash expense for asset deterioration (added back)
    - **Amortization**: Non-cash expense for intangible asset allocation (added back)
    
    **Filters:**
    - **Company**: Filter by specific company codes
    - **Cost Center**: Filter by cost center/ledger ID
    - **Fiscal Year**: Filter by fiscal year(s)
    
    **Use Cases:**
    - Monitor business performance trends
    - Identify seasonal patterns
    - Evaluate operational efficiency
    - Track profitability before financing and tax effects
    """)

# Navigation is now handled by the SAP-style sidebar