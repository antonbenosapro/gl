import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from datetime import date, datetime
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb

# Configure page
st.set_page_config(page_title="📋 Chart of Accounts Report", layout="wide", initial_sidebar_state="expanded")

# Navigation
show_sap_sidebar()
show_breadcrumb("Chart of Accounts Report", "Master Data", "Reports")

st.title("📋 Chart of Accounts Report")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        account_types = [row[0] for row in conn.execute(text("SELECT DISTINCT accounttype FROM glaccount ORDER BY accounttype")).fetchall() if row[0]]
        account_categories = [row[0] for row in conn.execute(text("SELECT DISTINCT LEFT(glaccountid, 1) as category FROM glaccount ORDER BY category")).fetchall() if row[0]]
        account_groups = [row[0] for row in conn.execute(text("SELECT DISTINCT account_group_code FROM glaccount WHERE account_group_code IS NOT NULL ORDER BY account_group_code")).fetchall() if row[0]]
        account_classes = [row[0] for row in conn.execute(text("SELECT DISTINCT account_class FROM glaccount WHERE account_class IS NOT NULL ORDER BY account_class")).fetchall() if row[0]]
        
        # Get account ranges
        result = conn.execute(text("SELECT MIN(glaccountid), MAX(glaccountid) FROM glaccount"))
        min_account, max_account = result.first()
        
        # Check if accounts have transactions
        transaction_status = conn.execute(text("""
            SELECT DISTINCT 
                CASE WHEN jel.glaccountid IS NOT NULL THEN 'With Transactions' ELSE 'No Transactions' END as status
            FROM glaccount coa
            LEFT JOIN journalentryline jel ON coa.glaccountid = jel.glaccountid
        """)).fetchall()
        transaction_statuses = [row[0] for row in transaction_status]
    
    return account_types, account_categories, account_groups, account_classes, min_account, max_account, transaction_statuses

# Get filter options
account_types, account_categories, account_groups, account_classes, min_account, max_account, transaction_statuses = get_filter_options()

# Filter Section
with st.expander("🔍 Filter Options", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("📋 Account Classification")
        selected_account_types = st.multiselect("Account Type(s)", ["All"] + account_types, default=["All"])
        selected_categories = st.multiselect("Account Category (First Digit)", ["All"] + account_categories, default=["All"])
        selected_transaction_status = st.multiselect("Transaction Status", ["All"] + transaction_statuses, default=["All"])
        
        st.subheader("🏗️ Account Structure")
        selected_account_groups = st.multiselect("Account Group", ["All"] + account_groups, default=["All"])
        selected_account_classes = st.multiselect("Account Class", ["All"] + account_classes, default=["All"])
    
    with col2:
        st.subheader("🔢 Account Range")
        account_range_start = st.text_input("Account ID From", value="", placeholder=f"e.g. {min_account}")
        account_range_end = st.text_input("Account ID To", value="", placeholder=f"e.g. {max_account}")
        
        st.subheader("📄 Search Options")
        account_id_search = st.text_input("Account ID (contains)", "")
        account_name_search = st.text_input("Account Name (contains)", "")
        # Note: Description search removed as glaccount table doesn't have description column
    
    with col3:
        st.subheader("📊 Display Options")
        show_reconciliation = st.checkbox("Show Only Reconciliation Accounts", value=False)
        show_zero_balance = st.checkbox("Include Zero Balance Accounts", value=True)
        group_by_type = st.checkbox("Group by Account Type", value=True)
        show_balances = st.checkbox("Show Current Balances", value=True, help="Calculate current account balances")
        
        st.subheader("📈 Analysis Options")
        show_statistics = st.checkbox("Show Account Statistics", value=True)
        show_transaction_count = st.checkbox("Show Transaction Count", value=True)
        sort_by = st.selectbox("Sort By", ["Account ID", "Account Name", "Account Type", "Balance"], index=0)

# Run Report Button
if st.button("📋 Generate Chart of Accounts", type="primary"):
    # Process filter selections
    if "All" in selected_account_types:
        selected_account_types = account_types
    if "All" in selected_categories:
        selected_categories = account_categories
    if "All" in selected_transaction_status:
        selected_transaction_status = transaction_statuses
    if "All" in selected_companies:
        selected_companies = companies
    
    # Build query
    where_conditions = []
    params = {}
    
    if selected_account_types:
        type_ph = ", ".join([f":type{i}" for i in range(len(selected_account_types))])
        where_conditions.append(f"coa.accounttype IN ({type_ph})")
        params.update({f"type{i}": v for i, v in enumerate(selected_account_types)})
    
    if selected_categories:
        cat_ph = ", ".join([f":cat{i}" for i in range(len(selected_categories))])
        where_conditions.append(f"LEFT(coa.glaccountid, 1) IN ({cat_ph})")
        params.update({f"cat{i}": v for i, v in enumerate(selected_categories)})
    
    if selected_account_groups and "All" not in selected_account_groups:
        group_ph = ", ".join([f":group{i}" for i in range(len(selected_account_groups))])
        where_conditions.append(f"coa.account_group_code IN ({group_ph})")
        params.update({f"group{i}": v for i, v in enumerate(selected_account_groups)})
    
    if selected_account_classes and "All" not in selected_account_classes:
        class_ph = ", ".join([f":class{i}" for i in range(len(selected_account_classes))])
        where_conditions.append(f"coa.account_class IN ({class_ph})")
        params.update({f"class{i}": v for i, v in enumerate(selected_account_classes)})
    
    if account_range_start:
        where_conditions.append("coa.glaccountid >= :account_start")
        params["account_start"] = account_range_start
    
    if account_range_end:
        where_conditions.append("coa.glaccountid <= :account_end")
        params["account_end"] = account_range_end
    
    if account_id_search:
        where_conditions.append("UPPER(coa.glaccountid) LIKE UPPER(:account_id_search)")
        params["account_id_search"] = f"%{account_id_search}%"
    
    if account_name_search:
        where_conditions.append("UPPER(coa.accountname) LIKE UPPER(:account_name_search)")
        params["account_name_search"] = f"%{account_name_search}%"
    
    # Description search removed - column doesn't exist in glaccount table
    
    if show_reconciliation:
        where_conditions.append("coa.reconciliation_account_type IS NOT NULL AND coa.reconciliation_account_type != 'NONE'")
    
    # Build the main query
    balance_calculation = ""
    transaction_count_calc = ""
    joins = ""
    
    if show_balances or show_transaction_count:
        joins = "LEFT JOIN journalentryline jel ON coa.glaccountid = jel.glaccountid"
        
        if show_balances:
            balance_calculation = ", COALESCE(SUM(COALESCE(jel.debitamount, 0)) - SUM(COALESCE(jel.creditamount, 0)), 0) as current_balance"
        
        if show_transaction_count:
            transaction_count_calc = ", COUNT(CASE WHEN jel.glaccountid IS NOT NULL THEN 1 END) as transaction_count"
    
    # Filter by transaction status
    having_conditions = []
    if "With Transactions" in selected_transaction_status and "No Transactions" not in selected_transaction_status:
        having_conditions.append("COUNT(CASE WHEN jel.glaccountid IS NOT NULL THEN 1 END) > 0")
    elif "No Transactions" in selected_transaction_status and "With Transactions" not in selected_transaction_status:
        having_conditions.append("COUNT(CASE WHEN jel.glaccountid IS NOT NULL THEN 1 END) = 0")
    
    if not show_zero_balance and show_balances:
        having_conditions.append("ABS(COALESCE(SUM(COALESCE(jel.debitamount, 0)) - SUM(COALESCE(jel.creditamount, 0)), 0)) > 0.01")
    
    # Build sort order
    if show_balances and sort_by == "Balance":
        order_by = "current_balance DESC"
    else:
        sort_mapping = {
            "Account ID": "coa.glaccountid",
            "Account Name": "coa.accountname", 
            "Account Type": "coa.accounttype, coa.glaccountid",
            "Balance": "coa.glaccountid"  # fallback if balance not available
        }
        order_by = sort_mapping.get(sort_by, "coa.glaccountid")
    
    query = f"""
    SELECT 
        coa.glaccountid,
        coa.accountname,
        coa.accounttype,
        coa.account_class,
        coa.account_group_code,
        coa.reconciliation_account_type,
        coa.open_item_management
        {balance_calculation}
        {transaction_count_calc}
    FROM 
        glaccount coa
        {joins}
    WHERE (coa.marked_for_deletion = FALSE OR coa.marked_for_deletion IS NULL)
        {f" AND {' AND '.join(where_conditions)}" if where_conditions else ""}
    {f"GROUP BY coa.glaccountid, coa.accountname, coa.accounttype, coa.account_class, coa.account_group_code, coa.reconciliation_account_type, coa.open_item_management" if joins else ""}
    {f"HAVING {' AND '.join(having_conditions)}" if having_conditions else ""}
    ORDER BY {order_by}
    """
    
    # Execute query
    with st.spinner("Generating Chart of Accounts..."):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            if df.empty:
                st.warning("No accounts found with the selected filters.")
            else:
                st.subheader(f"📋 Chart of Accounts Results")
                st.caption(f"Found {len(df)} accounts matching your criteria")
                
                # Format data for display using structured fields
                df['recon_status'] = df['reconciliation_account_type'].apply(lambda x: f"✅ {x}" if x and x != 'NONE' else "❌ No Reconciliation")
                df['openitem_status'] = df['open_item_management'].apply(lambda x: "✅ Open Item" if x else "❌ Standard")
                
                if show_balances:
                    df['balance_formatted'] = df['current_balance'].apply(lambda x: f"{x:,.2f}")
                
                # Show statistics if requested
                if show_statistics:
                    st.subheader("📊 Account Statistics")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Total Accounts", f"{len(df):,}")
                    with col2:
                        recon_count = (df['reconciliation_account_type'] != 'NONE').sum()
                        st.metric("Reconciliation Accounts", f"{recon_count:,}")
                    with col3:
                        openitem_count = df['open_item_management'].sum()
                        st.metric("Open Item Accounts", f"{openitem_count:,}")
                    with col4:
                        account_types_count = df['accounttype'].nunique()
                        st.metric("Account Types", f"{account_types_count:,}")
                    
                    if show_balances:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            total_balance = df['current_balance'].sum()
                            st.metric("Total Balance", f"{total_balance:,.2f}")
                        with col2:
                            positive_balance = df[df['current_balance'] > 0]['current_balance'].sum()
                            st.metric("Positive Balances", f"{positive_balance:,.2f}")
                        with col3:
                            negative_balance = df[df['current_balance'] < 0]['current_balance'].sum()
                            st.metric("Negative Balances", f"{negative_balance:,.2f}")
                    
                    st.markdown("---")
                
                if group_by_type:
                    # Group by account type and show details
                    account_types_in_data = df['accounttype'].unique()
                    
                    for acc_type in sorted(account_types_in_data):
                        type_data = df[df['accounttype'] == acc_type].copy()
                        
                        # Account type icons
                        icon = {"Asset": "🏢", "Liability": "💳", "Equity": "💰", "Revenue": "📈", "Expense": "💸"}.get(acc_type, "📋")
                        st.subheader(f"{icon} {acc_type} Accounts ({len(type_data)} accounts)")
                        
                        # Prepare display columns
                        display_columns = ['glaccountid', 'accountname', 'account_class', 'account_group_code', 'recon_status', 'openitem_status']
                        column_names = ['Account ID', 'Account Name', 'Class', 'Account Group', 'Reconciliation', 'Open Item']
                        
                        if show_balances:
                            display_columns.append('balance_formatted')
                            column_names.append('Current Balance')
                        
                        if show_transaction_count:
                            display_columns.append('transaction_count')
                            column_names.append('Transactions')
                        
                        display_df = type_data[display_columns].copy()
                        display_df.columns = column_names
                        st.dataframe(display_df, use_container_width=True, hide_index=True)
                        
                        # Show type summary
                        if show_balances:
                            type_balance = type_data['current_balance'].sum()
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**{acc_type} Total Balance: {type_balance:,.2f}**")
                            with col2:
                                avg_balance = type_data['current_balance'].mean()
                                st.markdown(f"**Average Balance: {avg_balance:,.2f}**")
                        
                        st.markdown("---")
                
                else:
                    # Show all accounts in one table
                    display_columns = ['glaccountid', 'accountname', 'accounttype', 'account_class', 'account_group_code', 'recon_status', 'openitem_status']
                    column_names = ['Account ID', 'Account Name', 'Type', 'Class', 'Account Group', 'Reconciliation', 'Open Item']
                    
                    if show_balances:
                        display_columns.append('balance_formatted')
                        column_names.append('Current Balance')
                    
                    if show_transaction_count:
                        display_columns.append('transaction_count')
                        column_names.append('Transactions')
                    
                    display_df = df[display_columns].copy()
                    display_df.columns = column_names
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Account Analysis
                if show_balances:
                    st.subheader("📈 Account Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Top 5 accounts by balance
                        top_accounts = df.nlargest(5, 'current_balance')[['glaccountid', 'accountname', 'balance_formatted']]
                        st.markdown("**🔝 Top 5 Accounts by Balance**")
                        st.dataframe(top_accounts, hide_index=True)
                    
                    with col2:
                        # Bottom 5 accounts by balance
                        bottom_accounts = df.nsmallest(5, 'current_balance')[['glaccountid', 'accountname', 'balance_formatted']]
                        st.markdown("**🔻 Bottom 5 Accounts by Balance**")
                        st.dataframe(bottom_accounts, hide_index=True)
                
                # Export options
                col1, col2 = st.columns(2)
                
                with col1:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Export detailed data
                        export_columns = ['glaccountid', 'accountname', 'accounttype', 'account_class', 'account_group_code', 'reconciliation_account_type', 'open_item_management']
                        if show_balances:
                            export_columns.append('current_balance')
                        if show_transaction_count:
                            export_columns.append('transaction_count')
                        
                        export_df = df[export_columns].copy()
                        export_df.to_excel(writer, index=False, sheet_name='Chart_of_Accounts')
                        
                        workbook = writer.book
                        worksheet = writer.sheets['Chart_of_Accounts']
                        
                        # Format columns
                        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
                        date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                        bold_fmt = workbook.add_format({'bold': True})
                        
                        worksheet.set_column('A:A', 12, bold_fmt)  # Account ID
                        worksheet.set_column('B:B', 30)           # Account Name
                        worksheet.set_column('C:C', 15)           # Account Type
                        worksheet.set_column('D:D', 12)           # Company Code
                        worksheet.set_column('E:E', 15)           # Reconciliation
                        worksheet.set_column('F:F', 15)           # Open Item
                        
                        if show_balances:
                            # Find the current_balance column position
                            balance_col_idx = None
                            for i, col in enumerate(export_columns):
                                if col == 'current_balance':
                                    balance_col_idx = i
                                    break
                            if balance_col_idx is not None:
                                worksheet.set_column(balance_col_idx, balance_col_idx, 15, currency_fmt)
                        
                        # Add summary
                        summary_start = len(export_df) + 2
                        worksheet.write(summary_start, 0, 'SUMMARY:', bold_fmt)
                        worksheet.write(summary_start + 1, 0, 'Total Accounts:', bold_fmt)
                        worksheet.write(summary_start + 1, 1, len(df))
                        worksheet.write(summary_start + 2, 0, 'Reconciliation Accounts:', bold_fmt)
                        worksheet.write(summary_start + 2, 1, (df['reconciliation_account_type'] != 'NONE').sum())
                        
                        if show_balances:
                            worksheet.write(summary_start + 3, 0, 'Total Balance:', bold_fmt)
                            worksheet.write(summary_start + 3, 1, df['current_balance'].sum(), currency_fmt)
                    
                    st.download_button(
                        label="📤 Download Excel",
                        data=output.getvalue(),
                        file_name=f"Chart_of_Accounts_{date.today().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # CSV export
                    export_columns = ['glaccountid', 'accountname', 'accounttype', 'account_class', 'account_group_code', 'reconciliation_account_type', 'open_item_management']
                    if show_balances:
                        export_columns.append('current_balance')
                    if show_transaction_count:
                        export_columns.append('transaction_count')
                    
                    csv_df = df[export_columns].copy()
                    csv = csv_df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"Chart_of_Accounts_{date.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
        except Exception as e:
            st.error(f"Error generating Chart of Accounts: {str(e)}")

# Information panel
with st.expander("ℹ️ About Chart of Accounts"):
    st.markdown("""
    **Chart of Accounts** is a comprehensive list of all accounts used in the general ledger.
    
    **Purpose:**
    - **Organization**: Systematic organization of all financial accounts
    - **Standardization**: Consistent account structure across the organization
    - **Reporting**: Foundation for all financial reports and analysis
    - **Control**: Account management and maintenance
    
    **Account Types:**
    - **🏢 Assets**: Resources owned by the company (Cash, Accounts Receivable, Equipment)
    - **💳 Liabilities**: Amounts owed to others (Accounts Payable, Loans, Accrued Expenses)
    - **💰 Equity**: Owner's interest in the company (Capital, Retained Earnings)
    - **📈 Revenue**: Income from business operations (Sales, Service Revenue)
    - **💸 Expenses**: Costs of doing business (Salaries, Rent, Utilities)
    
    **Account Numbering:**
    - **1xxx**: Asset accounts
    - **2xxx**: Liability accounts  
    - **3xxx**: Equity accounts
    - **4xxx**: Revenue accounts
    - **5xxx**: Expense accounts
    
    **Key Features:**
    - **Current Balances**: Real-time account balances based on transactions
    - **Transaction Count**: Number of transactions per account
    - **Account Properties**: Reconciliation account and open item management status
    - **Search & Filter**: Find accounts by various criteria
    - **Analysis Tools**: Top/bottom accounts, balance summaries
    
    **Use Cases:**
    - **Account Setup**: Initial setup and ongoing maintenance
    - **Financial Analysis**: Understanding account structure and balances
    - **Audit Support**: Complete account listing for auditors
    - **System Integration**: Export for other financial systems
    """)

# Navigation is now handled by the sidebar