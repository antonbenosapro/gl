import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from datetime import date
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb
from utils.pdf_generator import generate_balance_sheet_pdf

# Configure page
st.set_page_config(page_title="📊 Balance Sheet", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Balance Sheet", "Financial Reports", "Core Statements")

st.title("📊 Balance Sheet")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
        account_types = [row[0] for row in conn.execute(text("SELECT DISTINCT accounttype FROM glaccount WHERE accounttype IN ('Asset', 'Liability', 'Equity') ORDER BY accounttype")).fetchall() if row[0]]
    
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
        show_zero_balances = st.checkbox("Show Zero Balances", value=False)
        group_by_type = st.checkbox("Group by Account Type", value=True)
        show_subtotals = st.checkbox("Show Subtotals", value=True)
        balance_threshold = st.number_input("Minimum Balance Threshold", value=0.01, step=0.01, format="%.2f")

# Run Report Button
if st.button("📊 Generate Balance Sheet", type="primary"):
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
        where_conditions.append("coa.accounttype IN ('Asset', 'Liability', 'Equity')")
    
    query = f"""
    SELECT 
        coa.glaccountid,
        coa.accountname,
        coa.accounttype,
        SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0)) AS balance
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
        {'ABS(SUM(COALESCE(jel.debitamount, 0) - COALESCE(jel.creditamount, 0))) >= :threshold' if not show_zero_balances else 'TRUE'}
    ORDER BY 
        coa.accounttype, coa.glaccountid
    """
    
    if not show_zero_balances:
        params["threshold"] = balance_threshold
    
    # Execute query
    with st.spinner("Generating Balance Sheet..."):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            if df.empty:
                st.warning("No records found with the selected filters.")
            else:
                st.subheader(f"📊 Balance Sheet Results")
                st.caption(f"As of {date_to.strftime('%B %d, %Y')} | {len(df)} accounts")
                
                # Format balance column
                df['balance_formatted'] = df['balance'].apply(lambda x: f"{x:,.2f}")
                
                if group_by_type:
                    # Group by account type and show subtotals
                    account_types_in_data = df['accounttype'].unique()
                    
                    total_assets = 0
                    total_liabilities = 0
                    total_equity = 0
                    
                    for acc_type in sorted(account_types_in_data):
                        type_data = df[df['accounttype'] == acc_type].copy()
                        type_total = type_data['balance'].sum()
                        
                        # Update totals
                        if acc_type == 'Asset':
                            total_assets = type_total
                        elif acc_type == 'Liability':
                            total_liabilities = type_total
                        elif acc_type == 'Equity':
                            total_equity = type_total
                        
                        st.subheader(f"📋 {acc_type}")
                        
                        # Display accounts in this type
                        display_df = type_data[['glaccountid', 'accountname', 'balance_formatted']].copy()
                        display_df.columns = ['Account ID', 'Account Name', 'Balance']
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        if show_subtotals:
                            st.markdown(f"**Total {acc_type}: {type_total:,.2f}**")
                        
                        st.markdown("---")
                    
                    # Balance Sheet Summary
                    st.subheader("📊 Balance Sheet Summary")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Assets", f"{total_assets:,.2f}")
                    with col2:
                        st.metric("Total Liabilities", f"{total_liabilities:,.2f}")
                    with col3:
                        st.metric("Total Equity", f"{total_equity:,.2f}")
                    
                    # Balance check
                    balance_check = total_assets - (total_liabilities + total_equity)
                    if abs(balance_check) < 0.01:
                        st.success("✅ Balance Sheet is balanced!")
                    else:
                        st.error(f"⚠️ Balance Sheet is not balanced! Difference: {balance_check:,.2f}")
                    
                    # Key ratios (if liabilities > 0)
                    if total_liabilities != 0:
                        st.subheader("📈 Key Ratios")
                        debt_to_equity = total_liabilities / total_equity if total_equity != 0 else 0
                        equity_ratio = total_equity / total_assets if total_assets != 0 else 0
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Debt-to-Equity Ratio", f"{debt_to_equity:.2f}")
                        with col2:
                            st.metric("Equity Ratio", f"{equity_ratio:.2%}")
                
                else:
                    # Show all accounts in one table
                    display_df = df[['glaccountid', 'accountname', 'accounttype', 'balance_formatted']].copy()
                    display_df.columns = ['Account ID', 'Account Name', 'Account Type', 'Balance']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Export options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Export detailed data
                        export_df = df[['glaccountid', 'accountname', 'accounttype', 'balance']].copy()
                        export_df.to_excel(writer, index=False, sheet_name='Balance_Sheet')
                        
                        workbook = writer.book
                        worksheet = writer.sheets['Balance_Sheet']
                        
                        # Format columns
                        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
                        bold_fmt = workbook.add_format({'bold': True})
                        
                        worksheet.set_column('A:A', 12, bold_fmt)  # Account ID
                        worksheet.set_column('B:B', 30)           # Account Name
                        worksheet.set_column('C:C', 15)           # Account Type
                        worksheet.set_column('D:D', 15, currency_fmt)  # Balance
                        
                        # Add summary if grouped
                        if group_by_type:
                            summary_data = [
                                ['Summary', '', '', ''],
                                ['Total Assets', '', '', total_assets],
                                ['Total Liabilities', '', '', total_liabilities],
                                ['Total Equity', '', '', total_equity],
                                ['Balance Check', '', '', balance_check]
                            ]
                            
                            start_row = len(export_df) + 2
                            for i, row in enumerate(summary_data):
                                worksheet.write_row(start_row + i, 0, row, bold_fmt if i == 0 else None)
                    
                    st.download_button(
                        label="📤 Download Excel",
                        data=output.getvalue(),
                        file_name=f"Balance_Sheet_{date_to.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # PDF export
                    if st.button("📄 Generate PDF"):
                        try:
                            # Prepare data for PDF
                            pdf_df = df[['glaccountid', 'accountname', 'accounttype', 'balance']].copy()
                            pdf_df.columns = ['Account ID', 'Account Name', 'Account Type', 'Balance']
                            
                            # Prepare filters for PDF
                            pdf_filters = {
                                'date_from': date_from,
                                'date_to': date_to,
                                'companies': selected_companies,
                                'fiscal_years': selected_years
                            }
                            
                            # Prepare summary data
                            summary_data = {
                                'Total Assets': total_assets,
                                'Total Liabilities': total_liabilities,
                                'Total Equity': total_equity,
                                'Balance Check': balance_check
                            }
                            
                            # Add key ratios if applicable
                            if total_liabilities != 0 and total_equity != 0:
                                debt_to_equity = total_liabilities / total_equity
                                equity_ratio = total_equity / total_assets if total_assets != 0 else 0
                                summary_data['Debt-to-Equity Ratio'] = debt_to_equity
                                summary_data['Equity Ratio'] = equity_ratio
                            
                            # Add balance validation
                            if abs(balance_check) < 0.01:
                                summary_data['Balance Status'] = '✓ Balanced'
                            else:
                                summary_data['Balance Status'] = f'⚠ Out of Balance by {balance_check:,.2f}'
                            
                            # Generate PDF
                            result, file_type = generate_balance_sheet_pdf(pdf_df, pdf_filters, summary_data)
                            
                            if file_type == 'pdf':
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=result,
                                    file_name=f"Balance_Sheet_{date_to.strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf"
                                )
                                st.success("PDF generated successfully!")
                            else:  # HTML fallback
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=result,
                                    file_name=f"Balance_Sheet_{date_to.strftime('%Y%m%d')}.html",
                                    mime="text/html"
                                )
                                st.info("Downloaded as HTML file (print using browser)")
                                
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                
                with col3:
                    # CSV export
                    csv_df = df[['glaccountid', 'accountname', 'accounttype', 'balance']].copy()
                    csv = csv_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"Balance_Sheet_{date_to.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
        except Exception as e:
            st.error(f"Error generating Balance Sheet: {str(e)}")

# Information panel
with st.expander("ℹ️ About Balance Sheet"):
    st.markdown("""
    **Balance Sheet** shows the financial position of the company at a specific point in time.
    
    **Formula:** Assets = Liabilities + Equity
    
    **Account Types:**
    - **Assets**: Resources owned by the company (Cash, Accounts Receivable, Inventory, etc.)
    - **Liabilities**: Amounts owed to others (Accounts Payable, Loans, etc.)
    - **Equity**: Owner's interest in the company (Capital, Retained Earnings, etc.)
    
    **Key Ratios:**
    - **Debt-to-Equity Ratio**: Total Liabilities ÷ Total Equity
    - **Equity Ratio**: Total Equity ÷ Total Assets
    """)

# Navigation is now handled by the SAP-style sidebar
