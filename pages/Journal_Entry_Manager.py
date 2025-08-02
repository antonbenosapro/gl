import streamlit as st
import pandas as pd
from sqlalchemy import text
import os
from datetime import datetime
import io
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    st.warning("ReportLab not available. PDF generation will use alternative method.")

# Alternative PDF generation using weasyprint or basic HTML
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

# --- Database Setup ---
from db_config import engine
from utils.validation import (
    JournalEntryHeaderValidator, 
    JournalEntryLineValidator,
    validate_journal_entry_balance,
    ValidationError
)
from utils.logger import StreamlitLogHandler, log_database_operation, get_logger
from auth.middleware import authenticator
from utils.navigation import show_sap_sidebar, show_breadcrumb

logger = get_logger("journal_entry_manager")


# --- Cached Function ---
@st.cache_data(ttl=30)  # Cache for 30 seconds to reduce database load
def get_all_docs():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT documentnumber, companycodeid FROM journalentryheader ORDER BY documentnumber DESC LIMIT 1000"))
            return [(row[0], row[1]) for row in result]
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        return []

# --- Utility Functions ---
def generate_next_doc_number():
    try:
        docs = [doc for doc, _ in get_all_docs()]
        if not docs:
            return "JE00001"
        last_num = [int(s[2:]) for s in docs if s.startswith("JE") and s[2:].isdigit()]
        next_num = max(last_num) + 1 if last_num else 1
        return f"JE{next_num:05d}"
    except Exception as e:
        logger.error(f"Error generating document number: {e}")
        import random
        return f"JE{random.randint(10000, 99999):05d}"  # Fallback to random number

def enforce_column_order(df, desired_order):
    return df[[col for col in desired_order if col in df.columns]]

def generate_journal_entry_html(hdr, lines_df, doc_number, company_code):
    """Generate HTML for journal entry"""
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Journal Entry - {doc_number}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
            .info-table td {{ padding: 8px; border: 1px solid #ccc; }}
            .info-table .label {{ background-color: #f5f5f5; font-weight: bold; width: 20%; }}
            .lines-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            .lines-table th, .lines-table td {{ padding: 8px; border: 1px solid #ccc; text-align: left; }}
            .lines-table th {{ background-color: #f5f5f5; font-weight: bold; }}
            .lines-table .amount {{ text-align: right; }}
            .totals {{ background-color: #f5f5f5; font-weight: bold; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            .balance-check {{ margin-top: 15px; font-weight: bold; }}
            .balanced {{ color: green; }}
            .unbalanced {{ color: red; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>JOURNAL ENTRY</h1>
        </div>
        
        <table class="info-table">
            <tr>
                <td class="label">Document Number:</td>
                <td>{hdr["documentnumber"]}</td>
                <td class="label">Company Code:</td>
                <td>{hdr["companycodeid"]}</td>
            </tr>
            <tr>
                <td class="label">Posting Date:</td>
                <td>{hdr["postingdate"]}</td>
                <td class="label">Document Date:</td>
                <td>{hdr["documentdate"]}</td>
            </tr>
            <tr>
                <td class="label">Fiscal Year:</td>
                <td>{hdr["fiscalyear"]}</td>
                <td class="label">Period:</td>
                <td>{hdr["period"]}</td>
            </tr>
            <tr>
                <td class="label">Currency Code:</td>
                <td>{hdr["currencycode"]}</td>
                <td class="label">Created By:</td>
                <td>{hdr["createdby"]}</td>
            </tr>
            <tr>
                <td class="label">Reference:</td>
                <td colspan="3">{hdr["reference"]}</td>
            </tr>
        </table>
        
        <h2>JOURNAL ENTRY LINES</h2>
        <table class="lines-table">
            <thead>
                <tr>
                    <th>Line</th>
                    <th>GL Account</th>
                    <th>Description</th>
                    <th>Debit</th>
                    <th>Credit</th>
                    <th>Currency</th>
                </tr>
            </thead>
            <tbody>
    """
    
    if not lines_df.empty:
        total_debit = 0
        total_credit = 0
        
        for _, row in lines_df.iterrows():
            debit_amt = float(row['Debit Amount']) if row['Debit Amount'] else 0
            credit_amt = float(row['Credit Amount']) if row['Credit Amount'] else 0
            total_debit += debit_amt
            total_credit += credit_amt
            
            html_content += f"""
                <tr>
                    <td>{row['Line Number']}</td>
                    <td>{row['GL Account ID']}</td>
                    <td>{row['Description']}</td>
                    <td class="amount">{'${:,.2f}'.format(debit_amt) if debit_amt > 0 else ''}</td>
                    <td class="amount">{'${:,.2f}'.format(credit_amt) if credit_amt > 0 else ''}</td>
                    <td>{row['Currency Code']}</td>
                </tr>
            """
        
        # Add totals row
        html_content += f"""
                <tr class="totals">
                    <td colspan="3">TOTALS:</td>
                    <td class="amount">${total_debit:,.2f}</td>
                    <td class="amount">${total_credit:,.2f}</td>
                    <td></td>
                </tr>
        """
        
        # Balance check
        balance_diff = total_debit - total_credit
        balance_class = "balanced" if abs(balance_diff) < 0.01 else "unbalanced"
        balance_text = "✓ Entry is balanced" if abs(balance_diff) < 0.01 else f"⚠ Out of balance by: ${balance_diff:,.2f}"
        
        html_content += f"""
            </tbody>
        </table>
        <div class="balance-check {balance_class}">
            {balance_text}
        </div>
        """
    else:
        html_content += """
                <tr>
                    <td colspan="6">No journal entry lines found.</td>
                </tr>
            </tbody>
        </table>
        """
    
    html_content += f"""
        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </body>
    </html>
    """
    
    return html_content

def generate_journal_entry_pdf(hdr, lines_df, doc_number, company_code):
    """Generate PDF for journal entry"""
    if not REPORTLAB_AVAILABLE:
        # Fallback to HTML download
        html_content = generate_journal_entry_html(hdr, lines_df, doc_number, company_code)
        return html_content.encode('utf-8'), 'html'
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Create styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT
    )
    
    # Build PDF content
    story = []
    
    # Title
    title = Paragraph("JOURNAL ENTRY", title_style)
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Header information table
    header_data = [
        ['Document Number:', str(hdr["documentnumber"]), 'Company Code:', str(hdr["companycodeid"])],
        ['Posting Date:', str(hdr["postingdate"]), 'Document Date:', str(hdr["documentdate"])],
        ['Fiscal Year:', str(hdr["fiscalyear"]), 'Period:', str(hdr["period"])],
        ['Currency Code:', str(hdr["currencycode"]), 'Created By:', str(hdr["createdby"])],
        ['Reference:', str(hdr["reference"]), '', '']
    ]
    
    header_table = Table(header_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 2*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Make labels bold
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),  # Make labels bold
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
    ]))
    
    story.append(header_table)
    story.append(Spacer(1, 20))
    
    # Journal Entry Lines
    story.append(Paragraph("JOURNAL ENTRY LINES", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    if not lines_df.empty:
        # Prepare lines data
        lines_data = [['Line', 'GL Account', 'Description', 'Debit', 'Credit', 'Currency']]
        
        total_debit = 0
        total_credit = 0
        
        for _, row in lines_df.iterrows():
            debit_amt = float(row['Debit Amount']) if row['Debit Amount'] else 0
            credit_amt = float(row['Credit Amount']) if row['Credit Amount'] else 0
            total_debit += debit_amt
            total_credit += credit_amt
            
            lines_data.append([
                str(row['Line Number']),
                str(row['GL Account ID']),
                str(row['Description'])[:30] + ('...' if len(str(row['Description'])) > 30 else ''),
                f"{debit_amt:,.2f}" if debit_amt > 0 else "",
                f"{credit_amt:,.2f}" if credit_amt > 0 else "",
                str(row['Currency Code'])
            ])
        
        # Add totals row
        lines_data.append(['', '', 'TOTALS:', f"{total_debit:,.2f}", f"{total_credit:,.2f}", ''])
        
        lines_table = Table(lines_data, colWidths=[0.7*inch, 1.2*inch, 2.5*inch, 1*inch, 1*inch, 0.8*inch])
        lines_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Totals row
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 1), (4, -1), 'RIGHT'),  # Right align amounts
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # Header background
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  # Totals background
        ]))
        
        story.append(lines_table)
        
        # Balance check
        story.append(Spacer(1, 12))
        balance_diff = total_debit - total_credit
        if abs(balance_diff) < 0.01:
            balance_text = "✓ Entry is balanced"
            balance_style = styles['Normal']
        else:
            balance_text = f"⚠ Out of balance by: {balance_diff:,.2f}"
            balance_style = styles['Normal']
        
        story.append(Paragraph(balance_text, balance_style))
    else:
        story.append(Paragraph("No journal entry lines found.", styles['Normal']))
    
    # Add footer
    story.append(Spacer(1, 30))
    footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes, 'pdf'

# --- UI Initialization ---
def initialize_session():
    for key, val in {"mode": "view_list", "current_doc": None, "delete_confirm": False}.items():
        if key not in st.session_state:
            st.session_state[key] = val

def document_selector(docs):
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
    return docs_filtered

# --- UI Layout ---
def render_header_buttons():
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

# --- Mode Handlers ---
def handle_view_entry():
    if not isinstance(st.session_state.current_doc, tuple) or len(st.session_state.current_doc) != 2:
        st.error("Invalid document selection.")
        return
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
        # Define column order for view mode (same as edit mode)
        view_column_ids = ["linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode", "ledgerid"]
        
        # Ensure proper column order before renaming
        df_view = enforce_column_order(df_view, view_column_ids)
        
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
            f"**Total Debit:** {df_view['Debit Amount'].sum():,.2f}\u2003"
            f"**Total Credit:** {df_view['Credit Amount'].sum():,.2f}"
        )
    else:
        st.info("No entry lines for this document.")
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("📄 Print to PDF"):
            try:
                result, file_type = generate_journal_entry_pdf(hdr, df_view, doc, cc)
                
                if file_type == 'pdf':
                    st.download_button(
                        label="📥 Download PDF",
                        data=result,
                        file_name=f"Journal_Entry_{doc}_{cc}.pdf",
                        mime="application/pdf"
                    )
                    st.success("PDF generated successfully!")
                else:  # HTML fallback
                    st.download_button(
                        label="📥 Download HTML",
                        data=result,
                        file_name=f"Journal_Entry_{doc}_{cc}.html",
                        mime="text/html"
                    )
                    st.info("Downloaded as HTML file (print using browser)")
                    
            except Exception as e:
                st.error(f"Error generating file: {str(e)}")
    
    with col2:
        if st.button("Back to List"):
            st.session_state.mode = "view_list"

def handle_edit_entry(current_user):
    hdr = None
    if st.session_state.mode == "edit" and isinstance(st.session_state.current_doc, tuple) and len(st.session_state.current_doc) == 2:
        doc, cc = st.session_state.current_doc
        with engine.connect() as conn:
            hdr = conn.execute(
                text("SELECT * FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                {"doc": doc, "cc": cc}
            ).mappings().first()
    else:
        doc = generate_next_doc_number()
        cc = ""

    st.header("📝 Journal Entry Header")
    left, right = st.columns(2, gap="large")
    with left:
        st.text_input("Document Number", value=doc, disabled=True)
        cc = st.text_input("Company Code", value=cc, key="hdr_cc")
        fy = st.number_input("Fiscal Year", value=hdr["fiscalyear"] if hdr else pd.to_datetime("today").year, step=1)
        per = st.number_input("Period", value=hdr["period"] if hdr else 1, step=1)
    with right:
        pdate = st.date_input("Posting Date", value=hdr["postingdate"] if hdr else pd.to_datetime("today"))
        ddate = st.date_input("Document Date", value=hdr["documentdate"] if hdr else pd.to_datetime("today"))
        ref = st.text_input("Reference", value=hdr["reference"] if hdr else "")
        cur = st.text_input("Currency Code", value=hdr["currencycode"] if hdr else "")
        cb = st.text_input("Created By", value=hdr["createdby"] if hdr else current_user.username, disabled=True)

    st.divider()
    st.header("📋 Entry Lines")
    column_ids = ["linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode", "ledgerid"]

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
        df = pd.DataFrame(columns=column_ids)
    df = df.dropna(how="all").fillna("")
    df["linenumber"] = range(1, len(df) + 1)
    
    # Ensure proper column order before displaying in data_editor
    df = enforce_column_order(df, column_ids)
    
    # Set default currency for new rows if not already set
    if 'currencycode' in df.columns and cur:
        df['currencycode'] = df['currencycode'].fillna(cur)
        df.loc[df['currencycode'] == '', 'currencycode'] = cur

    # Create column config in the desired order
    column_config = {}
    for c in column_ids:
        if c == "currencycode":
            column_config[c] = st.column_config.TextColumn(
                "Currency Code",
                default=cur if cur else "",
                disabled=False
            )
        else:
            column_config[c] = st.column_config.Column(
                c.replace("_", " ").title(), 
                disabled=(c == "linenumber")
            )
    
    edited = st.data_editor(
        df,
        column_config=column_config,
        column_order=column_ids,
        use_container_width=True,
        num_rows="dynamic",
        disabled=["linenumber"],
        hide_index=True
    )
    edited["linenumber"] = range(1, len(edited) + 1)
    required_fields = ["glaccountid", "description", "debitamount", "creditamount"]
    edited = edited.dropna(subset=required_fields, how="all").reset_index(drop=True)
    
    # Ensure column order is maintained after all processing
    edited = enforce_column_order(edited, column_ids)
    edited["linenumber"] = range(1, len(edited) + 1)  # Re-apply line numbers after ordering

    debit_total = pd.to_numeric(edited["debitamount"], errors="coerce").fillna(0).sum()
    credit_total = pd.to_numeric(edited["creditamount"], errors="coerce").fillna(0).sum()
    st.write(f"**Total Debit:** {debit_total:,.2f} **Total Credit:** {credit_total:,.2f}")

    errors = []
    
    # Validate header
    try:
        header_data = {
            'documentnumber': doc,
            'companycodeid': cc,
            'postingdate': pdate,
            'documentdate': ddate,
            'fiscalyear': fy,
            'period': per,
            'reference': ref,
            'currencycode': cur,
            'createdby': cb
        }
        JournalEntryHeaderValidator(**header_data)
    except ValidationError as e:
        errors.extend(str(e).split('\n'))
    except ValueError as e:
        errors.append(str(e))
    
    # Validate lines
    if len(edited) == 0:
        errors.append("No entry lines to save!")
    else:
        try:
            line_validators = []
            for i, row in edited.iterrows():
                line_data = {
                    'linenumber': i + 1,
                    'glaccountid': str(row.get('glaccountid', '')),
                    'description': str(row.get('description', '')),
                    'debitamount': float(row.get('debitamount') or 0),
                    'creditamount': float(row.get('creditamount') or 0),
                    'currencycode': str(row.get('currencycode', cur)),
                    'ledgerid': str(row.get('ledgerid', ''))
                }
                line_validator = JournalEntryLineValidator(**line_data)
                line_validator.validate_debit_credit_balance()
                line_validators.append(line_validator)
            
            # Validate overall balance
            validate_journal_entry_balance(line_validators)
            
        except ValidationError as e:
            errors.append(str(e))
        except ValueError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
    
    for err in errors:
        st.warning(err)

    if st.button("💾 Save Journal Entry", disabled=bool(errors)):
        upsert_hdr = """
            INSERT INTO journalentryheader
            (documentnumber, companycodeid, postingdate, documentdate, fiscalyear, period, reference, currencycode, createdby)
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
                    (documentnumber, companycodeid, linenumber, glaccountid, description, debitamount, creditamount, currencycode, ledgerid)
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

def handle_delete_entry():
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

def handle_view_list(docs_filtered):
    st.header("📂 Existing Journal Entries")
    with engine.connect() as conn:
        df = pd.read_sql("SELECT * FROM journalentryheader ORDER BY documentnumber DESC", conn)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No journal entries found.")

# --- Main App ---
def main():
    # Configure page
    st.set_page_config(page_title="📄 Journal Entry Manager", layout="wide", initial_sidebar_state="expanded")
    
    # Require authentication and permission
    authenticator.require_auth()
    authenticator.require_permission("journal.read")
    
    # SAP-Style Navigation
    show_sap_sidebar()
    show_breadcrumb("Journal Entry Manager", "Transactions", "Management")
    
    initialize_session()
    current_user = authenticator.get_current_user()
    StreamlitLogHandler.log_page_access("Journal Entry Manager", current_user.username)
    
    st.title("📄 Journal Entry Management")
    render_header_buttons()
    st.divider()

    docs = get_all_docs()
    docs_filtered = document_selector(docs)

    if st.session_state.mode == "view_entry" and st.session_state.current_doc:
        handle_view_entry()
    elif st.session_state.mode == "edit":
        handle_edit_entry(current_user)
    elif st.session_state.mode == "add":
        handle_edit_entry(current_user)
    elif st.session_state.mode == "delete" and st.session_state.current_doc:
        handle_delete_entry()
    elif st.session_state.mode == "view_list":
        handle_view_list(docs_filtered)

    st.divider()

    # Navigation is now handled by the SAP-style sidebar

if __name__ == "__main__":
    main()
