"""Round Tripping Detection module."""

from __future__ import annotations

from datetime import timedelta

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.risk_engine import round_trip_risk, score_level
from modules.ui_components import ai_audit_remark, download_button_for_df, section_header


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    rename = {}
    for target in ["From Account", "To Account", "Amount", "Date", "Related Party Flag"]:
        if target.lower() in col_map:
            rename[col_map[target.lower()]] = target
    df = df.rename(columns=rename)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    return df


def detect_round_trips(df: pd.DataFrame, window_days: int = 7) -> pd.DataFrame:
    df = _normalize(df)
    suspicious = []

    for i, row in df.iterrows():
        reverse = df[
            (df["From Account"] == row["To Account"])
            & (df["To Account"] == row["From Account"])
            & (df.index != i)
        ]
        for _, rev in reverse.iterrows():
            days_diff = abs((rev["Date"] - row["Date"]).days)
            amt_diff = abs(rev["Amount"] - row["Amount"]) / max(row["Amount"], 1)
            if days_diff <= window_days and amt_diff < 0.05:
                score = 85 - days_diff * 5
                if str(row.get("Related Party Flag", "")).lower() == "yes":
                    score = min(100, score + 10)
                suspicious.append({
                    "From Account": row["From Account"],
                    "To Account": row["To Account"],
                    "Amount": row["Amount"],
                    "Return Date": rev["Date"],
                    "Original Date": row["Date"],
                    "Days Between": days_diff,
                    "Related Party": row.get("Related Party Flag", "No"),
                    "Pattern": "Round Trip",
                    "Risk Score": round(score, 1),
                    "Risk Level": score_level(score),
                })

    # Repeated same-value transfers
    grouped = df.groupby(["From Account", "To Account", "Amount"]).size().reset_index(name="Count")
    repeats = grouped[grouped["Count"] >= 3]
    for _, g in repeats.iterrows():
        subset = df[
            (df["From Account"] == g["From Account"])
            & (df["To Account"] == g["To Account"])
            & (df["Amount"] == g["Amount"])
        ]
        score = min(100, 50 + g["Count"] * 8)
        suspicious.append({
            "From Account": g["From Account"],
            "To Account": g["To Account"],
            "Amount": g["Amount"],
            "Return Date": subset["Date"].max(),
            "Original Date": subset["Date"].min(),
            "Days Between": (subset["Date"].max() - subset["Date"].min()).days,
            "Related Party": subset["Related Party Flag"].iloc[0] if "Related Party Flag" in subset else "No",
            "Pattern": f"Repeated Transfer (x{g['Count']})",
            "Risk Score": score,
            "Risk Level": score_level(score),
        })

    result = pd.DataFrame(suspicious)
    if not result.empty:
        result = result.drop_duplicates(subset=["From Account", "To Account", "Amount", "Pattern"])
    return result


def build_network_graph(df: pd.DataFrame) -> go.Figure:
    df = _normalize(df)
    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_edge(row["From Account"], row["To Account"], weight=row["Amount"])

    pos = nx.spring_layout(G, seed=42)
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines",
                            line=dict(width=1.5, color="#5B9BD5"), hoverinfo="none")

    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=list(G.nodes()), textposition="top center",
        marker=dict(size=18, color="#2C5DA3", line=dict(width=2, color="#D4AF37")),
        hovertext=list(G.nodes()), hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="Fund Movement Network",
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E8ECF1", xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=500,
    )
    return fig


def render_round_tripping_page(df: pd.DataFrame) -> None:
    section_header("Round Tripping Detection")
    window = st.slider("Detection window (days)", 1, 30, 7, key="rt_window")

    with st.spinner("Scanning for suspicious fund movements..."):
        suspicious = detect_round_trips(df, window)

    col1, col2, col3 = st.columns(3)
    col1.metric("Suspicious Patterns", len(suspicious))
    high = len(suspicious[suspicious["Risk Level"] == "High"]) if not suspicious.empty else 0
    col2.metric("High Risk", high)
    related_pct = (df["Related Party Flag"].astype(str).str.lower() == "yes").mean() if "Related Party Flag" in df.columns else 0
    risk = round_trip_risk(len(suspicious), len(df), related_pct)
    col3.metric("Module Risk Score", f"{risk:.0f}/100")

    tab1, tab2, tab3 = st.tabs(["Suspicious Transactions", "Network Graph", "Risk Distribution"])

    with tab1:
        if not suspicious.empty:
            st.dataframe(suspicious.sort_values("Risk Score", ascending=False), use_container_width=True, hide_index=True)
            download_button_for_df(suspicious, "Export Suspicious Transactions", "round_tripping.csv", "dl_rt")
        else:
            st.success("No round-tripping patterns detected.")

    with tab2:
        st.plotly_chart(build_network_graph(df), use_container_width=True)

    with tab3:
        if not suspicious.empty:
            fig = px.histogram(suspicious, x="Risk Score", color="Risk Level", nbins=15,
                               color_discrete_map={"High": "#FF4757", "Medium": "#FFA502", "Low": "#00C896"})
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
            st.plotly_chart(fig, use_container_width=True)

    findings = []
    if len(suspicious):
        findings.append(f"Detected {len(suspicious)} suspicious fund movement patterns.")
        if high:
            findings.append(f"{high} patterns classified as high risk requiring immediate investigation.")
        round_trips = suspicious[suspicious["Pattern"] == "Round Trip"]
        if len(round_trips):
            findings.append(f"{len(round_trips)} round-trip transfers identified within {window}-day window.")

    ai_audit_remark(findings)
