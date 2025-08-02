import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb

# Configure page
st.set_page_config(page_title="📘 General Ledger Report", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("General Ledger Report", "Financial Reports", "Detailed Reports")

st.title("📘 General Ledger Report")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        accounts = [row[0] for row in conn.execute(text("SELECT DISTINCT glaccountid FROM glaccount ORDER BY glaccountid")).fetchall() if row[0]]
        account_types = [row[0] for row in conn.execute(text("SELECT DISTINCT accounttype FROM glaccount ORDER BY accounttype")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
        creators = [row[0] for row in conn.execute(text("SELECT DISTINCT createdby FROM journalentryheader ORDER BY createdby")).fetchall() if row[0]]
        currencies = [row[0] for row in conn.execute(text("SELECT DISTINCT currencycode FROM journalentryheader ORDER BY currencycode")).fetchall() if row[0]]
    
    return companies, accounts, account_types, years, periods, creators, currencies

# Get filter options
companies, accounts, account_types, years, periods, creators, currencies = get_filter_options()

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
        st.subheader("📊 Account Selection")
        selected_accounts = st.multiselect("GL Account(s)", ["All"] + accounts, default=["All"])
        selected_account_types = st.multiselect("Account Type(s)", ["All"] + account_types, default=["All"])
        
        st.subheader("📊 Period")
        selected_years = st.multiselect("Fiscal Year(s)", ["All"] + years, default=["All"])
        selected_periods = st.multiselect("Period(s)", ["All"] + periods, default=["All"])
    
    with col3:
        st.subheader("💰 Transaction Options")
        selected_currencies = st.multiselect("Currency Code(s)", ["All"] + currencies, default=["All"])
        min_amount = st.number_input("Minimum Amount", value=0.00, step=0.01, format="%.2f")
        
        st.subheader("📄 Search Options")
        doc_number_search = st.text_input("Document Number (contains)", "")
        memo_search = st.text_input("Memo (contains)", "")
        reference_search = st.text_input("Reference (contains)", "")
        
        # Advanced Options
        with st.expander("⚙️ Advanced Options"):
            show_running_balance = st.checkbox("Show Running Balance", value=True, help="Calculate running balance for each account")
            group_by_account = st.checkbox("Group by Account", value=True, help="Group transactions by GL Account")
            show_subtotals = st.checkbox("Show Account Subtotals", value=True)
            limit_records = st.number_input("Limit Records", min_value=0, max_value=50000, value=5000, step=500)

# Run Report Button
if st.button("📘 Generate General Ledger Report", type="primary"):
    # Process filter selections
    if "All" in selected_companies:
        selected_companies = companies
    if "All" in selected_accounts:
        selected_accounts = accounts
    if "All" in selected_account_types:
        selected_account_types = account_types
    if "All" in selected_years:
        selected_years = years
    if "All" in selected_periods:
        selected_periods = periods
    if "All" in selected_creators:
        selected_creators = creators
    if "All" in selected_currencies:
        selected_currencies = currencies
    
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
    
    if selected_accounts:
        acct_ph = ", ".join([f":acct{i}" for i in range(len(selected_accounts))])
        where_conditions.append(f"coa.glaccountid IN ({acct_ph})")
        params.update({f"acct{i}": v for i, v in enumerate(selected_accounts)})
    
    if selected_account_types:
        type_ph = ", ".join([f":type{i}" for i in range(len(selected_account_types))])
        where_conditions.append(f"coa.accounttype IN ({type_ph})")
        params.update({f"type{i}": v for i, v in enumerate(selected_account_types)})
    
    if selected_years:
        year_ph = ", ".join([f":year{i}" for i in range(len(selected_years))])
        where_conditions.append(f"jeh.fiscalyear IN ({year_ph})")
        params.update({f"year{i}": v for i, v in enumerate(selected_years)})
    
    if selected_periods:
        period_ph = ", ".join([f":period{i}" for i in range(len(selected_periods))])
        where_conditions.append(f"jeh.period IN ({period_ph})")
        params.update({f"period{i}": v for i, v in enumerate(selected_periods)})
    
    if selected_creators:
        creator_ph = ", ".join([f":creator{i}" for i in range(len(selected_creators))])
        where_conditions.append(f"jeh.createdby IN ({creator_ph})")
        params.update({f"creator{i}": v for i, v in enumerate(selected_creators)})
    
    if selected_currencies:
        curr_ph = ", ".join([f":curr{i}" for i in range(len(selected_currencies))])
        where_conditions.append(f"jeh.currencycode IN ({curr_ph})")
        params.update({f"curr{i}": v for i, v in enumerate(selected_currencies)})
    
    if min_amount > 0:
        where_conditions.append("(ABS(COALESCE(jel.debitamount, 0)) >= :min_amount OR ABS(COALESCE(jel.creditamount, 0)) >= :min_amount)")
        params["min_amount"] = min_amount
    
    if doc_number_search:
        where_conditions.append("UPPER(jeh.documentnumber) LIKE UPPER(:doc_search)")
        params["doc_search"] = f"%{doc_number_search}%"
    
    if memo_search:
        where_conditions.append("UPPER(jel.description) LIKE UPPER(:memo_search)")
        params["memo_search"] = f"%{memo_search}%"
    
    if reference_search:
        where_conditions.append("UPPER(jeh.reference) LIKE UPPER(:ref_search)")
        params["ref_search"] = f"%{reference_search}%"
    
    # Build the query
    order_by_clause = "coa.glaccountid, jeh.documentdate, jeh.documentnumber, jel.linenumber" if group_by_account else "jeh.documentdate, jeh.documentnumber, jel.linenumber"
    
    query = f"""
    SELECT 
        coa.glaccountid,
        coa.accountname AS gl_description,
        coa.accounttype,
        jeh.documentnumber,
        jeh.documentdate,
        jeh.fiscalyear,
        jeh.period,
        jeh.companycodeid,
        jeh.currencycode,
        jeh.reference,
        jeh.createdby,
        jel.linenumber,
        jel.debitamount,
        jel.creditamount,
        jel.description AS memo,
        jel.costcenterid
    FROM 
        journalentryline jel
    JOIN 
        glaccount coa ON coa.glaccountid = jel.glaccountid
    JOIN 
        journalentryheader jeh ON jeh.documentnumber = jel.documentnumber
    WHERE 
        {' AND '.join(where_conditions)}
    ORDER BY 
        {order_by_clause}
    """
    
    if limit_records > 0:
        query += f" LIMIT {limit_records}"
    
    # Execute query
    with st.spinner("Generating General Ledger Report..."):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            if df.empty:
                st.warning("No records found with the selected filters.")
            else:
                st.subheader(f"📘 General Ledger Report Results")
                st.caption(f"For the period from {date_from.strftime('%B %d, %Y')} to {date_to.strftime('%B %d, %Y')} | {len(df)} transactions")
                
                # Format amounts
                df['debit_formatted'] = df['debitamount'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) and x != 0 else "")
                df['credit_formatted'] = df['creditamount'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) and x != 0 else "")
                
                # Calculate running balance if requested
                if show_running_balance:
                    df['running_balance'] = 0.0
                    for account in df['glaccountid'].unique():
                        account_mask = df['glaccountid'] == account
                        account_data = df[account_mask].copy()
                        account_data = account_data.sort_values(['documentdate', 'documentnumber', 'linenumber'])
                        
                        running_bal = 0.0
                        for idx in account_data.index:
                            debit = df.loc[idx, 'debitamount'] if pd.notna(df.loc[idx, 'debitamount']) else 0
                            credit = df.loc[idx, 'creditamount'] if pd.notna(df.loc[idx, 'creditamount']) else 0
                            running_bal += (debit - credit)
                            df.loc[idx, 'running_balance'] = running_bal
                    
                    df['balance_formatted'] = df['running_balance'].apply(lambda x: f"{x:,.2f}")
                
                if group_by_account:
                    # Group by account and show subtotals
                    accounts_in_data = df['glaccountid'].unique()
                    
                    total_debits = 0
                    total_credits = 0
                    
                    for account_id in sorted(accounts_in_data):
                        account_data = df[df['glaccountid'] == account_id].copy()
                        account_debit_total = account_data['debitamount'].fillna(0).sum()
                        account_credit_total = account_data['creditamount'].fillna(0).sum()
                        
                        # Update totals
                        total_debits += account_debit_total
                        total_credits += account_credit_total
                        
                        # Display account header
                        account_name = account_data['gl_description'].iloc[0]
                        account_type = account_data['accounttype'].iloc[0]
                        
                        st.subheader(f"📘 {account_id} - {account_name}")
                        st.caption(f"Account Type: {account_type} | {len(account_data)} transactions")
                        
                        # Display transactions for this account
                        display_columns = ['documentnumber', 'documentdate', 'fiscalyear', 'period', 'currencycode', 'reference', 'memo', 'debit_formatted', 'credit_formatted']
                        if show_running_balance:
                            display_columns.append('balance_formatted')
                        
                        display_df = account_data[display_columns].copy()
                        column_names = ['Document', 'Date', 'Fiscal Year', 'Period', 'Currency', 'Reference', 'Memo', 'Debit', 'Credit']
                        if show_running_balance:
                            column_names.append('Running Balance')
                        
                        display_df.columns = column_names
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        if show_subtotals:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.markdown(f"**Account Debits: {account_debit_total:,.2f}**")
                            with col2:
                                st.markdown(f"**Account Credits: {account_credit_total:,.2f}**")
                            with col3:
                                account_balance = account_debit_total - account_credit_total
                                st.markdown(f"**Account Balance: {account_balance:,.2f}**")
                        
                        st.markdown("---")
                    
                    # Overall Summary
                    st.subheader("📊 General Ledger Summary")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Debits", f"{total_debits:,.2f}")
                    with col2:
                        st.metric("Total Credits", f"{total_credits:,.2f}")
                    with col3:
                        balance_difference = total_debits - total_credits
                        st.metric("Difference", f"{balance_difference:,.2f}")
                    with col4:
                        unique_accounts = df['glaccountid'].nunique()
                        st.metric("Accounts", f"{unique_accounts:,}")
                    
                    # Balance validation
                    if abs(balance_difference) < 0.01:
                        st.success("✅ General Ledger is balanced!")
                    else:
                        st.warning(f"⚠️ Balance difference: {balance_difference:,.2f}")
                
                else:
                    # Show all transactions in one table
                    display_columns = ['glaccountid', 'gl_description', 'accounttype', 'documentnumber', 'documentdate', 'fiscalyear', 'period', 'currencycode', 'reference', 'memo', 'debit_formatted', 'credit_formatted']
                    if show_running_balance:
                        display_columns.append('balance_formatted')
                    
                    display_df = df[display_columns].copy()
                    column_names = ['Account ID', 'Account Name', 'Type', 'Document', 'Date', 'Fiscal Year', 'Period', 'Currency', 'Reference', 'Memo', 'Debit', 'Credit']
                    if show_running_balance:
                        column_names.append('Running Balance')
                    
                    display_df.columns = column_names
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    # Summary totals
                    total_debits = df['debitamount'].fillna(0).sum()
                    total_credits = df['creditamount'].fillna(0).sum()
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Debits", f"{total_debits:,.2f}")
                    with col2:
                        st.metric("Total Credits", f"{total_credits:,.2f}")
                    with col3:
                        difference = total_debits - total_credits
                        st.metric("Difference", f"{difference:,.2f}")
                
                # Export options
                col1, col2 = st.columns(2)
                
                with col1:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Export detailed data
                        export_columns = ['glaccountid', 'gl_description', 'accounttype', 'documentnumber', 'documentdate', 
                                        'fiscalyear', 'period', 'currencycode', 'reference', 'memo', 'debitamount', 'creditamount']
                        if show_running_balance:
                            export_columns.append('running_balance')
                        
                        export_df = df[export_columns].copy()
                        export_df.to_excel(writer, index=False, sheet_name='General_Ledger')
                        
                        workbook = writer.book
                        worksheet = writer.sheets['General_Ledger']
                        
                        # Format columns
                        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
                        date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                        bold_fmt = workbook.add_format({'bold': True})
                        
                        worksheet.set_column('A:A', 12, bold_fmt)  # Account ID
                        worksheet.set_column('B:B', 30)           # Account Name
                        worksheet.set_column('C:C', 12)           # Account Type
                        worksheet.set_column('D:D', 15, bold_fmt) # Document Number
                        worksheet.set_column('E:E', 12, date_fmt) # Date
                        worksheet.set_column('F:F', 12)           # Fiscal Year
                        worksheet.set_column('G:G', 8)            # Period
                        worksheet.set_column('H:H', 10)           # Currency
                        worksheet.set_column('I:I', 15)           # Reference
                        worksheet.set_column('J:J', 30)           # Memo
                        worksheet.set_column('K:K', 15, currency_fmt)  # Debit
                        worksheet.set_column('L:L', 15, currency_fmt)  # Credit
                        if show_running_balance:
                            worksheet.set_column('M:M', 15, currency_fmt)  # Running Balance
                        
                        # Add summary
                        summary_start = len(export_df) + 2
                        worksheet.write(summary_start, 0, 'SUMMARY:', bold_fmt)
                        worksheet.write(summary_start + 1, 0, 'Total Debits:', bold_fmt)
                        worksheet.write(summary_start + 1, 10, total_debits if group_by_account else df['debitamount'].fillna(0).sum(), currency_fmt)
                        worksheet.write(summary_start + 2, 0, 'Total Credits:', bold_fmt)
                        worksheet.write(summary_start + 2, 11, total_credits if group_by_account else df['creditamount'].fillna(0).sum(), currency_fmt)
                    
                    st.download_button(
                        label="📤 Download Excel",
                        data=output.getvalue(),
                        file_name=f"General_Ledger_{date_to.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # CSV export
                    export_columns = ['glaccountid', 'gl_description', 'accounttype', 'documentnumber', 'documentdate', 
                                    'fiscalyear', 'period', 'currencycode', 'reference', 'memo', 'debitamount', 'creditamount']
                    if show_running_balance:
                        export_columns.append('running_balance')
                    
                    csv_df = df[export_columns].copy()
                    csv = csv_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"General_Ledger_{date_to.strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
        except Exception as e:
            st.error(f"Error generating General Ledger Report: {str(e)}")

# Information panel
with st.expander("ℹ️ About General Ledger"):
    st.markdown("""
    **General Ledger Report** shows detailed transaction-level information for all accounts or selected accounts.
    
    **Key Features:**
    - **Transaction Detail**: Every debit and credit entry with supporting information
    - **Running Balance**: Cumulative account balance after each transaction
    - **Account Grouping**: Organize transactions by GL account for easier analysis
    - **Advanced Filtering**: Filter by date, account, amount, document number, and more
    
    **Use Cases:**
    - **Account Analysis**: Detailed review of specific account activity
    - **Audit Trail**: Complete transaction history for compliance and auditing
    - **Balance Investigation**: Understand how account balances were built up
    - **Data Verification**: Cross-check transactions against source documents
    
    **Report Options:**
    - **Group by Account**: Organize transactions by account with subtotals
    - **Running Balance**: See cumulative effect of each transaction
    - **Amount Filtering**: Focus on transactions above a certain threshold
    - **Search Functions**: Find specific documents, memos, or references
    
    **Export Options:**
    - **Excel**: Formatted spreadsheet with proper column formatting
    - **CSV**: Raw data for import into other systems or analysis tools
    """)

# Navigation is now handled by the SAP-style sidebar