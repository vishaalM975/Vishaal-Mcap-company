"""Additional analytics: cash flow, spending, vendors, accounts, trends."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.ui_components import download_button_for_df, section_header


def render_cashflow_page(df: pd.DataFrame) -> None:
    section_header("Cash Flow Analysis")
    df = df.copy()
    if "Month" in df.columns:
        df["Month"] = pd.to_datetime(df["Month"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Month"], y=df["Inflow"], name="Inflow", line=dict(color="#00C896", width=3)))
    fig.add_trace(go.Scatter(x=df["Month"], y=df["Outflow"], name="Outflow", line=dict(color="#FF4757", width=3)))
    fig.add_trace(go.Scatter(x=df["Month"], y=df["Net Cash Flow"], name="Net", line=dict(color="#D4AF37", width=2, dash="dot")))
    fig.update_layout(
        title="Monthly Cash Flow Trend", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E8ECF1", hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_spending_page(df: pd.DataFrame) -> None:
    section_header("Expense Classification")
    fig = px.pie(df, names="Category", values="Amount", hole=0.45,
                 color_discrete_sequence=px.colors.sequential.Teal_r, title="Spending by Category")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(df.sort_values("Amount", ascending=False), use_container_width=True, hide_index=True)
    with col2:
        fig2 = px.bar(df.sort_values("Amount"), x="Amount", y="Category", orientation="h",
                      color="Amount", color_continuous_scale="Blues")
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)


def render_vendor_page(df: pd.DataFrame) -> None:
    section_header("Vendor Payments")
    status_filter = st.multiselect("Filter by status", df["Status"].unique().tolist(), default=df["Status"].unique().tolist())
    filtered = df[df["Status"].isin(status_filter)]
    st.dataframe(filtered.sort_values("Amount", ascending=False), use_container_width=True, hide_index=True)
    download_button_for_df(filtered, "Export Vendor Payments", "vendor_payments.csv", "dl_vendor")

    overdue = filtered[filtered["Status"] == "Overdue"]
    if not overdue.empty:
        st.warning(f"{len(overdue)} overdue vendor payments totaling ₹{overdue['Amount'].sum():,.0f}")


def render_accounts_page(df: pd.DataFrame) -> None:
    section_header("Banking Account Details")
    st.dataframe(df, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        by_bank = df.groupby("Bank Name")["Balance"].sum().reset_index()
        fig = px.bar(by_bank, x="Bank Name", y="Balance", title="Balance by Bank",
                     color_discrete_sequence=["#2C5DA3"])
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        by_type = df.groupby("Account Type")["Balance"].sum().reset_index()
        fig2 = px.pie(by_type, names="Account Type", values="Balance", title="Balance by Account Type",
                      color_discrete_sequence=px.colors.sequential.Blues)
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
        st.plotly_chart(fig2, use_container_width=True)


def render_frequency_heatmap(df: pd.DataFrame) -> None:
    section_header("Transaction Frequency Heatmap")
    pivot = df.pivot_table(index="Day", columns="Hour", values="Count", aggfunc="sum", fill_value=0)
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig = px.imshow(pivot, labels=dict(x="Hour", y="Day", color="Transactions"),
                    color_continuous_scale="Blues", title="Transaction Frequency Heatmap")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
    st.plotly_chart(fig, use_container_width=True)


def render_bank_rent_page(df: pd.DataFrame) -> None:
    section_header("Bank Rent & Service Charges")
    excess = df[df["Flag"] == "Excess"] if "Flag" in df.columns else pd.DataFrame()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Charge Lines", len(df))
    col2.metric("Excess Charges", len(excess))
    col3.metric("Total Debited", f"₹{df['Actual Charge'].sum():,.0f}" if not df.empty else "₹0")

    fig = px.bar(
        df.groupby("Charge Type")["Actual Charge"].sum().reset_index(),
        x="Charge Type", y="Actual Charge", color="Actual Charge",
        title="Charges by Type", color_continuous_scale="Blues",
    )
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df.sort_values("Actual Charge", ascending=False), use_container_width=True, hide_index=True)
    download_button_for_df(excess, "Export Excess Charges", "bank_rent_excess.csv", "dl_rent")


def render_spending_details_page(df: pd.DataFrame) -> None:
    section_header("Money Spending Details")
    category_filter = st.multiselect(
        "Category", sorted(df["Category"].unique()), default=sorted(df["Category"].unique())[:5],
        key="spend_cat",
    )
    filtered = df[df["Category"].isin(category_filter)] if category_filter else df
    st.dataframe(filtered.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
    download_button_for_df(filtered, "Export Spending", "spending_details.csv", "dl_spend_det")

    by_mode = filtered.groupby("Payment Mode")["Amount"].sum().reset_index()
    fig = px.pie(by_mode, names="Payment Mode", values="Amount", hole=0.4, title="Spend by Payment Mode")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1")
    st.plotly_chart(fig, use_container_width=True)


def render_monthly_trends_page(df: pd.DataFrame) -> None:
    section_header("Monthly Bank Trend Analysis")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Month"], y=df["Transaction Count"], name="Transactions", yaxis="y2", opacity=0.6))
    fig.add_trace(go.Scatter(x=df["Month"], y=df["Avg Daily Balance"], name="Avg Balance", line=dict(color="#2C5DA3", width=3)))
    fig.add_trace(go.Scatter(x=df["Month"], y=df["Interest Earned"], name="Interest Earned", line=dict(color="#00C896", width=2)))
    fig.update_layout(
        title="Balance, Transactions & Interest Trends",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#E8ECF1",
        yaxis=dict(title="Balance / Interest (₹)"),
        yaxis2=dict(title="Transaction Count", overlaying="y", side="right"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_sankey(transfers_df: pd.DataFrame) -> None:
    section_header("Fund Flow Sankey Diagram")
    df = transfers_df.copy()
    if df.empty:
        st.info("No transfer data available for Sankey diagram.")
        return

    flows = df.groupby(["From Account", "To Account"])["Amount"].sum().reset_index()
    flows = flows.nlargest(20, "Amount")
    accounts = list(set(flows["From Account"].tolist() + flows["To Account"].tolist()))
    idx = {a: i for i, a in enumerate(accounts)}

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15, thickness=20, line=dict(color="#D4AF37", width=0.5),
            label=accounts, color="#2C5DA3",
        ),
        link=dict(
            source=[idx[r["From Account"]] for _, r in flows.iterrows()],
            target=[idx[r["To Account"]] for _, r in flows.iterrows()],
            value=flows["Amount"].tolist(),
            color="rgba(91, 155, 213, 0.4)",
        ),
    )])
    fig.update_layout(
        title="Top Fund Flows", font_color="#E8ECF1",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", height=550,
    )
    st.plotly_chart(fig, use_container_width=True)
