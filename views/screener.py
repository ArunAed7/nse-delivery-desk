from __future__ import annotations

import pandas as pd
import streamlit as st

from src.screener import apply_filters, filters_from_state
from src.ui import desk, empty_state, page_header, signal_badge

BOARD_COLS = [
    "SYMBOL", "NAME", "SECTOR", "CONVICTION", "SIGNAL", "SETUP_QUALITY", "RS_20D_PCT", "SIZE_CAP_CR",
    "CLOSE_PRICE", "CHG_1D", "CHG_5D", "CHG_20D", "MARKET_CAP_CR", "PE", "PE_VS_SECTOR", "TURNOVER_CR",
    "DELIV_PER", "DELIV_VS_AVG", "DELIV_VALUE_CR", "VOL_VS_AVG", "TREND", "RSI_14", "LIQUIDITY", "HAS_DEAL",
]


def page() -> None:
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    f = st.session_state.get("filters") or {}
    series = d.get("series") or ["EQ", "BE"]
    page_header(
        "Markets · mandate",
        "Screener",
        "Delivery, volume, 20D RS percentile, setup quality, liquidity size cap. Select a row to pin.",
    )
    if snapshot.empty:
        empty_state("No snapshot yet", "Refresh market data from the sidebar.")
        return
    wanted = {s.upper() for s in series}
    board = snapshot[snapshot["SERIES"].isin(wanted)].copy()
    search = st.session_state.get("stock_search_query") or ""
    jumped = st.session_state.get("focus_symbol")
    if search.strip():
        q = search.strip().upper()
        extra = snapshot[
            snapshot["SYMBOL"].eq(q)
            | snapshot["SYMBOL"].str.contains(q, na=False, regex=False)
            | snapshot["NAME"].astype(str).str.upper().str.contains(q, na=False, regex=False)
        ]
        board = pd.concat([board, extra]).drop_duplicates(["SYMBOL", "SERIES"])
    if jumped and jumped not in set(board["SYMBOL"]):
        board = pd.concat([board, snapshot[snapshot["SYMBOL"] == jumped]]).drop_duplicates(["SYMBOL", "SERIES"])
    filters = filters_from_state(f, search=search)
    screened = apply_filters(board, filters)
    show_cols = [c for c in BOARD_COLS if c in screened.columns]
    sort_keys = [c for c in ["SETUP_QUALITY", "ACCUM_SCORE", "DELIV_VALUE_CR"] if c in screened.columns]
    display = screened[show_cols].copy().sort_values(sort_keys, ascending=False, na_position="last")
    st.caption(f"{len(display):,} names pass the current mandate.")
    event = st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        height=560,
        column_config={
            "CLOSE_PRICE": st.column_config.NumberColumn("Close", format="%.2f"),
            "MARKET_CAP_CR": st.column_config.NumberColumn("MCap ₹ Cr", format="%.0f"),
            "SETUP_QUALITY": st.column_config.ProgressColumn("Setup", min_value=0, max_value=100, format="%.0f"),
            "RS_20D_PCT": st.column_config.NumberColumn("RS 20D", format="%.0f"),
            "SIZE_CAP_CR": st.column_config.NumberColumn("Size cap ₹ Cr", format="%.2f"),
            "DELIV_PER": st.column_config.NumberColumn("Deliv %", format="%.1f"),
            "HAS_DEAL": st.column_config.CheckboxColumn("Deal"),
        },
    )
    rows = event.selection.rows if event and event.selection else []
    if rows:
        st.session_state["focus_symbol"] = str(display.iloc[rows[0]]["SYMBOL"])
        signal_badge(str(display.iloc[rows[0]].get("SIGNAL") or "Neutral"))
