"""Reusable UI components and styling helpers."""

from __future__ import annotations

from pathlib import Path

import streamlit as st


def inject_custom_css() -> None:
    css_path = Path(__file__).parent.parent / "assets" / "styles.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_header(logo_path: Path) -> None:
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), width=120)
    with col_title:
        st.markdown(
            """
            <div class="app-header">
                <div>
                    <h1>Treasury & Banking Audit Analytics</h1>
                    <div class="subtitle">Enterprise-grade audit intelligence platform by CAP AI</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def kpi_card(label: str, value: str, icon: str = "📊", delta: str | None = None) -> str:
    delta_html = f'<div style="color:#8899AA;font-size:0.75rem;margin-top:4px;">{delta}</div>' if delta else ""
    return f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-value metric-pulse">{value}</div>
        <div class="kpi-label">{label}</div>
        {delta_html}
    </div>
    """


def render_kpi_row(metrics: list[tuple[str, str, str, str | None]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value, icon, delta) in zip(cols, metrics):
        with col:
            st.markdown(kpi_card(label, value, icon, delta), unsafe_allow_html=True)


def section_header(title: str) -> None:
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def glass_panel(content_fn) -> None:
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    content_fn()
    st.markdown("</div>", unsafe_allow_html=True)


def risk_badge(level: str) -> str:
    css = {"High": "badge-danger", "Medium": "badge-warning", "Low": "badge-success"}.get(level, "badge-info")
    return f'<span class="badge {css}">{level}</span>'


def ai_audit_remark(findings: list[str]) -> None:
    if not findings:
        st.info("No significant audit exceptions detected in this module.")
        return
    st.markdown("#### 🤖 AI-Generated Audit Remarks")
    for i, finding in enumerate(findings[:8], 1):
        st.markdown(f"**{i}.** {finding}")


def search_filter_bar(df, columns: list[str] | None = None):
    """Return filtered dataframe based on sidebar search."""
    search = st.text_input("🔍 Search records", placeholder="Type to filter...")
    if search and not df.empty:
        cols = columns or df.columns.tolist()
        mask = df[cols].astype(str).apply(
            lambda row: row.str.contains(search, case=False, na=False).any(), axis=1
        )
        return df[mask]
    return df


def download_button_for_df(df, label: str, filename: str, key: str) -> None:
    if df is not None and not df.empty:
        st.download_button(
            label=label,
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv",
            key=key,
        )


def show_loading(message: str = "Analyzing data...") -> None:
    with st.spinner(message):
        pass
