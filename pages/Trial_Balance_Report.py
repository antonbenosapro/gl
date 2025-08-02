import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb
from utils.pdf_generator import generate_trial_balance_pdf

# Configure page
st.set_page_config(page_title="📑 Trial Balance Report", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Trial Balance Report", "Financial Reports", "Core Statements")

st.title("📑 Trial Balance Report")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
        account_types = [row[0] for row in conn.execute(text("SELECT DISTINCT accounttype FROM glaccount ORDER BY accounttype")).fetchall() if row[0]]
        creators = [row[0] for row in conn.execute(text("SELECT DISTINCT createdby FROM journalentryheader ORDER BY createdby")).fetchall() if row[0]]
    
    return companies, years, periods, account_types, creators

# Get filter options
companies, years, periods, account_types, creators = get_filter_options()

# Filter Section
with st.expander("🔍 Filter Options", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📅 Date Range")
        date_from = st.date_input("From Date", value=date(2025, 1, 1), key="date_from")
        date_to = st.date_input("To Date", value=date.today(), key="date_to")
        
        st.subheader("🏢 Company & User")
        selected_companies = st.multiselect("Company Code(s)", ["All"] + companies, default=["All"])
        selected_creators = st.multiselect("Created By", ["All"] + creators, default=["All"])
    
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
        
        st.subheader("📄 Account Search")
        account_id_search = st.text_input("Account ID (contains)", "")
        account_name_search = st.text_input("Account Name (contains)", "")

# Run Report Button
if st.button("📑 Generate Trial Balance", type="primary"):
    # Process filter selections
    if "All" in selected_companies:
        selected_companies = companies
    if "All" in selected_years:
        selected_years = years
    if "All" in selected_periods:
        selected_periods = periods
    if "All" in selected_account_types:
        selected_account_types = account_types
    if "All" in selected_creators:
        selected_creators = creators
    
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
    
    if selected_creators:
        creator_ph = ", ".join([f":creator{i}" for i in range(len(selected_creators))])
        where_conditions.append(f"jeh.createdby IN ({creator_ph})")
        params.update({f"creator{i}": v for i, v in enumerate(selected_creators)})
    
    if account_id_search:
        where_conditions.append("UPPER(coa.glaccountid) LIKE UPPER(:account_id_search)")
        params["account_id_search"] = f"%{account_id_search}%"
    
    if account_name_search:
        where_conditions.append("UPPER(coa.accountname) LIKE UPPER(:account_name_search)")
        params["account_name_search"] = f"%{account_name_search}%"
    
    query = f"""
    SELECT 
        coa.glaccountid,
        coa.accountname,
        coa.accounttype,
        SUM(COALESCE(jel.debitamount, 0)) AS total_debit,
        SUM(COALESCE(jel.creditamount, 0)) AS total_credit,
        SUM(COALESCE(jel.debitamount, 0)) - SUM(COALESCE(jel.creditamount, 0)) AS net_balance,
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
        {'(ABS(SUM(COALESCE(jel.debitamount, 0))) >= :threshold OR ABS(SUM(COALESCE(jel.creditamount, 0))) >= :threshold)' if not show_zero_balances else 'TRUE'}
    ORDER BY 
        coa.accounttype, coa.glaccountid
    """
    
    if not show_zero_balances:
        params["threshold"] = balance_threshold
    
    # Execute query
    with st.spinner("Generating Trial Balance..."):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            if df.empty:
                st.warning("No records found with the selected filters.")
            else:
                st.subheader(f"📑 Trial Balance Results")
                st.caption(f"As of {date_to.strftime('%B %d, %Y')} | {len(df)} accounts")
                
                # Format columns
                df['debit_formatted'] = df['total_debit'].apply(lambda x: f"{x:,.2f}" if x != 0 else "")
                df['credit_formatted'] = df['total_credit'].apply(lambda x: f"{x:,.2f}" if x != 0 else "")
                df['balance_formatted'] = df['net_balance'].apply(lambda x: f"{x:,.2f}")
                
                if group_by_type:
                    # Group by account type and show subtotals
                    account_types_in_data = df['accounttype'].unique()
                    
                    grand_total_debits = 0
                    grand_total_credits = 0
                    
                    for acc_type in sorted(account_types_in_data):
                        type_data = df[df['accounttype'] == acc_type].copy()
                        type_debit_total = type_data['total_debit'].sum()
                        type_credit_total = type_data['total_credit'].sum()
                        
                        # Update grand totals
                        grand_total_debits += type_debit_total
                        grand_total_credits += type_credit_total
                        
                        # Display account type header
                        icon = {"Asset": "🏢", "Liability": "💳", "Equity": "💰", "Revenue": "📈", "Expense": "💸"}.get(acc_type, "📋")
                        st.subheader(f"{icon} {acc_type} Accounts")
                        
                        # Display accounts in this type
                        display_df = type_data[['glaccountid', 'accountname', 'debit_formatted', 'credit_formatted', 'balance_formatted', 'transaction_count']].copy()
                        display_df.columns = ['Account ID', 'Account Name', 'Total Debits', 'Total Credits', 'Net Balance', 'Transactions']
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        if show_subtotals:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f"**Debits: {type_debit_total:,.2f}**")
                            with col2:
                                st.markdown(f"**Credits: {type_credit_total:,.2f}**")
                            with col3:
                                type_balance = type_debit_total - type_credit_total
                                st.markdown(f"**Net: {type_balance:,.2f}**")
                        
                        st.markdown("---")
                    
                    # Trial Balance Summary
                    st.subheader("📊 Trial Balance Summary")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Debits", f"{grand_total_debits:,.2f}")
                    with col2:
                        st.metric("Total Credits", f"{grand_total_credits:,.2f}")
                    with col3:
                        balance_difference = grand_total_debits - grand_total_credits
                        st.metric("Difference", f"{balance_difference:,.2f}")
                    with col4:
                        total_transactions = df['transaction_count'].sum()
                        st.metric("Total Transactions", f"{total_transactions:,}")
                    
                    # Balance validation
                    if abs(balance_difference) < 0.01:
                        st.success("✅ Trial Balance is balanced! Debits equal Credits.")
                    else:
                        st.error(f"⚠️ Trial Balance is OUT OF BALANCE! Difference: {balance_difference:,.2f}")
                        st.warning("This indicates there may be data entry errors or incomplete transactions.")
                    
                    # Additional analysis
                    if len(df) > 0:
                        st.subheader("📈 Account Analysis")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Largest debit and credit accounts
                            largest_debit = df.loc[df['total_debit'].idxmax()] if df['total_debit'].max() > 0 else None
                            if largest_debit is not None:
                                st.metric("Largest Debit Account", 
                                        f"{largest_debit['glaccountid']} - {largest_debit['accountname'][:20]}...", 
                                        f"{largest_debit['total_debit']:,.2f}")
                        
                        with col2:
                            largest_credit = df.loc[df['total_credit'].idxmax()] if df['total_credit'].max() > 0 else None
                            if largest_credit is not None:
                                st.metric("Largest Credit Account", 
                                        f"{largest_credit['glaccountid']} - {largest_credit['accountname'][:20]}...", 
                                        f"{largest_credit['total_credit']:,.2f}")
                
                else:
                    # Show all accounts in one table
                    display_df = df[['glaccountid', 'accountname', 'accounttype', 'debit_formatted', 'credit_formatted', 'balance_formatted', 'transaction_count']].copy()
                    display_df.columns = ['Account ID', 'Account Name', 'Account Type', 'Total Debits', 'Total Credits', 'Net Balance', 'Transactions']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Summary totals
                    total_debits = df['total_debit'].sum()
                    total_credits = df['total_credit'].sum()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Debits", f"{total_debits:,.2f}")
                    with col2:
                        st.metric("Total Credits", f"{total_credits:,.2f}")
                    with col3:
                        difference = total_debits - total_credits
                        st.metric("Difference", f"{difference:,.2f}")
                
                # Export options
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Export detailed data
                        export_df = df[['glaccountid', 'accountname', 'accounttype', 'total_debit', 'total_credit', 'net_balance', 'transaction_count']].copy()
                        export_df.to_excel(writer, index=False, sheet_name='Trial_Balance')
                        
                        workbook = writer.book
                        worksheet = writer.sheets['Trial_Balance']
                        
                        # Format columns
                        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
                        bold_fmt = workbook.add_format({'bold': True})
                        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
                        
                        worksheet.set_column('A:A', 12, bold_fmt)  # Account ID
                        worksheet.set_column('B:B', 30)           # Account Name
                        worksheet.set_column('C:C', 15)           # Account Type
                        worksheet.set_column('D:D', 15, currency_fmt)  # Total Debit
                        worksheet.set_column('E:E', 15, currency_fmt)  # Total Credit
                        worksheet.set_column('F:F', 15, currency_fmt)  # Net Balance
                        worksheet.set_column('G:G', 12)           # Transaction Count
                        
                        # Add summary
                        summary_data = [
                            ['TRIAL BALANCE SUMMARY', '', '', '', '', '', ''],
                            ['Total Debits', '', '', grand_total_debits if group_by_type else df['total_debit'].sum(), '', '', ''],
                            ['Total Credits', '', '', '', grand_total_credits if group_by_type else df['total_credit'].sum(), '', ''],
                            ['Difference', '', '', '', '', balance_difference if group_by_type else (df['total_debit'].sum() - df['total_credit'].sum()), ''],
                            ['Total Transactions', '', '', '', '', '', df['transaction_count'].sum()]
                        ]
                        
                        start_row = len(export_df) + 2
                        for i, row in enumerate(summary_data):
                            fmt = header_fmt if i == 0 else bold_fmt if row[0] else None
                            worksheet.write_row(start_row + i, 0, row, fmt)
                    
                    st.download_button(
                        label="📤 Download Excel",
                        data=output.getvalue(),
                        file_name=f"Trial_Balance_{date_to.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # PDF export
                    if st.button("📄 Generate PDF"):
                        try:
                            # Prepare data for PDF
                            pdf_df = df[['glaccountid', 'accountname', 'accounttype', 'total_debit', 'total_credit', 'net_balance', 'transaction_count']].copy()
                            pdf_df.columns = ['Account ID', 'Account Name', 'Account Type', 'Total Debits', 'Total Credits', 'Net Balance', 'Transactions']
                            
                            # Prepare filters for PDF
                            pdf_filters = {
                                'date_from': date_from,
                                'date_to': date_to,
                                'companies': selected_companies,
                                'fiscal_years': selected_years
                            }
                            
                            # Calculate totals for summary
                            grand_total_debits = df['total_debit'].sum()
                            grand_total_credits = df['total_credit'].sum()
                            balance_difference = grand_total_debits - grand_total_credits
                            total_transactions = df['transaction_count'].sum()
                            
                            # Prepare summary data
                            summary_data = {
                                'Total Debits': grand_total_debits,
                                'Total Credits': grand_total_credits,
                                'Difference': balance_difference,
                                'Total Transactions': total_transactions
                            }
                            
                            # Add balance status
                            if abs(balance_difference) < 0.01:
                                summary_data['Balance Status'] = '✓ Balanced (Debits = Credits)'
                            else:
                                summary_data['Balance Status'] = f'⚠ Out of Balance by {balance_difference:,.2f}'
                            
                            # Add account analysis if available
                            if len(df) > 0:
                                if df['total_debit'].max() > 0:
                                    largest_debit = df.loc[df['total_debit'].idxmax()]
                                    summary_data['Largest Debit Account'] = f"{largest_debit['glaccountid']} ({largest_debit['total_debit']:,.2f})"
                                
                                if df['total_credit'].max() > 0:
                                    largest_credit = df.loc[df['total_credit'].idxmax()]
                                    summary_data['Largest Credit Account'] = f"{largest_credit['glaccountid']} ({largest_credit['total_credit']:,.2f})"
                            
                            # Generate PDF
                            result, file_type = generate_trial_balance_pdf(pdf_df, pdf_filters, summary_data)
                            
                            if file_type == 'pdf':
                                st.download_button(
                                    label="📥 Download PDF",
                                    data=result,
                                    file_name=f"Trial_Balance_{date_to.strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf"
                                )
                                st.success("PDF generated successfully!")
                            else:  # HTML fallback
                                st.download_button(
                                    label="📥 Download HTML",
                                    data=result,
                                    file_name=f"Trial_Balance_{date_to.strftime('%Y%m%d')}.html",
                                    mime="text/html"
                                )
                                st.info("Downloaded as HTML file (print using browser)")
                                
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                
                with col3:
                    # CSV export
                    csv_df = df[['glaccountid', 'accountname', 'accounttype', 'total_debit', 'total_credit', 'net_balance', 'transaction_count']].copy()
                    csv = csv_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"Trial_Balance_{date_to.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
        except Exception as e:
            st.error(f"Error generating Trial Balance: {str(e)}")

# Information panel
with st.expander("ℹ️ About Trial Balance"):
    st.markdown("""
    **Trial Balance** is a bookkeeping worksheet that lists all accounts and their balances at a specific point in time.
    
    **Purpose:**
    - Verify that total debits equal total credits (accounting equation)
    - Detect mathematical errors in the general ledger
    - Provide a summary of all account balances for financial statement preparation
    
    **Key Concepts:**
    - **Debit Balances**: Typically Asset and Expense accounts
    - **Credit Balances**: Typically Liability, Equity, and Revenue accounts
    - **Net Balance**: Debit total minus Credit total for each account
    
    **Balance Check:**
    - ✅ **Balanced**: Total Debits = Total Credits (difference ≈ 0)
    - ❌ **Unbalanced**: Indicates potential data entry errors or incomplete transactions
    
    **Account Type Normal Balances:**
    - **Assets**: Debit balance (increases with debits)
    - **Liabilities**: Credit balance (increases with credits)
    - **Equity**: Credit balance (increases with credits)
    - **Revenue**: Credit balance (increases with credits)
    - **Expenses**: Debit balance (increases with debits)
    """)

# Navigation is now handled by the SAP-style sidebar