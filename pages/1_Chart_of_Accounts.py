import streamlit as st
import pandas as pd
from db_config import engine
from sqlalchemy import text
from auth.optimized_middleware import optimized_authenticator as authenticator
from utils.logger import StreamlitLogHandler
from utils.navigation import show_sap_sidebar, show_breadcrumb

# Require authentication and permission
authenticator.require_auth()
authenticator.require_permission("glaccount.read")

current_user = authenticator.get_current_user()
StreamlitLogHandler.log_page_access("Chart of Accounts", current_user.username)

# Configure page
st.set_page_config(page_title="📘 Chart of Accounts", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("Chart of Accounts", "Master Data", "Setup")

st.title("📘 Chart of Accounts Management")

@st.cache_data
def load_glaccounts():
    sql = """
        SELECT glaccountid AS "GLAccountID", 
               companycodeid AS "CompanyCodeID", 
               accountname AS "AccountName", 
               accounttype AS "AccountType", 
               isreconaccount AS "IsReconAccount", 
               isopenitemmanaged AS "IsOpenItemManaged" 
        FROM glaccount 
        ORDER BY glaccountid
    """
    try:
        with engine.connect() as conn:
            return pd.read_sql(sql, conn)
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return pd.DataFrame()

# Load original data
df_orig = load_glaccounts()

st.subheader("Edit the table directly below. Click on column headers to sort. Add new rows, modify cells, or delete rows.")

# Inline editable table (header-click sorting supported by default)
if hasattr(st, 'data_editor'):
    edited_df = st.data_editor(
        df_orig,
        num_rows="dynamic",
        use_container_width=True
    )
else:
    st.error("Your Streamlit version does not support inline data editing. Please upgrade to 1.18+.")
    st.stop()

if st.button("Save Changes"):
    # Check permission for updates
    if not authenticator.has_permission("glaccount.update"):
        st.error("❌ Access Denied: You don't have permission to update GL accounts.")
        st.stop()
    
    if df_orig.empty:
        st.error("No data to save")
        st.stop()
        
    orig = df_orig.set_index("GLAccountID")
    edited = edited_df.set_index("GLAccountID")
    orig_ids = set(orig.index)
    new_ids = set(edited.index)
    inserts = new_ids - orig_ids
    deletes = orig_ids - new_ids
    common = orig_ids & new_ids

    try:
        with engine.begin() as conn:
            # Insert new rows
            for glid in inserts:
                row = edited.loc[glid]
                if pd.isna(glid) or str(glid).strip() == '':
                    continue
                conn.execute(text("""
                    INSERT INTO glaccount 
                    (glaccountid, companycodeid, accountname, accounttype, isreconaccount, isopenitemmanaged) 
                    VALUES (:glid, :companycode, :accountname, :accounttype, :isrecon, :isopenitem)
                """), {
                    'glid': glid,
                    'companycode': row['CompanyCodeID'],
                    'accountname': row['AccountName'],
                    'accounttype': row['AccountType'],
                    'isrecon': bool(row['IsReconAccount']),
                    'isopenitem': bool(row['IsOpenItemManaged'])
                })
            
            # Delete removed rows
            for glid in deletes:
                conn.execute(text("DELETE FROM glaccount WHERE glaccountid = :glid"), {'glid': glid})
            
            # Update modified rows
            for glid in common:
                orig_row = orig.loc[glid]
                new_row = edited.loc[glid]
                if not orig_row.equals(new_row):
                    conn.execute(text("""
                        UPDATE glaccount 
                        SET companycodeid = :companycode, accountname = :accountname, 
                            accounttype = :accounttype, isreconaccount = :isrecon, 
                            isopenitemmanaged = :isopenitem 
                        WHERE glaccountid = :glid
                    """), {
                        'companycode': new_row['CompanyCodeID'],
                        'accountname': new_row['AccountName'],
                        'accounttype': new_row['AccountType'],
                        'isrecon': bool(new_row['IsReconAccount']),
                        'isopenitem': bool(new_row['IsOpenItemManaged']),
                        'glid': glid
                    })
        
        st.success("All changes saved successfully!")
        load_glaccounts.clear()
        
    except Exception as e:
        st.error(f"Error saving changes: {e}")

# Navigation is now handled by the SAP-style sidebar
