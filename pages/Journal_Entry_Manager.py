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
from utils.field_status_validation import (
    field_status_engine,
    validate_journal_entry_line,
    PostingData,
    FieldStatusValidationError
)
from utils.logger import StreamlitLogHandler, log_database_operation, get_logger
from auth.optimized_middleware import optimized_authenticator as authenticator
from utils.navigation import show_sap_sidebar, show_breadcrumb
from utils.workflow_engine import WorkflowEngine

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

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_document_types():
    """Get available document types for dropdown"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT document_type, document_type_name, description 
                FROM document_types 
                WHERE is_active = TRUE 
                ORDER BY document_type
            """))
            return [(row[0], f"{row[0]} - {row[1]}", row[2]) for row in result]
    except Exception as e:
        logger.error(f"Error fetching document types: {e}")
        return [("SA", "SA - General Journal Entry", "Standard journal entry for general ledger postings")]

# --- Utility Functions ---
def generate_next_doc_number(company_code="1000", prefix="JE", max_retries=3, min_number=1, max_number=99999):
    """
    Generate next document number using database sequence for bulletproof concurrency.
    Creates and uses company-specific sequences to guarantee unique numbers.
    
    Args:
        company_code: Company code for the document
        prefix: Document number prefix (e.g., 'JE')  
        max_retries: Maximum retry attempts for sequence creation
        min_number: Minimum number to start from (default: 1)
        max_number: Maximum number allowed (default: 99999)
    """
    import time
    import random
    
    sequence_name = f"doc_seq_{company_code}_{prefix.lower()}"
    
    for attempt in range(max_retries):
        try:
            with engine.begin() as conn:
                # Ensure sequence exists for this company and prefix
                try:
                    # Check if sequence exists
                    seq_check = conn.execute(text("""
                        SELECT EXISTS(
                            SELECT 1 FROM pg_class 
                            WHERE relkind = 'S' AND relname = :seq_name
                        )
                    """), {"seq_name": sequence_name})
                    
                    sequence_exists = seq_check.fetchone()[0]
                    
                    if not sequence_exists:
                        # Find the current maximum number for this company/prefix to initialize sequence
                        max_result = conn.execute(text("""
                            SELECT COALESCE(
                                MAX(CAST(SUBSTRING(documentnumber FROM :prefix_len + 1) AS INTEGER)), 
                                :min_num - 1
                            ) as max_num
                            FROM journalentryheader 
                            WHERE documentnumber ~ :regex_pattern 
                            AND companycodeid = :company_code
                            AND CAST(SUBSTRING(documentnumber FROM :prefix_len + 1) AS INTEGER) BETWEEN :min_num AND :max_num
                        """), {
                            "prefix_len": len(prefix),
                            "regex_pattern": f"^{prefix}[0-9]+$",
                            "company_code": company_code,
                            "min_num": min_number,
                            "max_num": max_number
                        })
                        
                        current_max = max_result.fetchone()[0]
                        start_value = max(current_max + 1, min_number)
                        
                        # Create the sequence
                        conn.execute(text(f"""
                            CREATE SEQUENCE {sequence_name}
                            START WITH {start_value}
                            INCREMENT BY 1
                            MINVALUE {min_number}
                            MAXVALUE {max_number}
                            CACHE 1
                        """))
                        
                        logger.info(f"Created sequence {sequence_name} starting at {start_value}")
                
                except Exception as seq_error:
                    # If sequence creation fails, another process might have created it
                    if "already exists" not in str(seq_error).lower():
                        logger.warning(f"Sequence creation issue: {seq_error}")
                
                # Get next number from sequence
                next_result = conn.execute(text(f"SELECT nextval('{sequence_name}')"))
                next_num = next_result.fetchone()[0]
                
                # Check if we've exceeded the maximum (sequence should prevent this, but be safe)
                if next_num > max_number:
                    logger.error(f"Sequence {sequence_name} exceeded maximum value {max_number}")
                    # Reset sequence to find gaps or raise error
                    raise Exception(f"Document number sequence exceeded maximum {max_number}")
                
                # Generate the new document number
                new_doc_number = f"{prefix}{next_num:05d}"
                
                # Verify this number doesn't already exist (should be impossible with sequence, but double-check)
                check_result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM journalentryheader 
                    WHERE documentnumber = :doc_num 
                    AND companycodeid = :company_code
                """), {
                    "doc_num": new_doc_number,
                    "company_code": company_code
                })
                
                if check_result.fetchone()[0] > 0:
                    logger.warning(f"Generated number {new_doc_number} already exists! This should not happen with sequences.")
                    # This is very rare - sequence gave us a duplicate number
                    # Try once more
                    if attempt < max_retries - 1:
                        continue
                    else:
                        raise Exception(f"Sequence generated duplicate number: {new_doc_number}")
                
                logger.info(f"Generated document number: {new_doc_number} from sequence (attempt {attempt + 1})")
                return new_doc_number
                    
        except Exception as e:
            logger.error(f"Error generating document number (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                # Wait a bit before retrying
                time.sleep(random.uniform(0.1, 0.3))
                continue
    
    # Fallback: use timestamp-based unique number with process info
    from datetime import datetime
    import os
    import threading
    
    timestamp = datetime.now()
    thread_id = threading.current_thread().ident % 1000
    microseconds = timestamp.microsecond // 1000  # Convert to milliseconds
    
    # Create a highly unique fallback number
    fallback_num = f"{prefix}{timestamp.strftime('%H%M%S')}{thread_id:03d}"[-8:]  # Ensure max 8 chars after prefix
    logger.warning(f"Using fallback document number after {max_retries} attempts: {fallback_num}")
    return fallback_num

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
    for key, val in {"mode": "search", "current_doc": None, "delete_confirm": False}.items():
        if key not in st.session_state:
            st.session_state[key] = val

def document_selector(docs):
    """Simple document number search with recent documents sidebar"""
    
    # Add recent documents to sidebar
    with st.sidebar:
        st.subheader("📋 Recent Documents")
        try:
            with engine.connect() as conn:
                recent_docs = conn.execute(text("""
                    SELECT documentnumber, companycodeid, workflow_status, reference, 
                           createdat, createdby
                    FROM journalentryheader 
                    ORDER BY createdat DESC 
                    LIMIT 15
                """)).fetchall()
                
                if recent_docs:
                    for doc in recent_docs:
                        doc_number = doc[0]
                        company_code = doc[1]
                        workflow_status = doc[2] or 'DRAFT'
                        reference = doc[3] or 'No ref'
                        created_at = doc[4]
                        created_by = doc[5]
                        
                        # Status color coding
                        status_color = {
                            'DRAFT': '🟡',
                            'PENDING_APPROVAL': '🟠',
                            'APPROVED': '🟢',
                            'POSTED': '🔵',
                            'REJECTED': '🔴',
                            'REVERSED': '⚫'
                        }.get(workflow_status, '⚪')
                        
                        if st.button(
                            f"{status_color} {doc_number}",
                            help=f"Ref: {reference}\nBy: {created_by}\nStatus: {workflow_status}",
                            key=f"sidebar_doc_{doc_number}_{company_code}",
                            use_container_width=True
                        ):
                            st.session_state.current_doc = doc_number
                            st.session_state.current_company = company_code
                            if st.session_state.mode not in ["view_entry", "edit", "reverse"]:
                                st.session_state.mode = "view_entry"
                            st.rerun()
                else:
                    st.info("No recent documents")
        except Exception as e:
            st.error(f"Error loading recent docs: {e}")
    
    # Only show search interface for modes that need document selection
    if st.session_state.mode in ["view_entry", "edit", "delete"]:
        st.subheader("🔍 **Find Document**")
        
        # Simple search input
        search_term = st.text_input(
            "📄 Enter Document Number", 
            placeholder="e.g., JE00001, JE00123...",
            help="Enter full or partial document number to search"
        ).strip().upper()
        
        if search_term:
            # Search for matching documents
            try:
                with engine.connect() as conn:
                    results = conn.execute(text("""
                        SELECT documentnumber, companycodeid, postingdate, reference, 
                               createdby, status, createdat
                        FROM journalentryheader 
                        WHERE documentnumber ILIKE :search
                        ORDER BY createdat DESC
                        LIMIT 20
                    """), {"search": f"%{search_term}%"})
                    
                    matching_docs = list(results)
                    
                    if matching_docs:
                        st.success(f"✅ Found {len(matching_docs)} matching documents")
                        
                        # Create simple selection
                        doc_options = ["<Select a document>"] + [
                            f"{doc[0]} | {doc[1]} - {doc[3] or 'No reference'} ({doc[5]})"
                            for doc in matching_docs
                        ]
                        
                        selected = st.selectbox(
                            "Select Document:",
                            doc_options,
                            key="simple_doc_select"
                        )
                        
                        if selected != "<Select a document>":
                            # Parse selection
                            doc_parts = selected.split(" | ")
                            if len(doc_parts) >= 2:
                                doc_number = doc_parts[0]
                                company_parts = doc_parts[1].split(" - ")
                                company_code = company_parts[0]
                                
                                st.session_state.current_doc = (doc_number, company_code)
                                st.success(f"✅ **Selected:** {doc_number} | {company_code}")
                    else:
                        st.warning(f"⚠️ No documents found matching '{search_term}'")
                        st.session_state.current_doc = None
                        
            except Exception as e:
                st.error(f"Search error: {e}")
                st.session_state.current_doc = None
        else:
            st.info("💡 Enter a document number above to search")
            st.session_state.current_doc = None
    
    return []



# --- UI Layout ---
def render_header_buttons():
    btns = st.container()
    with btns:
        col_add, col_view, col_edit, col_del = st.columns([1,1,1,1], gap="small")
        with col_add:
            if st.button("➕ ADD"):
                st.session_state.mode = "add"
                st.session_state.current_doc = None
                # Clear any cached data for fresh start
                get_all_docs.clear()
                st.rerun()
        with col_view:
            if st.button("🔍 VIEW"):
                if st.session_state.current_doc:
                    st.session_state.mode = "view_entry"
                    st.rerun()
                else:
                    st.session_state.mode = "view_entry"
                    st.rerun()
        with col_edit:
            if st.button("✏️ EDIT"):
                if st.session_state.current_doc:
                    st.session_state.mode = "edit"
                    st.rerun()
                else:
                    st.session_state.mode = "edit"
                    st.rerun()
        with col_del:
            if st.button("🗑️ DELETE"):
                if st.session_state.current_doc:
                    st.session_state.mode = "delete"
                    st.session_state.delete_confirm = False
                    st.rerun()
                else:
                    st.session_state.mode = "delete"
                    st.session_state.delete_confirm = False
                    # Clear current selection to force user to select document for deletion
                    st.session_state.current_doc = None
                    st.rerun()

# --- Mode Handlers ---
def handle_view_entry():
    if not isinstance(st.session_state.current_doc, tuple) or len(st.session_state.current_doc) != 2:
        st.error("🚫 **Invalid document selection.** Please select a valid journal entry from the list.")
        if st.button("🔙 Back to Search"):
            st.session_state.mode = "search"
            st.rerun()
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
                       debitamount, creditamount, currencycode, business_unit_id, ledgerid
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
        st.text_area("Memo", value=hdr["memo"] if hdr["memo"] else "", disabled=True, height=80)
        st.text_input("Currency Code", hdr["currencycode"], disabled=True)
        st.text_input("Created By", hdr["createdby"], disabled=True)
        
        # Show workflow status
        workflow_status = hdr.get("workflow_status", "DRAFT")
        status_colors = {
            'DRAFT': '🟡 DRAFT',
            'PENDING_APPROVAL': '🟠 PENDING APPROVAL',
            'APPROVED': '🟢 APPROVED',
            'POSTED': '🔵 POSTED',
            'REJECTED': '🔴 REJECTED',
            'REVERSED': '⚫ REVERSED'
        }
        status_display = status_colors.get(workflow_status, f'⚪ {workflow_status}')
        st.text_input("Workflow Status", status_display, disabled=True)

    st.divider()
    st.header("📋 Entry Lines (View Only)")
    df_view = pd.DataFrame(lines)
    if not df_view.empty:
        # Define column order for view mode (same as edit mode)
        view_column_ids = ["linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode", "business_unit_id", "ledgerid"]
        
        # Ensure proper column order before renaming
        df_view = enforce_column_order(df_view, view_column_ids)
        
        df_view = df_view.rename(columns={
            "linenumber": "Line Number",
            "glaccountid": "GL Account ID",
            "description": "Description",
            "debitamount": "Debit Amount",
            "creditamount": "Credit Amount",
            "currencycode": "Currency Code",
            "business_unit_id": "Business Unit",
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
                st.error(f"📄 **File Generation Error:** Unable to create the report file. Please try again or contact support if the issue persists.")
    
    with col2:
        if st.button("🔙 Back to Search"):
            st.session_state.mode = "search"

def handle_edit_entry(current_user):
    hdr = None
    
    # Clear any form-related session state when starting a new entry (add mode)
    if st.session_state.mode == "add":
        # Clear any cached form data that might interfere with new entry
        for key in list(st.session_state.keys()):
            if key.startswith('hdr_') or key.startswith('gl_') or key.startswith('detail_'):
                del st.session_state[key]
    
    if st.session_state.mode == "edit" and isinstance(st.session_state.current_doc, tuple) and len(st.session_state.current_doc) == 2:
        doc, cc = st.session_state.current_doc
        with engine.connect() as conn:
            hdr = conn.execute(
                text("SELECT * FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                {"doc": doc, "cc": cc}
            ).mappings().first()
            
            # Check if document is reversed - prevent editing
            if hdr and hdr.get('status') == 'REVERSED':
                st.error("🚫 **Cannot Edit Reversed Entry**")
                st.warning(f"This journal entry has been reversed by document: **{hdr.get('reversed_by')}**")
                st.info(f"**Reversal Date:** {hdr.get('reversal_date')}")
                st.info(f"**Reversal Reason:** {hdr.get('reversal_reason', 'N/A')}")
                st.write("**Reversed entries cannot be modified to maintain audit trail integrity.**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔍 View Original Entry"):
                        st.session_state.mode = "view_entry"
                        st.rerun()
                with col2:
                    if st.button("🔙 Back to Search"):
                        st.session_state.mode = "search"
                        st.rerun()
                return
            
            # Check workflow status - prevent editing if not DRAFT
            workflow_status = hdr.get('workflow_status', 'DRAFT') if hdr else 'DRAFT'
            if hdr and workflow_status != 'DRAFT':
                st.error("🚫 **Cannot Edit Document in Workflow**")
                st.warning(f"This journal entry is in **{workflow_status}** status and cannot be edited.")
                st.info("🔒 Only DRAFT documents can be edited. Once a document enters the workflow, editing is prevented to maintain data integrity.")
                
                # Show workflow information
                if workflow_status == 'PENDING_APPROVAL':
                    st.info("📋 This document is currently awaiting approval.")
                elif workflow_status == 'APPROVED':
                    st.info("✅ This document has been approved and is ready for posting.")
                elif workflow_status == 'POSTED':
                    st.info("📊 This document has been posted to the General Ledger.")
                elif workflow_status == 'REJECTED':
                    st.info("❌ This document has been rejected and may need to be recreated.")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔍 View Document"):
                        st.session_state.mode = "view_entry"
                        st.rerun()
                with col2:
                    if st.button("🔙 Back to Search"):
                        st.session_state.mode = "search"
                        st.rerun()
                return
    else:
        cc = "1000"  # Default company code
        doc = generate_next_doc_number(company_code=cc)
        hdr = None

    st.header("📝 Journal Entry Header")
    left, right = st.columns(2, gap="large")
    with left:
        # Handle company code changes for new entries
        if not hdr:  # Only for new entries
            new_cc = st.text_input("Company Code", value=cc, key="hdr_cc")
            if new_cc != cc:
                # Company code changed, regenerate document number
                cc = new_cc
                doc = generate_next_doc_number(company_code=cc)
        else:
            cc = st.text_input("Company Code", value=cc, key="hdr_cc")
        
        st.text_input("Document Number", value=doc, disabled=True)
        fy = st.number_input("Fiscal Year", value=hdr["fiscalyear"] if hdr else datetime.now().year, step=1)
        per = st.number_input("Period", value=hdr["period"] if hdr else datetime.now().month, step=1)
    with right:
        # Document Type selection
        doc_types = get_document_types()
        doc_type_options = [dt[1] for dt in doc_types]  # Display names
        doc_type_codes = [dt[0] for dt in doc_types]    # Actual codes
        
        # Get current document type (from header or default to SA)
        current_doc_type = hdr.get("document_type", "SA") if hdr else "SA"
        
        # Find index of current document type
        try:
            current_index = doc_type_codes.index(current_doc_type)
        except ValueError:
            current_index = doc_type_codes.index("SA") if "SA" in doc_type_codes else 0
        
        selected_doc_type_index = st.selectbox(
            "Document Type",
            range(len(doc_type_options)),
            format_func=lambda x: doc_type_options[x],
            index=current_index,
            help="Select the document type - affects FSG validation rules"
        )
        
        doc_type = doc_type_codes[selected_doc_type_index]
        
        pdate = st.date_input("Posting Date", value=hdr["postingdate"] if hdr else datetime.now().date())
        ddate = st.date_input("Document Date", value=hdr["documentdate"] if hdr else datetime.now().date())
        ref = st.text_input("Reference", value=hdr["reference"] if hdr else "")
        memo = st.text_area("Memo", value=hdr["memo"] if hdr and hdr["memo"] else "", help="Optional memo or notes for this journal entry", height=80)
        cur = st.text_input("Currency Code", value=hdr["currencycode"] if hdr else "USD")
        cb = st.text_input("Created By", value=hdr["createdby"] if hdr else current_user.username, disabled=True)

    st.divider()
    st.header("📋 Entry Lines")
    column_ids = ["linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode", "business_unit_id", "ledgerid", "tax_code", "business_area", "reference", "assignment", "text"]
    
    # Debug: Check if we're in edit mode
    st.write(f"Debug: Edit mode = {bool(hdr)}, doc = {doc}, cc = {cc}")

    try:
        if hdr:
            st.write("Debug: Loading existing journal lines...")
            with engine.connect() as conn:
                rows = conn.execute(
                    text("""
                        SELECT linenumber, glaccountid, description, debitamount, creditamount, currencycode, 
                               business_unit_id, ledgerid, tax_code, business_area, reference, assignment, text
                        FROM journalentryline
                        WHERE documentnumber = :doc AND companycodeid = :cc
                        ORDER BY linenumber
                    """),
                    {"doc": doc, "cc": cc}
                ).mappings().all()
            st.write(f"Debug: Found {len(rows)} existing lines")
            df = pd.DataFrame(rows)
        else:
            st.write("Debug: Creating new journal entry...")
            df = pd.DataFrame(columns=column_ids)
        
        st.write(f"Debug: DataFrame shape before processing: {df.shape}")
        df = df.dropna(how="all").fillna("")
        df["linenumber"] = range(1, len(df) + 1)
        st.write(f"Debug: DataFrame shape after processing: {df.shape}")
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.write("Creating empty DataFrame as fallback...")
        df = pd.DataFrame(columns=column_ids)
        df["linenumber"] = range(1, len(df) + 1)
    
    # Ensure proper column order before displaying in data_editor
    df = enforce_column_order(df, column_ids)
    
    # Debug information - can be removed once issue is resolved
    st.write("DataFrame Info:")
    st.write(f"Shape: {df.shape}")
    st.write(f"Columns: {list(df.columns)}")
    st.write(f"Column IDs: {column_ids}")
    if not df.empty:
        st.write("First few rows:")
        st.dataframe(df.head())
    
    # Set default currency for new rows if not already set
    if 'currencycode' in df.columns and cur:
        df['currencycode'] = df['currencycode'].fillna(cur)
        df.loc[df['currencycode'] == '', 'currencycode'] = cur
    
    # ENTERPRISE FEATURE: Set default ledger for entries with NULL/empty ledgerid
    st.write("Debug: Setting default ledger...")
    if 'ledgerid' in df.columns:
        # Simplified - just use L1 as default to avoid service import issues
        df['ledgerid'] = df['ledgerid'].fillna('L1')
        df.loc[df['ledgerid'] == '', 'ledgerid'] = 'L1'
    st.write("Debug: Default ledger set successfully")
    st.write("Debug: About to process FSG functions...")

    # 🛡️ ENTERPRISE FSG FEATURE: Dynamic column configuration based on Field Status Groups
    # ISSUE: These function definitions should not be in the middle of execution flow!
    # Moving these to avoid execution hanging
    st.write("Debug: Skipping FSG function definitions...")
    
    # COMMENTED OUT - Function definitions should not be in execution flow
    # def get_fsg_field_status(gl_account_id, field_name):
    #     """Get field status (REQ/OPT/SUP/DIS) for a field based on FSG rules."""
    #     return 'OPT'  # Simplified for now
    
    # COMMENTED OUT - All function definitions moved to avoid execution flow issues
    # def get_field_status_help_text(field_status):
    #     return 'Field status unknown'
    
    # def detect_dis_field_violations(edited, original_data, doc_type):
    #     return []  # Simplified for now
    
    st.write("Debug: Function definitions skipped, continuing to column configuration...")
    
    # Create column config with FSG-aware field controls
    st.write("Debug: Starting column configuration...")
    column_config = {}
    fsg_controlled_fields = ['business_unit_id', 'tax_code', 'business_area', 'reference', 'assignment', 'text']
    
    try:
        for c in column_ids:
            st.write(f"Debug: Configuring column {c}")
            if c == "currencycode":
                column_config[c] = st.column_config.TextColumn(
                    "Currency Code",
                    default=cur if cur else "",
                    disabled=False
                )
            elif c == "ledgerid":
                # Simplified Ledger configuration
                column_config[c] = st.column_config.TextColumn(
                    "Ledger ID",
                    default="L1",
                    help="Enter ledger ID (L1, 2L, 3L, 4L, CL)",
                    disabled=False
                )
            elif c in fsg_controlled_fields:
                # 🛡️ FSG-controlled field configuration
                # Note: For data_editor, we'll handle suppression through validation rather than hiding columns
                # since Streamlit data_editor doesn't support dynamic column visibility per row
                
                field_title = c.replace("_", " ").title()
                help_text = f"Field controlled by FSG rules (REQ=Required, SUP=Suppressed, DIS=Display Only, OPT=Optional)"
                
                if c == 'business_unit_id':
                    # Business Unit with dropdown options using generated_code
                    try:
                        with engine.connect() as conn:
                            bu_result = conn.execute(text("""
                                SELECT generated_code, unit_name FROM business_units 
                                WHERE is_active = TRUE 
                                  AND generated_code IS NOT NULL 
                                  AND generated_code <> ''
                                ORDER BY unit_name
                                LIMIT 100
                            """))
                            rows = bu_result.fetchall()
                            if rows:
                                bu_options = [f"{row[0]} - {row[1][:30]}..." if len(row[1]) > 30 else f"{row[0]} - {row[1]}" for row in rows]
                            else:
                                bu_options = []
                        
                        if bu_options:
                            column_config[c] = st.column_config.SelectboxColumn(
                                "Business Unit",
                                help=f"{help_text} - Select from active business units (Format: ProductLine+Location)",
                                options=bu_options,
                                required=False  # FSG validation will handle requirements
                            )
                        else:
                            # No business units found, fallback to text input
                            column_config[c] = st.column_config.TextColumn(
                                "Business Unit Code",
                                help=f"{help_text} - Enter business unit code (ProductLine+Location format, e.g., 5110270200)",
                                disabled=False
                            )
                    except Exception as e:
                        # Database error or connection issue - fallback to text input
                        column_config[c] = st.column_config.TextColumn(
                            "Business Unit Code", 
                            help=f"{help_text} - Enter business unit code (ProductLine+Location format, e.g., 5110270200)",
                            disabled=False
                        )
                elif c == 'tax_code':
                    # Tax Code with common options
                    tax_options = ['V1', 'V2', 'V3', 'I1', 'I2', 'I3', 'A1', 'A2', 'A3']
                    column_config[c] = st.column_config.SelectboxColumn(
                    "Tax Code",
                    help=f"{help_text} - Select applicable tax code",
                    options=tax_options,
                    required=False  # FSG validation will handle requirements
                )
                elif c == 'business_area':
                    # Business Area with common options  
                    area_options = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'US', 'INTL', 'CORP']
                    column_config[c] = st.column_config.SelectboxColumn(
                        "Business Area",
                        help=f"{help_text} - Select business area",
                        options=area_options,
                        required=False  # FSG validation will handle requirements
                    )
                else:
                    # Text fields (reference, assignment, text)
                    column_config[c] = st.column_config.TextColumn(
                        field_title,
                        help=f"{help_text} - {field_title} field",
                        disabled=False
                    )
            else:
                column_config[c] = st.column_config.Column(
                    c.replace("_", " ").title(), 
                    disabled=(c == "linenumber")
                )
    
    except Exception as e:
        st.error(f"⚠️ Error configuring columns: {e}")
        # Fallback to basic column configuration
        column_config = {c: st.column_config.Column(c.replace("_", " ").title()) for c in column_ids}
    
    st.write("Debug: About to create data_editor...")
    st.write(f"Debug: DataFrame shape: {df.shape}, Column config keys: {list(column_config.keys())}")
    
    try:
        st.write("Debug: Creating enhanced data_editor...")
        edited = st.data_editor(
            df,
            column_config=column_config,
            column_order=column_ids,
            use_container_width=True,
            num_rows="dynamic",
            disabled=["linenumber"],
            hide_index=True
        )
        st.write("Debug: Enhanced data_editor created successfully!")
    except Exception as e:
        st.error(f"⚠️ Error loading enhanced data editor: {e}")
        st.write("Debug: Falling back to basic data editor...")
        try:
            # Fallback to basic data editor
            edited = st.data_editor(
                df,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )
            st.write("Debug: Basic data_editor created successfully!")
        except Exception as e2:
            st.error(f"⚠️ Error with basic data editor too: {e2}")
            st.write("Debug: Using fallback display...")
            st.dataframe(df)
            edited = df.copy()
    edited["linenumber"] = range(1, len(edited) + 1)
    required_fields = ["glaccountid", "description", "debitamount", "creditamount"]
    edited = edited.dropna(subset=required_fields, how="all").reset_index(drop=True)
    
    # Ensure column order is maintained after all processing
    edited = enforce_column_order(edited, column_ids)
    edited["linenumber"] = range(1, len(edited) + 1)  # Re-apply line numbers after ordering

    debit_total = pd.to_numeric(edited["debitamount"], errors="coerce").fillna(0).sum()
    credit_total = pd.to_numeric(edited["creditamount"], errors="coerce").fillna(0).sum()
    st.write(f"**Total Debit:** {debit_total:,.2f} **Total Credit:** {credit_total:,.2f}")

    # 🛡️ FSG FIELD SUPPRESSION WARNINGS - Display immediately after data entry
    if not edited.empty:
        fsg_warnings = []
        fsg_info_messages = []
        
        for i, row in edited.iterrows():
            line_number = i + 1
            gl_account = str(row.get('glaccountid', '')).strip()
            
            if gl_account:  # Only check lines with GL accounts
                try:
                    fsg = field_status_engine.get_effective_field_status_group(
                        document_type=doc_type,
                        gl_account_id=gl_account
                    )
                    
                    if fsg:
                        # Check each FSG-controlled field for suppression/requirement violations
                        field_checks = {
                            'business_unit_id': (fsg.business_unit_status.value, row.get('business_unit_id', '')),
                            'tax_code': (fsg.tax_code_status.value, row.get('tax_code', '')),
                            'business_area': (fsg.business_area_status.value, row.get('business_area', '')),
                            'reference': (fsg.reference_status.value, row.get('reference', '')),
                            'assignment': (fsg.assignment_status.value, row.get('assignment', '')),
                            'text': (fsg.text_status.value, row.get('text', ''))
                        }
                        
                        line_has_issues = False
                        for field_name, (status, value) in field_checks.items():
                            field_display = field_name.replace('_', ' ').title()
                            
                            # Proper null value handling for pandas DataFrame
                            if pd.isna(value) or value is None:
                                has_value = False
                                value_str = ""
                            else:
                                value_str = str(value).strip()
                                has_value = value_str and value_str not in ['', 'nan', 'None', 'none', 'NaN']
                            
                            if status == 'SUP' and has_value:
                                fsg_warnings.append(f"🚫 Line {line_number} - {field_display} is **suppressed** for GL Account {gl_account} but has value: '{value_str}'")
                                line_has_issues = True
                            elif status == 'DIS' and has_value:
                                fsg_warnings.append(f"👁️ Line {line_number} - {field_display} is **display-only** for GL Account {gl_account}")
                                line_has_issues = True
                            elif status == 'REQ' and not has_value:
                                fsg_warnings.append(f"🔴 Line {line_number} - {field_display} is **required** for GL Account {gl_account}")
                                line_has_issues = True
                        
                        # Show FSG info for this line if it has active requirements
                        if not line_has_issues:
                            requirements = []
                            for field_name, (status, value) in field_checks.items():
                                if status == 'REQ':
                                    requirements.append(field_name.replace('_', ' ').title())
                            
                            if requirements:
                                fsg_info_messages.append(f"ℹ️ Line {line_number} (GL {gl_account}) - FSG **{fsg.group_id}** requires: {', '.join(requirements)}")
                        
                except Exception as e:
                    logger.warning(f"FSG suppression check failed for line {line_number}: {e}")
        
        # Display FSG warnings and info
        if fsg_warnings:
            st.warning("🛡️ **Field Status Group Violations:**")
            for warning in fsg_warnings[:5]:  # Show max 5 warnings to avoid clutter
                st.write(f"• {warning}")
            if len(fsg_warnings) > 5:
                st.write(f"• ... and {len(fsg_warnings) - 5} more issues")
        
        # Always show FSG info for active GL accounts (not just when no warnings)
        if fsg_info_messages:
            with st.expander("🛡️ FSG Field Requirements", expanded=fsg_warnings and len(fsg_warnings) > 0):
                for info in fsg_info_messages[:3]:  # Show max 3 info messages
                    st.info(info)
                    
        # Debug: Show FSG detection for troubleshooting
        if st.checkbox("🔍 Debug FSG Detection", help="Show FSG detection details for troubleshooting"):
            st.write("**FSG Debug Information:**")
            for i, row in edited.iterrows():
                line_number = i + 1
                gl_account = str(row.get('glaccountid', '')).strip()
                if gl_account:
                    try:
                        fsg = field_status_engine.get_effective_field_status_group(
                            document_type=doc_type,
                            gl_account_id=gl_account
                        )
                        if fsg:
                            st.write(f"Line {line_number} - GL {gl_account}: FSG **{fsg.group_id}** - BU Status: **{fsg.business_unit_status.value}**")
                            bu_value = row.get('business_unit_id', '')
                            st.write(f"  → Business Unit Value: '{bu_value}' (Type: {type(bu_value)}, Is NaN: {pd.isna(bu_value)})")
                        else:
                            st.write(f"Line {line_number} - GL {gl_account}: No FSG found")
                    except Exception as e:
                        st.write(f"Line {line_number} - GL {gl_account}: FSG Error - {e}")

    errors = []
    
    # 🔍 GL Account Validation - Validate all GL accounts before allowing save
    if not edited.empty:
        st.subheader("🔍 GL Account Validation")
        
        # Get all unique GL accounts from the entry lines
        gl_accounts_to_validate = edited['glaccountid'].dropna().unique()
        
        if len(gl_accounts_to_validate) > 0:
            try:
                with engine.connect() as conn:
                    # Check which GL accounts exist in the database
                    placeholders = ','.join([f':acc_{i}' for i in range(len(gl_accounts_to_validate))])
                    params = {f'acc_{i}': acc for i, acc in enumerate(gl_accounts_to_validate)}
                    
                    existing_accounts_result = conn.execute(text(f"""
                        SELECT glaccountid, accountname, accounttype, account_class
                        FROM glaccount 
                        WHERE glaccountid IN ({placeholders})
                        AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)
                    """), params)
                    
                    existing_accounts = {row[0]: {
                        'name': row[1], 
                        'type': row[2], 
                        'class': row[3]
                    } for row in existing_accounts_result}
                    
                    # Display validation results
                    valid_accounts = []
                    invalid_accounts = []
                    
                    for gl_account in gl_accounts_to_validate:
                        if str(gl_account).strip() == '' or pd.isna(gl_account):
                            continue
                            
                        if gl_account in existing_accounts:
                            valid_accounts.append({
                                'account': gl_account,
                                'name': existing_accounts[gl_account]['name'],
                                'type': existing_accounts[gl_account]['type'],
                                'class': existing_accounts[gl_account]['class']
                            })
                        else:
                            invalid_accounts.append(gl_account)
                            errors.append(f"📊 GL Account '{gl_account}' does not exist or is marked for deletion")
                    
                    # Display validation results in a nice format
                    if valid_accounts:
                        st.success(f"✅ **{len(valid_accounts)} Valid GL Accounts:**")
                        valid_df = pd.DataFrame(valid_accounts)
                        st.dataframe(valid_df, use_container_width=True, hide_index=True)
                    
                    if invalid_accounts:
                        st.error(f"❌ **{len(invalid_accounts)} Invalid GL Accounts:**")
                        for acc in invalid_accounts:
                            st.write(f"• {acc}")
                        
                        # Suggest available accounts
                        suggestion_result = conn.execute(text("""
                            SELECT glaccountid, accountname 
                            FROM glaccount 
                            WHERE companycodeid = :company_code 
                            ORDER BY glaccountid 
                            LIMIT 10
                        """), {'company_code': cc})
                        
                        suggestions = suggestion_result.fetchall()
                        if suggestions:
                            st.info("💡 **Available GL Accounts (first 10):**")
                            for acc_id, acc_name in suggestions:
                                st.write(f"• {acc_id} - {acc_name}")
                            
                            # Add search functionality
                            with st.expander("🔍 Search for GL Accounts", expanded=False):
                                search_term = st.text_input("Search by Account ID or Name:", key="gl_search")
                                if search_term:
                                    search_result = conn.execute(text("""
                                        SELECT glaccountid, accountname, accounttype
                                        FROM glaccount 
                                        WHERE companycodeid = :company_code 
                                        AND (glaccountid ILIKE :search OR accountname ILIKE :search)
                                        ORDER BY glaccountid 
                                        LIMIT 20
                                    """), {
                                        'company_code': cc,
                                        'search': f'%{search_term}%'
                                    })
                                    
                                    search_results = search_result.fetchall()
                                    if search_results:
                                        st.success(f"Found {len(search_results)} matching accounts:")
                                        search_df = pd.DataFrame(search_results, columns=['Account ID', 'Account Name', 'Type'])
                                        st.dataframe(search_df, use_container_width=True, hide_index=True)
                                    else:
                                        st.warning(f"No accounts found matching '{search_term}'")
                            
            except Exception as e:
                errors.append(f"🚨 Error validating GL accounts: {str(e)}")
                logger.error(f"GL account validation error: {e}")
        else:
            st.info("ℹ️ No GL accounts to validate")
    else:
        st.info("ℹ️ No journal entry lines to validate")
    
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
        # Format validation errors more gracefully
        error_messages = str(e).split('\n')
        for error_msg in error_messages:
            if error_msg.strip():
                if 'documentnumber' in error_msg.lower():
                    errors.append(f"📄 Document Number: {error_msg}")
                elif 'companycode' in error_msg.lower():
                    errors.append(f"🏢 Company Code: {error_msg}")
                elif 'date' in error_msg.lower():
                    errors.append(f"📅 Date: {error_msg}")
                elif 'fiscal' in error_msg.lower():
                    errors.append(f"📊 Fiscal Year/Period: {error_msg}")
                elif 'currency' in error_msg.lower():
                    errors.append(f"💱 Currency: {error_msg}")
                else:
                    errors.append(f"ℹ️ Header: {error_msg}")
    except ValueError as e:
        errors.append(f"📝 Please check your header data: {str(e)}")
    except Exception as e:
        errors.append(f"🚨 Header validation error: Please review the form fields.")
    
    # ENTERPRISE FEATURE: Validate ledger assignments
    try:
        from utils.ledger_assignment_service import ledger_assignment_service
        for i, row in edited.iterrows():
            ledger_id = str(row.get('ledgerid', ''))
            if ledger_id:
                is_valid, message = ledger_assignment_service.validate_ledger_assignment(ledger_id)
                if not is_valid:
                    errors.append(f"🏦 Line {i + 1} - Ledger: {message}")
    except ImportError:
        logger.warning("Ledger assignment service not available for validation")

    # Validate lines
    if len(edited) == 0:
        errors.append("📝 Please add at least one journal entry line before saving.")
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
                    'business_unit_id': str(row.get('business_unit_id', '')),
                    'ledgerid': str(row.get('ledgerid', ''))
                }
                try:
                    line_validator = JournalEntryLineValidator(**line_data)
                    line_validator.validate_debit_credit_balance()
                    line_validators.append(line_validator)
                except ValidationError as ve:
                    errors.append(f"📍 Line {i + 1}: {str(ve)}")
                except Exception as le:
                    errors.append(f"📍 Line {i + 1}: Please check the data - {str(le)}")
            
            # 🎯 FIELD STATUS GROUP VALIDATION - New Enterprise Feature
            if not errors:  # Only run FSG validation if basic validations passed
                st.info("🛡️ **Running Field Status Group validation...**")
                fsg_errors = []
                
                for i, row in edited.iterrows():
                    line_number = i + 1
                    gl_account = str(row.get('glaccountid', ''))
                    
                    if gl_account.strip():  # Only validate lines with GL accounts
                        try:
                            # Proper null value handling for FSG validation
                            def clean_field_value(value):
                                if pd.isna(value) or value is None:
                                    return None
                                value_str = str(value).strip()
                                return value_str if value_str and value_str not in ['', 'nan', 'None', 'none', 'NaN'] else None
                            
                            # Validate using FSG engine
                            is_valid, line_fsg_errors = validate_journal_entry_line(
                                document_type=doc_type,
                                gl_account_id=gl_account,
                                business_unit_id=clean_field_value(row.get('business_unit_id')),
                                business_area=clean_field_value(row.get('business_area')),
                                tax_code=clean_field_value(row.get('tax_code')),
                                reference=clean_field_value(row.get('reference')),
                                assignment=clean_field_value(row.get('assignment')),
                                text=clean_field_value(row.get('description')),  # Use description as text
                                line_number=line_number
                            )
                            
                            if not is_valid:
                                fsg_errors.extend(line_fsg_errors)
                                
                        except Exception as fsg_e:
                            fsg_errors.append(f"🛡️ Line {line_number}: FSG validation error - {str(fsg_e)}")
                
                # Add FSG errors to main errors list
                if fsg_errors:
                    errors.extend(fsg_errors)
                    st.warning(f"🛡️ Field Status Group validation found {len(fsg_errors)} issue(s)")
                else:
                    st.success("🛡️ **Field Status Group validation passed!**")
            
            # 🛡️ DIS FIELD VALIDATION - Check for Display Only field modifications
            if hdr:  # Only validate DIS fields for existing journal entries
                original_df = df.copy()  # df contains the original data loaded from database
                dis_violations = detect_dis_field_violations(edited, original_df, doc_type)
                if dis_violations:
                    errors.extend(dis_violations)
                    st.warning(f"📄 Display Only (DIS) field validation found {len(dis_violations)} violation(s)")
                    for violation in dis_violations:
                        st.error(violation)
            
            # Validate overall balance only if individual lines are valid
            if line_validators and not errors:
                try:
                    validate_journal_entry_balance(line_validators)
                except ValidationError as ve:
                    errors.append(f"⚖️ Journal Entry Balance Issue: {str(ve)}")
            
        except Exception as e:
            errors.append(f"🚨 Unexpected validation error: Please check your data and try again.")
    
    # 🛡️ FSG INFORMATION PANEL - Show field requirements
    if not edited.empty and len(edited) > 0:
        with st.expander("🛡️ Field Status Group Information", expanded=False):
            try:
                # Get unique GL accounts from the entry
                unique_accounts = edited['glaccountid'].dropna().unique()
                
                for account in unique_accounts[:3]:  # Show max 3 accounts to avoid clutter
                    if account and str(account).strip():
                        fsg = field_status_engine.get_effective_field_status_group(
                            document_type=doc_type, 
                            gl_account_id=str(account)
                        )
                        
                        if fsg:
                            st.markdown(f"**GL Account {account}** → FSG: **{fsg.group_id}** ({fsg.group_name})")
                            
                            # Show key field requirements
                            requirements = []
                            if fsg.business_unit_status.value == 'REQ':
                                requirements.append("📋 Business Unit Required")
                            if fsg.tax_code_status.value == 'REQ':
                                requirements.append("💰 Tax Code Required")
                            if fsg.business_area_status.value == 'REQ':
                                requirements.append("🏢 Business Area Required")
                            
                            suppressions = []
                            if fsg.business_unit_status.value == 'SUP':
                                suppressions.append("📋 Business Unit Suppressed")
                            if fsg.tax_code_status.value == 'SUP':
                                suppressions.append("💰 Tax Code Suppressed")
                            if fsg.business_area_status.value == 'SUP':
                                suppressions.append("🏢 Business Area Suppressed")
                            
                            display_only = []
                            if fsg.business_unit_status.value == 'DIS':
                                display_only.append("📋 Business Unit Display Only")
                            if fsg.tax_code_status.value == 'DIS':
                                display_only.append("💰 Tax Code Display Only")
                            if fsg.business_area_status.value == 'DIS':
                                display_only.append("🏢 Business Area Display Only")
                            if fsg.reference_field_status.value == 'DIS':
                                display_only.append("📝 Reference Display Only")
                            if fsg.assignment_field_status.value == 'DIS':
                                display_only.append("📄 Assignment Display Only")
                            if fsg.text_field_status.value == 'DIS':
                                display_only.append("📄 Text Display Only")
                                
                            if requirements:
                                st.write("🔴 " + " • ".join(requirements))
                            if suppressions:
                                st.write("🚫 " + " • ".join(suppressions))
                            if display_only:
                                st.write("📄 " + " • ".join(display_only))
                            
                            if not requirements and not suppressions and not display_only:
                                st.write("✅ All fields optional")
                                
                if len(unique_accounts) > 3:
                    st.write(f"... and {len(unique_accounts) - 3} more accounts")
                    
            except Exception as e:
                st.write(f"Error loading FSG information: {e}")

    # Display errors with better formatting
    if errors:
        st.error("🚫 **Please fix the following issues before saving:**")
        for err in errors:
            st.write(f"• {err}")
    else:
        st.success("✅ **All validations passed!** Ready to save.")

    # Save options with workflow integration
    st.subheader("💾 Save Options")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("💾 Save as Draft", disabled=bool(errors)):
            success = save_journal_entry(doc, cc, pdate, ddate, fy, per, ref, memo, cur, cb, edited, "DRAFT", doc_type)
            if success:
                st.success(f"✅ Journal Entry '{doc} | {cc}' saved as draft ({len(edited)} lines).")
                st.session_state.mode = "search"
                get_all_docs.clear()
    
    with col2:
        if st.button("📤 Submit for Approval", disabled=bool(errors), type="primary"):
            # First save the entry
            success = save_journal_entry(doc, cc, pdate, ddate, fy, per, ref, memo, cur, cb, edited, "DRAFT", doc_type)
            if success:
                # Then submit for approval
                approval_success, message = WorkflowEngine.submit_for_approval(doc, cc, current_user.username)
                if approval_success:
                    st.success(f"✅ Journal Entry '{doc} | {cc}' submitted for approval!")
                    st.info(f"📋 {message}")
                    st.session_state.mode = "search"
                    get_all_docs.clear()
                else:
                    st.error(f"❌ Approval submission failed: {message}")
    
    with col3:
        # Show emergency post option only for users with special permission
        if authenticator.has_permission("journal.emergency_post"):
            if st.button("🚨 Emergency Post", disabled=bool(errors)):
                st.warning("⚠️ **Emergency Posting** bypasses normal approval workflow!")
                if st.button("Confirm Emergency Post", type="secondary"):
                    success = save_journal_entry(doc, cc, pdate, ddate, fy, per, ref, memo, cur, cb, edited, "POSTED", doc_type)
                    if success:
                        # Log emergency posting
                        with engine.begin() as conn:
                            WorkflowEngine._log_workflow_action(
                                conn, doc, cc, "EMERGENCY_POST", current_user.username,
                                "DRAFT", "POSTED", "Emergency posting bypass"
                            )
                        st.success(f"🚨 Journal Entry '{doc} | {cc}' posted via emergency procedure!")
                        st.session_state.mode = "search"
                        get_all_docs.clear()
        else:
            st.info("ℹ️ Emergency posting requires special permission")


def get_business_unit_id(business_unit_display, conn):
    """Extract unit_id from business unit display string like '7410520200 - 2D/3D Seismic - Abu Dhabi City'"""
    if not business_unit_display or business_unit_display.strip() == '':
        return None
    
    try:
        # Extract generated_code (first part before ' - ')
        generated_code = business_unit_display.split(' - ')[0].strip()
        
        # Look up unit_id by generated_code
        result = conn.execute(text("""
            SELECT unit_id FROM business_units WHERE generated_code = :code
        """), {"code": generated_code}).fetchone()
        
        if result:
            return result[0]
        else:
            # Fallback: try matching by unit name (everything after first ' - ')
            unit_name_part = ' - '.join(business_unit_display.split(' - ')[1:])
            result = conn.execute(text("""
                SELECT unit_id FROM business_units WHERE unit_name = :name
            """), {"name": unit_name_part}).fetchone()
            
            return result[0] if result else None
            
    except Exception as e:
        st.error(f"Error looking up business unit: {e}")
        return None

def save_journal_entry(doc, cc, pdate, ddate, fy, per, ref, memo, cur, cb, edited, workflow_status="DRAFT", doc_type="SA"):
    """Save journal entry with specified workflow status"""
    try:
        # Different upsert logic based on whether document is being posted to GL
        is_posting_to_gl = workflow_status == "POSTED"
        
        if is_posting_to_gl:
            # When posting to GL, update postingdate along with other fields
            upsert_hdr = """
                INSERT INTO journalentryheader
                (documentnumber, companycodeid, postingdate, documentdate, fiscalyear, period, 
                 reference, memo, currencycode, createdby, workflow_status)
                VALUES (:doc,:cc,:pdate,:ddate,:fy,:per,:ref,:memo,:cur,:cb,:status)
                ON CONFLICT (documentnumber, companycodeid) DO UPDATE SET
                    postingdate  = EXCLUDED.postingdate,
                    documentdate = EXCLUDED.documentdate,
                    fiscalyear   = EXCLUDED.fiscalyear,
                    period       = EXCLUDED.period,
                    reference    = EXCLUDED.reference,
                    memo         = EXCLUDED.memo,
                    currencycode = EXCLUDED.currencycode,
                    createdby    = EXCLUDED.createdby,
                    workflow_status = EXCLUDED.workflow_status;
            """
        else:
            # For draft/edit saves, don't update postingdate - preserve existing value
            upsert_hdr = """
                INSERT INTO journalentryheader
                (documentnumber, companycodeid, postingdate, documentdate, fiscalyear, period, 
                 reference, memo, currencycode, createdby, workflow_status)
                VALUES (:doc,:cc,:pdate,:ddate,:fy,:per,:ref,:memo,:cur,:cb,:status)
                ON CONFLICT (documentnumber, companycodeid) DO UPDATE SET
                    documentdate = EXCLUDED.documentdate,
                    fiscalyear   = EXCLUDED.fiscalyear,
                    period       = EXCLUDED.period,
                    reference    = EXCLUDED.reference,
                    memo         = EXCLUDED.memo,
                    currencycode = EXCLUDED.currencycode,
                    createdby    = EXCLUDED.createdby,
                    workflow_status = EXCLUDED.workflow_status;
            """
        with engine.begin() as conn:
            conn.execute(text(upsert_hdr), {
                "doc": doc, "cc": cc, "pdate": pdate, "ddate": ddate,
                "fy": fy,  "per": per, "ref": ref, "memo": memo, "cur": cur, "cb": cb,
                "status": workflow_status
            })
            
            # Delete existing lines and insert new ones
            conn.execute(
                text("DELETE FROM journalentryline WHERE documentnumber = :doc AND companycodeid = :cc"),
                {"doc": doc, "cc": cc}
            )
            
            for i, row in enumerate(edited.itertuples(index=False), start=1):
                # ENTERPRISE FEATURE: Ensure ledger assignment
                ledger_id = row.ledgerid if hasattr(row, 'ledgerid') and row.ledgerid else ''
                if not ledger_id or ledger_id.strip() == '':
                    # Apply default ledger assignment
                    try:
                        from utils.ledger_assignment_service import ledger_assignment_service
                        ledger_id = ledger_assignment_service.get_default_ledger_for_account(
                            row.glaccountid, cc
                        )
                    except ImportError:
                        ledger_id = 'L1'  # Fallback to leading ledger
                
                conn.execute(text("""
                    INSERT INTO journalentryline
                    (documentnumber, companycodeid, linenumber, glaccountid, description, 
                     debitamount, creditamount, currencycode, business_unit_code, ledgerid)
                    VALUES (:doc,:cc,:ln,:ga,:desc,:dr,:cr,:cur,:cost,:ld)
                """), {
                    "doc": doc, "cc": cc,
                    "ln": i,
                    "ga": row.glaccountid,
                    "desc": row.description,
                    "dr": float(row.debitamount) if row.debitamount else 0,
                    "cr": float(row.creditamount) if row.creditamount else 0,
                    "cur": row.currencycode,
                    "cost": row.business_unit_id.split(' - ')[0] if hasattr(row, 'business_unit_id') and row.business_unit_id else None,
                    "ld": ledger_id
                })
        
        logger.info(f"Journal Entry {doc} saved with status {workflow_status}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving journal entry {doc}: {e}")
        st.error(f"❌ Save failed: {str(e)}")
        return False

    # Navigation button
    if st.button("🔙 🔙 Back to Search"):
        st.session_state.mode = "search"

def handle_reverse_entry():
    current_user = authenticator.get_current_user()
    
    # Check if a document is properly selected
    if not isinstance(st.session_state.current_doc, tuple) or len(st.session_state.current_doc) != 2:
        st.error("🚫 **No document selected for reversal.** Please select a journal entry from the dropdown above.")
        if st.button("🔙 Back to Search"):
            st.session_state.mode = "search"
            st.rerun()
        return
    
    doc, cc = st.session_state.current_doc
    
    # Show document details before reversal
    st.subheader(f"🔄 Reverse Journal Entry: {doc} | {cc}")
    
    # Load and validate document for reversal
    try:
        with engine.connect() as conn:
            # Get header with status information
            hdr = conn.execute(
                text("""
                    SELECT *, 
                           CASE WHEN status = 'REVERSED' THEN reversed_by ELSE NULL END as reversed_by_doc
                    FROM journalentryheader 
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """),
                {"doc": doc, "cc": cc}
            ).mappings().first()
            
            if not hdr:
                st.error(f"❌ Document '{doc} | {cc}' not found in database.")
                if st.button("🔙 Back to Search"):
                    st.session_state.mode = "search"
                    st.rerun()
                return
            
            # Check if document is already reversed
            if hdr['status'] == 'REVERSED':
                st.error(f"❌ **Document already reversed!**")
                st.info(f"This entry was reversed by document: **{hdr['reversed_by_doc']}** on {hdr['reversal_date']}")
                st.write(f"**Reversal reason:** {hdr['reversal_reason'] or 'N/A'}")
                if st.button("🔙 Back to Search"):
                    st.session_state.mode = "search"
                    st.rerun()
                return
            
            # Check if this is itself a reversal entry
            if hdr['reversal_of']:
                st.warning(f"⚠️ **This is a reversal entry** that reverses document: **{hdr['reversal_of']}**")
                st.info("You can reverse this reversal entry, which will effectively restore the original transaction.")
                
            # Get line summary and details
            line_summary = conn.execute(
                text("""
                    SELECT COUNT(*) as line_count, 
                           SUM(debitamount) as total_debit, 
                           SUM(creditamount) as total_credit
                    FROM journalentryline
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """),
                {"doc": doc, "cc": cc}
            ).mappings().first()
            
            detailed_lines = conn.execute(
                text("""
                    SELECT linenumber, glaccountid, description,
                           debitamount, creditamount, currencycode, business_unit_id, ledgerid
                    FROM journalentryline
                    WHERE documentnumber = :doc AND companycodeid = :cc
                    ORDER BY linenumber
                """),
                {"doc": doc, "cc": cc}
            ).mappings().all()
            
    except Exception as e:
        st.error(f"❌ Error loading document details: {str(e)}")
        if st.button("🔙 Back to Search"):
            st.session_state.mode = "search"
            st.rerun()
        return
    
    # Display original document details
    st.info("📋 **Original Document Details:**")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Document Number:** {hdr['documentnumber']}")
        st.write(f"**Company Code:** {hdr['companycodeid']}")
        st.write(f"**Posting Date:** {hdr['postingdate']}")
        st.write(f"**Reference:** {hdr['reference'] or 'N/A'}")
        st.write(f"**Status:** {hdr['status']}")
    with col2:
        st.write(f"**Created By:** {hdr['createdby']}")
        st.write(f"**Currency:** {hdr['currencycode']}")
        st.write(f"**Number of Lines:** {line_summary['line_count']}")
        st.write(f"**Total Amount:** ${line_summary['total_debit']:,.2f}")
        if hdr['reversal_of']:
            st.write(f"**Reverses Document:** {hdr['reversal_of']}")
    
    # Display journal entry lines to be reversed
    st.subheader("📋 Journal Entry Lines to be Reversed")
    
    if detailed_lines:
        lines_df = pd.DataFrame(detailed_lines)
        column_ids = ["linenumber", "glaccountid", "description", "debitamount", "creditamount", "currencycode", "business_unit_id", "ledgerid"]
        lines_df = enforce_column_order(lines_df, column_ids)
        
        lines_df_display = lines_df.rename(columns={
            "linenumber": "Line #",
            "glaccountid": "GL Account",
            "description": "Description", 
            "debitamount": "Debit Amount",
            "creditamount": "Credit Amount",
            "currencycode": "Currency",
            "business_unit_id": "Business Unit",
            "ledgerid": "Ledger ID"
        })
        
        st.dataframe(
            lines_df_display, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Debit Amount": st.column_config.NumberColumn("Debit Amount", format="$%.2f"),
                "Credit Amount": st.column_config.NumberColumn("Credit Amount", format="$%.2f")
            }
        )
        
        # Show totals
        total_debit = lines_df['debitamount'].sum()
        total_credit = lines_df['creditamount'].sum()
        balance_diff = total_debit - total_credit
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Original Debit", f"${total_debit:,.2f}")
        with col2:
            st.metric("Original Credit", f"${total_credit:,.2f}")
        with col3:
            if abs(balance_diff) < 0.01:
                st.metric("Balance", "✅ Balanced", delta="0.00")
            else:
                st.metric("Balance", f"⚠️ ${balance_diff:,.2f}", delta=f"{balance_diff:,.2f}")
    else:
        st.info("ℹ️ This journal entry has no line items to reverse.")
        return
    
    st.divider()
    
    # Reversal entry creation form
    if not hasattr(st.session_state, 'reverse_confirm') or not st.session_state.reverse_confirm:
        st.subheader("🔄 **Create Reversal Entry**")
        
        # Reversal entry details
        col1, col2 = st.columns(2)
        with col1:
            reversal_date = st.date_input(
                "Reversal Date", 
                value=datetime.now().date(),
                help="Date for the reversal entry (typically today or original posting date)"
            )
            reversal_reason = st.text_area(
                "Reversal Reason", 
                placeholder="Enter business reason for reversal (required for audit trail)",
                help="This will be recorded in the audit trail"
            )
        with col2:
            st.info("**Reversal Entry Preview:**")
            new_doc_number = generate_next_doc_number(company_code=cc, prefix="RV")
            st.write(f"**New Document #:** {new_doc_number}")
            st.write(f"**Reference:** REVERSAL OF {doc}")
            st.write(f"**Debits ↔ Credits:** Amounts will be swapped")
            st.write(f"**Created By:** {current_user.username}")
        
        # Validation
        if not reversal_reason.strip():
            st.warning("⚠️ **Reversal reason is required** for audit compliance.")
            
        st.warning("⚠️ **Confirm Reversal Entry Creation**")
        st.write("This will create a new journal entry that exactly reverses the original transaction.")
        st.write("**The original entry will remain in the system** but will be marked as 'REVERSED'.")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 Create Reversal", type="primary", disabled=not reversal_reason.strip()):
                st.session_state.reverse_confirm = True
                st.session_state.reversal_date = reversal_date
                st.session_state.reversal_reason = reversal_reason.strip()
                st.session_state.new_reversal_doc = new_doc_number
                st.rerun()
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.mode = "search"
                if hasattr(st.session_state, 'reverse_confirm'):
                    del st.session_state.reverse_confirm
                st.rerun()
    else:
        # Execute the reversal
        try:
            reversal_date = st.session_state.reversal_date
            reversal_reason = st.session_state.reversal_reason
            new_doc_number = st.session_state.new_reversal_doc
            
            with engine.begin() as conn:
                # Create reversal entry header
                conn.execute(text("""
                    INSERT INTO journalentryheader
                    (documentnumber, companycodeid, postingdate, documentdate, fiscalyear, period, 
                     reference, currencycode, createdby, status, reversal_of, reversal_date, 
                     reversal_reason, reversal_created_by)
                    VALUES (:new_doc, :cc, :rev_date, :rev_date, :fy, :per, :ref, :cur, :created_by,
                            'ACTIVE', :original_doc, :rev_date, :reason, :created_by)
                """), {
                    'new_doc': new_doc_number,
                    'cc': cc,
                    'rev_date': reversal_date,
                    'fy': reversal_date.year,
                    'per': reversal_date.month,
                    'ref': f"REVERSAL OF {doc}",
                    'cur': hdr['currencycode'],
                    'created_by': current_user.username,
                    'original_doc': doc,
                    'reason': reversal_reason
                })
                
                # Create reversal entry lines (swap debits and credits)
                for i, line in enumerate(detailed_lines, 1):
                    conn.execute(text("""
                        INSERT INTO journalentryline
                        (documentnumber, companycodeid, linenumber, glaccountid, description,
                         debitamount, creditamount, currencycode, business_unit_code, ledgerid)
                        VALUES (:doc, :cc, :line_num, :gl_account, :desc, :credit, :debit, :cur, :business_unit, :ledger)
                    """), {
                        'doc': new_doc_number,
                        'cc': cc,
                        'line_num': i,
                        'gl_account': line['glaccountid'],
                        'desc': f"REV: {line['description']}",
                        'debit': float(line['creditamount']) if line['creditamount'] else 0,  # Swap!
                        'credit': float(line['debitamount']) if line['debitamount'] else 0,   # Swap!
                        'cur': line['currencycode'],
                        'business_unit': line.get('business_unit_code'),
                        'ledger': line['ledgerid']
                    })
                
                # Update original entry status
                conn.execute(text("""
                    UPDATE journalentryheader 
                    SET status = 'REVERSED', 
                        reversed_by = :reversal_doc,
                        reversal_date = :rev_date,
                        reversal_reason = :reason,
                        reversal_created_by = :created_by
                    WHERE documentnumber = :original_doc AND companycodeid = :cc
                """), {
                    'reversal_doc': new_doc_number,
                    'rev_date': reversal_date,
                    'reason': reversal_reason,
                    'created_by': current_user.username,
                    'original_doc': doc,
                    'cc': cc
                })
                
                # Create audit record
                conn.execute(text("""
                    INSERT INTO journal_reversal_audit
                    (original_document, reversal_document, company_code, reversal_date, 
                     reversal_reason, requested_by, original_total_debit, original_total_credit)
                    VALUES (:orig, :rev, :cc, :date, :reason, :user, :debit, :credit)
                """), {
                    'orig': doc,
                    'rev': new_doc_number,
                    'cc': cc,
                    'date': reversal_date,
                    'reason': reversal_reason,
                    'user': current_user.username,
                    'debit': float(line_summary['total_debit']),
                    'credit': float(line_summary['total_credit'])
                })
            
            st.success(f"✅ **Reversal Entry Created Successfully!**")
            st.info(f"📄 **Reversal Document:** {new_doc_number}")
            st.info(f"📊 **Original Document:** {doc} is now marked as REVERSED")
            st.info(f"🔍 **Audit Trail:** Complete reversal history maintained")
            
            # Reset state
            st.session_state.mode = "search"
            st.session_state.current_doc = None
            if hasattr(st.session_state, 'reverse_confirm'):
                del st.session_state.reverse_confirm
            get_all_docs.clear()
            
            if st.button("🔙 Back to Search"):
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ **Reversal failed:** {str(e)}")
            logger.error(f"Reversal error for {doc}: {e}")
            if hasattr(st.session_state, 'reverse_confirm'):
                del st.session_state.reverse_confirm


def handle_delete_entry():
    """Handle deletion of journal entries (drafts only)"""
    if not isinstance(st.session_state.current_doc, tuple) or len(st.session_state.current_doc) != 2:
        st.error("🚫 **Invalid document selection.** Please select a valid journal entry from the list.")
        if st.button("🔙 Back to Search"):
            st.session_state.mode = "search"
            st.rerun()
        return
    
    doc, cc = st.session_state.current_doc
    
    try:
        # Get document header to check status
        with engine.connect() as conn:
            hdr = conn.execute(text("""
                SELECT documentnumber, companycodeid, workflow_status, reference, 
                       createdby, createdat, postingdate, currencycode
                FROM journalentryheader
                WHERE documentnumber = :doc AND companycodeid = :cc
            """), {"doc": doc, "cc": cc}).mappings().first()
            
            if not hdr:
                st.error("❌ **Document not found!**")
                return
            
            # Check if document can be deleted (must be DRAFT)
            workflow_status = hdr.get('workflow_status', 'DRAFT')
            if workflow_status != 'DRAFT':
                st.error(f"❌ **Cannot delete document in {workflow_status} status!**")
                st.warning("🔒 Only DRAFT documents can be deleted. Once a document enters the workflow, it cannot be deleted.")
                
                # Show alternative actions
                if workflow_status in ['PENDING_APPROVAL', 'APPROVED']:
                    st.info("💡 You may be able to reject this document if you have approval permissions.")
                elif workflow_status == 'POSTED':
                    st.info("💡 Posted documents cannot be deleted. Consider creating a reversal entry instead.")
                
                if st.button("🔙 Back to Search"):
                    st.session_state.mode = "search"
                    st.rerun()
                return
            
            # Get lines for display
            lines = conn.execute(text("""
                SELECT linenumber, glaccountid, description, debitamount, creditamount
                FROM journalentryline
                WHERE documentnumber = :doc AND companycodeid = :cc
                ORDER BY linenumber
            """), {"doc": doc, "cc": cc}).mappings().all()
        
        st.header("🗑️ Delete Journal Entry")
        st.warning("⚠️ **DELETION WARNING**: This action cannot be undone!")
        
        # Show document details
        st.subheader("📄 Document to be Deleted")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Document Number", hdr["documentnumber"], disabled=True)
            st.text_input("Company Code", hdr["companycodeid"], disabled=True)
            st.text_input("Reference", hdr["reference"] or "No reference", disabled=True)
            st.text_area("Memo", value=hdr["memo"] if hdr["memo"] else "No memo", disabled=True, height=60)
        with col2:
            st.date_input("Posting Date", hdr["postingdate"], disabled=True)
            st.text_input("Created By", hdr["createdby"], disabled=True)
            st.text_input("Status", f"🟡 {workflow_status}", disabled=True)
        
        # Show lines
        if lines:
            st.subheader("📋 Entry Lines to be Deleted")
            df_lines = pd.DataFrame(lines)
            df_display = df_lines.rename(columns={
                "linenumber": "Line",
                "glaccountid": "GL Account",
                "description": "Description",
                "debitamount": "Debit",
                "creditamount": "Credit"
            })
            st.dataframe(df_display, use_container_width=True)
            
            total_debit = df_lines['debitamount'].sum()
            total_credit = df_lines['creditamount'].sum()
            st.write(f"**Total Debit:** {total_debit:,.2f} | **Total Credit:** {total_credit:,.2f}")
        else:
            st.info("No entry lines found.")
        
        # Confirmation step
        if not hasattr(st.session_state, 'delete_confirm') or not st.session_state.delete_confirm:
            st.divider()
            st.subheader("⚠️ Confirmation Required")
            st.write("Please confirm that you want to **permanently delete** this journal entry:")
            st.write("• This will remove the document and all its lines from the database")
            st.write("• This action cannot be undone")
            st.write("• Only DRAFT documents can be deleted")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ YES, DELETE PERMANENTLY", type="primary"):
                    st.session_state.delete_confirm = True
                    st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.mode = "search"
                    if hasattr(st.session_state, 'delete_confirm'):
                        del st.session_state.delete_confirm
                    st.rerun()
        else:
            # Execute deletion
            st.divider()
            st.subheader("🗑️ Executing Deletion...")
            
            try:
                with engine.begin() as conn:
                    # Delete lines first (foreign key constraint)
                    lines_deleted = conn.execute(text("""
                        DELETE FROM journalentryline 
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {"doc": doc, "cc": cc})
                    
                    # Delete header
                    header_deleted = conn.execute(text("""
                        DELETE FROM journalentryheader 
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {"doc": doc, "cc": cc})
                    
                    # Log the deletion
                    log_database_operation(
                        "DELETE", "journalentryheader", doc, 
                        f"Document {doc} deleted by user"
                    )
                    
                    logger.info(f"Document {doc} deleted successfully by user")
                
                st.success(f"✅ **Document {doc} deleted successfully!**")
                st.info(f"🗑️ Deleted {lines_deleted.rowcount} entry lines and 1 header record")
                
                # Clear cache and session
                get_all_docs.clear()
                st.session_state.mode = "search"
                st.session_state.current_doc = None
                if hasattr(st.session_state, 'delete_confirm'):
                    del st.session_state.delete_confirm
                
                # Auto-redirect after success
                st.balloons()
                time.sleep(2)
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ **Deletion failed:** {str(e)}")
                logger.error(f"Delete error for {doc}: {e}")
                if hasattr(st.session_state, 'delete_confirm'):
                    del st.session_state.delete_confirm
                
    except Exception as e:
        st.error(f"❌ **Error loading document:** {str(e)}")
        logger.error(f"Error loading document {doc} for deletion: {e}")


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
    
    # Show document selector for modes that need it
    docs_filtered = document_selector(docs)

    if st.session_state.mode == "add":
        handle_edit_entry(current_user)
    elif st.session_state.mode == "view_entry":
        if st.session_state.current_doc:
            handle_view_entry()
        else:
            st.info("ℹ️ Enter a document number above to view a journal entry.")
    elif st.session_state.mode == "edit":
        if st.session_state.current_doc:
            handle_edit_entry(current_user)
        else:
            st.info("ℹ️ Enter a document number above to edit a journal entry.")
    elif st.session_state.mode == "delete":
        if st.session_state.current_doc:
            handle_delete_entry()
        else:
            st.info("ℹ️ Enter a document number above to delete a journal entry.")
    else:
        # Default view - show recent entries
        st.subheader("📋 Recent Journal Entries")
        try:
            with engine.connect() as conn:
                recent_df = pd.read_sql("""
                    SELECT documentnumber, companycodeid, postingdate, reference, 
                           createdby, status, createdat
                    FROM journalentryheader 
                    ORDER BY createdat DESC 
                    LIMIT 10
                """, conn)
                
                if not recent_df.empty:
                    st.dataframe(
                        recent_df.rename(columns={
                            'documentnumber': 'Document',
                            'companycodeid': 'Company',
                            'postingdate': 'Posting Date',
                            'reference': 'Reference',
                            'createdby': 'Created By',
                            'status': 'Status',
                            'createdat': 'Created'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No journal entries found.")
        except Exception as e:
            st.error(f"Error loading recent entries: {e}")

    st.divider()

    # Navigation is now handled by the SAP-style sidebar

if __name__ == "__main__":
    main()
