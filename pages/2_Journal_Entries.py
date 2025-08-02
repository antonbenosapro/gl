
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import os

# --- Database Connection ---
from db_config import engine

st.set_page_config(page_title="Browse Journal Entries", layout="wide")
st.title("📋 Browse All Journal Entries")

# --- UI State ---
if "show_full_table" not in st.session_state:
    st.session_state.show_full_table = st.checkbox("Show All by Default", help="Tick to always show all entries on load.")

if "selected_header" not in st.session_state:
    st.session_state.selected_header = None

if st.button("Show All Journal Entries"):
    st.session_state.show_full_table = True

if st.session_state.get("show_full_table", False):
    with engine.connect() as conn:
        headers = pd.read_sql("SELECT * FROM journalentryheader ORDER BY documentnumber DESC, companycodeid", conn)

    if headers.empty:
        st.info("No journal entries found.")
    else:
        headers["postingdate"] = pd.to_datetime(headers["postingdate"]).dt.date

        # --- Filters ---
        st.markdown("### 🔎 Filter Options")
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        with filter_col1:
            search_text = st.text_input("Search Any Field", "")
        with filter_col2:
            fy_options = ['All'] + sorted([str(y) for y in headers['fiscalyear'].dropna().unique()])
            fy_filter = st.selectbox("Fiscal Year", fy_options)
        with filter_col3:
            comp_options = ['All'] + sorted([str(c) for c in headers['companycodeid'].dropna().unique()])
            comp_filter = st.selectbox("Company Code", comp_options)
        with filter_col4:
            cb_options = ['All'] + sorted([str(c) for c in headers['createdby'].dropna().unique()])
            cb_filter = st.selectbox("Created By", cb_options)

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            min_date = headers["postingdate"].min()
            max_date = headers["postingdate"].max()
            date_range = st.date_input("Posting Date Range", [min_date, max_date])

        # --- Apply Filters ---
        filtered = headers.copy()
        if fy_filter != 'All':
            filtered = filtered[filtered['fiscalyear'] == int(fy_filter)]
        if comp_filter != 'All':
            filtered = filtered[filtered['companycodeid'] == comp_filter]
        if cb_filter != 'All':
            filtered = filtered[filtered['createdby'] == cb_filter]
        if date_range and len(date_range) == 2:
            start = pd.Timestamp(date_range[0])
            end = pd.Timestamp(date_range[1])
            filtered = filtered[
                (pd.to_datetime(filtered['postingdate']) >= start) &
                (pd.to_datetime(filtered['postingdate']) <= end)
            ]
        if search_text:
            mask = pd.Series([False] * len(filtered))
            for col in filtered.select_dtypes(include='object').columns:
                mask = mask | filtered[col].str.contains(search_text, case=False, na=False)
            filtered = filtered[mask]

        filtered["id_key"] = filtered["documentnumber"] + "|" + filtered["companycodeid"]

        # --- Display Filtered Header ---
        st.markdown("### 📑 Filtered Journal Entry Headers")
        st.dataframe(filtered.drop(columns="id_key"), use_container_width=True, height=350)

        # --- Download CSV ---
        csv_data = filtered.drop(columns="id_key").to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Filtered Headers (CSV)", data=csv_data, file_name="JE_Headers.csv")

        # --- Select and View Lines ---
        entry_options = filtered["id_key"].tolist()
        entry_labels = [
            f"{row['documentnumber']} | {row['companycodeid']} | {row['postingdate']}"
            for _, row in filtered.iterrows()
        ]
        if entry_options:
            selected = st.selectbox(
                "Select Journal Entry to View Lines",
                options=entry_options,
                format_func=lambda k: entry_labels[entry_options.index(k)],
                key="selected_detail_entry"
            )
            sel_doc, sel_cc = selected.split("|")
            with engine.connect() as conn:
                lines = pd.read_sql(
                    "SELECT * FROM journalentryline WHERE documentnumber=%s AND companycodeid=%s ORDER BY linenumber",
                    conn, params=(sel_doc, sel_cc)
                )

            # Format amounts
            if not lines.empty:
                for amt_col in ["debitamount", "creditamount"]:
                    if amt_col in lines:
                        lines[amt_col] = pd.to_numeric(lines[amt_col], errors="coerce").fillna(0).map("{:,.2f}".format)

            st.markdown(f"### 📄 Entry Lines for Doc#: `{sel_doc}`, Company: `{sel_cc}`")
            with st.expander("📄 View Journal Entry Lines", expanded=True):
                st.dataframe(lines, use_container_width=True)
                if not lines.empty and "debitamount" in lines and "creditamount" in lines:
                    st.write(
                        f"**Total Debit:** {lines['debitamount'].str.replace(',','').astype(float).sum():,.2f}  "
                        f"**Total Credit:** {lines['creditamount'].str.replace(',','').astype(float).sum():,.2f}"
                    )
        else:
            st.warning("No entries match the current filters.")