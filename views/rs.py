from __future__ import annotations

import pandas as pd
import streamlit as st

from src.desk import snapshot_row, symbol_history
from src.institutional_view import analyze_symbol, market_close_proxy
from src.screener import apply_filters, filters_from_state
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    snapshot = d.get("snapshot", pd.DataFrame())
    page_header(
        "Research · cross-section",
        "Relative strength",
        "RS 20D percentile is rank among investable names on this board (1–99). Not IBD RS. Stage uses the price series vs the desk median close.",
    )
    if snapshot.empty:
        empty_state("No snapshot", "Refresh market data first.")
        return
    board = apply_filters(snapshot, filters_from_state(st.session_state.get("filters") or {}))
    if symbol:
        hist = symbol_history(d, symbol)
        row = snapshot_row(d, symbol)
        report = analyze_symbol(hist, market_close_proxy(d.get("history", pd.DataFrame())))
        st.subheader(symbol)
        if report.get("ok"):
            stage = report["stage"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Stage", str(stage.get("stage") or "—"))
            c2.metric("20D %ile (liquid)", fmt_num(row.get("RS_20D_PCT") if row is not None else None, "{:.0f}"))
            c3.metric("Sector %ile", fmt_num(row.get("RS_SECTOR_PCT") if row is not None else None, "{:.0f}"))
            c4.metric("20D %", fmt_num(row.get("CHG_20D") if row is not None else None, "{:+.1f}"))
    leaders = board if not board.empty else snapshot
    if "RS_20D_PCT" in leaders.columns:
        leaders = leaders.nlargest(40, "RS_20D_PCT")
    else:
        leaders = leaders.nlargest(40, "CHG_20D") if "CHG_20D" in leaders.columns else leaders.head(40)
    st.subheader("Leaders (investable 20D percentile)")
    show = [c for c in ["SYMBOL", "NAME", "SECTOR", "RS_20D_PCT", "RS_SECTOR_PCT", "CHG_20D", "CHG_LOOKBACK", "SETUP_QUALITY", "RSI_14"] if c in leaders.columns]
    st.dataframe(leaders[show], width="stretch", hide_index=True)
    st.caption("CHG_LOOKBACK is first→last of loaded sessions, not a calendar year.")
