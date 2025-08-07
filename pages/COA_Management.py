"""
Chart of Accounts Management Interface
Comprehensive UI for managing Account Groups, Field Status Groups, and GL Accounts
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from sqlalchemy import text
from db_config import engine
from utils.navigation import show_sap_sidebar, show_breadcrumb
from utils.logger import get_logger
import traceback

# Configure page
st.set_page_config(
    page_title="🏗️ COA Management", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Navigation
show_sap_sidebar()
show_breadcrumb("COA Management", "Master Data", "Configuration")

logger = get_logger("coa_management")

# Custom CSS for interface styling
st.markdown("""
<style>
.metric-container {
    background: linear-gradient(90deg, #0f4c75 0%, #3282b8 100%);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    margin: 0.5rem 0;
}
.account-group-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1rem;
    margin: 0.5rem 0;
    background: #f8f9fa;
}
.status-active { color: #28a745; font-weight: bold; }
.status-inactive { color: #dc3545; font-weight: bold; }
.coa-section {
    border-left: 4px solid #0f4c75;
    padding-left: 1rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

st.title("🏗️ Chart of Accounts Management")
st.markdown("Comprehensive management interface for Account Groups, Field Status Groups, and GL Accounts")

# Load current user info (you might want to integrate with your auth system)
current_user = st.session_state.get('username', 'SYSTEM_USER')

def get_coa_overview():
    """Get overview statistics for COA structure"""
    try:
        with engine.connect() as conn:
            # Account Groups stats
            ag_stats = conn.execute(text("""
                SELECT COUNT(*) as total_groups,
                       COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_groups,
                       COUNT(DISTINCT account_class) as distinct_classes
                FROM account_groups
            """)).fetchone()
            
            # GL Accounts stats
            gl_stats = conn.execute(text("""
                SELECT COUNT(*) as total_accounts,
                       COUNT(CASE WHEN marked_for_deletion = FALSE OR marked_for_deletion IS NULL THEN 1 END) as active_accounts,
                       COUNT(DISTINCT account_class) as classes_in_use,
                       COUNT(DISTINCT account_group_code) as groups_in_use
                FROM glaccount
            """)).fetchone()
            
            # Field Status Groups stats
            fsg_stats = conn.execute(text("""
                SELECT COUNT(*) as total_fsgs,
                       COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_fsgs
                FROM field_status_groups
            """)).fetchone()
            
            # Usage statistics
            usage_stats = conn.execute(text("""
                SELECT ag.account_class,
                       COUNT(ga.glaccountid) as account_count,
                       ag.number_range_from,
                       ag.number_range_to,
                       ROUND(COUNT(ga.glaccountid) * 100.0 / 
                             NULLIF((ag.number_range_to::bigint - ag.number_range_from::bigint + 1), 0), 2) as utilization_pct
                FROM account_groups ag
                LEFT JOIN glaccount ga ON ag.group_code = ga.account_group_code
                    AND (ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL)
                WHERE ag.is_active = TRUE
                GROUP BY ag.account_class, ag.number_range_from, ag.number_range_to
                ORDER BY ag.account_class
            """)).fetchall()
            
        return ag_stats, gl_stats, fsg_stats, usage_stats
    except Exception as e:
        st.error(f"Error loading COA overview: {e}")
        logger.error(f"COA overview error: {e}")
        return None, None, None, None

def manage_account_groups():
    """Account Groups Management Interface"""
    st.markdown('<div class="coa-section">', unsafe_allow_html=True)
    st.subheader("📁 Account Groups Management")
    
    # Load existing account groups
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text("""
                SELECT group_code, group_name, account_class, 
                       number_range_from, number_range_to,
                       require_business_unit, require_business_area,
                       default_field_status_group, is_active,
                       created_by, created_at
                FROM account_groups
                ORDER BY account_class, group_code
            """), conn)
    except Exception as e:
        st.error(f"Error loading account groups: {e}")
        return
    
    # Display current account groups
    if not df.empty:
        st.markdown("**Current Account Groups:**")
        
        # Group by account class for better display
        for account_class in df['account_class'].unique():
            class_data = df[df['account_class'] == account_class]
            
            with st.expander(f"{account_class} ({len(class_data)} groups)", expanded=True):
                display_df = class_data[['group_code', 'group_name', 'number_range_from', 
                                       'number_range_to', 'require_business_unit', 'is_active']].copy()
                display_df.columns = ['Code', 'Name', 'From', 'To', 'Req BU', 'Active']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Account Group Form
    st.markdown("**Create/Edit Account Group:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Basic Information
        ag_mode = st.selectbox("Mode", ["Create New", "Edit Existing"])
        
        if ag_mode == "Edit Existing" and not df.empty:
            selected_group = st.selectbox("Select Group to Edit", 
                                        options=df['group_code'].tolist(),
                                        format_func=lambda x: f"{x} - {df[df['group_code']==x]['group_name'].iloc[0]}")
            edit_data = df[df['group_code'] == selected_group].iloc[0] if selected_group else None
        else:
            edit_data = None
            selected_group = None
        
        group_code = st.text_input("Group Code", 
                                 value=edit_data['group_code'] if edit_data is not None else "",
                                 max_chars=10,
                                 disabled=ag_mode == "Edit Existing")
        
        group_name = st.text_input("Group Name", 
                                 value=edit_data['group_name'] if edit_data is not None else "",
                                 max_chars=100)
        
        account_class = st.selectbox("Account Class", 
                                   options=['ASSETS', 'LIABILITIES', 'EQUITY', 'REVENUE', 'EXPENSES', 'STATISTICAL'],
                                   index=['ASSETS', 'LIABILITIES', 'EQUITY', 'REVENUE', 'EXPENSES', 'STATISTICAL'].index(edit_data['account_class']) if edit_data is not None else 0)
        
        group_description = st.text_area("Description", 
                                       value="",
                                       height=100)
    
    with col2:
        # Number Range
        st.markdown("**Number Range:**")
        range_from = st.text_input("Range From", 
                                 value=edit_data['number_range_from'] if edit_data is not None else "",
                                 max_chars=10)
        
        range_to = st.text_input("Range To", 
                               value=edit_data['number_range_to'] if edit_data is not None else "",
                               max_chars=10)
        
        # Field Requirements
        st.markdown("**Field Requirements:**")
        req_business_unit = st.checkbox("Require Business Unit", 
                                    value=edit_data['require_business_unit'] if edit_data is not None else False)
        
        req_business_area = st.checkbox("Require Business Area", 
                                      value=edit_data['require_business_area'] if edit_data is not None else False)
        
        # Field Status Group
        try:
            with engine.connect() as conn:
                fsg_options = pd.read_sql(text("SELECT group_id, group_name FROM field_status_groups WHERE is_active = TRUE ORDER BY group_id"), conn)
                fsg_list = fsg_options['group_id'].tolist()
        except:
            fsg_list = []
        
        default_fsg = st.selectbox("Default Field Status Group", 
                                 options=fsg_list,
                                 index=fsg_list.index(edit_data['default_field_status_group']) if edit_data is not None and edit_data['default_field_status_group'] in fsg_list else 0)
        
        is_active = st.checkbox("Active", 
                              value=edit_data['is_active'] if edit_data is not None else True)
    
    # Save/Update Button
    if st.button(f"{'Update' if ag_mode == 'Edit Existing' else 'Create'} Account Group", type="primary"):
        if not all([group_code, group_name, range_from, range_to]):
            st.error("Please fill in all required fields")
        else:
            try:
                with engine.connect() as conn:
                    with conn.begin():
                        if ag_mode == "Create New":
                            # Check if group code already exists
                            existing = conn.execute(text("SELECT COUNT(*) FROM account_groups WHERE group_code = :code"), 
                                                  {"code": group_code}).fetchone()[0]
                            if existing > 0:
                                st.error(f"Account Group {group_code} already exists")
                                return
                            
                            # Insert new group
                            conn.execute(text("""
                                INSERT INTO account_groups (
                                    group_code, group_name, group_description, account_class,
                                    number_range_from, number_range_to,
                                    require_business_unit, require_business_area,
                                    default_field_status_group, is_active, created_by
                                ) VALUES (
                                    :code, :name, :desc, :class,
                                    :from_range, :to_range,
                                    :req_bu, :req_ba,
                                    :fsg, :active, :user
                                )
                            """), {
                                "code": group_code, "name": group_name, "desc": group_description,
                                "class": account_class, "from_range": range_from, "to_range": range_to,
                                "req_bu": req_business_unit, "req_ba": req_business_area,
                                "fsg": default_fsg, "active": is_active, "user": current_user
                            })
                            st.success(f"Account Group {group_code} created successfully!")
                        
                        else:  # Edit mode
                            conn.execute(text("""
                                UPDATE account_groups SET
                                    group_name = :name, group_description = :desc, account_class = :class,
                                    number_range_from = :from_range, number_range_to = :to_range,
                                    require_business_unit = :req_bu, 
                                    require_business_area = :req_ba, default_field_status_group = :fsg,
                                    is_active = :active, modified_by = :user, modified_at = CURRENT_TIMESTAMP
                                WHERE group_code = :code
                            """), {
                                "code": group_code, "name": group_name, "desc": group_description,
                                "class": account_class, "from_range": range_from, "to_range": range_to,
                                "req_bu": req_business_unit, "req_ba": req_business_area,
                                "fsg": default_fsg, "active": is_active, "user": current_user
                            })
                            st.success(f"Account Group {group_code} updated successfully!")
                        
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error saving account group: {e}")
                logger.error(f"Account group save error: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def manage_field_status_groups():
    """Field Status Groups Management Interface"""
    st.markdown('<div class="coa-section">', unsafe_allow_html=True)
    st.subheader("🔧 Field Status Groups Management")
    
    # Load existing FSGs
    try:
        with engine.connect() as conn:
            fsg_df = pd.read_sql(text("""
                SELECT group_id, group_name, group_description,
                       cost_center_status, profit_center_status, business_area_status,
                       tax_code_status, trading_partner_status,
                       is_active, created_by, created_at
                FROM field_status_groups
                ORDER BY group_id
            """), conn)
    except Exception as e:
        st.error(f"Error loading field status groups: {e}")
        return
    
    # Display current FSGs
    if not fsg_df.empty:
        st.markdown("**Current Field Status Groups:**")
        display_fsg = fsg_df[['group_id', 'group_name', 'cost_center_status', 
                            'profit_center_status', 'tax_code_status', 'is_active']].copy()
        display_fsg.columns = ['ID', 'Name', 'Cost Center', 'Profit Center', 'Tax Code', 'Active']
        st.dataframe(display_fsg, use_container_width=True, hide_index=True)
    
    # FSG Form
    st.markdown("**Create/Edit Field Status Group:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fsg_mode = st.selectbox("FSG Mode", ["Create New", "Edit Existing"], key="fsg_mode")
        
        if fsg_mode == "Edit Existing" and not fsg_df.empty:
            selected_fsg = st.selectbox("Select FSG to Edit", 
                                      options=fsg_df['group_id'].tolist(),
                                      format_func=lambda x: f"{x} - {fsg_df[fsg_df['group_id']==x]['group_name'].iloc[0]}")
            fsg_edit_data = fsg_df[fsg_df['group_id'] == selected_fsg].iloc[0] if selected_fsg else None
        else:
            fsg_edit_data = None
        
        fsg_id = st.text_input("FSG ID", 
                             value=fsg_edit_data['group_id'] if fsg_edit_data is not None else "",
                             max_chars=10,
                             disabled=fsg_mode == "Edit Existing")
        
        fsg_name = st.text_input("FSG Name", 
                               value=fsg_edit_data['group_name'] if fsg_edit_data is not None else "",
                               max_chars=100)
        
        fsg_description = st.text_area("FSG Description", 
                                     value=fsg_edit_data['group_description'] if fsg_edit_data is not None else "",
                                     height=100)
    
    with col2:
        st.markdown("**Field Control Settings:**")
        
        status_options = ['SUP', 'REQ', 'OPT', 'DIS']
        status_labels = {'SUP': 'Suppress', 'REQ': 'Required', 'OPT': 'Optional', 'DIS': 'Display Only'}
        
        cc_status = st.selectbox("Cost Center Status", 
                               options=status_options,
                               format_func=lambda x: f"{x} - {status_labels[x]}",
                               index=status_options.index(fsg_edit_data['cost_center_status']) if fsg_edit_data is not None else 2)
        
        pc_status = st.selectbox("Profit Center Status", 
                               options=status_options,
                               format_func=lambda x: f"{x} - {status_labels[x]}",
                               index=status_options.index(fsg_edit_data['profit_center_status']) if fsg_edit_data is not None else 2)
        
        ba_status = st.selectbox("Business Area Status", 
                               options=status_options,
                               format_func=lambda x: f"{x} - {status_labels[x]}",
                               index=status_options.index(fsg_edit_data['business_area_status']) if fsg_edit_data is not None else 0)
        
        tax_status = st.selectbox("Tax Code Status", 
                                options=status_options,
                                format_func=lambda x: f"{x} - {status_labels[x]}",
                                index=status_options.index(fsg_edit_data['tax_code_status']) if fsg_edit_data is not None else 2)
        
        tp_status = st.selectbox("Trading Partner Status", 
                               options=status_options,
                               format_func=lambda x: f"{x} - {status_labels[x]}",
                               index=status_options.index(fsg_edit_data['trading_partner_status']) if fsg_edit_data is not None else 0)
        
        fsg_active = st.checkbox("FSG Active", 
                               value=fsg_edit_data['is_active'] if fsg_edit_data is not None else True)
    
    # Save FSG Button
    if st.button(f"{'Update' if fsg_mode == 'Edit Existing' else 'Create'} Field Status Group", type="primary", key="save_fsg"):
        if not all([fsg_id, fsg_name]):
            st.error("Please fill in FSG ID and Name")
        else:
            try:
                with engine.connect() as conn:
                    with conn.begin():
                        if fsg_mode == "Create New":
                            # Check if FSG ID already exists
                            existing = conn.execute(text("SELECT COUNT(*) FROM field_status_groups WHERE group_id = :id"), 
                                                  {"id": fsg_id}).fetchone()[0]
                            if existing > 0:
                                st.error(f"Field Status Group {fsg_id} already exists")
                                return
                            
                            # Insert new FSG
                            conn.execute(text("""
                                INSERT INTO field_status_groups (
                                    group_id, group_name, group_description,
                                    cost_center_status, profit_center_status, business_area_status,
                                    tax_code_status, trading_partner_status,
                                    is_active, created_by
                                ) VALUES (
                                    :id, :name, :desc,
                                    :cc_status, :pc_status, :ba_status,
                                    :tax_status, :tp_status,
                                    :active, :user
                                )
                            """), {
                                "id": fsg_id, "name": fsg_name, "desc": fsg_description,
                                "cc_status": cc_status, "pc_status": pc_status, "ba_status": ba_status,
                                "tax_status": tax_status, "tp_status": tp_status,
                                "active": fsg_active, "user": current_user
                            })
                            st.success(f"Field Status Group {fsg_id} created successfully!")
                        
                        else:  # Edit mode
                            conn.execute(text("""
                                UPDATE field_status_groups SET
                                    group_name = :name, group_description = :desc,
                                    cost_center_status = :cc_status, profit_center_status = :pc_status,
                                    business_area_status = :ba_status, tax_code_status = :tax_status,
                                    trading_partner_status = :tp_status, is_active = :active,
                                    modified_by = :user, modified_at = CURRENT_TIMESTAMP
                                WHERE group_id = :id
                            """), {
                                "id": fsg_id, "name": fsg_name, "desc": fsg_description,
                                "cc_status": cc_status, "pc_status": pc_status, "ba_status": ba_status,
                                "tax_status": tax_status, "tp_status": tp_status,
                                "active": fsg_active, "user": current_user
                            })
                            st.success(f"Field Status Group {fsg_id} updated successfully!")
                        
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error saving field status group: {e}")
                logger.error(f"FSG save error: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def manage_gl_accounts():
    """GL Accounts Management Interface"""
    st.markdown('<div class="coa-section">', unsafe_allow_html=True)
    st.subheader("📊 GL Accounts Management")
    
    # Account search and filtering
    col1, col2, col3 = st.columns(3)
    
    with col1:
        account_search = st.text_input("Search Account ID/Name", "")
    
    with col2:
        # Load account groups for filter
        try:
            with engine.connect() as conn:
                ag_options = pd.read_sql(text("SELECT group_code, group_name FROM account_groups WHERE is_active = TRUE ORDER BY group_code"), conn)
                ag_list = ['All'] + ag_options['group_code'].tolist()
        except:
            ag_list = ['All']
        
        selected_ag = st.selectbox("Filter by Account Group", ag_list)
    
    with col3:
        account_class_filter = st.selectbox("Filter by Account Class", 
                                          ['All', 'ASSETS', 'LIABILITIES', 'EQUITY', 'REVENUE', 'EXPENSES', 'STATISTICAL'])
    
    # Load and display GL accounts
    try:
        with engine.connect() as conn:
            where_conditions = ["(ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL)"]
            params = {}
            
            if account_search:
                where_conditions.append("(UPPER(ga.glaccountid) LIKE UPPER(:search) OR UPPER(ga.accountname) LIKE UPPER(:search))")
                params["search"] = f"%{account_search}%"
            
            if selected_ag != 'All':
                where_conditions.append("ga.account_group_code = :ag")
                params["ag"] = selected_ag
            
            if account_class_filter != 'All':
                where_conditions.append("ga.account_class = :class")
                params["class"] = account_class_filter
            
            where_clause = " AND ".join(where_conditions)
            
            gl_df = pd.read_sql(text(f"""
                SELECT ga.glaccountid, ga.accountname, ga.account_class, ga.account_group_code,
                       ga.balance_sheet_indicator, ga.pnl_statement_type,
                       ga.business_unit_required, ga.business_area_required,
                       ga.field_status_group, ga.reconciliation_account_type,
                       ga.migration_date, ag.group_name
                FROM glaccount ga
                LEFT JOIN account_groups ag ON ga.account_group_code = ag.group_code
                WHERE {where_clause}
                ORDER BY ga.glaccountid
                LIMIT 100
            """), conn, params=params)
    except Exception as e:
        st.error(f"Error loading GL accounts: {e}")
        return
    
    # Display results
    if not gl_df.empty:
        st.markdown(f"**Found {len(gl_df)} accounts** (showing first 100)")
        
        # Enhanced display with account group info
        display_gl = gl_df[['glaccountid', 'accountname', 'account_class', 'group_name', 
                           'business_unit_required', 'field_status_group']].copy()
        display_gl.columns = ['Account ID', 'Account Name', 'Class', 'Account Group', 
                            'Req BU', 'FSG']
        
        st.dataframe(display_gl, use_container_width=True, hide_index=True)
    else:
        st.info("No accounts found with the specified criteria")
    
    # GL Account Form
    st.markdown("**Create New GL Account:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_account_id = st.text_input("Account ID", max_chars=10, help="Enter 6-digit account number")
        new_account_name = st.text_input("Account Name", max_chars=100)
        new_account_type = st.selectbox("Account Type", 
                                      ['STANDARD', 'RECEIVABLE', 'PAYABLE', 'ASSET', 'STATISTICAL'])
        
        # Account Group selection
        try:
            with engine.connect() as conn:
                ag_create_options = pd.read_sql(text("SELECT group_code, group_name FROM account_groups WHERE is_active = TRUE ORDER BY group_code"), conn)
                ag_create_list = ag_create_options['group_code'].tolist()
        except:
            ag_create_list = []
        
        new_account_group = st.selectbox("Account Group", ag_create_list,
                                       format_func=lambda x: f"{x} - {ag_create_options[ag_create_options['group_code']==x]['group_name'].iloc[0] if x in ag_create_options['group_code'].values else x}")
    
    with col2:
        new_short_text = st.text_input("Short Text", max_chars=20)
        new_long_text = st.text_input("Long Text", max_chars=50)
        
        new_currency = st.selectbox("Account Currency", ['USD', 'EUR', 'PHP', 'JPY'])
        
        col2a, col2b = st.columns(2)
        with col2a:
            new_line_items = st.checkbox("Line Item Display", value=True)
            new_open_items = st.checkbox("Open Item Management", value=False)
        
        with col2b:
            new_bs_indicator = st.checkbox("Balance Sheet Account", value=True)
            new_planning_level = st.selectbox("Planning Level", ['ACCOUNT', 'COST_CENTER', 'PROFIT_CENTER'])
    
    # Create Account Button
    if st.button("Create GL Account", type="primary"):
        if not all([new_account_id, new_account_name, new_account_group]):
            st.error("Please fill in Account ID, Name, and Account Group")
        else:
            try:
                with engine.connect() as conn:
                    with conn.begin():
                        # Check if account already exists
                        existing = conn.execute(text("SELECT COUNT(*) FROM glaccount WHERE glaccountid = :id"), 
                                              {"id": new_account_id}).fetchone()[0]
                        if existing > 0:
                            st.error(f"Account {new_account_id} already exists")
                            return
                        
                        # Get account group info
                        ag_info = conn.execute(text("""
                            SELECT account_class, require_business_unit, 
                                   require_business_area, default_field_status_group,
                                   balance_sheet_type, pnl_type
                            FROM account_groups WHERE group_code = :code
                        """), {"code": new_account_group}).fetchone()
                        
                        if not ag_info:
                            st.error("Invalid account group selected")
                            return
                        
                        # Insert new account
                        conn.execute(text("""
                            INSERT INTO glaccount (
                                glaccountid, accountname, accounttype, account_class, account_group_code,
                                short_text, long_text, account_currency, balance_sheet_indicator,
                                pnl_statement_type, line_item_display, open_item_management,
                                business_unit_required, business_area_required,
                                field_status_group, planning_level, reconciliation_account_type,
                                migrated_from_legacy, migration_date
                            ) VALUES (
                                :id, :name, :type, :class, :group,
                                :short_text, :long_text, :currency, :bs_indicator,
                                :pnl_type, :line_items, :open_items,
                                :req_bu, :req_ba,
                                :fsg, :planning, :recon_type,
                                'MANUAL_CREATION', CURRENT_TIMESTAMP
                            )
                        """), {
                            "id": new_account_id, "name": new_account_name, "type": new_account_type,
                            "class": ag_info[0], "group": new_account_group,
                            "short_text": new_short_text or new_account_name[:20],
                            "long_text": new_long_text or new_account_name[:50],
                            "currency": new_currency, "bs_indicator": new_bs_indicator,
                            "pnl_type": ag_info[5] or 'NOT_APPLICABLE',
                            "line_items": new_line_items, "open_items": new_open_items,
                            "req_bu": ag_info[1], "req_ba": ag_info[2],
                            "fsg": ag_info[3], "planning": new_planning_level,
                            "recon_type": 'CUSTOMER' if new_account_type == 'RECEIVABLE' else 
                                        'VENDOR' if new_account_type == 'PAYABLE' else 'NONE'
                        })
                        
                        st.success(f"GL Account {new_account_id} created successfully!")
                        st.rerun()
                        
            except Exception as e:
                st.error(f"Error creating GL account: {e}")
                logger.error(f"GL account creation error: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Main Interface
def main():
    # Overview Section
    ag_stats, gl_stats, fsg_stats, usage_stats = get_coa_overview()
    
    if ag_stats and gl_stats and fsg_stats:
        st.markdown("## 📊 COA Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Account Groups", f"{ag_stats[1]}/{ag_stats[0]}", help="Active/Total")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("GL Accounts", f"{gl_stats[1]}/{gl_stats[0]}", help="Active/Total")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Field Status Groups", f"{fsg_stats[1]}/{fsg_stats[0]}", help="Active/Total")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-container">', unsafe_allow_html=True)
            st.metric("Account Classes", gl_stats[2], help="Classes in use")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Usage Statistics
        if usage_stats:
            st.markdown("### 📈 Account Group Utilization")
            usage_df = pd.DataFrame(usage_stats, columns=['Class', 'Accounts', 'Range From', 'Range To', 'Utilization %'])
            st.dataframe(usage_df, use_container_width=True, hide_index=True)
    
    # Management Tabs
    tab1, tab2, tab3 = st.tabs(["📁 Account Groups", "🔧 Field Status Groups", "📊 GL Accounts"])
    
    with tab1:
        manage_account_groups()
    
    with tab2:
        manage_field_status_groups()
    
    with tab3:
        manage_gl_accounts()

if __name__ == "__main__":
    main()