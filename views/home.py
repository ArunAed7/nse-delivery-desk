from __future__ import annotations

import pandas as pd
import streamlit as st

from src.institutional_view import market_regime, sector_rotation
from src.insights import top_ideas
from src.ui import (
    desk,
    empty_state,
    fmt_num,
    idea_card_html,
    page_header,
    sector_bar_chart,
    signal_badge,
    tape_roll,
)


def page() -> None:
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    pulse = d.get("pulse", pd.Series(dtype=float))
    last_dt = d.get("last_dt")
    page_header(
        "Markets · amber terminal",
        "Command",
        "Delivery tape, disclosed-flow heat, and regime on one board. Pin a name to open Thesis and research. If this page still has blue tabs named Opportunity board, you are on an old process — stop Streamlit and restart app.py.",
    )
    if snapshot.empty:
        empty_state("No session in cache", "Use Refresh market data in the sidebar to pull NSE bhav copies.")
        return
    pulse_vals = pulse.dropna().tail(20).tolist()
    pulse_last = float(pulse.iloc[-1]) if not pulse.empty else None
    pulse_prev = float(pulse.iloc[-2]) if len(pulse) > 1 else None
    pulse_delta = None if pulse_last is None or pulse_prev is None else pulse_last - pulse_prev
    strong_n = int((snapshot["SIGNAL"] == "Strong accumulation").sum())
    invest_n = int(snapshot["INVESTABLE"].sum()) if "INVESTABLE" in snapshot.columns else 0
    net_flow = float(snapshot["NET_DISCLOSED_CR"].sum()) if "NET_DISCLOSED_CR" in snapshot.columns else 0
    as_of = last_dt.strftime("%d %b %Y") if last_dt else "—"
    ideas = top_ideas(snapshot, n=6)
    roll = ideas if not ideas.empty else (
        snapshot.nlargest(8, "ACCUM_SCORE") if "ACCUM_SCORE" in snapshot.columns else snapshot.head(0)
    )
    tape_roll(roll)
    r1 = st.columns(3, gap="small")
    r1[0].metric("As of", as_of, border=True)
    r1[1].metric(
        "Market delivery %",
        f"{pulse_last:.1f}" if pulse_last is not None else "—",
        f"{pulse_delta:+.1f} vs prior" if pulse_delta is not None else None,
        chart_data=pulse_vals or None,
        chart_type="line",
        border=True,
    )
    r1[2].metric("Investable", f"{invest_n:,}", border=True)
    r2 = st.columns(3, gap="small")
    r2[0].metric("Strong accumulation", f"{strong_n:,}", border=True)
    r2[1].metric("90d disclosed net", f"₹{net_flow:,.0f} Cr", border=True)
    r2[2].metric("Regime", market_regime(d.get("history", pd.DataFrame())), border=True)

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        st.subheader("High-conviction tape")
        if ideas.empty:
            empty_state("No high-conviction names", "Loosen filters or turn off investable-only.")
        else:
            for start in range(0, min(len(ideas), 6), 3):
                chunk = ideas.iloc[start : start + 3]
                cols = st.columns(len(chunk), gap="small")
                for col, (_, idea) in zip(cols, chunk.iterrows()):
                    with col:
                        signal_badge(str(idea["SIGNAL"]))
                        st.markdown(idea_card_html(idea), unsafe_allow_html=True)
                        if st.button("Pin for research", key=f"pin_{idea['SYMBOL']}", width="stretch"):
                            st.session_state["focus_symbol"] = str(idea["SYMBOL"])
                            st.rerun()
    with right:
        st.subheader("Sector rotation")
        rot = sector_rotation(snapshot, n=8)
        if rot.empty:
            st.caption("No sector 20D moves.")
        else:
            st.plotly_chart(sector_bar_chart(rot), width="stretch")
            st.caption("Median 20-day price change among names on the board.")
