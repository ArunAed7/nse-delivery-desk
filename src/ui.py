from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


def inject_css() -> None:
    st.markdown(
        """
<style>
[data-testid="stMetric"] { background: #1E293B; border: 1px solid #334155; border-radius: 10px; padding: 8px 12px; }
.block-container { padding-top: 1.1rem; padding-bottom: 2.4rem; }
[data-testid="stSidebar"] { min-width: 20rem; }
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stMetric"]) { gap: 0.6rem; }
</style>
""",
        unsafe_allow_html=True,
    )


def signal_badge(signal: str) -> None:
    color = {
        "Strong accumulation": "green",
        "Quiet accumulation": "blue",
        "Dip absorption": "orange",
        "Overheated": "orange",
        "Speculative": "red",
        "Distribution risk": "red",
        "T2T volume surge": "orange",
        "T2T (delivery n/a)": "gray",
        "Thin tape": "gray",
        "Illiquid": "red",
        "Neutral": "gray",
    }.get(signal, "gray")
    st.badge(signal, color=color)


def fmt_num(value, fmt: str = "{:.1f}", empty: str = "—") -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return empty
    if pd.isna(n):
        return empty
    return fmt.format(n)


def build_price_chart(hist: pd.DataFrame, symbol: str) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.52, 0.24, 0.24],
        specs=[[{"secondary_y": True}], [{}], [{}]],
    )
    fig.add_trace(
        go.Candlestick(
            x=hist["TRADE_DATE"],
            open=hist["OPEN_PRICE"],
            high=hist["HIGH_PRICE"],
            low=hist["LOW_PRICE"],
            close=hist["CLOSE_PRICE"],
            name="Price",
            increasing_line_color="#34D399",
            decreasing_line_color="#F87171",
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    if "SMA_20" in hist.columns:
        fig.add_trace(
            go.Scatter(x=hist["TRADE_DATE"], y=hist["SMA_20"], name="20DMA", line=dict(width=1.5, color="#60A5FA")),
            row=1, col=1, secondary_y=False,
        )
    if "DELIV_PER" in hist.columns:
        fig.add_trace(
            go.Scatter(x=hist["TRADE_DATE"], y=hist["DELIV_PER"], name="Delivery %", line=dict(width=2, color="#FBBF24")),
            row=1, col=1, secondary_y=True,
        )
    fig.add_trace(go.Bar(x=hist["TRADE_DATE"], y=hist["TTL_TRD_QNTY"], name="Volume", marker_color="#64748B"), row=2, col=1)
    if "DELIV_QTY" in hist.columns:
        fig.add_trace(go.Bar(x=hist["TRADE_DATE"], y=hist["DELIV_QTY"], name="Delivery qty", marker_color="#34D399"), row=3, col=1)
    fig.update_layout(
        title=f"{symbol} — price, delivery, volume",
        template="plotly_dark",
        height=620,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=12, t=48, b=20),
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(color="#F1F5F9", family="Inter"),
    )
    fig.update_yaxes(gridcolor="#1E293B")
    fig.update_xaxes(gridcolor="#1E293B")
    return fig


def desk() -> dict:
    return st.session_state.get("desk") or {}


def pick_symbol() -> str | None:
    return st.session_state.get("focus_symbol")
