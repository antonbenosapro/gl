import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb

st.set_page_config(page_title="💧 Liquidity & Working Capital Metrics", layout="wide", initial_sidebar_state="expanded")

show_sap_sidebar()
show_breadcrumb("Liquidity & Working Capital Metrics", "Financial Reports", "Analytics")

st.title("💧 Liquidity & Working Capital Metrics Analysis")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
    
    return companies, years, periods

def get_liquidity_data(companies, years, periods):
    """Get liquidity and working capital data"""
    
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
                WHEN coa.accounttype = 'Asset' THEN
                    SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0))
                WHEN coa.accounttype = 'Liability' THEN
                    SUM(COALESCE(jel.creditamount, 0) - COALESCE(jel.debitamount, 0))
                ELSE 0
            END as amount,
            CASE 
                -- Revenue for DSO calculation
                WHEN coa.accounttype = 'Revenue' THEN 'Revenue'
                -- Current Assets
                WHEN coa.accounttype = 'Asset' AND (
                    LOWER(coa.accountname) LIKE '%cash%'
                    OR LOWER(coa.accountname) LIKE '%bank%'
                    OR LOWER(coa.accountname) LIKE '%checking%'
                    OR LOWER(coa.accountname) LIKE '%savings%'
                    OR LOWER(coa.accountname) LIKE '%petty cash%'
                ) THEN 'Cash and Cash Equivalents'
                WHEN coa.accounttype = 'Asset' AND (
                    LOWER(coa.accountname) LIKE '%receivable%'
                    OR LOWER(coa.accountname) LIKE '%accounts rec%'
                    OR LOWER(coa.accountname) LIKE '%trade rec%'
                    OR LOWER(coa.accountname) LIKE '%customer%'
                ) THEN 'Accounts Receivable'
                WHEN coa.accounttype = 'Asset' AND (
                    LOWER(coa.accountname) LIKE '%inventory%'
                    OR LOWER(coa.accountname) LIKE '%stock%'
                    OR LOWER(coa.accountname) LIKE '%merchandise%'
                    OR LOWER(coa.accountname) LIKE '%raw materials%'
                    OR LOWER(coa.accountname) LIKE '%finished goods%'
                ) THEN 'Inventory'
                WHEN coa.accounttype = 'Asset' AND (
                    LOWER(coa.accountname) LIKE '%prepaid%'
                    OR LOWER(coa.accountname) LIKE '%short-term invest%'
                    OR LOWER(coa.accountname) LIKE '%marketable securities%'
                    OR LOWER(coa.accountname) LIKE '%current%'
                ) THEN 'Other Current Assets'
                WHEN coa.accounttype = 'Asset' THEN 'Total Assets'
                -- Current Liabilities
                WHEN coa.accounttype = 'Liability' AND (
                    LOWER(coa.accountname) LIKE '%payable%'
                    OR LOWER(coa.accountname) LIKE '%accounts pay%'
                    OR LOWER(coa.accountname) LIKE '%trade pay%'
                    OR LOWER(coa.accountname) LIKE '%vendor%'
                ) THEN 'Accounts Payable'
                WHEN coa.accounttype = 'Liability' AND (
                    LOWER(coa.accountname) LIKE '%accrued%'
                    OR LOWER(coa.accountname) LIKE '%wages payable%'
                    OR LOWER(coa.accountname) LIKE '%salary payable%'
                    OR LOWER(coa.accountname) LIKE '%tax payable%'
                ) THEN 'Accrued Liabilities'
                WHEN coa.accounttype = 'Liability' AND (
                    LOWER(coa.accountname) LIKE '%short-term%'
                    OR LOWER(coa.accountname) LIKE '%current portion%'
                    OR LOWER(coa.accountname) LIKE '%notes payable%'
                    OR LOWER(coa.accountname) LIKE '%credit line%'
                ) THEN 'Short-term Debt'
                WHEN coa.accounttype = 'Liability' AND (
                    LOWER(coa.accountname) LIKE '%current%'
                    OR LOWER(coa.accountname) LIKE '%deferred revenue%'
                    OR LOWER(coa.accountname) LIKE '%unearned%'
                ) THEN 'Other Current Liabilities'
                WHEN coa.accounttype = 'Liability' THEN 'Total Liabilities'
                ELSE 'Other'
            END as category
        FROM journalentryline jel
        JOIN glaccount coa ON coa.glaccountid = jel.glaccountid
        JOIN journalentryheader jeh ON jeh.documentnumber = jel.documentnumber 
            AND jeh.companycodeid = jel.companycodeid
        WHERE {' AND '.join(where_conditions)}
            AND (coa.accounttype IN ('Asset', 'Liability', 'Revenue'))
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

def calculate_liquidity_metrics(pivot_df):
    """Calculate all liquidity and working capital metrics"""
    
    # Current Assets
    cash = pivot_df.get('Cash and Cash Equivalents', pd.Series([0] * len(pivot_df)))
    accounts_receivable = pivot_df.get('Accounts Receivable', pd.Series([0] * len(pivot_df)))
    inventory = pivot_df.get('Inventory', pd.Series([0] * len(pivot_df)))
    other_current_assets = pivot_df.get('Other Current Assets', pd.Series([0] * len(pivot_df)))
    
    current_assets = cash + accounts_receivable + inventory + other_current_assets
    pivot_df['Current Assets'] = current_assets
    
    # Quick Assets (Current Assets - Inventory)
    quick_assets = current_assets - inventory
    pivot_df['Quick Assets'] = quick_assets
    
    # Current Liabilities
    accounts_payable = pivot_df.get('Accounts Payable', pd.Series([0] * len(pivot_df)))
    accrued_liabilities = pivot_df.get('Accrued Liabilities', pd.Series([0] * len(pivot_df)))
    short_term_debt = pivot_df.get('Short-term Debt', pd.Series([0] * len(pivot_df)))
    other_current_liabilities = pivot_df.get('Other Current Liabilities', pd.Series([0] * len(pivot_df)))
    
    current_liabilities = accounts_payable + accrued_liabilities + short_term_debt + other_current_liabilities
    pivot_df['Current Liabilities'] = current_liabilities
    
    # Other metrics
    revenue = pivot_df.get('Revenue', pd.Series([0] * len(pivot_df)))
    total_assets = pivot_df.get('Total Assets', pd.Series([0] * len(pivot_df)))
    
    # Liquidity Ratios
    pivot_df['Current Ratio'] = (current_assets / current_liabilities).replace([float('inf'), float('-inf')], 0).fillna(0)
    pivot_df['Quick Ratio'] = (quick_assets / current_liabilities).replace([float('inf'), float('-inf')], 0).fillna(0)
    
    # Working Capital
    working_capital = current_assets - current_liabilities
    pivot_df['Working Capital'] = working_capital
    
    # Days Sales Outstanding (DSO) - assuming monthly periods
    # DSO = (Accounts Receivable / Revenue) * Days in Period
    days_in_period = 30  # Assuming monthly periods
    pivot_df['Days Sales Outstanding'] = ((accounts_receivable / revenue) * days_in_period).replace([float('inf'), float('-inf')], 0).fillna(0)
    
    # Asset Turnover (Revenue / Average Total Assets)
    avg_total_assets = total_assets.rolling(window=2, min_periods=1).mean()
    pivot_df['Asset Turnover'] = (revenue / avg_total_assets).replace([float('inf'), float('-inf')], 0).fillna(0)
    
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

if st.button("💧 Generate Liquidity Analysis", type="primary"):
    with st.spinner("Calculating liquidity and working capital metrics..."):
        try:
            df = get_liquidity_data(selected_companies, selected_years, selected_periods)
            
            if df.empty:
                st.warning("No data found for the selected filters.")
            else:
                pivot_df = df.pivot_table(
                    index=['year_month', 'fiscalyear', 'period'], 
                    columns='category', 
                    values='total_amount', 
                    fill_value=0
                ).reset_index()
                
                pivot_df = calculate_liquidity_metrics(pivot_df)
                pivot_df = pivot_df.sort_values(['fiscalyear', 'period'])
                
                st.subheader("💧 Liquidity Metrics Overview")
                
                # Key Metrics Dashboard
                col1, col2, col3, col4, col5 = st.columns(5)
                
                latest_period = pivot_df.iloc[-1] if len(pivot_df) > 0 else None
                
                if latest_period is not None:
                    with col1:
                        st.metric("Current Ratio", f"{latest_period['Current Ratio']:.2f}")
                    with col2:
                        st.metric("Quick Ratio", f"{latest_period['Quick Ratio']:.2f}")
                    with col3:
                        st.metric("Working Capital", f"{latest_period['Working Capital']:,.0f}")
                    with col4:
                        st.metric("DSO (Days)", f"{latest_period['Days Sales Outstanding']:.1f}")
                    with col5:
                        st.metric("Asset Turnover", f"{latest_period['Asset Turnover']:.2f}")
                
                # Liquidity Trends Charts
                st.subheader("📈 Liquidity Trends")
                
                fig = make_subplots(
                    rows=2, cols=2,
                    subplot_titles=("Liquidity Ratios", "Working Capital ($)", 
                                  "Days Sales Outstanding", "Asset Turnover"),
                    vertical_spacing=0.12,
                    horizontal_spacing=0.1
                )
                
                # Liquidity Ratios
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Current Ratio'],
                              mode='lines+markers', name='Current Ratio',
                              line=dict(color='#1f77b4', width=3)),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Quick Ratio'],
                              mode='lines+markers', name='Quick Ratio',
                              line=dict(color='#ff7f0e', width=3)),
                    row=1, col=1
                )
                
                # Working Capital
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Working Capital'],
                              mode='lines+markers', name='Working Capital',
                              line=dict(color='#2ca02c', width=3)),
                    row=1, col=2
                )
                
                # Days Sales Outstanding
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Days Sales Outstanding'],
                              mode='lines+markers', name='DSO',
                              line=dict(color='#d62728', width=3)),
                    row=2, col=1
                )
                
                # Asset Turnover
                fig.add_trace(
                    go.Scatter(x=pivot_df['year_month'], y=pivot_df['Asset Turnover'],
                              mode='lines+markers', name='Asset Turnover',
                              line=dict(color='#9467bd', width=3)),
                    row=2, col=2
                )
                
                fig.update_layout(height=700, showlegend=False)
                fig.update_xaxes(title_text="Period")
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Working Capital Composition Chart
                st.subheader("🔍 Working Capital Composition")
                
                fig2 = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=("Current Assets Breakdown", "Current Liabilities Breakdown"),
                    specs=[[{"type": "domain"}, {"type": "domain"}]]
                )
                
                # Current Assets Pie Chart (latest period)
                if latest_period is not None:
                    assets_data = [
                        latest_period.get('Cash and Cash Equivalents', 0),
                        latest_period.get('Accounts Receivable', 0),
                        latest_period.get('Inventory', 0),
                        latest_period.get('Other Current Assets', 0)
                    ]
                    assets_labels = ['Cash & Equivalents', 'Accounts Receivable', 'Inventory', 'Other Current Assets']
                    
                    fig2.add_trace(
                        go.Pie(values=assets_data, labels=assets_labels, name="Current Assets"),
                        row=1, col=1
                    )
                    
                    # Current Liabilities Pie Chart
                    liabilities_data = [
                        latest_period.get('Accounts Payable', 0),
                        latest_period.get('Accrued Liabilities', 0),
                        latest_period.get('Short-term Debt', 0),
                        latest_period.get('Other Current Liabilities', 0)
                    ]
                    liabilities_labels = ['Accounts Payable', 'Accrued Liabilities', 'Short-term Debt', 'Other Current Liabilities']
                    
                    fig2.add_trace(
                        go.Pie(values=liabilities_data, labels=liabilities_labels, name="Current Liabilities"),
                        row=1, col=2
                    )
                
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
                
                # Detailed Metrics Table
                st.subheader("📊 Detailed Liquidity Metrics")
                
                display_df = pivot_df.copy()
                
                # Format monetary columns
                monetary_columns = ['Current Assets', 'Current Liabilities', 'Working Capital', 
                                  'Cash and Cash Equivalents', 'Accounts Receivable', 'Inventory']
                for col in monetary_columns:
                    if col in display_df.columns:
                        display_df[f'{col}_formatted'] = display_df[col].apply(lambda x: f"{x:,.0f}")
                
                # Format ratio columns
                ratio_columns = ['Current Ratio', 'Quick Ratio', 'Asset Turnover']
                for col in ratio_columns:
                    if col in display_df.columns:
                        display_df[f'{col}_formatted'] = display_df[col].apply(lambda x: f"{x:.2f}")
                
                # Format DSO
                if 'Days Sales Outstanding' in display_df.columns:
                    display_df['DSO_formatted'] = display_df['Days Sales Outstanding'].apply(lambda x: f"{x:.1f}")
                
                final_display_columns = ['year_month']
                final_column_names = ['Year-Month']
                
                # Add key liquidity metrics
                key_columns = [
                    ('Current Assets', 'Current Assets'),
                    ('Current Liabilities', 'Current Liabilities'),
                    ('Working Capital', 'Working Capital'),
                    ('Current Ratio', 'Current Ratio'),
                    ('Quick Ratio', 'Quick Ratio'),
                    ('DSO_formatted', 'DSO (Days)'),
                    ('Asset Turnover', 'Asset Turnover')
                ]
                
                for col_key, col_name in key_columns:
                    if col_key in display_df.columns:
                        final_display_columns.append(col_key)
                        final_column_names.append(col_name)
                    elif f'{col_key}_formatted' in display_df.columns:
                        final_display_columns.append(f'{col_key}_formatted')
                        final_column_names.append(col_name)
                
                if len(final_display_columns) > 1:
                    final_df = display_df[final_display_columns].copy()
                    final_df.columns = final_column_names
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                
                # Liquidity Analysis Summary
                st.subheader("📋 Liquidity Analysis Summary")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Average Liquidity Ratios:**")
                    avg_current_ratio = pivot_df['Current Ratio'].mean()
                    avg_quick_ratio = pivot_df['Quick Ratio'].mean()
                    avg_asset_turnover = pivot_df['Asset Turnover'].mean()
                    
                    st.write(f"• Average Current Ratio: {avg_current_ratio:.2f}")
                    st.write(f"• Average Quick Ratio: {avg_quick_ratio:.2f}")
                    st.write(f"• Average Asset Turnover: {avg_asset_turnover:.2f}")
                    
                    # Liquidity Health Assessment
                    st.markdown("**Liquidity Health Assessment:**")
                    if avg_current_ratio >= 2.0:
                        st.success("• Strong liquidity position")
                    elif avg_current_ratio >= 1.5:
                        st.info("• Adequate liquidity position")
                    elif avg_current_ratio >= 1.0:
                        st.warning("• Moderate liquidity concerns")
                    else:
                        st.error("• Potential liquidity issues")
                
                with col2:
                    st.markdown("**Working Capital Analysis:**")
                    avg_working_capital = pivot_df['Working Capital'].mean()
                    avg_dso = pivot_df['Days Sales Outstanding'].mean()
                    
                    st.write(f"• Average Working Capital: ${avg_working_capital:,.0f}")
                    st.write(f"• Average DSO: {avg_dso:.1f} days")
                    
                    # DSO Assessment
                    st.markdown("**Collection Efficiency:**")
                    if avg_dso <= 30:
                        st.success("• Excellent collection efficiency")
                    elif avg_dso <= 45:
                        st.info("• Good collection efficiency")
                    elif avg_dso <= 60:
                        st.warning("• Moderate collection concerns")
                    else:
                        st.error("• Collection efficiency issues")
                
                # Export functionality
                st.subheader("📤 Export Data")
                csv_data = final_df.to_csv(index=False) if 'final_df' in locals() else pivot_df.to_csv(index=False)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"Liquidity_Working_Capital_Metrics_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"Error generating liquidity analysis: {str(e)}")

with st.expander("ℹ️ About Liquidity & Working Capital Metrics"):
    st.markdown("""
    **Liquidity & Working Capital Metrics** analyze the company's ability to meet short-term obligations and manage cash flow.
    
    **Key Metrics:**
    
    **Liquidity Ratios:**
    - **Current Ratio**: Current Assets ÷ Current Liabilities
    - **Quick Ratio**: (Current Assets - Inventory) ÷ Current Liabilities
    
    **Working Capital Metrics:**
    - **Working Capital**: Current Assets - Current Liabilities
    - **Days Sales Outstanding (DSO)**: (Accounts Receivable ÷ Revenue) × 30 days
    - **Asset Turnover**: Revenue ÷ Average Total Assets
    
    **Components:**
    
    **Current Assets:**
    - Cash and Cash Equivalents
    - Accounts Receivable  
    - Inventory
    - Other Current Assets (prepaid expenses, short-term investments)
    
    **Current Liabilities:**
    - Accounts Payable
    - Accrued Liabilities
    - Short-term Debt
    - Other Current Liabilities
    
    **Interpretation Guidelines:**
    - **Current Ratio**: > 2.0 (Strong), 1.5-2.0 (Adequate), 1.0-1.5 (Moderate), < 1.0 (Concern)
    - **Quick Ratio**: > 1.0 (Good), 0.8-1.0 (Adequate), < 0.8 (Concern)
    - **DSO**: < 30 days (Excellent), 30-45 (Good), 45-60 (Moderate), > 60 (Concern)
    
    **Use Cases:**
    - Assess short-term financial health
    - Monitor cash conversion cycle
    - Evaluate collection efficiency
    - Plan for working capital needs
    - Compare with industry benchmarks
    """)