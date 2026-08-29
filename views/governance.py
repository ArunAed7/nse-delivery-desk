from __future__ import annotations

import pandas as pd
import streamlit as st

from src.desk import snapshot_row
from src.promoters import load_cached_promoters
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    page_header(
        "Research · SAST overlay",
        "Governance",
        "Reg-29 / PIT promoter prints only. This desk does not have NSE pledge % or board filings, so it does not print ESG or pledge scores.",
    )
    if not symbol:
        empty_state("Pin a stock", "Jump or Search in the sidebar.")
        return
    row = snapshot_row(d, symbol)
    st.subheader(symbol)
    pit = load_cached_promoters()
    stock = pit[pit["SYMBOL"] == symbol] if not pit.empty else pd.DataFrame()
    if stock.empty:
        empty_state("No promoter SAST/PIT rows", "Nothing in the 90-day cache for this symbol.")
        return
    st.dataframe(stock.sort_values("DEAL_DATE", ascending=False), width="stretch", hide_index=True)
    if row is not None:
        st.caption(
            f"Sector {row.get('SECTOR')} · net promoter (qty × last close when value missing) "
            f"₹ {fmt_num(row.get('NET_PROMOTER_CR'), '{:.1f}')} Cr"
        )
    st.caption("VALUE_CR on SAST rows is often imputed. Not a SEBI pledge ratio.")
