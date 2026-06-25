"""Main dashboard with KPIs and overview charts."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.authorization import verify_authorizations
from modules.charges import validate_charges
from modules.idle_balance import analyze_idle_balances
from modules.reconciliation import analyze_reconciliation
from modules.risk_engine import (
    authorization_risk,
    charges_risk,
    composite_risk,
    idle_balance_risk,
    reconciliation_risk,
    round_trip_risk,
    score_level,
)
from modules.round_tripping import detect_round_trips
from modules.ui_components import ai_audit_remark, render_kpi_row, section_header


def compute_dashboard_metrics(data: dict[str, pd.DataFrame]) -> dict:
    metrics = {
        "total_accounts": len(data.get("accounts", pd.DataFrame())),
        "total_transactions": 0,
        "suspicious": 0,
        "idle_funds": 0.0,
        "unauthorized": 0,
        "excess_charges": 0,
        "risk_scores": {},
    }

    recon = data.get("reconciliation", pd.DataFrame())
    if not recon.empty:
        unmatched, _, long_pending, _ = analyze_reconciliation(recon)
        metrics["total_transactions"] += len(recon)
        metrics["risk_scores"]["reconciliation"] = reconciliation_risk(len(unmatched), len(long_pending), len(recon))

    transfers = data.get("transfers", pd.DataFrame())
    if not transfers.empty:
        suspicious = detect_round_trips(transfers)
        metrics["suspicious"] = len(suspicious)
        metrics["total_transactions"] += len(transfers)
        related_pct = (transfers["Related Party Flag"].astype(str).str.lower() == "yes").mean() if "Related Party Flag" in transfers.columns else 0
        metrics["risk_scores"]["round_trip"] = round_trip_risk(len(suspicious), len(transfers), related_pct)

    charges = data.get("charges", pd.DataFrame())
    if not charges.empty:
        validated = validate_charges(charges)
        flagged = validated[validated["Flag"] != "Within Tolerance"]
        metrics["excess_charges"] = len(flagged)
        metrics["risk_scores"]["charges"] = charges_risk(len(flagged), len(charges))

    idle = data.get("idle_balance", pd.DataFrame())
    if not idle.empty:
        idle_result = analyze_idle_balances(idle)
        idle_only = idle_result[idle_result["Idle Amount"] > 0]
        metrics["idle_funds"] = idle_only["Idle Amount"].sum()
        metrics["risk_scores"]["idle_balance"] = idle_balance_risk(
            metrics["idle_funds"], idle_result["Daily Balance"].sum()
        )

    auth = data.get("authorization", pd.DataFrame())
    if not auth.empty:
        auth_result = verify_authorizations(auth)
        metrics["unauthorized"] = len(auth_result[auth_result["Flag"] == "Unauthorized"])
        metrics["total_transactions"] += len(auth)
        metrics["risk_scores"]["authorization"] = authorization_risk(
            metrics["unauthorized"],
            len(auth_result[auth_result["Flag"] == "Duplicate Approval"]),
            len(auth),
        )

    metrics["composite_risk"] = composite_risk(metrics["risk_scores"])
    metrics["risk_level"] = score_level(metrics["composite_risk"])
    return metrics


def render_dashboard(data: dict[str, pd.DataFrame]) -> None:
    section_header("Executive Dashboard")

    with st.spinner("Computing audit intelligence..."):
        metrics = compute_dashboard_metrics(data)

    render_kpi_row([
        ("Total Accounts", str(metrics["total_accounts"]), "🏦", None),
        ("Total Transactions", f"{metrics['total_transactions']:,}", "💳", None),
        ("Suspicious Transactions", str(metrics["suspicious"]), "⚠️", "Requires review"),
        ("Idle Funds", f"₹{metrics['idle_funds']:,.0f}", "💤", "Sweep opportunity"),
        ("Unauthorized Approvals", str(metrics["unauthorized"]), "🔒", None),
        ("Excess Charges", str(metrics["excess_charges"]), "💰", None),
    ])

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        # Risk gauge
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=metrics["composite_risk"],
            title={"text": f"Composite Risk Score ({metrics['risk_level']})", "font": {"color": "#E8ECF1"}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8899AA"},
                "bar": {"color": "#2C5DA3"},
                "steps": [
                    {"range": [0, 40], "color": "rgba(0,200,150,0.3)"},
                    {"range": [40, 70], "color": "rgba(255,165,2,0.3)"},
                    {"range": [70, 100], "color": "rgba(255,71,87,0.3)"},
                ],
                "threshold": {"line": {"color": "#D4AF37", "width": 4}, "value": 70},
            },
            number={"font": {"color": "#E8ECF1"}},
        ))
        fig_gauge.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        if metrics["risk_scores"]:
            risk_df = pd.DataFrame([
                {"Module": k.replace("_", " ").title(), "Score": v}
                for k, v in metrics["risk_scores"].items()
            ])
            fig_bar = px.bar(
                risk_df, x="Module", y="Score", color="Score",
                color_continuous_scale=["#00C896", "#FFA502", "#FF4757"],
                title="Risk by Module",
            )
            fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
            st.plotly_chart(fig_bar, use_container_width=True)

    # Quick charts row
    col1, col2 = st.columns(2)

    with col1:
        cashflow = data.get("cashflow", pd.DataFrame())
        if not cashflow.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=cashflow["Month"], y=cashflow["Net Cash Flow"],
                                     fill="tozeroy", line=dict(color="#2C5DA3")))
            fig.update_layout(title="Net Cash Flow", plot_bgcolor="rgba(0,0,0,0)",
                              paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1", height=300)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        spending = data.get("spending", pd.DataFrame())
        if not spending.empty:
            fig2 = px.pie(spending, names="Category", values="Amount", hole=0.5,
                          color_discrete_sequence=px.colors.sequential.Blues_r)
            fig2.update_layout(title="Spending Categories", plot_bgcolor="rgba(0,0,0,0)",
                               paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1", height=300)
            st.plotly_chart(fig2, use_container_width=True)

    # Exception summary
    findings = []
    if metrics["suspicious"]:
        findings.append(f"{metrics['suspicious']} suspicious fund movement patterns detected.")
    if metrics["unauthorized"]:
        findings.append(f"{metrics['unauthorized']} unauthorized approval(s) require immediate action.")
    if metrics["excess_charges"]:
        findings.append(f"{metrics['excess_charges']} charge validation exceptions found.")
    if metrics["idle_funds"] > 0:
        findings.append(f"₹{metrics['idle_funds']:,.0f} in idle funds — sweep recommended.")
    findings.append(f"Overall audit risk level: {metrics['risk_level']} ({metrics['composite_risk']:.0f}/100).")

    ai_audit_remark(findings)
