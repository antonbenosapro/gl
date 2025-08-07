import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from datetime import date
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb

# Configure page
st.set_page_config(page_title="🔍 GL Report Query", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("GL Report Query", "Financial Reports", "Detailed Reports")

st.title("🔍 General Ledger Report with Dynamic Grouping")

# Report Settings in expandable section
with st.expander("⚙️ Report Settings", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        # View options
        st.subheader("📊 View Options")
        expanded_view = st.checkbox("🔍 Expanded View", value=False, help="Expand the report to use full screen width")
        show_filters = st.checkbox("🔽 Show Filter Panel", value=True)
        show_columns_panel = st.checkbox("📋 Show Columns Panel", value=True)
    
    with col2:
        # Data options
        st.subheader("📄 Data Options")
        limit_records = st.number_input("📊 Limit Records", min_value=0, max_value=50000, value=10000, step=1000)
    
    # Export options
    st.subheader("📤 Export Options")
    export_format = st.selectbox("Export Format", ["Excel", "CSV"])
    include_formatting = st.checkbox("Include Number Formatting", value=True)

# Fetch GL data from database
def get_gl_data(limit=None):
    """Fetch GL data with optional limit"""
    query = """
    SELECT
        jel.documentnumber,
        jel.linenumber,
        coa.glaccountid,
        coa.accountname AS gl_description,
        coa.accounttype,
        jeh.companycodeid,
        jeh.documentdate,
        jeh.fiscalyear,
        jeh.period,
        jel.debitamount,
        jel.creditamount,
        jel.description AS memo,
        jel.business_unit_id,
        jeh.reference,
        jeh.createdby,
        jeh.createdat
    FROM
        journalentryline jel
    JOIN glaccount coa ON coa.glaccountid = jel.glaccountid
    JOIN journalentryheader jeh ON jeh.documentnumber = jel.documentnumber
    ORDER BY
        coa.glaccountid, jeh.documentdate, jel.linenumber
    """
    
    if limit and limit > 0:
        query += f" LIMIT {limit}"
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    
    return df

# Load data
with st.spinner("Loading GL data..."):
    df = get_gl_data(limit_records if limit_records > 0 else None)

# Display data info
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 Total Records", f"{len(df):,}")
with col2:
    total_debits = df['debitamount'].sum()
    st.metric("💰 Total Debits", f"{total_debits:,.2f}")
with col3:
    total_credits = df['creditamount'].sum()
    st.metric("💰 Total Credits", f"{total_credits:,.2f}")

# Balance check
balance_diff = total_debits - total_credits
if abs(balance_diff) < 0.01:
    st.success("✅ Debits and Credits are balanced!")
else:
    st.error(f"⚠️ Unbalanced: Difference of {balance_diff:,.2f}")

# AG Grid setup
gb = GridOptionsBuilder.from_dataframe(df)

# Configure columns with proper formatting
gb.configure_default_column(
    enableRowGroup=True,
    enablePivot=True,
    enableValue=True,
    sortable=True,
    filter=True,
    resizable=True
)

# Configure specific columns
gb.configure_column('documentnumber', header_name='Document Number', width=120, pinned='left')
gb.configure_column('documentdate', header_name='Date', width=100, type=["dateColumnFilter"])
gb.configure_column('glaccountid', header_name='GL Account', width=100)
gb.configure_column('gl_description', header_name='Account Description', width=200)
gb.configure_column('accounttype', header_name='Type', width=100)
gb.configure_column('companycodeid', header_name='Company', width=100)
gb.configure_column('fiscalyear', header_name='Year', width=80)
gb.configure_column('period', header_name='Period', width=80)

# Configure amount columns with proper formatting
gb.configure_column(
    'debitamount', 
    header_name='Debit Amount',
    type=["numericColumn", "numberColumnFilter"], 
    precision=2,
    aggFunc='sum',
    cellStyle={'textAlign': 'right'},
    valueFormatter="x => x ? x.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : ''"
)

gb.configure_column(
    'creditamount', 
    header_name='Credit Amount',
    type=["numericColumn", "numberColumnFilter"], 
    precision=2,
    aggFunc='sum',
    cellStyle={'textAlign': 'right'},
    valueFormatter="x => x ? x.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : ''"
)

gb.configure_column('memo', header_name='Memo', width=200)
gb.configure_column('business_unit_id', header_name='Business Unit', width=100)
gb.configure_column('reference', header_name='Reference', width=120)
gb.configure_column('createdby', header_name='Created By', width=100)
gb.configure_column('createdat', header_name='Created At', width=120, type=["dateColumnFilter"])

# Default grouping
gb.configure_column('companycodeid', rowGroup=True, hide=True)
gb.configure_column('fiscalyear', rowGroup=True, hide=True)
gb.configure_column('period', rowGroup=True, hide=True)
gb.configure_column('glaccountid', rowGroup=True, hide=True)

# Sidebar configuration
sidebar_config = {}
if show_filters:
    sidebar_config['filters_panel'] = True
if show_columns_panel:
    sidebar_config['columns_panel'] = True

if sidebar_config:
    gb.configure_side_bar(**sidebar_config, defaultToolPanel='columns')

# Grid options
gb.configure_grid_options(
    groupDisplayType='multipleColumns',
    autoGroupColumnDef={
        'headerName': 'Grouped Data',
        'cellRendererParams': {'suppressCount': False},
        'minWidth': 200
    },
    suppressAggFuncInHeader=True,
    animateRows=True,
    enableRangeSelection=True,
    rowSelection='multiple'
)

# Interactive features
gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren=True, groupSelectsFiltered=True)

# Build grid options
grid_options = gb.build()

# Display grid with conditional width
if expanded_view:
    # Full width expanded view
    st.markdown("### 📊 Expanded General Ledger View")
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        theme='alpine',
        height=700,
        fit_columns_on_grid_load=False
    )
else:
    # Standard view
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        theme='alpine',
        height=600
    )

# Export functionality
st.markdown("---")
st.subheader("📤 Export Data")

# Get selected data or all data
if grid_response['selected_rows'] is not None and len(grid_response['selected_rows']) > 0:
    export_df = pd.DataFrame(grid_response['selected_rows'])
    st.info(f"Exporting {len(export_df)} selected rows")
else:
    export_df = df.copy()
    st.info(f"Exporting all {len(export_df)} rows")

# Export options
col1, col2, col3 = st.columns(3)

with col1:
    # Excel export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Prepare export data
        if include_formatting:
            export_data = export_df.copy()
            # Format amounts for display
            export_data['debitamount'] = export_data['debitamount'].apply(lambda x: x if pd.notna(x) else 0)
            export_data['creditamount'] = export_data['creditamount'].apply(lambda x: x if pd.notna(x) else 0)
        else:
            export_data = export_df.copy()
        
        export_data.to_excel(writer, index=False, sheet_name='GL_Report')
        
        workbook = writer.book
        worksheet = writer.sheets['GL_Report']
        
        # Format columns
        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        date_fmt = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        bold_fmt = workbook.add_format({'bold': True})
        
        # Apply formatting
        for idx, col in enumerate(export_data.columns):
            if 'amount' in col.lower():
                worksheet.set_column(idx, idx, 15, currency_fmt)
            elif 'date' in col.lower():
                worksheet.set_column(idx, idx, 12, date_fmt)
            elif col in ['documentnumber', 'glaccountid']:
                worksheet.set_column(idx, idx, 15, bold_fmt)
            elif col == 'gl_description':
                worksheet.set_column(idx, idx, 30)
            else:
                worksheet.set_column(idx, idx, 12)
        
        # Add summary at the bottom
        summary_row = len(export_data) + 2
        worksheet.write(summary_row, 0, 'TOTALS:', bold_fmt)
        
        # Find amount columns
        debit_col = export_data.columns.get_loc('debitamount')
        credit_col = export_data.columns.get_loc('creditamount')
        
        # Add sum formulas
        debit_col_letter = chr(65 + debit_col)
        credit_col_letter = chr(65 + credit_col)
        
        worksheet.write_formula(summary_row, debit_col, f'=SUM({debit_col_letter}2:{debit_col_letter}{len(export_data)+1})', currency_fmt)
        worksheet.write_formula(summary_row, credit_col, f'=SUM({credit_col_letter}2:{credit_col_letter}{len(export_data)+1})', currency_fmt)
    
    st.download_button(
        label="📊 Download Excel",
        data=output.getvalue(),
        file_name=f"GL_Report_{date.today().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

with col2:
    # CSV export
    if include_formatting:
        csv_df = export_df.copy()
        csv_df['debitamount'] = csv_df['debitamount'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "0.00")
        csv_df['creditamount'] = csv_df['creditamount'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "0.00")
    else:
        csv_df = export_df.copy()
    
    csv = csv_df.to_csv(index=False)
    st.download_button(
        label="📄 Download CSV",
        data=csv,
        file_name=f"GL_Report_{date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

with col3:
    # JSON export for advanced users
    json_data = export_df.to_json(orient='records', indent=2)
    st.download_button(
        label="🔗 Download JSON",
        data=json_data,
        file_name=f"GL_Report_{date.today().strftime('%Y%m%d')}.json",
        mime="application/json"
    )

# Summary statistics
st.markdown("---")
st.subheader("📈 Summary Statistics")

if len(export_df) > 0:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Records", f"{len(export_df):,}")
    with col2:
        unique_accounts = export_df['glaccountid'].nunique()
        st.metric("Unique Accounts", f"{unique_accounts:,}")
    with col3:
        export_debit_total = export_df['debitamount'].sum()
        st.metric("Total Debits", f"{export_debit_total:,.2f}")
    with col4:
        export_credit_total = export_df['creditamount'].sum()
        st.metric("Total Credits", f"{export_credit_total:,.2f}")

# Tips and instructions
with st.expander("💡 Usage Tips"):
    st.markdown("""
    **Grid Features:**
    - **Grouping**: Drag column headers to the row group panel to group data
    - **Filtering**: Use the filter icons in column headers to filter data
    - **Sorting**: Click column headers to sort (hold Shift for multi-column sorting)
    - **Selection**: Use checkboxes to select specific rows for export
    - **Aggregation**: Numeric columns automatically show sums when grouped
    
    **Export Options:**
    - **Excel**: Best for detailed analysis with formatting
    - **CSV**: Best for importing into other systems
    - **JSON**: Best for developers and API integration
    
    **Pro Tips:**
    - Use the expanded view for better visibility of all columns
    - Select specific rows before exporting to get only the data you need
    - Group by Account Type and GL Account for hierarchical analysis
    """)

# Back button
if st.button("🔙 Back to Home"):
    st.switch_page("Home.py")