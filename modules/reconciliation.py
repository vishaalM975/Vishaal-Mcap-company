"""Bank Reconciliation Aging analysis module."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.risk_engine import reconciliation_risk, score_level
from modules.ui_components import ai_audit_remark, download_button_for_df, section_header


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    rename = {}
    for target in ["Date", "Transaction ID", "Amount", "Bank Status", "Ledger Status", "Reconciliation Status"]:
        key = target.lower()
        if key in col_map:
            rename[col_map[key]] = target
    return df.rename(columns=rename)


def _compute_aging(df: pd.DataFrame, ref_date: datetime | None = None) -> pd.DataFrame:
    ref = ref_date or datetime.now()
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Days Outstanding"] = (pd.Timestamp(ref) - df["Date"]).dt.days.clip(lower=0)

    def bucket(days: float) -> str:
        if days <= 30:
            return "0-30 days"
        if days <= 60:
            return "31-60 days"
        if days <= 90:
            return "61-90 days"
        return "90+ days"

    df["Aging Bucket"] = df["Days Outstanding"].apply(bucket)
    return df


def analyze_reconciliation(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    df = _normalize_columns(df)
    df = _compute_aging(df)

    unmatched = df[df["Reconciliation Status"].astype(str).str.lower().isin(["unmatched", "partial", "pending review"])]
    long_pending = df[df["Days Outstanding"] > 90]

    summary = (
        unmatched.groupby("Aging Bucket", observed=True)
        .agg(Count=("Transaction ID", "count"), Total_Amount=("Amount", "sum"))
        .reset_index()
        .sort_values("Aging Bucket")
    )

    unmatched["Risk Score"] = unmatched.apply(
        lambda r: min(100, r["Days Outstanding"] * 0.5 + (30 if str(r["Reconciliation Status"]).lower() == "unmatched" else 15)),
        axis=1,
    )
    unmatched["Risk Level"] = unmatched["Risk Score"].apply(score_level)

    findings = []
    if len(unmatched):
        findings.append(f"{len(unmatched)} reconciliation items remain unmatched or partially matched.")
    if len(long_pending):
        findings.append(f"{len(long_pending)} entries have been pending for over 90 days — immediate review recommended.")
    high_risk = unmatched[unmatched["Risk Level"] == "High"]
    if len(high_risk):
        findings.append(f"{len(high_risk)} high-risk items identified with extended aging periods.")

    return unmatched, summary, long_pending, findings


def render_reconciliation_page(df: pd.DataFrame) -> None:
    section_header("Bank Reconciliation Aging")
    with st.spinner("Analyzing reconciliation data..."):
        unmatched, summary, long_pending, findings = analyze_reconciliation(df)

    col1, col2, col3 = st.columns(3)
    col1.metric("Unmatched Items", len(unmatched))
    col2.metric("90+ Day Pending", len(long_pending))
    total = len(df) if len(df) else 1
    risk = reconciliation_risk(len(unmatched), len(long_pending), total)
    col3.metric("Module Risk Score", f"{risk:.0f}/100")

    tab1, tab2, tab3 = st.tabs(["Aging Summary", "Unmatched Transactions", "Long Pending"])

    with tab1:
        if not summary.empty:
            fig = px.bar(
                summary, x="Aging Bucket", y="Count", color="Aging Bucket",
                title="Reconciliation Aging Distribution",
                color_discrete_sequence=px.colors.sequential.Blues_r,
                text="Count",
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font_color="#E8ECF1", showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            fig2 = go.Figure(data=[go.Bar(
                x=summary["Aging Bucket"], y=summary["Total_Amount"],
                marker_color=["#2C5DA3", "#5B9BD5", "#FFA502", "#FF4757"],
            )])
            fig2.update_layout(
                title="Outstanding Amount by Aging Bucket",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1",
            )
            st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(summary, use_container_width=True, hide_index=True)

    with tab2:
        search = st.text_input("Search unmatched", key="recon_search")
        display = unmatched
        if search:
            display = unmatched[unmatched.astype(str).apply(lambda r: r.str.contains(search, case=False).any(), axis=1)]
        st.dataframe(display, use_container_width=True, hide_index=True)
        download_button_for_df(display, "Download Unmatched Report", "unmatched_reconciliation.csv", "dl_recon")

    with tab3:
        st.dataframe(long_pending, use_container_width=True, hide_index=True)

    ai_audit_remark(findings)
