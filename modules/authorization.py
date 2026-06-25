"""Authorisation Verification module."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.risk_engine import authorization_risk, score_level
from modules.ui_components import ai_audit_remark, download_button_for_df, section_header


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    rename = {}
    for target in ["Transaction ID", "Approved By", "Authorized List", "Approval Timestamp"]:
        if target.lower() in col_map:
            rename[col_map[target.lower()]] = target
    return df.rename(columns=rename)


def verify_authorizations(df: pd.DataFrame) -> pd.DataFrame:
    df = _normalize(df)
    if "Approval Timestamp" in df.columns:
        df["Approval Timestamp"] = pd.to_datetime(df["Approval Timestamp"], errors="coerce")

    def is_authorized(row) -> bool:
        approver = str(row.get("Approved By", "")).strip().lower()
        auth_list = str(row.get("Authorized List", "")).lower()
        return approver in auth_list

    df["Is Authorized"] = df.apply(is_authorized, axis=1)
    df["Flag"] = df["Is Authorized"].apply(lambda x: "OK" if x else "Unauthorized")

    # Duplicate approvals (same approver, same timestamp)
    if "Approval Timestamp" in df.columns:
        dup_mask = df.duplicated(subset=["Approved By", "Approval Timestamp"], keep=False)
        df.loc[dup_mask, "Flag"] = "Duplicate Approval"

    def risk(row) -> float:
        if row["Flag"] == "Unauthorized":
            return 90
        if row["Flag"] == "Duplicate Approval":
            return 60
        return 10

    df["Risk Score"] = df.apply(risk, axis=1)
    df["Risk Level"] = df["Risk Score"].apply(score_level)
    return df


def render_authorization_page(df: pd.DataFrame) -> None:
    section_header("Authorisation Verification")

    with st.spinner("Cross-checking authorizations..."):
        result = verify_authorizations(df)
        unauthorized = result[result["Flag"] == "Unauthorized"]
        duplicates = result[result["Flag"] == "Duplicate Approval"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Transactions", len(result))
    col2.metric("Unauthorized", len(unauthorized))
    col3.metric("Duplicate Approvals", len(duplicates))
    risk = authorization_risk(len(unauthorized), len(duplicates), len(result))
    col4.metric("Module Risk Score", f"{risk:.0f}/100")

    tab1, tab2 = st.tabs(["Verification Results", "Approver Analysis"])

    with tab1:
        flagged = result[result["Flag"] != "OK"]
        st.dataframe(result, use_container_width=True, hide_index=True)
        download_button_for_df(flagged, "Export Flagged Approvals", "authorization_issues.csv", "dl_auth")

    with tab2:
        approver_counts = result.groupby("Approved By").agg(
            Count=("Transaction ID", "count"),
            Unauthorized=("Flag", lambda x: (x == "Unauthorized").sum()),
        ).reset_index()
        fig = px.bar(approver_counts, x="Approved By", y="Count", color="Unauthorized",
                     title="Approvals by Signatory", color_continuous_scale="Reds")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
        st.plotly_chart(fig, use_container_width=True)

    findings = []
    if len(unauthorized):
        findings.append(f"{len(unauthorized)} transactions approved by unauthorized signatories.")
    if len(duplicates):
        findings.append(f"{len(duplicates)} duplicate approval entries detected.")
    ai_audit_remark(findings)
