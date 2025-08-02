import streamlit as st
import pandas as pd
import io
from datetime import date
from sqlalchemy import create_engine, text

# Configure pandas to handle large datasets
pd.set_option("styler.render.max_elements", 500000)

# DB Connection
from db_config import engine


def render_report_layout(report_title: str, query_sql: str, params: dict = None):
    st.set_page_config(page_title=report_title)
    st.title(report_title)

    # --- Query & Display ---
    with engine.connect() as conn:
        df = pd.read_sql(text(query_sql), conn, params=params)
    st.dataframe(df.style.format({col: "{:,.2f}" for col in df.select_dtypes(include='number').columns}), use_container_width=True)

    # --- Totals and balance check ---
    total_line = {}
    debit_total = credit_total = 0.0
    if not df.empty:
        for col in df.columns:
            if 'debit' in col.lower():
                debit_total += df[col].sum()
                total_line[col] = df[col].sum()
            elif 'credit' in col.lower():
                credit_total += df[col].sum()
                total_line[col] = df[col].sum()
    if total_line:
        st.subheader("🔢 Totals")
        st.write(pd.DataFrame([total_line]).style.format("{:,.2f}"))
        if abs(debit_total - credit_total) > 0.005:
            st.error(f"⚠️ Debits and Credits do not match! Difference: {debit_total - credit_total:,.2f}")
        else:
            st.success("✅ Debits and Credits are balanced.")

    # --- Export to Excel ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
        workbook = writer.book
        worksheet = writer.sheets['Report']

        currency_fmt = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
        bold_fmt = workbook.add_format({'bold': True})
        for idx, col in enumerate(df.columns):
            if pd.api.types.is_numeric_dtype(df[col]):
                worksheet.set_column(idx, idx, 15, currency_fmt)
            elif 'account' in col.lower():
                worksheet.set_column(idx, idx, 25, bold_fmt)
            else:
                worksheet.set_column(idx, idx, 20)

        if not df.empty and df.select_dtypes(include='number').shape[1] > 0:
            total_row = [''] * len(df.columns)
            for idx, col in enumerate(df.columns):
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_letter = chr(65 + idx)
                    total_row[idx] = f'=SUM({col_letter}2:{col_letter}{len(df)+1})'
            worksheet.write_row(len(df)+1, 0, total_row, currency_fmt)

    st.download_button(
        label="📤 Download as Excel",
        data=output.getvalue(),
        file_name=f"{report_title.replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- Back Button ---
    if st.button("🔙 Back to Home"):
        st.switch_page("Home.py")