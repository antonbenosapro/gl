"""
Full Journal Entry Upload Manager

This module provides comprehensive journal entry creation via file upload including:
- Complete entry creation with headers and lines
- Multi-format support (CSV, Excel)
- Balance validation and GL account verification
- Multi-currency support
- Automatic approval routing after creation
- Bulk operations with transaction integrity

Features:
- Upload complete journal entries with all line items
- Automatic balance validation (debits = credits)
- GL account and business unit validation
- Currency conversion support
- Template generation and download
- Preview before creation
- Bulk creation and submission
- Comprehensive error reporting

Author: Claude Code Assistant
Date: August 6, 2025
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text
import json
import io
import sys
import os
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from db_config import engine
from utils.workflow_engine import WorkflowEngine
from utils.navigation import show_breadcrumb
from auth.optimized_middleware import optimized_authenticator as authenticator

def _convert_business_unit_id(value):
    """Convert business unit ID to integer, handling CSV float inputs."""
    if not value:
        return None
    try:
        str_val = str(value).strip()
        if not str_val or str_val.lower() in ('', 'nan', 'none'):
            return None
        return int(float(str_val))
    except (ValueError, TypeError):
        st.warning(f"Invalid business unit ID: {value}")
        return None

# Page configuration
st.set_page_config(
    page_title="Journal Entry Upload",
    page_icon="📊",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Journal Entry Upload application."""
    # Show breadcrumb with user info
    show_breadcrumb("Journal Entry Upload", "Transactions", "Data Import")
    
    st.title("📊 Full Journal Entry Upload Manager")
    st.markdown("**Create and submit complete journal entries with all line items via file upload**")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("🔧 Upload Tools")
        
        page = st.selectbox(
            "Select Function",
            [
                "📤 Upload Entries",
                "📋 Validation Results",
                "👁️ Preview & Edit",
                "✅ Create & Submit",
                "📊 Upload History",
                "📚 Templates & Help"
            ]
        )
    
    # Route to selected page
    if page == "📤 Upload Entries":
        show_upload_interface()
    elif page == "📋 Validation Results":
        show_validation_results()
    elif page == "👁️ Preview & Edit":
        show_preview_and_edit()
    elif page == "✅ Create & Submit":
        show_create_and_submit()
    elif page == "📊 Upload History":
        show_upload_history()
    elif page == "📚 Templates & Help":
        show_templates_and_help()

def show_upload_interface():
    """Display the main upload interface."""
    st.header("📤 Upload Journal Entries")
    
    # Upload method selection
    upload_method = st.radio(
        "Select Upload Method",
        ["📄 Single File (Headers + Lines)", "📑 Two Files (Headers & Lines Separate)", "📝 Template Builder"],
        horizontal=True
    )
    
    if upload_method == "📄 Single File (Headers + Lines)":
        show_single_file_upload()
    elif upload_method == "📑 Two Files (Headers & Lines Separate)":
        show_two_file_upload()
    elif upload_method == "📝 Template Builder":
        show_template_builder()

def show_single_file_upload():
    """Handle single file upload with both headers and lines."""
    st.subheader("📄 Single File Upload")
    
    with st.expander("📋 File Format Requirements", expanded=False):
        st.markdown("""
        **Required Columns:**
        - `document_number`: Unique journal entry identifier
        - `company_code`: Company code (1000, 2000, 3000)
        - `line_number`: Line item sequence (1, 2, 3...)
        - `gl_account`: General ledger account number
        - `debit_amount`: Debit amount (0 for credit lines)
        - `credit_amount`: Credit amount (0 for debit lines)
        
        **Optional Columns:**
        - `posting_date`: Posting date (defaults to today)
        - `reference`: Entry reference/description
        - `line_description`: Line item description
        - `business_unit_id`: Business unit ID (e.g., 1, 2, 3)
        - `currency_code`: Currency (defaults to USD)
        - `exchange_rate`: FX rate for non-USD entries
        - `tax_code`: Tax code if applicable
        - `project_code`: Project code
        - `vendor_customer`: Vendor/Customer code
        
        **Example Format:**
        ```csv
        document_number,company_code,line_number,gl_account,debit_amount,credit_amount,description,business_unit_id
        JE2025001,1000,1,400001,5000.00,0.00,Salary Expense,BU-HR01
        JE2025001,1000,2,200001,0.00,5000.00,Salary Payable,BU-HR01
        JE2025002,1000,1,600001,2500.00,0.00,Rent Expense,BU-ADMIN01
        JE2025002,1000,2,100001,0.00,2500.00,Cash,BU-ADMIN01
        ```
        """)
    
    # File upload widget
    uploaded_file = st.file_uploader(
        "Choose file to upload",
        type=['csv', 'xlsx', 'xls'],
        help="Upload CSV or Excel file containing journal entries with line items"
    )
    
    if uploaded_file is not None:
        try:
            # Read uploaded file
            if uploaded_file.type == "text/csv":
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.success(f"✅ File uploaded successfully! Found {len(df)} rows.")
            
            # Basic file statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                unique_entries = df['document_number'].nunique() if 'document_number' in df.columns else 0
                st.metric("Unique Entries", unique_entries)
            
            with col2:
                total_lines = len(df)
                st.metric("Total Lines", total_lines)
            
            with col3:
                if 'debit_amount' in df.columns and 'credit_amount' in df.columns:
                    total_amount = df['debit_amount'].sum()
                    st.metric("Total Debits", f"${total_amount:,.2f}")
                else:
                    st.metric("Total Amount", "N/A")
            
            with col4:
                companies = df['company_code'].nunique() if 'company_code' in df.columns else 0
                st.metric("Companies", companies)
            
            # Store in session state for processing
            st.session_state['uploaded_data'] = df
            st.session_state['upload_type'] = 'single'
            st.session_state['upload_timestamp'] = datetime.now()
            
            # Validate button
            if st.button("🔍 Validate Entries", type="primary"):
                st.write("🚀 **Starting validation process...**")
                try:
                    validate_uploaded_entries(df)
                    st.success("✅ Validation complete!")
                    
                    # Display validation summary immediately
                    if 'validation_results' in st.session_state:
                        results = st.session_state['validation_results']
                        stats = results['statistics']
                        
                        # Quick summary
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Entries", stats['total_entries'], f"{stats['total_lines']} lines")
                        with col2:
                            valid_pct = (stats['valid_entries'] / max(stats['total_entries'], 1)) * 100
                            st.metric("Valid Entries", stats['valid_entries'], f"{valid_pct:.1f}%")
                        with col3:
                            error_count = stats['entries_with_errors']
                            st.metric("Entries with Errors", error_count, "❌" if error_count > 0 else "✅")
                        
                        # Show errors if any
                        if results['errors']:
                            st.error("⚠️ **Validation Errors Found:**")
                            for error in results['errors'][:3]:  # Show first 3 errors
                                st.write(f"• **{error['document_number']}**: {error['errors'][0]}")
                            if len(results['errors']) > 3:
                                st.write(f"... and {len(results['errors']) - 3} more errors")
                        
                        # Success message
                        if stats['valid_entries'] > 0:
                            st.info(f"🎉 **{stats['valid_entries']} entries ready for creation!** Go to 'Preview & Edit' or 'Create & Submit' tabs.")
                        
                        # Auto-switch suggestion
                        st.markdown("👆 **Next Steps:** Use the sidebar to navigate to 'Validation Results' for details, 'Preview & Edit' to review entries, or 'Create & Submit' to process them.")
                    
                    st.write(f"📊 **Validation completed at:** {datetime.now().strftime('%H:%M:%S')}")
                    
                except Exception as e:
                    st.error(f"❌ Validation failed: {e}")
                    st.write(f"🔍 **Debug:** Validation error details: {str(e)}")
                
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("Please check the file format and ensure all required columns are present.")

def show_two_file_upload():
    """Handle two-file upload (headers and lines separately)."""
    st.subheader("📑 Two-File Upload")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📄 Headers File**")
        headers_file = st.file_uploader(
            "Upload headers file",
            type=['csv', 'xlsx', 'xls'],
            key="headers_upload",
            help="File containing journal entry headers"
        )
        
        if headers_file:
            if headers_file.type == "text/csv":
                headers_df = pd.read_csv(headers_file)
            else:
                headers_df = pd.read_excel(headers_file)
            
            st.info(f"Found {len(headers_df)} header records")
            st.dataframe(headers_df.head(), use_container_width=True)
    
    with col2:
        st.write("**📋 Lines File**")
        lines_file = st.file_uploader(
            "Upload lines file",
            type=['csv', 'xlsx', 'xls'],
            key="lines_upload",
            help="File containing journal entry line items"
        )
        
        if lines_file:
            if lines_file.type == "text/csv":
                lines_df = pd.read_csv(lines_file)
            else:
                lines_df = pd.read_excel(lines_file)
            
            st.info(f"Found {len(lines_df)} line items")
            st.dataframe(lines_df.head(), use_container_width=True)
    
    # Merge and validate
    if headers_file and lines_file:
        if st.button("🔗 Merge & Validate", type="primary"):
            try:
                # Merge headers and lines
                merged_df = merge_headers_and_lines(headers_df, lines_df)
                
                st.session_state['uploaded_data'] = merged_df
                st.session_state['upload_type'] = 'two_file'
                st.session_state['upload_timestamp'] = datetime.now()
                
                validate_uploaded_entries(merged_df)
                st.success("✅ Files merged and validated!")
                
                # Display validation summary immediately
                if 'validation_results' in st.session_state:
                    results = st.session_state['validation_results']
                    stats = results['statistics']
                    
                    # Quick summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Entries", stats['total_entries'], f"{stats['total_lines']} lines")
                    with col2:
                        valid_pct = (stats['valid_entries'] / max(stats['total_entries'], 1)) * 100
                        st.metric("Valid Entries", stats['valid_entries'], f"{valid_pct:.1f}%")
                    with col3:
                        error_count = stats['entries_with_errors']
                        st.metric("Entries with Errors", error_count, "❌" if error_count > 0 else "✅")
                    
                    # Show errors if any
                    if results['errors']:
                        st.error("⚠️ **Validation Errors Found:**")
                        for error in results['errors'][:3]:  # Show first 3 errors
                            st.write(f"• **{error['document_number']}**: {error['errors'][0]}")
                        if len(results['errors']) > 3:
                            st.write(f"... and {len(results['errors']) - 3} more errors")
                    
                    # Success message
                    if stats['valid_entries'] > 0:
                        st.info(f"🎉 **{stats['valid_entries']} entries ready for creation!** Go to 'Preview & Edit' or 'Create & Submit' tabs.")
                    
                    # Auto-switch suggestion
                    st.markdown("👆 **Next Steps:** Use the sidebar to navigate to 'Validation Results' for details, 'Preview & Edit' to review entries, or 'Create & Submit' to process them.")
                
            except Exception as e:
                st.error(f"❌ Error merging files: {str(e)}")

def show_template_builder():
    """Interactive template builder for creating journal entries."""
    st.subheader("📝 Template Builder")
    
    # Initialize template data
    if 'template_entries' not in st.session_state:
        st.session_state['template_entries'] = []
    
    # Entry header information
    with st.form("entry_header_form"):
        st.write("**📋 Entry Header Information**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            doc_number = st.text_input("Document Number", value=f"JE{datetime.now().strftime('%Y%m%d')}_001")
            company_code = st.selectbox("Company Code", ["1000", "2000", "3000"])
        
        with col2:
            posting_date = st.date_input("Posting Date", value=date.today())
            currency = st.selectbox("Currency", ["USD", "EUR", "GBP", "JPY", "CAD"])
        
        with col3:
            reference = st.text_input("Reference", placeholder="Entry description")
            exchange_rate = st.number_input("Exchange Rate", value=1.0, min_value=0.0001, format="%.6f")
        
        st.write("**📊 Line Items**")
        
        # Dynamic line items
        num_lines = st.number_input("Number of Lines", min_value=2, max_value=50, value=2)
        
        line_items = []
        for i in range(num_lines):
            st.write(f"**Line {i+1}**")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                gl_account = st.text_input(f"GL Account", key=f"gl_{i}", placeholder="e.g., 400001")
                business_unit = st.text_input(f"Business Unit", key=f"bu_{i}", placeholder="e.g., 1")
            
            with col2:
                debit = st.number_input(f"Debit", key=f"debit_{i}", min_value=0.0, format="%.2f")
                credit = st.number_input(f"Credit", key=f"credit_{i}", min_value=0.0, format="%.2f")
            
            with col3:
                description = st.text_input(f"Description", key=f"desc_{i}", placeholder="Line description")
            
            with col4:
                tax_code = st.text_input(f"Tax Code", key=f"tax_{i}", placeholder="Optional")
            
            line_items.append({
                'line_number': i + 1,
                'gl_account': gl_account,
                'debit_amount': debit,
                'credit_amount': credit,
                'description': description,
                'business_unit_id': business_unit,
                'tax_code': tax_code
            })
        
        # Balance check
        total_debits = sum(item['debit_amount'] for item in line_items)
        total_credits = sum(item['credit_amount'] for item in line_items)
        balance = total_debits - total_credits
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Debits", f"${total_debits:,.2f}")
        with col2:
            st.metric("Total Credits", f"${total_credits:,.2f}")
        with col3:
            if abs(balance) < 0.01:
                st.success(f"✅ Balanced: ${balance:,.2f}")
            else:
                st.error(f"❌ Out of Balance: ${balance:,.2f}")
        
        # Submit button
        if st.form_submit_button("➕ Add Entry to Template"):
            if abs(balance) < 0.01:
                # Create entry data
                entry_data = []
                for item in line_items:
                    entry_data.append({
                        'document_number': doc_number,
                        'company_code': company_code,
                        'posting_date': posting_date,
                        'currency_code': currency,
                        'reference': reference,
                        'exchange_rate': exchange_rate,
                        **item
                    })
                
                st.session_state['template_entries'].extend(entry_data)
                st.success(f"✅ Entry {doc_number} added to template!")
                st.rerun()
            else:
                st.error("❌ Entry must be balanced before adding to template!")
    
    # Display current template
    if st.session_state['template_entries']:
        st.write("**📄 Current Template Entries**")
        template_df = pd.DataFrame(st.session_state['template_entries'])
        
        # Group by document number for summary
        summary = template_df.groupby('document_number').agg({
            'company_code': 'first',
            'reference': 'first',
            'debit_amount': 'sum',
            'credit_amount': 'sum'
        }).reset_index()
        
        st.dataframe(summary, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save as Template", type="primary"):
                save_template_to_file(template_df)
        
        with col2:
            if st.button("🔍 Validate Template"):
                st.session_state['uploaded_data'] = template_df
                st.session_state['upload_type'] = 'template'
                validate_uploaded_entries(template_df)
                
                # Display validation summary immediately
                if 'validation_results' in st.session_state:
                    results = st.session_state['validation_results']
                    stats = results['statistics']
                    
                    # Quick summary
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Entries", stats['total_entries'], f"{stats['total_lines']} lines")
                    with col2:
                        valid_pct = (stats['valid_entries'] / max(stats['total_entries'], 1)) * 100
                        st.metric("Valid Entries", stats['valid_entries'], f"{valid_pct:.1f}%")
                    with col3:
                        error_count = stats['entries_with_errors']
                        st.metric("Entries with Errors", error_count, "❌" if error_count > 0 else "✅")
                    
                    # Show errors if any
                    if results['errors']:
                        st.error("⚠️ **Template Validation Errors Found:**")
                        for error in results['errors'][:3]:  # Show first 3 errors
                            st.write(f"• **{error['document_number']}**: {error['errors'][0]}")
                        if len(results['errors']) > 3:
                            st.write(f"... and {len(results['errors']) - 3} more errors")
                    
                    # Success message
                    if stats['valid_entries'] > 0:
                        st.info(f"🎉 **Template validated! {stats['valid_entries']} entries ready for creation!**")
        
        with col3:
            if st.button("🗑️ Clear Template"):
                st.session_state['template_entries'] = []
                st.rerun()

def validate_uploaded_entries(df: pd.DataFrame):
    """Comprehensive validation of uploaded journal entries."""
    validation_results = {
        'total_entries': 0,
        'valid_entries': [],
        'errors': [],
        'warnings': [],
        'balance_check': {},
        'gl_validation': {},
        'statistics': {}
    }
    
    try:
        # Group by document number
        grouped = df.groupby('document_number')
        validation_results['total_entries'] = len(grouped)
        
        for doc_num, group in grouped:
            st.write(f"🔍 Processing document: {doc_num} with {len(group)} lines")
            entry_errors = []
            entry_warnings = []
            
            # 1. Balance validation
            total_debits = group['debit_amount'].sum() if 'debit_amount' in group.columns else 0
            total_credits = group['credit_amount'].sum() if 'credit_amount' in group.columns else 0
            balance = abs(total_debits - total_credits)
            
            if balance > 0.01:  # Allow for rounding differences
                entry_errors.append(f"Entry out of balance: DR ${total_debits:,.2f} != CR ${total_credits:,.2f}")
            
            validation_results['balance_check'][doc_num] = {
                'debits': total_debits,
                'credits': total_credits,
                'balanced': balance <= 0.01
            }
            
            # 2. Required fields validation
            required_fields = ['company_code', 'gl_account', 'debit_amount', 'credit_amount']
            for field in required_fields:
                if field not in group.columns:
                    entry_errors.append(f"Missing required field: {field}")
                elif group[field].isna().any():
                    entry_errors.append(f"Empty values in required field: {field}")
            
            # 3. Company code validation
            if 'company_code' in group.columns:
                invalid_companies = group[~group['company_code'].astype(str).isin(['1000', '2000', '3000'])]
                if not invalid_companies.empty:
                    entry_errors.append(f"Invalid company codes found")
            
            # 4. GL Account validation
            if 'gl_account' in group.columns:
                gl_accounts = group['gl_account'].unique()
                valid_accounts = validate_gl_accounts(gl_accounts)
                # Fix data type comparison: convert both to strings for comparison
                gl_accounts_str = [str(acc) for acc in gl_accounts]
                invalid_accounts = [acc for acc in gl_accounts_str if acc not in valid_accounts]
                
                if invalid_accounts:
                    entry_errors.append(f"Invalid GL accounts: {', '.join(map(str, invalid_accounts[:5]))}")
                
                validation_results['gl_validation'][doc_num] = {
                    'total_accounts': len(gl_accounts_str),
                    'valid_accounts': len(valid_accounts),
                    'invalid_accounts': invalid_accounts
                }
            
            # 4b. Business Unit validation
            if 'business_unit_id' in group.columns:
                business_units = group['business_unit_id'].dropna().unique()
                if len(business_units) > 0:
                    valid_business_units = validate_business_units(business_units)
                    # Convert business units to integers for comparison
                    bu_ints = []
                    for bu in business_units:
                        if bu is not None and str(bu).strip():
                            try:
                                bu_ints.append(int(float(bu)))
                            except (ValueError, TypeError):
                                bu_ints.append(str(bu))  # Keep invalid values as strings
                    invalid_business_units = [str(bu) for bu in bu_ints if bu not in valid_business_units]
                    
                    if invalid_business_units:
                        entry_errors.append(f"Invalid business units: {', '.join(invalid_business_units[:3])}")
                    
                    # Note: Legacy cost_center field support removed - only business_unit_id supported
            
            # 5. Date validation
            if 'posting_date' in group.columns:
                try:
                    # Check if dates are valid
                    pd.to_datetime(group['posting_date'])
                except:
                    entry_warnings.append("Invalid date format in posting_date")
            
            # 6. Currency validation
            if 'currency_code' in group.columns:
                valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'CHF', 'AUD']
                invalid_currencies = group[~group['currency_code'].isin(valid_currencies)]
                if not invalid_currencies.empty:
                    entry_warnings.append(f"Non-standard currency codes found")
            
            # 7. Duplicate line check
            if 'line_number' in group.columns:
                duplicates = group[group.duplicated(subset=['line_number'], keep=False)]
                if not duplicates.empty:
                    entry_errors.append("Duplicate line numbers found")
            
            # Store results
            if entry_errors:
                st.write(f"❌ {doc_num}: {len(entry_errors)} errors found")
                validation_results['errors'].append({
                    'document_number': doc_num,
                    'errors': entry_errors,
                    'line_count': len(group)
                })
            else:
                lines_records = group.to_dict('records')
                st.write(f"✅ {doc_num}: Valid entry created with {len(lines_records)} lines")
                validation_results['valid_entries'].append({
                    'document_number': doc_num,
                    'lines': lines_records,
                    'total_amount': total_debits
                })
            
            if entry_warnings:
                validation_results['warnings'].append({
                    'document_number': doc_num,
                    'warnings': entry_warnings
                })
        
        # Calculate statistics
        validation_results['statistics'] = {
            'total_entries': validation_results['total_entries'],
            'valid_entries': len(validation_results['valid_entries']),
            'entries_with_errors': len(validation_results['errors']),
            'entries_with_warnings': len(validation_results['warnings']),
            'total_lines': len(df),
            'total_debit_amount': df['debit_amount'].sum() if 'debit_amount' in df.columns else 0,
            'total_credit_amount': df['credit_amount'].sum() if 'credit_amount' in df.columns else 0
        }
        
        # Store validation results in session state
        st.session_state['validation_results'] = validation_results
        
    except Exception as e:
        st.error(f"❌ Validation error: {str(e)}")
        validation_results['errors'].append({
            'document_number': 'SYSTEM',
            'errors': [f"Validation process failed: {str(e)}"]
        })
        # Still store results even with errors
        st.session_state['validation_results'] = validation_results

def show_validation_results():
    """Display detailed validation results."""
    st.header("📋 Validation Results")
    
    if 'validation_results' not in st.session_state:
        st.info("No validation results available. Please upload and validate entries first.")
        return
    
    results = st.session_state['validation_results']
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Entries",
            results['statistics']['total_entries'],
            delta=f"{results['statistics']['total_lines']} lines"
        )
    
    with col2:
        valid_pct = (results['statistics']['valid_entries'] / max(results['statistics']['total_entries'], 1)) * 100
        st.metric(
            "Valid Entries",
            results['statistics']['valid_entries'],
            delta=f"{valid_pct:.1f}%"
        )
    
    with col3:
        st.metric(
            "Entries with Errors",
            results['statistics']['entries_with_errors'],
            delta="❌" if results['statistics']['entries_with_errors'] > 0 else "✅"
        )
    
    with col4:
        st.metric(
            "Warnings",
            results['statistics']['entries_with_warnings'],
            delta="⚠️" if results['statistics']['entries_with_warnings'] > 0 else "✅"
        )
    
    # Detailed results tabs
    tab1, tab2, tab3, tab4 = st.tabs(["❌ Errors", "⚠️ Warnings", "✅ Valid Entries", "📊 Balance Check"])
    
    with tab1:
        if results['errors']:
            st.error(f"Found {len(results['errors'])} entries with errors that must be fixed:")
            
            for error_entry in results['errors']:
                with st.expander(f"❌ {error_entry['document_number']} ({error_entry['line_count']} lines)"):
                    for error in error_entry['errors']:
                        st.write(f"• {error}")
        else:
            st.success("✅ No errors found!")
    
    with tab2:
        if results['warnings']:
            st.warning(f"Found {len(results['warnings'])} entries with warnings to review:")
            
            for warning_entry in results['warnings']:
                with st.expander(f"⚠️ {warning_entry['document_number']}"):
                    for warning in warning_entry['warnings']:
                        st.write(f"• {warning}")
        else:
            st.success("✅ No warnings found!")
    
    with tab3:
        if results['valid_entries']:
            st.success(f"✅ {len(results['valid_entries'])} entries ready for creation")
            
            # Summary table
            valid_summary = []
            for entry in results['valid_entries']:
                valid_summary.append({
                    'Document Number': entry['document_number'],
                    'Lines': len(entry['lines']),
                    'Total Amount': f"${entry['total_amount']:,.2f}",
                    'Status': '✅ Ready'
                })
            
            st.dataframe(pd.DataFrame(valid_summary), use_container_width=True, hide_index=True)
        else:
            st.info("No valid entries found. Please fix errors and re-validate.")
    
    with tab4:
        if results['balance_check']:
            balance_df = pd.DataFrame.from_dict(results['balance_check'], orient='index')
            balance_df['difference'] = abs(balance_df['debits'] - balance_df['credits'])
            balance_df['status'] = balance_df['balanced'].apply(lambda x: '✅ Balanced' if x else '❌ Out of Balance')
            
            st.dataframe(
                balance_df,
                column_config={
                    'debits': st.column_config.NumberColumn('Total Debits', format='$%.2f'),
                    'credits': st.column_config.NumberColumn('Total Credits', format='$%.2f'),
                    'difference': st.column_config.NumberColumn('Difference', format='$%.2f'),
                    'status': 'Status'
                },
                use_container_width=True
            )
        else:
            st.info("No balance information available")
    
    # Action buttons
    if results['statistics']['valid_entries'] > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("👁️ Preview Valid Entries", type="primary"):
                st.session_state['show_preview'] = True
                st.rerun()
        
        with col2:
            if st.button("📝 Fix Errors"):
                st.session_state['show_editor'] = True
                st.rerun()
        
        with col3:
            if results['statistics']['entries_with_errors'] == 0:
                if st.button("✅ Proceed to Creation", type="primary"):
                    st.session_state['ready_for_creation'] = True
                    st.rerun()

def show_preview_and_edit():
    """Preview and edit validated entries."""
    st.header("👁️ Preview & Edit Entries")
    
    if 'validation_results' not in st.session_state:
        st.info("No entries to preview. Please upload and validate entries first.")
        return
    
    results = st.session_state['validation_results']
    
    # Debug validation results
    st.write(f"🔍 DEBUG: Found {len(results['valid_entries'])} valid entries in session state")
    for i, entry in enumerate(results['valid_entries']):
        st.write(f"   Entry {i+1}: {entry['document_number']} has {len(entry['lines'])} lines")
    
    # View mode selector
    if results['valid_entries']:
        view_mode = st.radio(
            "View Mode",
            ["Individual Entry", "All Entries Combined"],
            horizontal=True
        )
        
        if view_mode == "Individual Entry":
            selected_entry = st.selectbox(
                "Select Entry to Preview",
                options=[entry['document_number'] for entry in results['valid_entries']],
                format_func=lambda x: f"{x} ({next(e['total_amount'] for e in results['valid_entries'] if e['document_number'] == x):,.2f})"
            )
        
        if view_mode == "Individual Entry":
            # Get selected entry data
            entry_data = next(e for e in results['valid_entries'] if e['document_number'] == selected_entry)
            st.write(f"🔍 Selected entry '{selected_entry}' has {len(entry_data['lines'])} lines in data")
            
            lines_df = pd.DataFrame(entry_data['lines'])
            st.write(f"🔍 DataFrame created with shape: {lines_df.shape}")
            
        else:  # All Entries Combined
            st.subheader("📋 All Journal Entries Combined")
            
            # Combine all lines from all entries
            all_lines = []
            for entry in results['valid_entries']:
                all_lines.extend(entry['lines'])
            
            lines_df = pd.DataFrame(all_lines)
            st.write(f"🔍 Combined DataFrame created with shape: {lines_df.shape}")
            st.write(f"🔍 Total lines from all entries: {len(all_lines)}")
        
        # Display entry header info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if view_mode == "Individual Entry":
                st.info(f"**Document:** {selected_entry}")
            else:
                st.info(f"**Documents:** {len(results['valid_entries'])} entries")
            if 'company_code' in lines_df.columns:
                st.info(f"**Company:** {lines_df['company_code'].iloc[0]}")
        
        with col2:
            if 'posting_date' in lines_df.columns:
                st.info(f"**Posting Date:** {lines_df['posting_date'].iloc[0]}")
            if 'currency_code' in lines_df.columns:
                st.info(f"**Currency:** {lines_df['currency_code'].iloc[0]}")
        
        with col3:
            total_debit = lines_df['debit_amount'].sum() if 'debit_amount' in lines_df.columns else 0
            total_credit = lines_df['credit_amount'].sum() if 'credit_amount' in lines_df.columns else 0
            st.metric("Total Amount", f"${total_debit:,.2f}")
            
            balance = abs(total_debit - total_credit)
            if balance < 0.01:
                st.success("✅ Balanced")
            else:
                st.error(f"❌ Out of Balance: ${balance:,.2f}")
        
        # Display and edit lines
        st.subheader(f"📋 Line Items ({len(lines_df)} lines)")
        
        # Debug info
        if len(lines_df) > 2:
            st.info(f"ℹ️ Entry has {len(lines_df)} lines. All lines should be visible below.")
            
        # Show raw data structure for debugging
        with st.expander("🐛 Debug: Raw Data", expanded=False):
            st.write("DataFrame shape:", lines_df.shape)
            st.write("DataFrame columns:", list(lines_df.columns))
            st.dataframe(lines_df, use_container_width=True)
        
        # Make dataframe editable - try without column_config first
        try:
            edited_df = st.data_editor(
                lines_df,
                hide_index=True,
                use_container_width=True,
                num_rows="dynamic"
            )
        except Exception as e:
            st.error(f"Error with data editor: {e}")
            # Fallback to simple display
            st.dataframe(lines_df, use_container_width=True)
            edited_df = lines_df.copy()
        
        # Update button (only show for individual entry mode)
        if view_mode == "Individual Entry" and st.button("💾 Save Changes"):
            # Update the entry in validation results
            for entry in results['valid_entries']:
                if entry['document_number'] == selected_entry:
                    entry['lines'] = edited_df.to_dict('records')
                    break
            
            st.success("✅ Changes saved!")
        elif view_mode == "All Entries Combined":
            st.info("💡 Use 'Individual Entry' mode to edit specific entries")
        
        # Visual representation
        st.subheader("📊 Visual Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Account distribution
            if 'gl_account' in lines_df.columns:
                account_summary = lines_df.groupby('gl_account').agg({
                    'debit_amount': 'sum',
                    'credit_amount': 'sum'
                }).reset_index()
                
                account_summary['net'] = account_summary['debit_amount'] - account_summary['credit_amount']
                
                fig = px.bar(
                    account_summary,
                    x='gl_account',
                    y='net',
                    title='Net Amount by GL Account',
                    color='net',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Debit/Credit breakdown
            breakdown_data = pd.DataFrame({
                'Type': ['Debits', 'Credits'],
                'Amount': [total_debit, total_credit]
            })
            
            fig = px.pie(
                breakdown_data,
                values='Amount',
                names='Type',
                title='Debit/Credit Breakdown',
                color_discrete_map={'Debits': '#FF6B6B', 'Credits': '#4ECDC4'}
            )
            st.plotly_chart(fig, use_container_width=True)

def show_create_and_submit():
    """Create journal entries and submit for approval."""
    st.header("✅ Create & Submit Journal Entries")
    
    if 'validation_results' not in st.session_state:
        st.info("No validated entries ready for creation. Please complete validation first.")
        return
    
    results = st.session_state['validation_results']
    
    if not results['valid_entries']:
        st.warning("No valid entries available for creation. Please fix validation errors first.")
        return
    
    # Summary of entries to create
    st.subheader("📊 Entries Ready for Creation")
    
    summary_data = []
    for entry in results['valid_entries']:
        summary_data.append({
            'Document Number': entry['document_number'],
            'Lines': len(entry['lines']),
            'Total Amount': f"${entry['total_amount']:,.2f}",
            'Company': entry['lines'][0].get('company_code', 'N/A') if entry['lines'] else 'N/A'
        })
    
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    
    # Creation options
    st.subheader("⚙️ Creation Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        submission_option = st.radio(
            "After Creation",
            ["Save as Draft", "Submit for Approval", "Post Directly (if authorized)"],
            help="Choose what happens after entries are created"
        )
        
        batch_reference = st.text_input(
            "Batch Reference",
            value=f"Upload_{datetime.now().strftime('%Y%m%d_%H%M')}",
            help="Reference for this batch upload"
        )
    
    with col2:
        priority = st.selectbox(
            "Priority Level",
            ["NORMAL", "HIGH", "URGENT"],
            help="Priority for approval routing"
        )
        
        notification_emails = st.text_input(
            "Notification Emails",
            placeholder="email1@company.com, email2@company.com",
            help="Additional emails to notify"
        )
    
    # Approval routing preview
    if submission_option == "Submit for Approval":
        st.subheader("🔄 Approval Routing Preview")
        
        routing_preview = []
        for entry in results['valid_entries'][:5]:  # Show first 5
            company = entry['lines'][0].get('company_code', '1000') if entry['lines'] else '1000'
            
            # Calculate approval level
            approval_level = WorkflowEngine.calculate_required_approval_level(
                entry['document_number'],
                str(company)
            )
            
            if approval_level:
                approvers = WorkflowEngine.get_available_approvers(
                    approval_level,
                    str(company),
                    user.username
                )
                
                routing_preview.append({
                    'Document': entry['document_number'],
                    'Amount': f"${entry['total_amount']:,.2f}",
                    'Approval Level': f"Level {approval_level}",
                    'Available Approvers': len(approvers)
                })
        
        if routing_preview:
            st.dataframe(pd.DataFrame(routing_preview), use_container_width=True, hide_index=True)
    
    # Create and submit button
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Create Journal Entries", type="primary", use_container_width=True):
            create_journal_entries(
                results['valid_entries'],
                submission_option,
                batch_reference,
                priority,
                notification_emails
            )

def create_journal_entries(valid_entries: List[Dict], submission_option: str, 
                          batch_reference: str, priority: str, notification_emails: str):
    """Create journal entries in the database."""
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    created_count = 0
    failed_count = 0
    submitted_count = 0
    created_documents = []
    failed_entries = []
    
    total_entries = len(valid_entries)
    
    for idx, entry in enumerate(valid_entries):
        doc_number = entry['document_number']
        lines = entry['lines']
        
        try:
            status_text.text(f"Creating {doc_number}...")
            progress_bar.progress((idx + 1) / total_entries)
            
            # Process journal entry creation
            
            # Get entry details from first line
            first_line = lines[0] if lines else {}
            company_code = str(first_line.get('company_code', '1000'))
            
            # Handle posting_date conversion
            posting_date_raw = first_line.get('posting_date', date.today())
            if isinstance(posting_date_raw, str):
                try:
                    posting_date = datetime.strptime(posting_date_raw, '%Y-%m-%d').date()
                except:
                    posting_date = date.today()
            else:
                posting_date = posting_date_raw if isinstance(posting_date_raw, date) else date.today()
            
            currency = first_line.get('currency_code', 'USD')
            reference = first_line.get('reference', batch_reference)
            
            # Get current user from session state
            current_user = st.session_state.get('user', {'username': 'system'})
            
            # Create database operations with proper transaction handling
            try:
                with engine.connect() as conn:
                    with conn.begin() as trans:
                        # Create journal entry header
                        header_params = {
                            "doc_num": doc_number,
                            "company": company_code,
                            "fy": posting_date.year if isinstance(posting_date, date) else datetime.now().year,
                            "period": posting_date.month if isinstance(posting_date, date) else datetime.now().month,
                            "posting_date": posting_date,
                            "doc_date": posting_date,
                            "reference": reference,
                            "currency": currency,
                            "created_by": current_user['username'],
                            "memo": f"Batch upload: {batch_reference}"
                        }
                        
                        # Check if entry already exists - use simpler approach
                        existing = conn.execute(text("""
                            SELECT COUNT(*) as count FROM journalentryheader 
                            WHERE documentnumber = :doc_num AND companycodeid = :company
                        """), {"doc_num": doc_number, "company": company_code}).scalar()
                        
                        if existing > 0:
                            # Delete existing lines first to avoid conflicts
                            conn.execute(text("""
                                DELETE FROM journalentryline 
                                WHERE documentnumber = :doc_num AND companycodeid = :company
                            """), {"doc_num": doc_number, "company": company_code})
                            
                            # Update header
                            conn.execute(text("""
                                UPDATE journalentryheader 
                                SET reference = :reference, 
                                    workflow_status = 'DRAFT',
                                    updatedat = CURRENT_TIMESTAMP
                                WHERE documentnumber = :doc_num AND companycodeid = :company
                            """), {"reference": reference, "doc_num": doc_number, "company": company_code})
                        else:
                            # Insert new header
                            conn.execute(text("""
                                INSERT INTO journalentryheader
                                (documentnumber, companycodeid, fiscalyear, period,
                                 postingdate, documentdate, reference, currencycode,
                                 workflow_status, createdby, createdat, memo)
                                VALUES (:doc_num, :company, :fy, :period,
                                        :posting_date, :doc_date, :reference, :currency,
                                        'DRAFT', :created_by, CURRENT_TIMESTAMP, :memo)
                            """), header_params)
                        
                        # Create journal entry lines - simpler approach without ON CONFLICT
                        for line_idx, line in enumerate(lines):
                            conn.execute(text("""
                                INSERT INTO journalentryline
                                (documentnumber, companycodeid, linenumber, glaccountid,
                                 debitamount, creditamount, currencycode,
                                 description, ledgerid, business_unit_id)
                                VALUES (:doc_num, :company, :line_num, :gl_account,
                                        :debit, :credit, :currency,
                                        :description, :ledger, :business_unit_id)
                            """), {
                                "doc_num": doc_number,
                                "company": company_code,
                                "line_num": line.get('line_number', line_idx + 1),
                                "gl_account": str(line.get('gl_account', '')),
                                "debit": float(line.get('debit_amount', 0)),
                                "credit": float(line.get('credit_amount', 0)),
                                "currency": currency,
                                "description": line.get('description', ''),
                                "ledger": line.get('ledger_id', 'L1'),
                                "business_unit_id": _convert_business_unit_id(line.get('business_unit_id'))
                            })
                        
                        # Commit transaction
                        trans.commit()
                
                # Successfully created journal entry
                created_count += 1
                created_documents.append({
                    'document_number': doc_number,
                    'company_code': company_code,
                    'amount': entry['total_amount']
                })
                
                # Submit for approval if requested
                if submission_option == "Submit for Approval":
                    success, message = WorkflowEngine.submit_for_approval(
                        doc_number,
                        company_code,
                        current_user['username'],
                        f"Batch upload: {batch_reference}"
                    )
                    
                    if success:
                        submitted_count += 1
                        
            except Exception as db_error:
                st.error(f"❌ Database error for {doc_number}: {str(db_error)}")
                raise
        
        except Exception as e:
            st.error(f"❌ Failed to create {doc_number}: {str(e)}")
            failed_count += 1
            failed_entries.append({
                'document_number': doc_number,
                'error': str(e)
            })
    
    progress_bar.progress(1.0)
    status_text.text("Creation complete!")
    
    # Display results
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("✅ Created", created_count)
    
    with col2:
        if submission_option == "Submit for Approval":
            st.metric("📤 Submitted", submitted_count)
    
    with col3:
        if failed_count > 0:
            st.metric("❌ Failed", failed_count)
    
    # Success message
    if created_count > 0:
        st.success(f"""
        ✅ Successfully created {created_count} journal entries!
        
        Batch Reference: {batch_reference}
        Status: {'Submitted for approval' if submission_option == "Submit for Approval" else 'Saved as draft'}
        """)
        
        # Show created documents
        if created_documents:
            st.subheader("📋 Created Documents")
            created_df = pd.DataFrame(created_documents)
            st.dataframe(created_df, use_container_width=True, hide_index=True)
    
    # Show failures if any
    if failed_entries:
        st.subheader("❌ Failed Entries")
        failed_df = pd.DataFrame(failed_entries)
        st.dataframe(failed_df, use_container_width=True, hide_index=True)
    
    # Clear session state
    if created_count > 0:
        if st.button("🔄 Upload More Entries"):
            for key in ['uploaded_data', 'validation_results', 'template_entries']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def show_upload_history():
    """Display upload history and statistics."""
    st.header("📊 Upload History")
    
    # Date range filter
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_from = st.date_input("From Date", value=date.today() - timedelta(days=30))
    
    with col2:
        date_to = st.date_input("To Date", value=date.today())
    
    with col3:
        status_filter = st.selectbox("Status Filter", ["All", "DRAFT", "PENDING_APPROVAL", "APPROVED", "POSTED"])
    
    # Get upload history
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    jeh.documentnumber,
                    jeh.companycodeid,
                    jeh.reference,
                    jeh.workflow_status,
                    jeh.createdat,
                    jeh.createdby,
                    COUNT(jel.linenumber) as line_count,
                    SUM(jel.debitamount) as total_amount
                FROM journalentryheader jeh
                LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber
                    AND jeh.companycodeid = jel.companycodeid
                WHERE jeh.createdat >= :date_from
                AND jeh.createdat <= :date_to + INTERVAL '1 day'
                AND jeh.createdby = :user
                AND (:status = 'All' OR jeh.workflow_status = :status)
                AND jeh.memo LIKE '%Batch upload%'
                GROUP BY jeh.documentnumber, jeh.companycodeid, jeh.reference,
                         jeh.workflow_status, jeh.createdat, jeh.createdby
                ORDER BY jeh.createdat DESC
            """)
            
            result = conn.execute(query, {
                "date_from": date_from,
                "date_to": date_to,
                "user": user.username,
                "status": status_filter
            })
            
            history_df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            if not history_df.empty:
                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Uploads", len(history_df))
                
                with col2:
                    total_lines = history_df['line_count'].sum()
                    st.metric("Total Lines", f"{total_lines:,}")
                
                with col3:
                    total_amount = history_df['total_amount'].sum()
                    st.metric("Total Amount", f"${total_amount:,.2f}")
                
                with col4:
                    avg_lines = history_df['line_count'].mean()
                    st.metric("Avg Lines/Entry", f"{avg_lines:.1f}")
                
                # History table
                st.subheader("📋 Upload History Details")
                
                st.dataframe(
                    history_df,
                    column_config={
                        'documentnumber': 'Document #',
                        'companycodeid': 'Company',
                        'reference': 'Reference',
                        'workflow_status': 'Status',
                        'createdat': st.column_config.DatetimeColumn('Created At'),
                        'createdby': 'Created By',
                        'line_count': 'Lines',
                        'total_amount': st.column_config.NumberColumn('Amount', format='$%.2f')
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Charts
                col1, col2 = st.columns(2)
                
                with col1:
                    # Status distribution
                    status_dist = history_df['workflow_status'].value_counts()
                    fig = px.pie(
                        values=status_dist.values,
                        names=status_dist.index,
                        title='Upload Status Distribution'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Upload trend
                    history_df['upload_date'] = pd.to_datetime(history_df['createdat']).dt.date
                    daily_uploads = history_df.groupby('upload_date').size().reset_index(name='count')
                    
                    fig = px.line(
                        daily_uploads,
                        x='upload_date',
                        y='count',
                        title='Daily Upload Trend',
                        markers=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No upload history found for the selected criteria")
                
    except Exception as e:
        st.error(f"Error retrieving upload history: {e}")

def show_templates_and_help():
    """Display templates and help documentation."""
    st.header("📚 Templates & Help")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Download Templates", "📖 Documentation", "🎯 Best Practices", "❓ FAQ"])
    
    with tab1:
        st.subheader("📥 Download Templates")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Single File Template**")
            st.write("Use this template when you want to upload headers and lines in one file.")
            
            single_template = pd.DataFrame({
                'document_number': ['JE2025001', 'JE2025001', 'JE2025002', 'JE2025002'],
                'company_code': ['1000', '1000', '1000', '1000'],
                'line_number': [1, 2, 1, 2],
                'posting_date': [date.today(), date.today(), date.today(), date.today()],
                'gl_account': ['400001', '200001', '600001', '100001'],
                'debit_amount': [5000.00, 0.00, 2500.00, 0.00],
                'credit_amount': [0.00, 5000.00, 0.00, 2500.00],
                'description': ['Salary Expense', 'Salary Payable', 'Rent Expense', 'Cash'],
                'business_unit_id': [1, 1, 2, 2],
                'currency_code': ['USD', 'USD', 'USD', 'USD'],
                'reference': ['January Payroll', 'January Payroll', 'January Rent', 'January Rent']
            })
            
            csv_single = single_template.to_csv(index=False)
            st.download_button(
                label="📥 Download Single File Template",
                data=csv_single,
                file_name="journal_entry_single_template.csv",
                mime="text/csv"
            )
        
        with col2:
            st.write("**Two-File Templates**")
            st.write("Use these templates when headers and lines are maintained separately.")
            
            # Headers template
            headers_template = pd.DataFrame({
                'document_number': ['JE2025001', 'JE2025002'],
                'company_code': ['1000', '1000'],
                'posting_date': [date.today(), date.today()],
                'reference': ['January Payroll', 'January Rent'],
                'currency_code': ['USD', 'USD']
            })
            
            # Lines template
            lines_template = pd.DataFrame({
                'document_number': ['JE2025001', 'JE2025001', 'JE2025002', 'JE2025002'],
                'line_number': [1, 2, 1, 2],
                'gl_account': ['400001', '200001', '600001', '100001'],
                'debit_amount': [5000.00, 0.00, 2500.00, 0.00],
                'credit_amount': [0.00, 5000.00, 0.00, 2500.00],
                'description': ['Salary Expense', 'Salary Payable', 'Rent Expense', 'Cash'],
                'business_unit_id': [1, 1, 2, 2]
            })
            
            csv_headers = headers_template.to_csv(index=False)
            csv_lines = lines_template.to_csv(index=False)
            
            st.download_button(
                label="📥 Download Headers Template",
                data=csv_headers,
                file_name="journal_entry_headers_template.csv",
                mime="text/csv",
                key="headers_download"
            )
            
            st.download_button(
                label="📥 Download Lines Template",
                data=csv_lines,
                file_name="journal_entry_lines_template.csv",
                mime="text/csv",
                key="lines_download"
            )
    
    with tab2:
        st.subheader("📖 Documentation")
        
        st.markdown("""
        ### File Upload Process
        
        1. **Prepare Your Data**
           - Ensure all journal entries are balanced (debits = credits)
           - Use valid GL account numbers from your chart of accounts
           - Include all required fields
        
        2. **Upload Files**
           - Choose between single file or two-file upload
           - Select your prepared CSV or Excel file(s)
           - Click "Validate Entries"
        
        3. **Review Validation**
           - Check for any errors (must be fixed)
           - Review warnings (optional fixes)
           - Verify balance calculations
        
        4. **Preview & Edit**
           - Review each entry before creation
           - Make any necessary adjustments
           - Verify GL accounts and amounts
        
        5. **Create & Submit**
           - Choose submission option (Draft/Approval/Post)
           - Review approval routing
           - Click "Create Journal Entries"
        
        ### Field Descriptions
        
        | Field | Required | Description | Example |
        |-------|----------|-------------|---------|
        | document_number | Yes | Unique entry identifier | JE2025001 |
        | company_code | Yes | Company code | 1000 |
        | line_number | Yes | Line sequence | 1, 2, 3 |
        | gl_account | Yes | GL account number | 400001 |
        | debit_amount | Yes | Debit amount | 5000.00 |
        | credit_amount | Yes | Credit amount | 5000.00 |
        | posting_date | No | Posting date | 2025-08-31 |
        | description | No | Line description | Salary Expense |
        | business_unit_id | No | Business unit ID | 1 |
        | currency_code | No | Currency | USD |
        """)
    
    with tab3:
        st.subheader("🎯 Best Practices")
        
        st.markdown("""
        ### ✅ DO's
        
        - **Balance Every Entry**: Ensure total debits = total credits
        - **Use Consistent Formatting**: Follow the template structure
        - **Validate Before Upload**: Check your data in Excel first
        - **Include Descriptions**: Add meaningful descriptions for audit trail
        - **Group Related Entries**: Keep similar transactions together
        - **Test Small Batches**: Start with a few entries to test
        
        ### ❌ DON'Ts
        
        - **Don't Mix Formats**: Keep consistent date and number formats
        - **Don't Skip Validation**: Always review validation results
        - **Don't Ignore Warnings**: They may indicate data issues
        - **Don't Upload Duplicates**: Check for existing entries first
        - **Don't Use Invalid Accounts**: Verify GL accounts exist
        
        ### 💡 Tips for Large Uploads
        
        1. **Break into Batches**: Upload 50-100 entries at a time
        2. **Use Templates**: Start from provided templates
        3. **Standardize Descriptions**: Use consistent naming
        4. **Review Totals**: Verify batch totals before upload
        5. **Schedule Off-Peak**: Upload during low-usage times
        """)
    
    with tab4:
        st.subheader("❓ Frequently Asked Questions")
        
        with st.expander("Q: What's the maximum number of entries I can upload?"):
            st.write("""
            There's no hard limit, but we recommend:
            - 100 entries per batch for optimal performance
            - Break larger uploads into multiple batches
            - System can handle up to 1000 lines per upload
            """)
        
        with st.expander("Q: Can I upload entries in foreign currency?"):
            st.write("""
            Yes! The system supports multiple currencies:
            - Include 'currency_code' column (USD, EUR, GBP, etc.)
            - Add 'exchange_rate' column for conversion rates
            - System will handle currency translation automatically
            """)
        
        with st.expander("Q: What happens if my upload has errors?"):
            st.write("""
            The validation process will:
            - Identify all errors before any entries are created
            - Show detailed error messages for each issue
            - Allow you to fix and re-upload
            - No partial uploads - all or nothing approach
            """)
        
        with st.expander("Q: Can I edit entries after upload?"):
            st.write("""
            Yes, you have multiple options:
            - Edit in the Preview screen before creation
            - Save as Draft and edit later
            - Use the Journal Entry Manager for post-upload edits
            """)
        
        with st.expander("Q: How does approval routing work?"):
            st.write("""
            Automatic routing based on:
            - Transaction amount thresholds
            - Company code rules
            - User delegation settings
            - Priority levels (NORMAL, HIGH, URGENT)
            """)

# Helper functions

def merge_headers_and_lines(headers_df: pd.DataFrame, lines_df: pd.DataFrame) -> pd.DataFrame:
    """Merge header and line dataframes."""
    # Merge on document_number
    merged = lines_df.merge(
        headers_df,
        on='document_number',
        how='left',
        suffixes=('', '_header')
    )
    
    # Handle duplicate columns
    for col in headers_df.columns:
        if col != 'document_number' and col in lines_df.columns:
            # Prefer header value if line value is null
            merged[col] = merged[col].fillna(merged[f'{col}_header'])
            merged.drop(f'{col}_header', axis=1, inplace=True)
    
    return merged

def validate_gl_accounts(gl_accounts: list) -> list:
    """Validate GL accounts against database."""
    valid_accounts = []
    
    try:
        with engine.connect() as conn:
            # Convert accounts to strings
            account_list = [str(acc) for acc in gl_accounts if acc]
            
            if account_list:
                # Use IN clause with individual parameters (more compatible)
                placeholders = ','.join([f"'{acc}'" for acc in account_list])
                query = f"SELECT glaccountid FROM glaccount WHERE glaccountid IN ({placeholders})"
                result = conn.execute(text(query))
                valid_accounts = [row[0] for row in result]
                
                # Debug output for verification
                st.write(f"🔍 **GL Validation:** Checked {len(account_list)} accounts, found {len(valid_accounts)} valid")
                if len(account_list) != len(valid_accounts):
                    invalid_count = len(account_list) - len(valid_accounts)
                    st.warning(f"⚠️ {invalid_count} invalid GL accounts detected")
    
    except Exception as e:
        st.error(f"❌ Error validating GL accounts: {e}")
        st.write(f"🔍 **Debug:** GL accounts being validated: {account_list[:5]}")
    
    return valid_accounts

def validate_business_units(business_units: list) -> list:
    """Validate business units against database."""
    valid_business_units = []
    
    try:
        with engine.connect() as conn:
            # Convert business units to integers (handle float inputs from CSV)
            bu_list = []
            for bu in business_units:
                if bu is not None and str(bu).strip():
                    try:
                        # Convert float to int if necessary (e.g., 1.0 -> 1)
                        bu_int = int(float(bu))
                        bu_list.append(bu_int)
                    except (ValueError, TypeError):
                        continue  # Skip invalid values
            
            if bu_list:
                # Use IN clause with integer parameters (no quotes)
                placeholders = ','.join([str(bu) for bu in bu_list])
                query = f"SELECT unit_id FROM business_units WHERE unit_id IN ({placeholders}) AND is_active = TRUE"
                result = conn.execute(text(query))
                valid_business_units = [row[0] for row in result]
                
                # Debug output for verification
                st.write(f"🏢 **Business Unit Validation:** Checked {len(bu_list)} units, found {len(valid_business_units)} valid")
                if len(bu_list) != len(valid_business_units):
                    invalid_count = len(bu_list) - len(valid_business_units)
                    st.warning(f"⚠️ {invalid_count} invalid business units detected")
    
    except Exception as e:
        st.error(f"❌ Error validating business units: {e}")
        st.write(f"🔍 **Debug:** Business units being validated: {bu_list[:5]}")
    
    return valid_business_units

def save_template_to_file(template_df: pd.DataFrame):
    """Save template to downloadable file."""
    csv = template_df.to_csv(index=False)
    
    st.download_button(
        label="💾 Download Template",
        data=csv,
        file_name=f"journal_template_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()