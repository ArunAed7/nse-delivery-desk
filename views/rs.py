from __future__ import annotations

import pandas as pd
import streamlit as st

from src.desk import snapshot_row, symbol_history
from src.institutional_view import analyze_symbol, market_close_proxy
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    snapshot = d.get("snapshot", pd.DataFrame())
    page_header(
        "Research · vs market median",
        "Relative strength",
        "RS grade, Weinstein stage, breakouts. Universe ranking uses 20D change as a proxy.",
    )
    if snapshot.empty:
        empty_state("No snapshot", "Refresh market data first.")
        return
    if symbol:
        hist = symbol_history(d, symbol)
        report = analyze_symbol(hist, market_close_proxy(d.get("history", pd.DataFrame())))
        st.subheader(symbol)
        if report.get("ok"):
            stage = report["stage"]
            rs = report.get("rs") or {}
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Stage", str(stage.get("stage") or "—"))
            c2.metric("Signal", str(stage.get("signal") or "—"))
            c3.metric("RS grade", str(rs.get("rs_grade") or "—"))
            c4.metric("RS 20D", fmt_num(rs.get("rs_20d"), "{:+.1f}"))
    board = snapshot.nlargest(40, "CHG_20D") if "CHG_20D" in snapshot.columns else snapshot.head(40)
    st.subheader("Leaders (20D)")
    show = [c for c in ["SYMBOL", "NAME", "SECTOR", "CHG_20D", "CHG_1Y", "ACCUM_SCORE", "HEAT", "RSI_14"] if c in board.columns]
    st.dataframe(board[show], width="stretch", hide_index=True)
