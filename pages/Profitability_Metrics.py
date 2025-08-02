import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb

st.set_page_config(page_title="📈 Profitability Metrics", layout="wide", initial_sidebar_state="expanded")

show_sap_sidebar()
show_breadcrumb("Profitability Metrics", "Financial Reports", "Analytics")

st.title("📈 Profitability Metrics Analysis")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
    
    return companies, years, periods

def get_profitability_data(companies, years, periods):
    """Get profitability data for calculations"""
    
    where_conditions = ["1=1"]
    params = {}
    
    if companies and "All" not in companies:
        comp_ph = ", ".join([f":comp{i}" for i in range(len(companies))])
        where_conditions.append(f"jeh.companycodeid IN ({comp_ph})")
        params.update({f"comp{i}": v for i, v in enumerate(companies)})
    
    if years and "All" not in years:
        year_ph = ", ".join([f":year{i}" for i in range(len(years))])
        where_conditions.append(f"jeh.fiscalyear IN ({year_ph})")
        params.update({f"year{i}": v for i, v in enumerate(years)})
    
    if periods and "All" not in periods:
        period_ph = ", ".join([f":period{i}" for i in range(len(periods))])
        where_conditions.append(f"jeh.period IN ({period_ph})")
        params.update({f"period{i}": v for i, v in enumerate(periods)})
    
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
                WHEN coa.accounttype = 'Asset' THEN
                    SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0))
                WHEN coa.accounttype = 'Liability' THEN
                    SUM(COALESCE(jel.creditamount, 0) - COALESCE(jel.debitamount, 0))
                WHEN coa.accounttype = 'Equity' THEN
                    SUM(COALESCE(jel.creditamount, 0) - COALESCE(jel.debitamount, 0))
                ELSE 0
            END as amount,
            CASE 
                -- Revenue categories
                WHEN coa.accounttype = 'Revenue' THEN 'Revenue'
                -- Expense categories for profitability analysis
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%cost of goods%' 
                    OR LOWER(coa.accountname) LIKE '%cogs%'
                    OR LOWER(coa.accountname) LIKE '%direct cost%'
                    OR LOWER(coa.accountname) LIKE '%cost of sales%'
                    OR LOWER(coa.accountname) LIKE '%cost of revenue%'
                ) THEN 'Cost of Goods Sold'
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%depreciation%'
                    OR LOWER(coa.accountname) LIKE '%amortization%'
                ) THEN 'Depreciation and Amortization'
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%interest%'
                ) THEN 'Interest Expense'
                WHEN coa.accounttype IN ('Expense', 'Expenses') AND (
                    LOWER(coa.accountname) LIKE '%tax%'
                ) THEN 'Income Taxes'
                WHEN coa.accounttype IN ('Expense', 'Expenses') THEN 'Operating Expenses'
                -- Balance sheet categories
                WHEN coa.accounttype = 'Asset' AND (
                    LOWER(coa.accountname) LIKE '%cash%'
                    OR LOWER(coa.accountname) LIKE '%bank%'
                    OR LOWER(coa.accountname) LIKE '%checking%'
                    OR LOWER(coa.accountname) LIKE '%savings%'
                ) THEN 'Cash and Cash Equivalents'
                WHEN coa.accounttype = 'Asset' AND (
                    LOWER(coa.accountname) LIKE '%receivable%'
                    OR LOWER(coa.accountname) LIKE '%accounts rec%'
                    OR LOWER(coa.accountname) LIKE '%trade rec%'
                ) THEN 'Accounts Receivable'
                WHEN coa.accounttype = 'Asset' AND (
                    LOWER(coa.accountname) LIKE '%inventory%'
                    OR LOWER(coa.accountname) LIKE '%stock%'
                    OR LOWER(coa.accountname) LIKE '%merchandise%'
                ) THEN 'Inventory'
                WHEN coa.accounttype = 'Asset' THEN 'Total Assets'
                WHEN coa.accounttype = 'Liability' AND (
                    LOWER(coa.accountname) LIKE '%payable%'
                    OR LOWER(coa.accountname) LIKE '%accounts pay%'
                    OR LOWER(coa.accountname) LIKE '%trade pay%'
                ) THEN 'Accounts Payable'
                WHEN coa.accounttype = 'Liability' AND (
                    LOWER(coa.accountname) LIKE '%current%'
                    OR LOWER(coa.accountname) LIKE '%short%'
                    OR LOWER(coa.accountname) LIKE '%accrued%'
                ) THEN 'Current Liabilities'
                WHEN coa.accounttype = 'Liability' THEN 'Total Liabilities'
                WHEN coa.accounttype = 'Equity' THEN 'Total Equity'
                ELSE coa.accounttype
            END as category
        FROM journalentryline jel
        JOIN glaccount coa ON coa.glaccountid = jel.glaccountid
        JOIN journalentryheader jeh ON jeh.documentnumber = jel.documentnumber 
            AND jeh.companycodeid = jel.companycodeid
        WHERE {' AND '.join(where_conditions)}
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

def calculate_profitability_metrics(pivot_df):
    """Calculate all profitability metrics"""
    
    revenue = pivot_df.get('Revenue', pd.Series([0] * len(pivot_df)))
    cogs = pivot_df.get('Cost of Goods Sold', pd.Series([0] * len(pivot_df)))
    operating_expenses = pivot_df.get('Operating Expenses', pd.Series([0] * len(pivot_df)))
    depreciation = pivot_df.get('Depreciation and Amortization', pd.Series([0] * len(pivot_df)))
    interest_expense = pivot_df.get('Interest Expense', pd.Series([0] * len(pivot_df)))
    income_taxes = pivot_df.get('Income Taxes', pd.Series([0] * len(pivot_df)))
    total_assets = pivot_df.get('Total Assets', pd.Series([0] * len(pivot_df)))
    total_equity = pivot_df.get('Total Equity', pd.Series([0] * len(pivot_df)))
    
    # Calculate key profitability metrics
    gross_profit = revenue - cogs
    pivot_df['Gross Profit'] = gross_profit
    
    # EBIT = Revenue - COGS - Operating Expenses - Depreciation
    ebit = revenue - cogs - operating_expenses - depreciation
    pivot_df['EBIT'] = ebit
    
    # Net Income = EBIT - Interest - Taxes
    net_income = ebit - interest_expense - income_taxes
    pivot_df['Net Income'] = net_income
    
    # Profitability Ratios
    pivot_df['Gross Margin %'] = (gross_profit / revenue * 100).fillna(0)
    pivot_df['Operating Margin %'] = (ebit / revenue * 100).fillna(0)
    pivot_df['Net Profit Margin %'] = (net_income / revenue * 100).fillna(0)
    
    # Calculate average assets and equity for ROA and ROE
    avg_assets = total_assets.rolling(window=2, min_periods=1).mean()
    avg_equity = total_equity.rolling(window=2, min_periods=1).mean()
    
    pivot_df['ROA %'] = (net_income / avg_assets * 100).fillna(0)
    pivot_df['ROE %'] = (net_income / avg_equity * 100).fillna(0)
    
    return pivot_df

companies, years, periods = get_filter_options()

with st.expander("🔍 Filter Options", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🏢 Company")
        selected_companies = st.multiselect("Company Code(s)", ["All"] + companies, default=["All"])
    
    with col2:
        st.subheader("📅 Fiscal Year")
        selected_years = st.multiselect("Fiscal Year(s)", ["All"] + years, default=["All"])
    
    with col3:
        st.subheader("📊 Period")
        selected_periods = st.multiselect("Period(s)", ["All"] + periods, default=["All"])

if st.button("📈 Generate Profitability Analysis", type="primary"):
    with st.spinner("Calculating profitability metrics..."):
        try:
            df = get_profitability_data(selected_companies, selected_years, selected_periods)
            
            if df.empty:
                st.warning("No data found for the selected filters.")
            else:
                pivot_df = df.pivot_table(
                    index=['year_month', 'fiscalyear', 'period'], 
                    columns='category', 
                    values='total_amount', 
                    fill_value=0
                ).reset_index()
                
                pivot_df = calculate_profitability_metrics(pivot_df)
                pivot_df = pivot_df.sort_values(['fiscalyear', 'period'])
                
                st.subheader("📊 Profitability Metrics Overview")
                
                # Key Metrics Dashboard
                col1, col2, col3, col4, col5 = st.columns(5)
                
                latest_period = pivot_df.iloc[-1] if len(pivot_df) > 0 else None
                
                if latest_period is not None:
                    with col1:
                        st.metric("Gross Margin", f"{latest_period['Gross Margin %']:.2f}%")
                    with col2:
                        st.metric("Operating Margin", f"{latest_period['Operating Margin %']:.2f}%")
                    with col3:
                        st.metric("Net Profit Margin", f"{latest_period['Net Profit Margin %']:.2f}%")
                    with col4:
                        st.metric("ROA", f"{latest_period['ROA %']:.2f}%")
                    with col5:
                        st.metric("ROE", f"{latest_period['ROE %']:.2f}%")
                
                # Profitability Trends Chart
                st.subheader("📈 Profitability Trends")
                
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("Margin Analysis (%)", "Return Analysis (%)"),
                    vertical_spacing=0.12
                )
                
                # Margin trends
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Gross Margin %'],
                              mode='lines+markers', name='Gross Margin %',
                              line=dict(color='#1f77b4', width=3)),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Operating Margin %'],
                              mode='lines+markers', name='Operating Margin %',
                              line=dict(color='#ff7f0e', width=3)),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Net Profit Margin %'],
                              mode='lines+markers', name='Net Profit Margin %',
                              line=dict(color='#2ca02c', width=3)),
                    row=1, col=1
                )
                
                # Return analysis
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['ROA %'],
                              mode='lines+markers', name='ROA %',
                              line=dict(color='#d62728', width=3)),
                    row=2, col=1
                )
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['ROE %'],
                              mode='lines+markers', name='ROE %',
                              line=dict(color='#9467bd', width=3)),
                    row=2, col=1
                )
                
                fig.update_layout(height=700, showlegend=True)
                fig.update_xaxes(title_text="Period")
                fig.update_yaxes(title_text="Percentage (%)")
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed Metrics Table
                st.subheader("📊 Detailed Profitability Metrics")
                
                display_df = pivot_df.copy()
                display_columns = ['year_month', 'Revenue', 'Cost of Goods Sold', 'Gross Profit', 
                                 'EBIT', 'Net Income', 'Gross Margin %', 'Operating Margin %', 
                                 'Net Profit Margin %', 'ROA %', 'ROE %']
                
                # Format numeric columns
                for col in ['Revenue', 'Cost of Goods Sold', 'Gross Profit', 'EBIT', 'Net Income']:
                    if col in display_df.columns:
                        display_df[f'{col}_formatted'] = display_df[col].apply(lambda x: f"{x:,.0f}")
                
                for col in ['Gross Margin %', 'Operating Margin %', 'Net Profit Margin %', 'ROA %', 'ROE %']:
                    if col in display_df.columns:
                        display_df[f'{col}_formatted'] = display_df[col].apply(lambda x: f"{x:.2f}%")
                
                final_display_columns = ['year_month']
                final_column_names = ['Year-Month']
                
                for col in ['Revenue', 'Cost of Goods Sold', 'Gross Profit', 'EBIT', 'Net Income']:
                    if col in display_df.columns:
                        final_display_columns.append(f'{col}_formatted')
                        final_column_names.append(col)
                
                for col in ['Gross Margin %', 'Operating Margin %', 'Net Profit Margin %', 'ROA %', 'ROE %']:
                    if col in display_df.columns:
                        final_display_columns.append(f'{col}_formatted')
                        final_column_names.append(col)
                
                if len(final_display_columns) > 1:
                    final_df = display_df[final_display_columns].copy()
                    final_df.columns = final_column_names
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                
                # Summary Statistics
                st.subheader("📋 Summary Statistics")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Average Profitability Metrics:**")
                    avg_gross_margin = pivot_df['Gross Margin %'].mean()
                    avg_operating_margin = pivot_df['Operating Margin %'].mean()
                    avg_net_margin = pivot_df['Net Profit Margin %'].mean()
                    
                    st.write(f"• Average Gross Margin: {avg_gross_margin:.2f}%")
                    st.write(f"• Average Operating Margin: {avg_operating_margin:.2f}%")
                    st.write(f"• Average Net Profit Margin: {avg_net_margin:.2f}%")
                
                with col2:
                    st.markdown("**Average Return Metrics:**")
                    avg_roa = pivot_df['ROA %'].mean()
                    avg_roe = pivot_df['ROE %'].mean()
                    
                    st.write(f"• Average ROA: {avg_roa:.2f}%")
                    st.write(f"• Average ROE: {avg_roe:.2f}%")
                
                # Export functionality
                st.subheader("📤 Export Data")
                csv_data = final_df.to_csv(index=False) if 'final_df' in locals() else pivot_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"Profitability_Metrics_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"Error generating profitability analysis: {str(e)}")

with st.expander("ℹ️ About Profitability Metrics"):
    st.markdown("""
    **Profitability Metrics Analysis** provides insights into company profitability and efficiency.
    
    **Key Metrics:**
    
    **Margin Analysis:**
    - **Gross Margin**: (Revenue - COGS) ÷ Revenue × 100
    - **Operating Margin**: EBIT ÷ Revenue × 100
    - **Net Profit Margin**: Net Income ÷ Revenue × 100
    
    **Return Analysis:**
    - **Return on Assets (ROA)**: Net Income ÷ Average Total Assets × 100
    - **Return on Equity (ROE)**: Net Income ÷ Average Total Equity × 100
    
    **Calculations:**
    - **Gross Profit**: Revenue - Cost of Goods Sold
    - **EBIT**: Revenue - COGS - Operating Expenses - Depreciation & Amortization
    - **Net Income**: EBIT - Interest Expense - Income Taxes
    
    **Use Cases:**
    - Monitor profitability trends over time
    - Compare performance across periods
    - Identify operational efficiency improvements
    - Evaluate management effectiveness (ROA, ROE)
    - Benchmark against industry standards
    """)