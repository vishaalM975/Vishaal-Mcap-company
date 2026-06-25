"""Bank Charges & Interest Validation module."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.risk_engine import charges_risk, score_level
from modules.ui_components import ai_audit_remark, download_button_for_df, section_header

PROCESSING_FEE_PCT = 1.0
PENALTY_PCT = 2.0


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    rename = {}
    for target in ["Loan Amount", "Interest Rate", "Charges", "Tenure", "Actual Debit"]:
        if target.lower() in col_map:
            rename[col_map[target.lower()]] = target
    return df.rename(columns=rename)


def validate_charges(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize(df)
    for col in ["Loan Amount", "Interest Rate", "Charges", "Tenure", "Actual Debit"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Expected Interest"] = df["Loan Amount"] * (df["Interest Rate"] / 100) * (df["Tenure"] / 12)
    df["Expected Processing Fee"] = df["Loan Amount"] * (PROCESSING_FEE_PCT / 100)
    df["Expected Total"] = df["Expected Interest"] + df["Expected Processing Fee"]
    df["Variance"] = df["Actual Debit"] - df["Expected Total"]
    df["Variance %"] = (df["Variance"] / df["Expected Total"] * 100).round(2)

    def classify(v: float) -> str:
        if abs(v) < 1000:
            return "Within Tolerance"
        if v > 0:
            return "Excess Charge"
        return "Undercharged"

    df["Flag"] = df["Variance"].apply(classify)
    df["Risk Score"] = df["Variance"].abs().apply(lambda v: min(100, v / 1000))
    df["Risk Level"] = df["Risk Score"].apply(score_level)
    return df


def render_charges_page(df: pd.DataFrame) -> None:
    section_header("Bank Charges & Interest Validation")

    col1, col2, col3 = st.columns(3)
    col1.metric("Processing Fee Rate", f"{PROCESSING_FEE_PCT}%")
    col2.metric("Penalty Rate", f"{PENALTY_PCT}%")
    tolerance = st.number_input("Tolerance (₹)", value=1000, step=500, key="charge_tol")

    with st.spinner("Validating charges and interest..."):
        result = validate_charges(df)
        flagged = result[result["Flag"] != "Within Tolerance"]
        excess = result[result["Flag"] == "Excess Charge"]
        under = result[result["Flag"] == "Undercharged"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Loans", len(result))
    col2.metric("Excess Charges", len(excess))
    col3.metric("Undercharged", len(under))
    risk = charges_risk(len(flagged), len(result))
    col4.metric("Module Risk Score", f"{risk:.0f}/100")

    tab1, tab2 = st.tabs(["Validation Results", "Variance Analysis"])

    with tab1:
        st.dataframe(result.round(2), use_container_width=True, hide_index=True)
        download_button_for_df(flagged, "Export Flagged Items", "charge_validation.csv", "dl_charges")

    with tab2:
        fig = px.scatter(
            result, x="Expected Total", y="Actual Debit", color="Flag",
            hover_data=["Loan Amount", "Variance"],
            color_discrete_map={"Excess Charge": "#FF4757", "Undercharged": "#FFA502", "Within Tolerance": "#00C896"},
            title="Expected vs Actual Debits",
        )
        fig.add_shape(type="line", x0=result["Expected Total"].min(), y0=result["Expected Total"].min(),
                      x1=result["Expected Total"].max(), y1=result["Expected Total"].max(),
                      line=dict(dash="dash", color="#D4AF37"))
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
        st.plotly_chart(fig, use_container_width=True)

    findings = []
    if len(excess):
        total_excess = excess["Variance"].sum()
        findings.append(f"{len(excess)} accounts with excess charges totaling ₹{total_excess:,.0f}.")
    if len(under):
        findings.append(f"{len(under)} accounts appear undercharged — potential revenue leakage.")
    ai_audit_remark(findings)
