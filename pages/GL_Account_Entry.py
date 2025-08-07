import streamlit as st
import psycopg2
import pandas as pd

# Database connection - configure with Streamlit secrets or replace with your credentials
conn = psycopg2.connect(
    host="localhost",
    database="gl_erp",
    user="postgres",
    password="admin123"
)
cur = conn.cursor()

st.title("GLAccount Data Entry")

# Load existing records function
def load_glaccounts():
    return pd.read_sql(
        "SELECT glaccountid AS \"GLAccountID\", accountname AS \"AccountName\", accounttype AS \"AccountType\", account_class AS \"AccountClass\", account_group_code AS \"AccountGroup\" FROM glaccount WHERE (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)",
        conn
    )

# Initial load
df = load_glaccounts()
account_types = ["Asset", "Liability", "Equity", "Revenue", "Expense"]

# Single form for Add, Update, Delete
with st.form("glaccount_form"):
    st.subheader("Manage GLAccount")
    id_options = ["Add New"] + df["GLAccountID"].tolist()
    selected = st.selectbox("GLAccount ID", id_options)

    if selected == "Add New":
        action = "Add"
        glid = st.text_input("New GLAccount ID")
        company_code_id = st.text_input("Company Code ID")
        account_name = st.text_input("Account Name")
        account_type = st.selectbox("Account Type", account_types)
        is_recon = st.checkbox("Is Recon Account")
        is_open_item = st.checkbox("Is Open Item Managed")
        button_label = "Insert"
    else:
        record = df[df["GLAccountID"] == selected].iloc[0]
        action = st.radio("Action", ("Update", "Delete"))
        glid = selected
        if action == "Update":
            company_code_id = st.text_input("Company Code ID", value=record["CompanyCodeID"])
            account_name = st.text_input("Account Name", value=record["AccountName"])
            account_type = st.selectbox(
                "Account Type", account_types, index=account_types.index(record["AccountType"]))
            is_recon = st.checkbox("Is Recon Account", value=record["IsReconAccount"])
            is_open_item = st.checkbox("Is Open Item Managed", value=record["IsOpenItemManaged"])
            button_label = "Update"
        else:
            st.write(f"⚠️ This will permanently delete GLAccount ID **{selected}**.")
            button_label = "Delete"

    # Action buttons
    col1, col2 = st.columns(2)
    ok = col1.form_submit_button(button_label)
    cancel = col2.form_submit_button("Cancel")

# Handle Cancel
if cancel:
    st.info("Operation cancelled.")

# Handle Submit
elif ok:
    try:
        if action == "Add":
            cur.execute(
                "INSERT INTO glaccount (glaccountid, companycodeid, accountname, accounttype, isreconaccount, isopenitemmanaged) VALUES (%s, %s, %s, %s, %s, %s)",
                (glid, company_code_id, account_name, account_type, is_recon, is_open_item)
            )
            conn.commit()
            st.success("Record inserted successfully!")
        elif action == "Update":
            cur.execute(
                "UPDATE glaccount SET companycodeid=%s, accountname=%s, accounttype=%s, isreconaccount=%s, isopenitemmanaged=%s WHERE glaccountid=%s",
                (company_code_id, account_name, account_type, is_recon, is_open_item, glid)
            )
            conn.commit()
            st.success("Record updated successfully!")
        else:  # Delete
            cur.execute(
                "DELETE FROM glaccount WHERE glaccountid=%s", (glid,)
            )
            conn.commit()
            st.success("Record deleted successfully!")
        # Refresh data after operation
        df = load_glaccounts()
    except Exception as e:
        conn.rollback()
        st.error(f"Error during {action.lower()}: {e}")

# Optionally display table
if st.checkbox("Show GLAccount Records"):
    st.dataframe(df)

# Cleanup
cur.close()
conn.close()
