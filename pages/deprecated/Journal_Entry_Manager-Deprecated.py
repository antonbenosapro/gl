import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:admin123@localhost:5432/gl_erp"
)
engine = create_engine(DATABASE_URL)

@st.cache_data
def get_all_docs():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT documentnumber, companycodeid FROM journalentryheader ORDER BY documentnumber DESC")
        )
        return [(row[0], row[1]) for row in result]

def generate_next_doc_number():
    docs = [doc for doc, _ in get_all_docs()]
    if not docs:
        return "JE00001"
    last_num = [int(s[2:]) for s in docs if s.startswith("JE") and s[2:].isdigit()]
    next_num = max(last_num) + 1 if last_num else 1
    return f"JE{next_num:05d}"

if "mode" not in st.session_state:
    st.session_state.mode = "view_list"
if "current_doc" not in st.session_state:
    st.session_state.current_doc = None  # tuple: (documentnumber, companycodeid)
if "delete_confirm" not in st.session_state:
    st.session_state.delete_confirm = False

st.title("📒 Journal Entry Management")

btns = st.container()
with btns:
    col_add, col_view, col_edit, col_del = st.columns([1,1,1,1], gap="small")
    with col_add:
        if st.button("➕ ADD"):
            st.session_state.mode = "add"
            st.session_state.current_doc = None
    with col_view:
        if st.button("🔍 VIEW"):
            st.session_state.mode = "view_entry"
    with col_edit:
        if st.button("✏️ EDIT"):
            st.session_state.mode = "edit"
    with col_del:
        if st.button("🗑️ DELETE"):
            st.session_state.mode = "delete"
            st.session_state.delete_confirm = False

st.divider()

# Document filter/search
docs = get_all_docs()
search_term = st.text_input("Search Document Number", "", placeholder="Type to filter...").strip().upper()
docs_filtered = [d for d in docs if search_term in d[0].upper()]
doc_display = [f"{doc} | {cc}" for doc, cc in docs_filtered]
doc_dict = {f"{doc} | {cc}": (doc, cc) for doc, cc in docs_filtered}

if st.session_state.mode in ("view_entry", "edit", "delete"):
    options = ["<new>"] + doc_display
    idx = 0
    if st.session_state.current_doc:
        try:
            idx = doc_display.index(f"{st.session_state.current_doc[0]} | {st.session_state.current_doc[1]}") + 1
        except:
            idx = 0
    choice = st.selectbox("Select Document", options, index=idx, key="doc_choice")
    st.session_state.current_doc = None if choice == "<new>" else doc_dict[choice]

# VIEW ENTRY logic
if st.session_state.mode == "view_entry" and st.session_state.current_doc:
    doc, cc = st.session_state.current_doc
    with engine.connect() as conn:
        hdr = conn.execute(
            text("SELECT * FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
            {"doc": doc, "cc": cc}
        ).mappings().first()
        lines = conn.execute(
            text("""
                SELECT linenumber, glaccountid, description,
                       debitamount, creditamount, currencycode, ledgerid
                FROM journalentryline
                WHERE documentnumber = :doc AND companycodeid = :cc
                ORDER BY linenumber
            """),
            {"doc": doc, "cc": cc}
        ).mappings().all()
    st.header("📝 Journal Entry Header (View Only)")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.text_input("Document Number", hdr["documentnumber"], disabled=True)
        st.text_input("Company Code", hdr["companycodeid"], disabled=True)
        st.number_input("Fiscal Year", hdr["fiscalyear"], disabled=True)
        st.number_input("Period", hdr["period"], disabled=True)
    with c2:
        st.date_input("Posting Date", hdr["postingdate"], disabled=True)
        st.date_input("Document Date", hdr["documentdate"], disabled=True)
        st.text_input("Reference", hdr["reference"], disabled=True)
        st.text_input("Currency Code", hdr["currencycode"], disabled=True)
        st.text_input("Created By", hdr["createdby"], disabled=True)
    st.divider()
    st.header("📋 Entry Lines (View Only)")
    df_view = pd.DataFrame(lines)
    if not df_view.empty:
        df_view = df_view.rename(columns={
            "linenumber": "Line Number",
            "glaccountid": "GL Account ID",
            "description": "Description",
            "debitamount": "Debit Amount",
            "creditamount": "Credit Amount",
            "currencycode": "Currency Code",
            "ledgerid": "Ledger ID"
        })
        st.dataframe(df_view, use_container_width=True)
        st.write(
            f"**Total Debit:** {df_view['Debit Amount'].sum():,.2f}  "
            f"**Total Credit:** {df_view['Credit Amount'].sum():,.2f}"
        )
    else:
        st.info("No entry lines for this document.")
    if st.button("Back to List"):
        st.session_state.mode = "view_list"

# DELETE logic with confirmation
elif st.session_state.mode == "delete" and st.session_state.current_doc:
    doc, cc = st.session_state.current_doc
    if not st.session_state.delete_confirm:
        st.warning(f"Are you sure you want to delete journal entry '{doc} | {cc}'?")
        if st.button("Confirm Delete", type="primary"):
            st.session_state.delete_confirm = True
        if st.button("Cancel"):
            st.session_state.mode = "view_list"
    else:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM journalentryline WHERE documentnumber = :doc AND companycodeid = :cc"),
                {"doc": doc, "cc": cc}
            )
            conn.execute(
                text("DELETE FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                {"doc": doc, "cc": cc}
            )
        st.success(f"Deleted journal entry '{doc} | {cc}'.")
        st.session_state.mode = "view_list"
        st.session_state.delete_confirm = False
        get_all_docs.clear()

# ADD / EDIT logic
elif st.session_state.mode in ("add", "edit"):
    hdr = None
    if st.session_state.mode == "edit" and st.session_state.current_doc:
        doc, cc = st.session_state.current_doc
        with engine.connect() as conn:
            hdr = conn.execute(
                text("SELECT * FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                {"doc": doc, "cc": cc}
            ).mappings().first()

    st.header("📝 Journal Entry Header")
    left, right = st.columns(2, gap="large")
    with left:
        if st.session_state.mode == "add":
            doc = generate_next_doc_number()
            cc = st.text_input("Company Code", value="", key="hdr_cc")
            st.info(f"Document Number: {doc}")
        else:
            doc = hdr["documentnumber"]
            cc = hdr["companycodeid"]
            st.text_input("Document Number", value=doc, disabled=True, key="hdr_doc")
            st.text_input("Company Code", value=cc, disabled=True, key="hdr_cc")
        fy = st.number_input("Fiscal Year", value=hdr["fiscalyear"] if hdr else pd.to_datetime("today").year, step=1, key="hdr_fy")
        per = st.number_input("Period", value=hdr["period"] if hdr else 1, step=1, key="hdr_per")
    with right:
        pdate = st.date_input("Posting Date", value=hdr["postingdate"] if hdr else pd.to_datetime("today"), key="hdr_pdate")
        ddate = st.date_input("Document Date", value=hdr["documentdate"] if hdr else pd.to_datetime("today"), key="hdr_ddate")
        ref = st.text_input("Reference", value=hdr["reference"] if hdr else "", key="hdr_ref")
        cur = st.text_input("Currency Code", value=hdr["currencycode"] if hdr else "", key="hdr_cur")
        cb = st.text_input("Created By", value=hdr["createdby"] if hdr else "", key="hdr_cb")

    st.divider()
    st.header("📋 Entry Lines")
    columns = [
        {"id": "linenumber", "name": "Line Number"},
        {"id": "glaccountid", "name": "GL Account ID"},
        {"id": "description", "name": "Description"},
        {"id": "debitamount", "name": "Debit Amount"},
        {"id": "creditamount", "name": "Credit Amount"},
        {"id": "currencycode", "name": "Currency Code"},
        {"id": "ledgerid", "name": "Ledger ID"}
    ]
    if hdr:
        with engine.connect() as conn:
            rows = conn.execute(
                text("""
                    SELECT linenumber, glaccountid, description, debitamount, creditamount, currencycode, ledgerid
                    FROM journalentryline
                    WHERE documentnumber = :doc AND companycodeid = :cc
                    ORDER BY linenumber
                """),
                {"doc": doc, "cc": cc}
            ).mappings().all()
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(columns=[col["id"] for col in columns])
    df = df.dropna(how="all")
    df = df.fillna("")
    df["linenumber"] = range(1, len(df) + 1)
    edited = st.data_editor(
        df,
        column_config={ 
            "linenumber": st.column_config.Column("Line Number", disabled=True),
            "glaccountid": st.column_config.Column("GL Account ID"),
            "description": st.column_config.Column("Description"),
            "debitamount": st.column_config.Column("Debit Amount"),
            "creditamount": st.column_config.Column("Credit Amount"),
            "currencycode": st.column_config.Column("Currency Code"),
            "ledgerid": st.column_config.Column("Ledger ID"),
        },
        use_container_width=True,
        num_rows="dynamic",
        disabled=["linenumber"],
        hide_index=True
    )
    edited["linenumber"] = range(1, len(edited) + 1)
    required_fields = ["glaccountid", "description", "debitamount", "creditamount"]
    edited = edited.dropna(subset=required_fields, how="all")
    edited = edited.reset_index(drop=True)
    
    debit_total = pd.to_numeric(edited["debitamount"], errors="coerce").fillna(0).sum() if not edited.empty else 0
    credit_total = pd.to_numeric(edited["creditamount"], errors="coerce").fillna(0).sum() if not edited.empty else 0
    st.write(f"**Total Debit:** {debit_total:,.2f}  **Total Credit:** {credit_total:,.2f}")

    error_msgs = []

    if cc == "":
        error_msgs.append("Company Code cannot be empty!")
    if cur == "":
        error_msgs.append("Currency Code cannot be empty!")
    
    if len(edited) == 0:            
        
       error_msgs.append("No entry lines to save!" )       
           
    
    if abs(debit_total - credit_total) > 1e-2:
        error_msgs.append("Debits and Credits must be equal before saving!")
     
  
    for msg in error_msgs:
        st.warning(msg)

    if st.button("💾 Save Journal Entry", disabled=bool(error_msgs)):

       
            upsert_hdr = """
                INSERT INTO journalentryheader
                (documentnumber, companycodeid, postingdate, documentdate,
                fiscalyear, period, reference, currencycode, createdby)
                VALUES (:doc,:cc,:pdate,:ddate,:fy,:per,:ref,:cur,:cb)
                ON CONFLICT (documentnumber, companycodeid) DO UPDATE SET
                    postingdate  =EXCLUDED.postingdate,
                    documentdate =EXCLUDED.documentdate,
                    fiscalyear   =EXCLUDED.fiscalyear,
                    period       =EXCLUDED.period,
                    reference    =EXCLUDED.reference,
                    currencycode =EXCLUDED.currencycode,
                    createdby    =EXCLUDED.createdby;
            """
            with engine.begin() as conn:
                conn.execute(text(upsert_hdr), {
                    "doc": doc, "cc": cc, "pdate": pdate, "ddate": ddate,
                    "fy": fy,  "per": per, "ref": ref, "cur": cur, "cb": cb
                })
                conn.execute(
                    text("DELETE FROM journalentryline WHERE documentnumber = :doc AND companycodeid = :cc"),
                    {"doc": doc, "cc": cc}
                )
                for i, row in enumerate(edited.itertuples(index=False), start=1):
                    conn.execute(text("""
                        INSERT INTO journalentryline
                        (documentnumber, companycodeid, linenumber, glaccountid,
                        description, debitamount, creditamount, currencycode, ledgerid)
                        VALUES (:doc,:cc,:ln,:ga,:desc,:dr,:cr,:cur,:ld)
                    """), {
                        "doc": doc, "cc": cc,
                        "ln": i,
                        "ga": row.glaccountid,
                        "desc": row.description,
                        "dr": float(row.debitamount) if row.debitamount else 0,
                        "cr": float(row.creditamount) if row.creditamount else 0,
                        "cur": row.currencycode,
                        "ld": row.ledgerid
                    })
            st.success(f"Journal Entry '{doc} | {cc}' saved ({len(edited)} lines).")
            st.session_state.mode = "view_list"
            get_all_docs.clear()
    if st.button("Back to List"):
        st.session_state.mode = "view_list"

elif st.session_state.mode == "view_list":
    st.header("📂 Existing Journal Entries")
    df_list = pd.DataFrame(docs_filtered, columns=["documentnumber", "companycodeid"])
    if not df_list.empty:
        df_list["ID"] = df_list["documentnumber"] + " | " + df_list["companycodeid"]
        st.table(df_list[["ID"]])
    else:
        st.table(pd.DataFrame([["No entries found"]], columns=["documentnumber | companycodeid"]))
    st.divider()


# import pages.Journal_Listing_Report as jl_report

# with st.expander("📑 Journal Listing", expanded=False):
#     jl_report.render_filtered_journal_listing()
