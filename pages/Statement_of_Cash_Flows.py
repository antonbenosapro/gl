import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb
from utils.pdf_generator import generate_cash_flow_statement_pdf

# Configure page
st.set_page_config(page_title="💧 Statement of Cash Flows", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Statement of Cash Flows", "Financial Reports", "Core Statements")

st.title("💧 Statement of Cash Flows")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
        cash_accounts = [row[0] for row in conn.execute(text("SELECT DISTINCT glaccountid FROM glaccount WHERE accounttype = 'Asset' AND (accountname ILIKE '%cash%' OR accountname ILIKE '%bank%') ORDER BY glaccountid")).fetchall() if row[0]]
    
    return companies, years, periods, cash_accounts

# Get filter options
companies, years, periods, cash_accounts = get_filter_options()

# Filter Section
with st.expander("🔍 Filter Options", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📅 Date Range")
        date_from = st.date_input("From Date", value=date(2025, 1, 1), key="date_from")
        date_to = st.date_input("To Date", value=date.today(), key="date_to")
        
        st.subheader("🏢 Company")
        selected_companies = st.multiselect("Company Code(s)", ["All"] + companies, default=["All"])
    
    with col2:
        st.subheader("📊 Period")
        selected_years = st.multiselect("Fiscal Year(s)", ["All"] + years, default=["All"])
        selected_periods = st.multiselect("Period(s)", ["All"] + periods, default=["All"])
        
        st.subheader("💰 Cash Accounts")
        selected_cash_accounts = st.multiselect("Cash Account(s)", ["All"] + cash_accounts, default=["All"])
    
    with col3:
        st.subheader("⚙️ Report Options")
        cash_flow_method = st.selectbox("Cash Flow Method", ["Direct Method", "Indirect Method"], index=0)
        show_zero_amounts = st.checkbox("Show Zero Amounts", value=False)
        show_account_details = st.checkbox("Show Account Details", value=True)
        amount_threshold = st.number_input("Minimum Amount Threshold", value=0.01, step=0.01, format="%.2f")
        
        st.subheader("📋 Categorization")
        auto_categorize = st.checkbox("Auto-categorize by Account Type", value=True, help="Automatically categorize accounts into Operating, Investing, and Financing activities")

# Run Report Button
if st.button("💧 Generate Cash Flow Statement", type="primary"):
    # Process filter selections
    if "All" in selected_companies:
        selected_companies = companies
    if "All" in selected_years:
        selected_years = years
    if "All" in selected_periods:
        selected_periods = periods
    if "All" in selected_cash_accounts:
        selected_cash_accounts = cash_accounts
    
    # Validate filters
    if not (selected_companies and date_from and date_to):
        st.error("⚠️ Please ensure Company Code(s) and date range are provided.")
        st.stop()
    
    # Build query for cash flow analysis
    where_conditions = ["jeh.documentdate BETWEEN :date_from AND :date_to"]
    params = {"date_from": date_from, "date_to": date_to}
    
    if selected_companies:
        comp_ph = ", ".join([f":comp{i}" for i in range(len(selected_companies))])
        where_conditions.append(f"jeh.companycodeid IN ({comp_ph})")
        params.update({f"comp{i}": v for i, v in enumerate(selected_companies)})
    
    if selected_years:
        year_ph = ", ".join([f":year{i}" for i in range(len(selected_years))])
        where_conditions.append(f"jeh.fiscalyear IN ({year_ph})")
        params.update({f"year{i}": v for i, v in enumerate(selected_years)})
    
    if selected_periods:
        period_ph = ", ".join([f":period{i}" for i in range(len(selected_periods))])
        where_conditions.append(f"jeh.period IN ({period_ph})")
        params.update({f"period{i}": v for i, v in enumerate(selected_periods)})
    
    # Enhanced cash flow query with proper categorization
    if cash_flow_method == "Direct Method":
        # Direct method - analyze actual cash receipts and payments
        query = f"""
        SELECT 
            coa.glaccountid,
            coa.accountname,
            coa.accounttype,
            SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0)) AS net_change,
            CASE 
                WHEN coa.accounttype = 'Asset' AND (coa.accountname ILIKE '%cash%' OR coa.accountname ILIKE '%bank%') THEN 'Cash and Cash Equivalents'
                WHEN coa.accounttype = 'Revenue' THEN 'Operating Activities'
                WHEN coa.accounttype = 'Expense' AND coa.accountname NOT ILIKE '%depreciation%' THEN 'Operating Activities'
                WHEN coa.accounttype = 'Asset' AND coa.accountname ILIKE '%equipment%' THEN 'Investing Activities'
                WHEN coa.accounttype = 'Asset' AND coa.accountname ILIKE '%property%' THEN 'Investing Activities'
                WHEN coa.accounttype = 'Asset' AND coa.accountname ILIKE '%investment%' THEN 'Investing Activities'
                WHEN coa.accounttype = 'Liability' AND coa.accountname ILIKE '%loan%' THEN 'Financing Activities'
                WHEN coa.accounttype = 'Liability' AND coa.accountname ILIKE '%debt%' THEN 'Financing Activities'
                WHEN coa.accounttype = 'Equity' THEN 'Financing Activities'
                ELSE 'Operating Activities'
            END AS cash_flow_category,
            COUNT(*) as transaction_count
        FROM 
            journalentryline jel
        JOIN 
            glaccount coa ON coa.glaccountid = jel.glaccountid
        JOIN 
            journalentryheader jeh ON jeh.documentnumber = jel.documentnumber
        WHERE 
            {' AND '.join(where_conditions)}
        GROUP BY 
            coa.glaccountid, coa.accountname, coa.accounttype
        HAVING 
            {'ABS(SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0))) >= :threshold' if not show_zero_amounts else 'TRUE'}
        ORDER BY 
            cash_flow_category, coa.accounttype, coa.glaccountid
        """
    else:
        # Indirect method - start with net income and adjust
        query = f"""
        WITH net_income AS (
            SELECT 
                SUM(COALESCE(jel.creditamount, 0) - COALESCE(jel.debitamount, 0)) AS net_income_amount
            FROM journalentryline jel
            JOIN glaccount coa ON coa.glaccountid = jel.glaccountid
            JOIN journalentryheader jeh ON jeh.documentnumber = jel.documentnumber
            WHERE {' AND '.join(where_conditions)}
            AND coa.accounttype IN ('Revenue', 'Expense')
        )
        SELECT 
            coa.glaccountid,
            coa.accountname,
            coa.accounttype,
            SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0)) AS net_change,
            CASE 
                WHEN coa.accounttype = 'Asset' AND (coa.accountname ILIKE '%cash%' OR coa.accountname ILIKE '%bank%') THEN 'Cash and Cash Equivalents'
                WHEN coa.accounttype IN ('Revenue', 'Expense') THEN 'Net Income Adjustment'
                WHEN coa.accounttype = 'Asset' AND coa.accountname NOT ILIKE '%cash%' AND coa.accountname NOT ILIKE '%bank%' THEN 'Operating Activities'
                WHEN coa.accounttype = 'Liability' AND coa.accountname NOT ILIKE '%loan%' AND coa.accountname NOT ILIKE '%debt%' THEN 'Operating Activities'
                WHEN coa.accounttype = 'Asset' AND (coa.accountname ILIKE '%equipment%' OR coa.accountname ILIKE '%property%') THEN 'Investing Activities'
                WHEN coa.accounttype = 'Liability' AND (coa.accountname ILIKE '%loan%' OR coa.accountname ILIKE '%debt%') THEN 'Financing Activities'
                WHEN coa.accounttype = 'Equity' THEN 'Financing Activities'
                ELSE 'Operating Activities'
            END AS cash_flow_category,
            COUNT(*) as transaction_count
        FROM 
            journalentryline jel
        JOIN 
            glaccount coa ON coa.glaccountid = jel.glaccountid
        JOIN 
            journalentryheader jeh ON jeh.documentnumber = jel.documentnumber
        WHERE 
            {' AND '.join(where_conditions)}
        GROUP BY 
            coa.glaccountid, coa.accountname, coa.accounttype
        HAVING 
            {'ABS(SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0))) >= :threshold' if not show_zero_amounts else 'TRUE'}
        ORDER BY 
            cash_flow_category, coa.accounttype, coa.glaccountid
        """
    
    if not show_zero_amounts:
        params["threshold"] = amount_threshold
    
    # Execute query
    with st.spinner("Generating Cash Flow Statement..."):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            if df.empty:
                st.warning("No records found with the selected filters.")
            else:
                st.subheader(f"💧 Statement of Cash Flows - {cash_flow_method}")
                st.caption(f"For the period from {date_from.strftime('%B %d, %Y')} to {date_to.strftime('%B %d, %Y')} | {len(df)} accounts")
                
                # Format amount column
                df['amount_formatted'] = df['net_change'].apply(lambda x: f"{x:,.2f}")
                
                # Group by cash flow categories
                categories = df['cash_flow_category'].unique()
                
                total_operating = 0
                total_investing = 0
                total_financing = 0
                total_cash_change = 0
                
                for category in sorted(categories):
                    category_data = df[df['cash_flow_category'] == category].copy()
                    category_total = category_data['net_change'].sum()
                    
                    # Update totals
                    if 'Operating' in category:
                        total_operating += category_total
                    elif 'Investing' in category:
                        total_investing += category_total
                    elif 'Financing' in category:
                        total_financing += category_total
                    elif 'Cash and Cash Equivalents' in category:
                        total_cash_change += category_total
                    
                    # Display category
                    if category == 'Cash and Cash Equivalents':
                        st.subheader(f"💰 {category}")
                    elif 'Operating' in category:
                        st.subheader(f"🔄 {category}")
                    elif 'Investing' in category:
                        st.subheader(f"📈 {category}")
                    elif 'Financing' in category:
                        st.subheader(f"🏦 {category}")
                    else:
                        st.subheader(f"📋 {category}")
                    
                    if show_account_details:
                        # Show detailed accounts
                        display_df = category_data[['glaccountid', 'accountname', 'amount_formatted', 'transaction_count']].copy()
                        display_df.columns = ['Account ID', 'Account Name', 'Net Change', 'Transactions']
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    st.markdown(f"**{category} Total: {category_total:,.2f}**")
                    st.markdown("---")
                
                # Cash Flow Summary
                st.subheader("📊 Cash Flow Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Operating Activities", f"{total_operating:,.2f}")
                with col2:
                    st.metric("Investing Activities", f"{total_investing:,.2f}")
                with col3:
                    st.metric("Financing Activities", f"{total_financing:,.2f}")
                with col4:
                    net_cash_flow = total_operating + total_investing + total_financing
                    st.metric("Net Cash Flow", f"{net_cash_flow:,.2f}", 
                            delta=f"{'Positive' if net_cash_flow >= 0 else 'Negative'}")
                
                # Cash flow analysis
                st.subheader("📈 Cash Flow Analysis")
                
                col1, col2 = st.columns(2)
                with col1:
                    # Cash flow ratios
                    if total_operating != 0:
                        operating_ratio = abs(total_investing) / abs(total_operating) if total_operating != 0 else 0
                        st.metric("Investment Ratio", f"{operating_ratio:.2f}", help="Investing Activities / Operating Activities")
                    
                    free_cash_flow = total_operating + total_investing
                    st.metric("Free Cash Flow", f"{free_cash_flow:,.2f}", help="Operating + Investing Activities")
                
                with col2:
                    # Cash flow quality indicators
                    total_transactions = df['transaction_count'].sum()
                    st.metric("Total Transactions", f"{total_transactions:,}")
                    
                    if total_cash_change != 0:
                        cash_efficiency = net_cash_flow / total_cash_change if total_cash_change != 0 else 0
                        st.metric("Cash Efficiency", f"{cash_efficiency:.2f}", help="Net Cash Flow / Cash Account Changes")
                
                # Export options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Export detailed data
                        export_df = df[['glaccountid', 'accountname', 'accounttype', 'cash_flow_category', 'net_change', 'transaction_count']].copy()
                        export_df.to_excel(writer, index=False, sheet_name='Cash_Flow_Statement')
                        
                        workbook = writer.book
                        worksheet = writer.sheets['Cash_Flow_Statement']
                        
                        # Format columns
                        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
                        bold_fmt = workbook.add_format({'bold': True})
                        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
                        
                        worksheet.set_column('A:A', 12, bold_fmt)  # Account ID
                        worksheet.set_column('B:B', 30)           # Account Name
                        worksheet.set_column('C:C', 15)           # Account Type
                        worksheet.set_column('D:D', 20)           # Category
                        worksheet.set_column('E:E', 15, currency_fmt)  # Net Change
                        worksheet.set_column('F:F', 12)           # Transaction Count
                        
                        # Add summary
                        summary_data = [
                            ['CASH FLOW SUMMARY', '', '', '', '', ''],
                            ['Operating Activities', '', '', '', total_operating, ''],
                            ['Investing Activities', '', '', '', total_investing, ''],
                            ['Financing Activities', '', '', '', total_financing, ''],
                            ['Net Cash Flow', '', '', '', net_cash_flow, ''],
                            ['Free Cash Flow', '', '', '', free_cash_flow, '']
                        ]
                        
                        start_row = len(export_df) + 2
                        for i, row in enumerate(summary_data):
                            fmt = header_fmt if i == 0 else bold_fmt if row[0] else None
                            worksheet.write_row(start_row + i, 0, row, fmt)
                    
                    st.download_button(
                        label="📤 Download Excel",
                        data=output.getvalue(),
                        file_name=f"Cash_Flow_Statement_{date_to.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # PDF export
                    if st.button("📄 Generate PDF"):
                        try:
                            # Prepare data for PDF
                            pdf_df = df[['glaccountid', 'accountname', 'cash_flow_category', 'net_change', 'transaction_count']].copy()
                            pdf_df.columns = ['Account ID', 'Account Name', 'Category', 'Net Change', 'Transactions']
                            
                            # Prepare filters for PDF
                            pdf_filters = {
                                'date_from': date_from,
                                'date_to': date_to,
                                'companies': selected_companies,
                                'fiscal_years': selected_years,
                                'cash_flow_method': cash_flow_method
                            }
                            
                            # Prepare summary data
                            summary_data = {
                                'Operating Activities': total_operating,
                                'Investing Activities': total_investing,
                                'Financing Activities': total_financing,
                                'Net Cash Flow': net_cash_flow,
                                'Free Cash Flow': free_cash_flow
                            }
                            
                            # Add additional metrics
                            if total_operating != 0:
                                operating_ratio = abs(total_investing) / abs(total_operating)
                                summary_data['Investment Ratio'] = operating_ratio
                            
                            if total_cash_change != 0:
                                cash_efficiency = net_cash_flow / total_cash_change
                                summary_data['Cash Efficiency'] = cash_efficiency
                            
                            summary_data['Total Transactions'] = df['transaction_count'].sum()
                            summary_data['Method Used'] = cash_flow_method
                            
                            # Generate PDF
                            result, file_type = generate_cash_flow_statement_pdf(
                                pdf_df, pdf_filters, summary_data, cash_flow_method
                            )
                            
                            if file_type == 'pdf':
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=result,
                                    file_name=f"Cash_Flow_Statement_{date_to.strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf"
                                )
                                st.success("PDF generated successfully!")
                            else:  # HTML fallback
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=result,
                                    file_name=f"Cash_Flow_Statement_{date_to.strftime('%Y%m%d')}.html",
                                    mime="text/html"
                                )
                                st.info("Downloaded as HTML file (print using browser)")
                                
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                
                with col3:
                    # CSV export
                    csv_df = df[['glaccountid', 'accountname', 'accounttype', 'cash_flow_category', 'net_change', 'transaction_count']].copy()
                    csv = csv_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"Cash_Flow_Statement_{date_to.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
        except Exception as e:
            st.error(f"Error generating Cash Flow Statement: {str(e)}")

# Information panel
with st.expander("ℹ️ About Statement of Cash Flows"):
    st.markdown("""
    **Statement of Cash Flows** shows how cash and cash equivalents moved during a specific period.
    
    **Three Categories of Cash Flow:**
    - **Operating Activities**: Cash flows from primary business operations (sales, purchases, operating expenses)
    - **Investing Activities**: Cash flows from buying/selling long-term assets (equipment, property, investments)
    - **Financing Activities**: Cash flows from borrowing, repaying debt, issuing equity, paying dividends
    
    **Two Methods:**
    - **Direct Method**: Reports actual cash receipts and payments by category
    - **Indirect Method**: Starts with net income and adjusts for non-cash items
    
    **Key Metrics:**
    - **Free Cash Flow**: Operating Activities + Investing Activities
    - **Investment Ratio**: Shows how much investing activities consume relative to operations
    - **Cash Efficiency**: How well the company converts net income to cash flow
    
    **Auto-categorization Rules:**
    - Revenue/Expense accounts → Operating Activities
    - Asset accounts (equipment, property) → Investing Activities  
    - Loan/Debt accounts → Financing Activities
    - Equity accounts → Financing Activities
    - Cash/Bank accounts → Cash and Cash Equivalents
    """)

# Navigation is now handled by the SAP-style sidebar
