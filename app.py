"""
Treasury & Banking Audit Analytics
Enterprise-grade Streamlit application by CAP AI
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from modules.analytics import (
    render_accounts_page,
    render_bank_rent_page,
    render_cashflow_page,
    render_frequency_heatmap,
    render_monthly_trends_page,
    render_sankey,
    render_spending_details_page,
    render_spending_page,
    render_vendor_page,
)
from modules.authorization import render_authorization_page
from modules.charges import render_charges_page
from modules.dashboard import render_dashboard
from modules.data_loader import (
    apply_date_filters,
    ensure_sample_excel,
    get_all_sample_data,
    load_uploaded_file,
    merge_uploaded_data,
    sample_data_summary,
    to_excel_bytes,
)
from modules.idle_balance import render_idle_balance_page
from modules.reconciliation import render_reconciliation_page
from modules.round_tripping import render_round_tripping_page
from modules.ui_components import inject_custom_css, render_header

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CAP AI | Treasury Audit Analytics",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent
LOGO_PATH = BASE_DIR / "logo.png"
SAMPLE_EXCEL = BASE_DIR / "sample_data" / "demo_banking_data.xlsx"

inject_custom_css()
render_header(LOGO_PATH)

# Pre-generate bundled demo workbook (no upload needed)
ensure_sample_excel(SAMPLE_EXCEL)

# ── Session state ──────────────────────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = get_all_sample_data()
if "using_sample" not in st.session_state:
    st.session_state.using_sample = True

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏦 Navigation")
    page = st.radio(
        "Select Module",
        [
            "📊 Dashboard",
            "🔄 Bank Reconciliation",
            "🔁 Round Tripping",
            "💳 Charges & Interest",
            "💤 Idle Balance",
            "🔒 Authorization",
            "📈 Cash Flow",
            "🥧 Expense Classification",
            "🏢 Vendor Payments",
            "🏦 Account Details",
            "🏧 Bank Rent & Charges",
            "💸 Spending Details",
            "📉 Monthly Trends",
            "🔥 Transaction Heatmap",
            "🌊 Fund Flow Sankey",
            "📁 Data Import / Export",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 📅 Date Range Filter")
    date_start = st.date_input("From", value=datetime.now() - timedelta(days=180), key="date_start")
    date_end = st.date_input("To", value=datetime.now(), key="date_end")

    st.markdown("---")
    if st.session_state.using_sample:
        st.success("**Demo mode** — dummy banking data loaded")
        with st.expander("View demo datasets"):
            st.dataframe(sample_data_summary(st.session_state.data), hide_index=True, use_container_width=True)
        if SAMPLE_EXCEL.exists():
            st.download_button(
                "Download demo Excel",
                data=SAMPLE_EXCEL.read_bytes(),
                file_name="demo_banking_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_demo_excel",
            )
    else:
        st.success("Custom data loaded.")

# Apply date range to demo / uploaded data
data = apply_date_filters(
    st.session_state.data,
    datetime.combine(date_start, datetime.min.time()),
    datetime.combine(date_end, datetime.max.time()),
)

if page == "📊 Dashboard":
    if st.session_state.using_sample:
        st.info(
            "Exploring with **dummy banking data** — all modules are pre-populated with sample "
            "reconciliation, transfers, charges, idle balances, and authorization records. "
            "Use the sidebar to switch modules, or upload your own Excel/CSV under **Data Import / Export**."
        )
    render_dashboard(data)

elif page == "🔄 Bank Reconciliation":
    render_reconciliation_page(data.get("reconciliation", pd.DataFrame()))

elif page == "🔁 Round Tripping":
    render_round_tripping_page(data.get("transfers", pd.DataFrame()))

elif page == "💳 Charges & Interest":
    render_charges_page(data.get("charges", pd.DataFrame()))

elif page == "💤 Idle Balance":
    render_idle_balance_page(data.get("idle_balance", pd.DataFrame()))

elif page == "🔒 Authorization":
    render_authorization_page(data.get("authorization", pd.DataFrame()))

elif page == "📈 Cash Flow":
    render_cashflow_page(data.get("cashflow", pd.DataFrame()))

elif page == "🥧 Expense Classification":
    render_spending_page(data.get("spending", pd.DataFrame()))

elif page == "🏢 Vendor Payments":
    render_vendor_page(data.get("vendors", pd.DataFrame()))

elif page == "🏦 Account Details":
    render_accounts_page(data.get("accounts", pd.DataFrame()))

elif page == "🏧 Bank Rent & Charges":
    render_bank_rent_page(data.get("bank_rent", pd.DataFrame()))

elif page == "💸 Spending Details":
    render_spending_details_page(data.get("spending_details", pd.DataFrame()))

elif page == "📉 Monthly Trends":
    render_monthly_trends_page(data.get("monthly_trends", pd.DataFrame()))

elif page == "🔥 Transaction Heatmap":
    render_frequency_heatmap(data.get("frequency", pd.DataFrame()))

elif page == "🌊 Fund Flow Sankey":
    render_sankey(data.get("transfers", pd.DataFrame()))

elif page == "📁 Data Import / Export":
    st.markdown('<div class="section-header">Data Import & Export</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload Excel (.xlsx) or CSV (.csv)",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
    )

    if uploaded:
        all_uploaded = {}
        for f in uploaded:
            sheets = load_uploaded_file(f)
            all_uploaded.update(sheets)
            st.success(f"Loaded **{f.name}** — {len(sheets)} sheet(s)")

        for sheet_name, df in all_uploaded.items():
            with st.expander(f"Preview: {sheet_name} ({len(df)} rows)"):
                st.dataframe(df.head(20), use_container_width=True)

        if st.button("Apply Uploaded Data", type="primary"):
            st.session_state.data = merge_uploaded_data(all_uploaded, get_all_sample_data())
            st.session_state.using_sample = False
            st.rerun()

    st.markdown("---")
    st.markdown("#### Export Audit Reports")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export All Data to Excel"):
            excel_bytes = to_excel_bytes(st.session_state.data)
            st.download_button(
                "Download Excel Report",
                data=excel_bytes,
                file_name="audit_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    with col2:
        if st.button("Reset to Sample Data"):
            st.session_state.data = get_all_sample_data()
            st.session_state.using_sample = True
            st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#8899AA;font-size:0.8rem;">'
    "CAP AI Treasury & Banking Audit Analytics v1.0 | Enterprise Audit Intelligence Platform"
    "</div>",
    unsafe_allow_html=True,
)
