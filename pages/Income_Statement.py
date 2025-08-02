import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb
from utils.pdf_generator import generate_income_statement_pdf

# Configure page
st.set_page_config(page_title="📈 Income Statement", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Income Statement", "Financial Reports", "Core Statements")

st.title("📈 Income Statement")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
        account_types = [row[0] for row in conn.execute(text("SELECT DISTINCT accounttype FROM glaccount WHERE accounttype IN ('Revenue', 'Expense') ORDER BY accounttype")).fetchall() if row[0]]
    
    return companies, years, periods, account_types

# Get filter options
companies, years, periods, account_types = get_filter_options()

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
        
        st.subheader("📋 Account Types")
        selected_account_types = st.multiselect("Account Type(s)", ["All"] + account_types, default=["All"])
    
    with col3:
        st.subheader("⚙️ Report Options")
        show_zero_amounts = st.checkbox("Show Zero Amounts", value=False)
        group_by_type = st.checkbox("Group by Account Type", value=True)
        show_subtotals = st.checkbox("Show Subtotals", value=True)
        amount_threshold = st.number_input("Minimum Amount Threshold", value=0.01, step=0.01, format="%.2f")
        
        st.subheader("📊 Analysis Options")
        compare_previous_period = st.checkbox("Compare with Previous Period", value=False)
        show_percentages = st.checkbox("Show % of Revenue", value=True)

# Run Report Button
if st.button("📈 Generate Income Statement", type="primary"):
    # Process filter selections
    if "All" in selected_companies:
        selected_companies = companies
    if "All" in selected_years:
        selected_years = years
    if "All" in selected_periods:
        selected_periods = periods
    if "All" in selected_account_types:
        selected_account_types = account_types
    
    # Validate filters
    if not (selected_companies and date_from and date_to):
        st.error("⚠️ Please ensure Company Code(s) and date range are provided.")
        st.stop()
    
    # Build query
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
    
    if selected_account_types:
        type_ph = ", ".join([f":type{i}" for i in range(len(selected_account_types))])
        where_conditions.append(f"coa.accounttype IN ({type_ph})")
        params.update({f"type{i}": v for i, v in enumerate(selected_account_types)})
    else:
        where_conditions.append("coa.accounttype IN ('Revenue', 'Expense')")
    
    query = f"""
    SELECT 
        coa.glaccountid,
        coa.accountname,
        coa.accounttype,
        SUM(COALESCE(jel.creditamount, 0) - COALESCE(jel.debitamount, 0)) AS net_amount
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
        {'ABS(SUM(COALESCE(jel.creditamount, 0) - COALESCE(jel.debitamount, 0))) >= :threshold' if not show_zero_amounts else 'TRUE'}
    ORDER BY 
        coa.accounttype DESC, coa.glaccountid
    """
    
    if not show_zero_amounts:
        params["threshold"] = amount_threshold
    
    # Execute query
    with st.spinner("Generating Income Statement..."):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            if df.empty:
                st.warning("No records found with the selected filters.")
            else:
                st.subheader(f"📈 Income Statement Results")
                st.caption(f"For the period from {date_from.strftime('%B %d, %Y')} to {date_to.strftime('%B %d, %Y')} | {len(df)} accounts")
                
                # Format amount column
                df['amount_formatted'] = df['net_amount'].apply(lambda x: f"{x:,.2f}")
                
                if group_by_type:
                    # Group by account type and show subtotals
                    total_revenue = 0
                    total_expenses = 0
                    
                    # Process Revenue first
                    revenue_data = df[df['accounttype'] == 'Revenue'].copy()
                    if not revenue_data.empty:
                        total_revenue = revenue_data['net_amount'].sum()
                        
                        st.subheader("💰 Revenue")
                        display_df = revenue_data[['glaccountid', 'accountname', 'amount_formatted']].copy()
                        display_df.columns = ['Account ID', 'Account Name', 'Amount']
                        
                        # Add percentage of total revenue if showing percentages
                        if show_percentages and total_revenue != 0:
                            revenue_data['percentage'] = (revenue_data['net_amount'] / total_revenue * 100).round(2)
                            display_df['% of Revenue'] = revenue_data['percentage'].apply(lambda x: f"{x:.1f}%")
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        if show_subtotals:
                            st.markdown(f"**Total Revenue: {total_revenue:,.2f}**")
                        
                        st.markdown("---")
                    
                    # Process Expenses
                    expense_data = df[df['accounttype'] == 'Expense'].copy()
                    if not expense_data.empty:
                        total_expenses = expense_data['net_amount'].sum()
                        
                        st.subheader("💸 Expenses")
                        display_df = expense_data[['glaccountid', 'accountname', 'amount_formatted']].copy()
                        display_df.columns = ['Account ID', 'Account Name', 'Amount']
                        
                        # Add percentage of total revenue if showing percentages
                        if show_percentages and total_revenue != 0:
                            expense_data['percentage'] = (expense_data['net_amount'] / total_revenue * 100).round(2)
                            display_df['% of Revenue'] = expense_data['percentage'].apply(lambda x: f"{x:.1f}%")
                        
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        if show_subtotals:
                            st.markdown(f"**Total Expenses: {total_expenses:,.2f}**")
                        
                        st.markdown("---")
                    
                    # Income Statement Summary
                    st.subheader("📊 Income Statement Summary")
                    
                    net_income = total_revenue - total_expenses
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Revenue", f"{total_revenue:,.2f}")
                    with col2:
                        st.metric("Total Expenses", f"{total_expenses:,.2f}")
                    with col3:
                        delta_color = "normal" if net_income >= 0 else "inverse"
                        st.metric("Net Income", f"{net_income:,.2f}", 
                                delta=f"{'Profit' if net_income >= 0 else 'Loss'}")
                    
                    # Profitability ratios
                    if total_revenue != 0:
                        st.subheader("📈 Profitability Analysis")
                        
                        gross_margin = (net_income / total_revenue) * 100
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Net Margin", f"{gross_margin:.2f}%")
                        with col2:
                            if total_expenses != 0:
                                expense_ratio = (total_expenses / total_revenue) * 100
                                st.metric("Expense Ratio", f"{expense_ratio:.2f}%")
                        with col3:
                            revenue_per_account = total_revenue / len(revenue_data) if not revenue_data.empty else 0
                            st.metric("Avg Revenue/Account", f"{revenue_per_account:,.2f}")
                
                else:
                    # Show all accounts in one table
                    display_df = df[['glaccountid', 'accountname', 'accounttype', 'amount_formatted']].copy()
                    display_df.columns = ['Account ID', 'Account Name', 'Account Type', 'Amount']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Export options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Export detailed data
                        export_df = df[['glaccountid', 'accountname', 'accounttype', 'net_amount']].copy()
                        export_df.to_excel(writer, index=False, sheet_name='Income_Statement')
                        
                        workbook = writer.book
                        worksheet = writer.sheets['Income_Statement']
                        
                        # Format columns
                        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
                        bold_fmt = workbook.add_format({'bold': True})
                        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
                        
                        worksheet.set_column('A:A', 12, bold_fmt)  # Account ID
                        worksheet.set_column('B:B', 30)           # Account Name
                        worksheet.set_column('C:C', 15)           # Account Type
                        worksheet.set_column('D:D', 15, currency_fmt)  # Amount
                        
                        # Add summary if grouped
                        if group_by_type:
                            summary_data = [
                                ['INCOME STATEMENT SUMMARY', '', '', ''],
                                ['Total Revenue', '', '', total_revenue],
                                ['Total Expenses', '', '', total_expenses],
                                ['Net Income', '', '', net_income],
                                ['', '', '', ''],
                                ['Net Margin %', '', '', gross_margin if total_revenue != 0 else 0]
                            ]
                            
                            start_row = len(export_df) + 2
                            for i, row in enumerate(summary_data):
                                fmt = header_fmt if i == 0 else bold_fmt if row[0] else None
                                worksheet.write_row(start_row + i, 0, row, fmt)
                    
                    st.download_button(
                        label="📤 Download Excel",
                        data=output.getvalue(),
                        file_name=f"Income_Statement_{date_to.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # PDF export
                    if st.button("📄 Generate PDF"):
                        try:
                            # Prepare data for PDF
                            pdf_df = df[['glaccountid', 'accountname', 'accounttype', 'net_amount']].copy()
                            pdf_df.columns = ['Account ID', 'Account Name', 'Account Type', 'Amount']
                            
                            # Add percentage column if showing percentages
                            if show_percentages and group_by_type:
                                revenue_data = df[df['accounttype'] == 'Revenue']
                                expense_data = df[df['accounttype'] == 'Expense']
                                total_revenue = revenue_data['net_amount'].sum() if not revenue_data.empty else 0
                                
                                percentages = []
                                for _, row in df.iterrows():
                                    if total_revenue != 0:
                                        pct = (row['net_amount'] / total_revenue * 100)
                                        percentages.append(f"{pct:.1f}%")
                                    else:
                                        percentages.append("0.0%")
                                
                                pdf_df['% of Revenue'] = percentages
                            
                            # Prepare filters for PDF
                            pdf_filters = {
                                'date_from': date_from,
                                'date_to': date_to,
                                'companies': selected_companies,
                                'fiscal_years': selected_years
                            }
                            
                            # Prepare summary data
                            summary_data = {
                                'Total Revenue': total_revenue,
                                'Total Expenses': total_expenses,
                                'Net Income': net_income
                            }
                            
                            if total_revenue != 0:
                                summary_data['Net Margin %'] = gross_margin
                                if total_expenses != 0:
                                    summary_data['Expense Ratio %'] = (total_expenses / total_revenue) * 100
                            
                            # Generate PDF
                            result, file_type = generate_income_statement_pdf(pdf_df, pdf_filters, summary_data)
                            
                            if file_type == 'pdf':
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=result,
                                    file_name=f"Income_Statement_{date_to.strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf"
                                )
                                st.success("PDF generated successfully!")
                            else:  # HTML fallback
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=result,
                                    file_name=f"Income_Statement_{date_to.strftime('%Y%m%d')}.html",
                                    mime="text/html"
                                )
                                st.info("Downloaded as HTML file (print using browser)")
                                
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                
                with col3:
                    # CSV export
                    csv_df = df[['glaccountid', 'accountname', 'accounttype', 'net_amount']].copy()
                    csv = csv_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"Income_Statement_{date_to.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
        except Exception as e:
            st.error(f"Error generating Income Statement: {str(e)}")

# Information panel
with st.expander("ℹ️ About Income Statement"):
    st.markdown("""
    **Income Statement** shows the company's financial performance over a specific period.
    
    **Formula:** Net Income = Revenue - Expenses
    
    **Account Types:**
    - **Revenue**: Income generated from business operations (Sales, Service Revenue, etc.)
    - **Expenses**: Costs incurred in generating revenue (Cost of Goods Sold, Operating Expenses, etc.)
    
    **Key Metrics:**
    - **Net Margin**: Net Income ÷ Total Revenue × 100
    - **Expense Ratio**: Total Expenses ÷ Total Revenue × 100
    - **% of Revenue**: Each line item as a percentage of total revenue
    
    **Note:** In this system:
    - Revenue accounts typically have Credit balances (shown as positive amounts)
    - Expense accounts typically have Debit balances (shown as positive amounts)
    - Net amounts are calculated as Credits minus Debits
    """)

# Navigation is now handled by the SAP-style sidebar
