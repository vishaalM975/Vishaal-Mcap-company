"""Idle Balance Monitoring module."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.risk_engine import idle_balance_risk, score_level
from modules.ui_components import ai_audit_remark, download_button_for_df, section_header


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    rename = {}
    for target in ["Account Number", "Daily Balance", "Sweep Threshold", "Interest Rate"]:
        if target.lower() in col_map:
            rename[col_map[target.lower()]] = target
    return df.rename(columns=rename)


def analyze_idle_balances(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize(df)
    for col in ["Daily Balance", "Sweep Threshold", "Interest Rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Idle Amount"] = (df["Daily Balance"] - df["Sweep Threshold"]).clip(lower=0)
    df["Idle %"] = (df["Idle Amount"] / df["Daily Balance"] * 100).round(1)
    df["Missed Daily Interest"] = df["Idle Amount"] * (df["Interest Rate"] / 100) / 365
    df["Missed Annual Earnings"] = df["Missed Daily Interest"] * 365

    def action(row) -> str:
        if row["Idle Amount"] <= 0:
            return "No Action"
        if row["Idle %"] > 50:
            return "Immediate Sweep Required"
        if row["Idle %"] > 25:
            return "Review Investment Options"
        return "Monitor"

    df["Suggested Action"] = df.apply(action, axis=1)
    df["Risk Score"] = df["Idle %"].apply(lambda p: min(100, p))
    df["Risk Level"] = df["Risk Score"].apply(score_level)
    return df


def render_idle_balance_page(df: pd.DataFrame) -> None:
    section_header("Idle Balance Monitoring")

    with st.spinner("Analyzing idle balances..."):
        result = analyze_idle_balances(df)
        idle = result[result["Idle Amount"] > 0]

    total_idle = idle["Idle Amount"].sum() if not idle.empty else 0
    total_missed = idle["Missed Annual Earnings"].sum() if not idle.empty else 0
    total_balance = result["Daily Balance"].sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accounts with Idle Funds", len(idle))
    col2.metric("Total Idle Balance", f"₹{total_idle:,.0f}")
    col3.metric("Est. Missed Earnings/yr", f"₹{total_missed:,.0f}")
    risk = idle_balance_risk(total_idle, total_balance)
    col4.metric("Module Risk Score", f"{risk:.0f}/100")

    tab1, tab2 = st.tabs(["Idle Balance Report", "Visualization"])

    with tab1:
        display = idle.sort_values("Idle Amount", ascending=False) if not idle.empty else result
        st.dataframe(display.round(2), use_container_width=True, hide_index=True)
        download_button_for_df(idle, "Export Idle Balance Report", "idle_balances.csv", "dl_idle")

    with tab2:
        if not idle.empty:
            fig = px.bar(
                idle.head(15), x="Account Number", y="Idle Amount",
                color="Suggested Action", title="Top Idle Balances by Account",
                color_discrete_sequence=px.colors.sequential.Teal,
            )
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
            st.plotly_chart(fig, use_container_width=True)

    findings = []
    if total_idle > 0:
        findings.append(f"₹{total_idle:,.0f} in idle funds detected across {len(idle)} accounts.")
        findings.append(f"Estimated missed annual earnings of ₹{total_missed:,.0f} if funds remain uninvested.")
        urgent = idle[idle["Suggested Action"] == "Immediate Sweep Required"]
        if len(urgent):
            findings.append(f"{len(urgent)} accounts require immediate sweep action.")
    ai_audit_remark(findings)
