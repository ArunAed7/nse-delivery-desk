from __future__ import annotations

import pandas as pd
import streamlit as st

from src.desk import snapshot_row
from src.fundamentals import fetch_fundamentals
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    page_header(
        "Research · NSE tape + PE",
        "Fundamentals",
        "NSE PE vs sector median, delivery and liquidity. Yahoo filings are optional and blocked unless the snapshot is complete.",
    )
    if not symbol:
        empty_state("Pin a stock first", "Use Jump or the screener.")
        return
    row = snapshot_row(d, symbol)
    st.subheader(symbol)
    if row is None:
        st.warning("Name is not on the current board.")
        return
    a, b, c, dcol = st.columns(4)
    a.metric("NSE PE", fmt_num(row.get("PE"), "{:.1f}"))
    b.metric("PE vs sector", fmt_num(row.get("PE_VS_SECTOR"), "{:.2f}×"))
    c.metric("PE vs market", fmt_num(row.get("PE_VS_MKT"), "{:.2f}×"))
    dcol.metric("Setup quality", fmt_num(row.get("SETUP_QUALITY"), "{:.0f}"))
    st.caption(
        f"Delivery {fmt_num(row.get('DELIV_PER'), '{:.0f}%')} · vs 20D {fmt_num(row.get('DELIV_VS_AVG'), '{:.2f}×')} · "
        f"turnover ₹{fmt_num(row.get('TURNOVER_CR'), '{:.1f}')} Cr · mcap ₹{fmt_num(row.get('MARKET_CAP_CR'), '{:.0f}')} Cr"
    )
    st.info("Delivery is not a substitute for earnings quality. This page will not invent a Piotroski F-score.")
    if st.button("Try Yahoo snapshot", width="stretch"):
        with st.spinner(f"Yahoo {symbol}.NS"):
            try:
                info = fetch_fundamentals(symbol)
            except Exception as exc:
                st.error(str(exc))
                return
        if not info or "error" in info:
            st.warning("No Yahoo snapshot.")
            return
        from src.bridges import yahoo_to_quality_inputs

        fin = yahoo_to_quality_inputs(info, float(row["CLOSE_PRICE"]) if pd.notna(row.get("CLOSE_PRICE")) else None)
        if not fin.get("inputs_complete"):
            st.warning("Yahoo balance sheet is incomplete. Scores are not shown.")
            return
        st.json({k: fin[k] for k in ("roe", "net_income", "total_assets", "fcff", "market_cap") if k in fin})
