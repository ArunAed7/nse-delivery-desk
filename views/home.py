from __future__ import annotations

import pandas as pd
import streamlit as st

from src.institutional_view import market_regime, sector_rotation
from src.insights import top_ideas
from src.ui import desk, fmt_num, inject_css, signal_badge


def page() -> None:
    inject_css()
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    pulse = d.get("pulse", pd.Series(dtype=float))
    last_dt = d.get("last_dt")
    if snapshot.empty:
        st.info("Load market data from the sidebar.")
        return
    st.title("Command")
    st.caption("Delivery tape, disclosed flow heat, and regime — one screen, live NSE cache.")
    pulse_vals = pulse.dropna().tail(20).tolist()
    pulse_last = float(pulse.iloc[-1]) if not pulse.empty else None
    pulse_prev = float(pulse.iloc[-2]) if len(pulse) > 1 else None
    pulse_delta = None if pulse_last is None or pulse_prev is None else pulse_last - pulse_prev
    strong_n = int((snapshot["SIGNAL"] == "Strong accumulation").sum())
    invest_n = int(snapshot["INVESTABLE"].sum()) if "INVESTABLE" in snapshot.columns else 0
    net_flow = float(snapshot["NET_DISCLOSED_CR"].sum()) if "NET_DISCLOSED_CR" in snapshot.columns else 0
    as_of = last_dt.strftime("%d %b %Y") if last_dt else "—"
    with st.container(horizontal=True):
        st.metric("As of", as_of, border=True)
        st.metric(
            "Market delivery %",
            f"{pulse_last:.1f}" if pulse_last is not None else "—",
            f"{pulse_delta:+.1f} vs prior" if pulse_delta is not None else None,
            chart_data=pulse_vals or None,
            chart_type="line",
            border=True,
        )
        st.metric("Investable", f"{invest_n:,}", border=True)
        st.metric("Strong accumulation", f"{strong_n:,}", border=True)
        st.metric("90d disclosed net", f"₹{net_flow:,.0f} Cr", border=True)
        st.metric("Regime", market_regime(d.get("history", pd.DataFrame())), border=True)

    ideas = top_ideas(snapshot, n=6)
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("High-conviction tape")
        if ideas.empty:
            st.info("No high-conviction names under current filters.")
        else:
            for start in range(0, min(len(ideas), 6), 3):
                chunk = ideas.iloc[start : start + 3]
                cols = st.columns(len(chunk), border=True)
                for col, (_, idea) in zip(cols, chunk.iterrows()):
                    with col:
                        signal_badge(str(idea["SIGNAL"]))
                        st.markdown(f"**{idea['SYMBOL']}**")
                        st.caption(str(idea.get("NAME") or "")[:48])
                        a, b, c = st.columns(3)
                        a.metric("Tape", fmt_num(idea.get("ACCUM_SCORE"), "{:.0f}"))
                        b.metric("Heat", fmt_num(idea.get("HEAT"), "{:.0f}"))
                        c.metric("5D", fmt_num(idea.get("CHG_5D"), "{:+.1f}%"))
    with right:
        st.subheader("Sector rotation (20D)")
        rot = sector_rotation(snapshot, n=8)
        if rot.empty:
            st.caption("No sector moves.")
        else:
            st.dataframe(
                rot,
                width="stretch",
                hide_index=True,
                column_config={
                    "CHG_20D": st.column_config.NumberColumn("Median 20D %", format="%.2f"),
                    "HEAT": st.column_config.ProgressColumn("Heat", min_value=0, max_value=100, format="%.0f"),
                },
            )
        st.caption("Hottest sectors by median 20-day price change among names on the board.")
