import os
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

def safe_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0

# ========== DB SETUP ==========
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin123@localhost:5432/gl_erp")
engine = create_engine(DB_URL)

def fetch_journal_headers():
    try:
        df = pd.read_sql("SELECT documentnumber, postingdate FROM journalentryheader ORDER BY documentnumber DESC", engine)
        return df
    except Exception as e:
        return pd.DataFrame(columns=["documentnumber", "postingdate"])

def fetch_journal_header(doc_num):
    try:
        df = pd.read_sql(
            text("SELECT * FROM journalentryheader WHERE documentnumber = :doc"),
            engine, params={"doc": doc_num}
        )
        return df.iloc[0] if not df.empty else None
    except Exception as e:
        return None

def fetch_journal_lines(doc_num):
    try:
        return pd.read_sql(
            text("SELECT * FROM journalentryline WHERE documentnumber = :doc ORDER BY linenumber"),
            engine, params={"doc": doc_num}
        )
    except Exception as e:
        return pd.DataFrame(columns=[
            "linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode"
        ])

def save_journal(header: dict, lines: pd.DataFrame):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO journalentryheader
                    (documentnumber, postingdate, companycodeid, fiscalyear, period, reference, currencycode, createdby, memo)
                    VALUES (:doc, :pd, :cc, :fy, :per, :ref, :cur, :by, :memo)
                    ON CONFLICT (documentnumber, companycodeid) DO UPDATE SET
                    postingdate=EXCLUDED.postingdate,
                    fiscalyear=EXCLUDED.fiscalyear,
                    period=EXCLUDED.period,
                    reference=EXCLUDED.reference,
                    currencycode=EXCLUDED.currencycode,
                    createdby=EXCLUDED.createdby,
                    memo=EXCLUDED.memo
                """),
                {
                    "doc": header["documentnumber"],
                    "pd": header["postingdate"],
                    "cc": header["companycodeid"],
                    "fy": header["fiscalyear"],
                    "per": header["period"],
                    "ref": header["reference"],
                    "cur": header["currencycode"],
                    "by": header["createdby"],
                    "memo": header["memo"],
                }
            )
            conn.execute(
                text("DELETE FROM journalentryline WHERE documentnumber=:doc AND companycodeid=:cc"),
                {"doc": header["documentnumber"], "cc": header["companycodeid"]}
            )
            for idx, row in lines.dropna(subset=["glaccountid"]).iterrows():
                conn.execute(
                    text("""
                        INSERT INTO journalentryline
                        (documentnumber, companycodeid, linenumber, glaccountid, description, debitamount, creditamount, currencycode)
                        VALUES (:doc, :cc, :ln, :gl, :desc, :db, :cr, :cur)
                    """),
                    {
                        "doc": header["documentnumber"],
                        "cc": header["companycodeid"],
                        "ln": int(row["linenumber"]) if not pd.isna(row["linenumber"]) else (idx+1),
                        "gl": row["glaccountid"],
                        "desc": row["description"] if not pd.isna(row["description"]) else "",
                        "db": safe_float(row["debitamount"]) if "debitamount" in row else 0,
                        "cr": safe_float(row["creditamount"]) if "creditamount" in row else 0,
                        "cur": row["currencycode"] if not pd.isna(row["currencycode"]) else header["currencycode"]
                    }
                )
        return True, f"Journal Entry '{header['documentnumber']}' saved."
    except Exception as e:
        return False, f"Save failed: {e}"

# ========== UI HELPERS ==========
def show_header_form(header: dict, edit_mode: bool, currency_options):
    col1, col2 = st.columns(2)
    with col1:
        document_number = st.text_input("Document Number", value=header.get("documentnumber", ""), disabled=not edit_mode)
        posting_date = st.date_input("Posting Date", value=header.get("postingdate", date.today()), disabled=not edit_mode)
        company_code = st.text_input("Company Code", value=header.get("companycodeid", ""), disabled=not edit_mode)
        fiscal_year = st.number_input("Fiscal Year", value=int(header.get("fiscalyear", date.today().year)), step=1, disabled=not edit_mode)
    with col2:
        period = st.number_input("Period", value=int(header.get("period", 1)), step=1, disabled=not edit_mode)
        reference = st.text_input("Reference", value=header.get("reference", ""), disabled=not edit_mode)
        currency_code = st.selectbox("Currency", currency_options, index=currency_options.index(header.get("currencycode", "USD")) if header.get("currencycode", "USD") in currency_options else 0, disabled=not edit_mode)
        created_by = st.text_input("Created By", value=header.get("createdby", ""), disabled=not edit_mode)
        memo = st.text_area("Memo", value=header.get("memo", ""), disabled=not edit_mode)
    return {
        "documentnumber": document_number,
        "postingdate": posting_date,
        "companycodeid": company_code,
        "fiscalyear": fiscal_year,
        "period": period,
        "reference": reference,
        "currencycode": currency_code,
        "createdby": created_by,
        "memo": memo
    }

def show_lines_table(lines_df, edit_mode: bool, currency_options, key="editor"):
    expected_cols = ["linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode"]
    lines_editor = st.data_editor(
        lines_df,
        num_rows="dynamic" if edit_mode else "fixed",
        disabled=not edit_mode,
        key=key,
        use_container_width=True,
        column_order=expected_cols,
        column_config={
            "linenumber": st.column_config.NumberColumn("Line #", min_value=1),
            "glaccountid": st.column_config.TextColumn("GL Account"),
            "description": st.column_config.TextColumn("Description"),
            "debitamount": st.column_config.NumberColumn("Debit", min_value=0, step=0.01),
            "creditamount": st.column_config.NumberColumn("Credit", min_value=0, step=0.01),
            "currencycode": st.column_config.SelectboxColumn("Currency", options=currency_options),
        }
    )
    return lines_editor

def show_totals(lines_editor):
    real_lines = lines_editor if "glaccountid" in lines_editor.columns else pd.DataFrame()
    if "glaccountid" in real_lines.columns:
        real_lines = real_lines.dropna(subset=["glaccountid"])
    total_debit = real_lines["debitamount"].apply(safe_float).sum() if "debitamount" in real_lines.columns else 0
    total_credit = real_lines["creditamount"].apply(safe_float).sum() if "creditamount" in real_lines.columns else 0
    is_balanced = abs(total_debit - total_credit) < 0.01
    st.markdown(
        f"<div style='margin-top:1em;'><b>Total Debit:</b> {total_debit:.2f} &nbsp;&nbsp; <b>Total Credit:</b> {total_credit:.2f} &nbsp;&nbsp; <b>Balance:</b> {'✅' if is_balanced else '❌'}</div>",
        unsafe_allow_html=True
    )

def validate_lines(lines):
    if "glaccountid" not in lines.columns:
        return False, "No lines to validate."
    real = lines.dropna(subset=["glaccountid"])
    if len(real) < 2:
        return False, "At least two journal entry lines are required."
    if real["glaccountid"].isnull().any() or (real["glaccountid"].astype(str).str.strip() == "").any():
        return False, "GL Account is required on every line."
    total_debit = real["debitamount"].apply(safe_float).sum() if "debitamount" in real.columns else 0
    total_credit = real["creditamount"].apply(safe_float).sum() if "creditamount" in real.columns else 0
    if abs(total_debit - total_credit) > 0.01:
        return False, f"Debits ({total_debit:.2f}) and Credits ({total_credit:.2f}) must be equal."
    return True, "Valid!"

# ========== MAIN APP ==========
st.set_page_config(page_title="Journal Entry Manager", layout="wide")
st.title("Journal Entry Manager (Lowercase Schema)")

expected_cols = ["linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode"]
currency_options = ["USD", "PHP", "EUR", "JPY"]

if "edit_mode" not in st.session_state:
    st.session_state["edit_mode"] = False
if "current_doc" not in st.session_state:
    st.session_state["current_doc"] = None
if "header_cache" not in st.session_state:
    st.session_state["header_cache"] = None
if "lines_cache" not in st.session_state:
    st.session_state["lines_cache"] = None

headers_df = fetch_journal_headers()
doc_options = ["+ New Entry"] + headers_df["documentnumber"].tolist()

if st.session_state["edit_mode"]:
    st.sidebar.radio("Select Journal Entry (disabled in edit mode)", doc_options, index=doc_options.index(st.session_state["current_doc"]), disabled=True, key="sidebar_radio")
    st.sidebar.warning("Exit edit mode to switch documents.")
    selected_doc = st.session_state["current_doc"]
else:
    selected_doc = st.sidebar.radio("Select Journal Entry", doc_options, index=0 if st.session_state["current_doc"] is None else doc_options.index(st.session_state["current_doc"]))

doc_switched = selected_doc != st.session_state["current_doc"]
if not st.session_state["edit_mode"] and (doc_switched or st.session_state["header_cache"] is None or st.session_state["lines_cache"] is None):
    st.session_state["current_doc"] = selected_doc
    if selected_doc == "+ New Entry":
        st.session_state["header_cache"] = {
            "documentnumber": "",
            "postingdate": date.today(),
            "companycodeid": "",
            "fiscalyear": date.today().year,
            "period": 1,
            "reference": "",
            "currencycode": "USD",
            "createdby": "",
            "memo": ""
        }
        st.session_state["lines_cache"] = pd.DataFrame(columns=expected_cols)
    else:
        header_row = fetch_journal_header(selected_doc)
        st.session_state["header_cache"] = dict(header_row) if header_row is not None else {}
        lines_df = fetch_journal_lines(selected_doc)
        if lines_df.empty or any(col not in lines_df.columns for col in expected_cols):
            lines_df = pd.DataFrame(columns=expected_cols)
        else:
            lines_df = lines_df[expected_cols]
        st.session_state["lines_cache"] = lines_df.copy()

header = st.session_state["header_cache"]
lines_df = st.session_state["lines_cache"]

with st.form("journal_entry_form"):
    st.subheader("Header")
    header_input = show_header_form(header, st.session_state["edit_mode"], currency_options)
    st.markdown("---")
    st.subheader("Journal Entry Lines")
    lines_input = show_lines_table(lines_df, st.session_state["edit_mode"], currency_options, key="editor" if st.session_state["edit_mode"] else "viewer")
    show_totals(lines_input)

    button_cols = st.columns([1,1,1,1])
    action = None
    if st.session_state["edit_mode"]:
        with button_cols[0]:
            if st.form_submit_button("Save"):
                action = "save"
        with button_cols[1]:
            if st.form_submit_button("Cancel"):
                action = "cancel"
    else:
        with button_cols[0]:
            if st.form_submit_button("Edit"):
                action = "edit"
        with button_cols[1]:
            if st.form_submit_button("Validate"):
                action = "validate"
        with button_cols[2]:
            if st.form_submit_button("Export"):
                action = "export"

if action == "edit":
    st.session_state["edit_mode"] = True
    st.session_state["lines_cache"] = lines_input.copy()
    st.experimental_rerun()

if action == "cancel":
    st.session_state["edit_mode"] = False
    if st.session_state["current_doc"] == "+ New Entry":
        st.session_state["header_cache"] = {
            "documentnumber": "",
            "postingdate": date.today(),
            "companycodeid": "",
            "fiscalyear": date.today().year,
            "period": 1,
            "reference": "",
            "currencycode": "USD",
            "createdby": "",
            "memo": ""
        }
        st.session_state["lines_cache"] = pd.DataFrame(columns=expected_cols)
    else:
        header_row = fetch_journal_header(st.session_state["current_doc"])
        st.session_state["header_cache"] = dict(header_row) if header_row is not None else {}
        lines_df = fetch_journal_lines(st.session_state["current_doc"])
        if lines_df.empty or any(col not in lines_df.columns for col in expected_cols):
            lines_df = pd.DataFrame(columns=expected_cols)
        else:
            lines_df = lines_df[expected_cols]
        st.session_state["lines_cache"] = lines_df.copy()
    st.experimental_rerun()

if action == "save":
    ok, msg = validate_lines(lines_input)
    if not ok:
        st.error(msg)
    else:
        saved, save_msg = save_journal(header_input, lines_input)
        if saved:
            st.session_state["edit_mode"] = False
            st.session_state["header_cache"] = header_input
            st.session_state["lines_cache"] = fetch_journal_lines(header_input["documentnumber"])
            st.success(save_msg)
            st.experimental_rerun()
        else:
            st.error(save_msg)

if action == "validate":
    ok, msg = validate_lines(lines_input)
    if ok:
        st.success(msg)
    else:
        st.error(msg)

if action == "export":
    def generate_excel(df_lines, header_data):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_lines.to_excel(writer, sheet_name="Lines", index=False)
            pd.DataFrame([header_data]).to_excel(writer, sheet_name="Header", index=False)
        output.seek(0)
        return output
    out = generate_excel(lines_input, header_input)
    st.download_button("Download Excel File", data=out, file_name=f"{header_input['documentnumber']}.xlsx")
