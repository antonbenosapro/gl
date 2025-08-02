import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from datetime import date
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb

# Configure page
st.set_page_config(page_title="📑 Journal Listing Report", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Journal Listing Report", "Financial Reports", "Detailed Reports")

st.title("📑 Journal Listing Report")

def get_filter_options():
    """Get filter options from database"""
    with engine.connect() as conn:
        companies = [row[0] for row in conn.execute(text("SELECT DISTINCT companycodeid FROM journalentryheader ORDER BY companycodeid")).fetchall() if row[0]]
        creators = [row[0] for row in conn.execute(text("SELECT DISTINCT createdby FROM journalentryheader ORDER BY createdby")).fetchall() if row[0]]
        currencies = [row[0] for row in conn.execute(text("SELECT DISTINCT currencycode FROM journalentryheader ORDER BY currencycode")).fetchall() if row[0]]
        years = [row[0] for row in conn.execute(text("SELECT DISTINCT fiscalyear FROM journalentryheader ORDER BY fiscalyear")).fetchall() if row[0]]
        periods = [row[0] for row in conn.execute(text("SELECT DISTINCT period FROM journalentryheader ORDER BY period")).fetchall() if row[0]]
    
    return companies, creators, currencies, years, periods

def show_journal_entry_lines_popup(document_number):
    """Show popup with journal entry lines for selected document"""
    st.subheader(f"📄 Journal Entry Lines - Document: {document_number}")
    
    query = """
    SELECT 
        jel.glaccountid,
        coa.accountname,
        jel.debitamount,
        jel.creditamount,
        jel.description,
        jel.reference
    FROM journalentryline jel
    JOIN glaccount coa ON coa.glaccountid = jel.glaccountid
    WHERE jel.documentnumber = :doc_num
    ORDER BY jel.glaccountid
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params={"doc_num": document_number})
    
    if not df.empty:
        # Format numbers
        df['debitamount'] = df['debitamount'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) and x != 0 else "")
        df['creditamount'] = df['creditamount'].apply(lambda x: f"{x:,.2f}" if pd.notna(x) and x != 0 else "")
        
        st.dataframe(df, use_container_width=True)
        
        # Show totals
        total_debits = df['debitamount'].str.replace(',', '').str.replace('', '0').astype(float).sum()
        total_credits = df['creditamount'].str.replace(',', '').str.replace('', '0').astype(float).sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Debits", f"{total_debits:,.2f}")
        with col2:
            st.metric("Total Credits", f"{total_credits:,.2f}")
        with col3:
            balance = total_debits - total_credits
            st.metric("Balance", f"{balance:,.2f}", delta=None if abs(balance) < 0.01 else "Unbalanced")
    else:
        st.warning("No journal entry lines found for this document.")

# Initialize session state for popup
if 'show_popup' not in st.session_state:
    st.session_state.show_popup = False
if 'selected_doc' not in st.session_state:
    st.session_state.selected_doc = None

# Show popup if requested
if st.session_state.show_popup and st.session_state.selected_doc:
    with st.expander(f"📋 Journal Entry Details - {st.session_state.selected_doc}", expanded=True):
        show_journal_entry_lines_popup(st.session_state.selected_doc)
        if st.button("❌ Close Details"):
            st.session_state.show_popup = False
            st.session_state.selected_doc = None
            st.rerun()

# Get filter options
companies, creators, currencies, years, periods = get_filter_options()

# Filter Section
with st.expander("🔍 Filter Options", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 Date Range")
        date_from = st.date_input("From Date", value=date(2025, 1, 1), key="date_from")
        date_to = st.date_input("To Date", value=date.today(), key="date_to")
        
        st.subheader("🏢 Company & User")
        selected_companies = st.multiselect("Company Code(s)", ["All"] + companies, default=["All"])
        selected_creators = st.multiselect("Created By", ["All"] + creators, default=["All"])
    
    with col2:
        st.subheader("💰 Currency & Period")
        selected_currencies = st.multiselect("Currency Code(s)", ["All"] + currencies, default=["All"])
        selected_years = st.multiselect("Fiscal Year(s)", ["All"] + years, default=["All"])
        selected_periods = st.multiselect("Period(s)", ["All"] + periods, default=["All"])
        
        st.subheader("📄 Document Search")
        doc_number_search = st.text_input("Document Number (contains)", "")
        reference_search = st.text_input("Reference (contains)", "")

    # Advanced Options
    with st.expander("⚙️ Advanced Options"):
        show_memo = st.checkbox("Show Memo Column", value=True)
        show_reference = st.checkbox("Show Reference Column", value=True)
        show_currency = st.checkbox("Show Currency Column", value=True)
        limit_records = st.number_input("Limit Records", min_value=0, max_value=10000, value=1000, step=100)

# Run Report Button
if st.button("🔍 Run Report", type="primary"):
    # Process filter selections
    if "All" in selected_companies:
        selected_companies = companies
    if "All" in selected_creators:
        selected_creators = creators
    if "All" in selected_currencies:
        selected_currencies = currencies
    if "All" in selected_years:
        selected_years = years
    if "All" in selected_periods:
        selected_periods = periods
    
    # Validate filters
    if not (selected_companies and selected_creators and date_from and date_to):
        st.error("⚠️ Please ensure Company Code(s) and Created By are selected, and date range is provided.")
        st.stop()
    
    # Build query
    where_conditions = ["documentdate BETWEEN :date_from AND :date_to"]
    params = {"date_from": date_from, "date_to": date_to}
    
    if selected_companies:
        comp_ph = ", ".join([f":comp{i}" for i in range(len(selected_companies))])
        where_conditions.append(f"companycodeid IN ({comp_ph})")
        params.update({f"comp{i}": v for i, v in enumerate(selected_companies)})
    
    if selected_creators:
        creator_ph = ", ".join([f":creator{i}" for i in range(len(selected_creators))])
        where_conditions.append(f"createdby IN ({creator_ph})")
        params.update({f"creator{i}": v for i, v in enumerate(selected_creators)})
    
    if selected_currencies:
        curr_ph = ", ".join([f":curr{i}" for i in range(len(selected_currencies))])
        where_conditions.append(f"currencycode IN ({curr_ph})")
        params.update({f"curr{i}": v for i, v in enumerate(selected_currencies)})
    
    if selected_years:
        year_ph = ", ".join([f":year{i}" for i in range(len(selected_years))])
        where_conditions.append(f"fiscalyear IN ({year_ph})")
        params.update({f"year{i}": v for i, v in enumerate(selected_years)})
    
    if selected_periods:
        period_ph = ", ".join([f":period{i}" for i in range(len(selected_periods))])
        where_conditions.append(f"period IN ({period_ph})")
        params.update({f"period{i}": v for i, v in enumerate(selected_periods)})
    
    if doc_number_search:
        where_conditions.append("UPPER(documentnumber) LIKE UPPER(:doc_search)")
        params["doc_search"] = f"%{doc_number_search}%"
    
    if reference_search:
        where_conditions.append("UPPER(reference) LIKE UPPER(:ref_search)")
        params["ref_search"] = f"%{reference_search}%"
    
    # Build column list
    columns = ["documentnumber", "documentdate", "companycodeid", "createdby", "createdat"]
    if show_reference:
        columns.append("reference")
    if show_currency:
        columns.append("currencycode")
    if show_memo:
        columns.append("memo")
    
    query = f"""
    SELECT {', '.join(columns)}
    FROM journalentryheader
    WHERE {' AND '.join(where_conditions)}
    ORDER BY documentdate DESC, documentnumber
    """
    
    if limit_records > 0:
        query += f" LIMIT {limit_records}"
    
    # Execute query
    with st.spinner("Generating report..."):
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params)
            
            if df.empty:
                st.warning("No records found with the selected filters.")
            else:
                st.subheader(f"📊 Results ({len(df)} records)")
                
                # Add clickable document numbers
                def make_clickable(doc_num):
                    return f'<a href="javascript:void(0)" onclick="streamlit.setComponentValue(\'{doc_num}\')">{doc_num}</a>'
                
                # Display dataframe with formatting
                st.dataframe(df, use_container_width=True)
                
                # Export options
                col1, col2 = st.columns(2)
                
                with col1:
                    # Excel export
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Journal_Listing')
                        workbook = writer.book
                        worksheet = writer.sheets['Journal_Listing']
                        
                        # Format columns
                        for idx, col in enumerate(df.columns):
                            if 'date' in col.lower():
                                worksheet.set_column(idx, idx, 12)
                            elif 'number' in col.lower():
                                worksheet.set_column(idx, idx, 15)
                            else:
                                worksheet.set_column(idx, idx, 20)
                    
                    st.download_button(
                        label="📤 Download Excel",
                        data=output.getvalue(),
                        file_name=f"Journal_Listing_{date.today().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                with col2:
                    # CSV export
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv,
                        file_name=f"Journal_Listing_{date.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                
                # Click handler for document numbers (using selectbox as workaround)
                st.subheader("🔍 View Journal Entry Details")
                doc_numbers = df['documentnumber'].unique().tolist()
                selected_doc = st.selectbox(
                    "Select a document number to view details:",
                    options=[""] + doc_numbers,
                    key="doc_selector"
                )
                
                if selected_doc and selected_doc != "":
                    if st.button(f"📄 View Details for {selected_doc}"):
                        st.session_state.selected_doc = selected_doc
                        st.session_state.show_popup = True
                        st.rerun()
                
        except Exception as e:
            st.error(f"Error generating report: {str(e)}")

# Navigation is now handled by the SAP-style sidebar
