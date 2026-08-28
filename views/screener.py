from __future__ import annotations

import pandas as pd
import streamlit as st

from src.screener import ScreenFilters, apply_filters
from src.ui import desk, inject_css, signal_badge

BOARD_COLS = [
    "SYMBOL", "NAME", "SECTOR", "SIGNAL", "ACCUM_SCORE", "HEAT", "CLOSE_PRICE",
    "CHG_1D", "CHG_5D", "CHG_20D", "MARKET_CAP_CR", "PE", "TURNOVER_CR",
    "DELIV_PER", "DELIV_PER_AVG_20", "DELIV_VS_AVG", "DELIV_VS_3M", "DELIV_VALUE_CR",
    "VOL_VS_AVG", "HIGH_DELIV_STREAK", "TREND", "RSI_14", "PCT_VS_SMA20", "LIQUIDITY", "HAS_DEAL",
]


def page() -> None:
    inject_css()
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    f = st.session_state.get("filters") or {}
    series = d.get("series") or ["EQ", "BE"]
    if snapshot.empty:
        st.info("No snapshot yet.")
        return
    st.title("Screener")
    st.caption("Delivery, volume, trend and disclosed-flow heat. Select a row to pin the focus stock.")
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
    filters = ScreenFilters(
        search=search,
        min_deliv_per=None if f.get("min_deliv", 0) <= 0 else float(f["min_deliv"]),
        max_deliv_per=None if f.get("max_deliv", 100) >= 100 else float(f["max_deliv"]),
        min_deliv_vs_avg=None if f.get("min_deliv_vs", 0) <= 0 else float(f["min_deliv_vs"]),
        min_vol_vs_avg=None if f.get("min_vol_vs", 0) <= 0 else float(f["min_vol_vs"]),
        min_deliv_qty_vs_avg=None if f.get("min_dq_vs", 0) <= 0 else float(f["min_dq_vs"]),
        min_turnover=None if f.get("min_turn", 0) <= 0 else float(f["min_turn"]),
        min_market_cap_cr=None if f.get("min_mcap", 0) <= 0 else float(f["min_mcap"]),
        rsi_min=None if f.get("rsi", (0, 100))[0] <= 0 else float(f["rsi"][0]),
        rsi_max=None if f.get("rsi", (0, 100))[1] >= 100 else float(f["rsi"][1]),
        min_chg_5d=None if f.get("chg5", (-50, 50))[0] <= -50 else float(f["chg5"][0]),
        max_chg_5d=None if f.get("chg5", (-50, 50))[1] >= 50 else float(f["chg5"][1]),
        above_sma20=bool(f.get("above_sma20")),
        above_sma50=bool(f.get("above_sma50")),
        sma20_gt_sma50=bool(f.get("sma_cross")),
        bulk_or_block_only=bool(f.get("deals_only")),
        investable_only=bool(f.get("investable_only", True)),
        signal=f.get("signal_filter") or "All",
        preset=f.get("preset") or "None",
        sectors=tuple(f["picked_sectors"]) if f.get("picked_sectors") else None,
    )
    screened = apply_filters(board, filters)
    show_cols = [c for c in BOARD_COLS if c in screened.columns]
    display = screened[show_cols].copy().sort_values(["ACCUM_SCORE", "DELIV_VALUE_CR"], ascending=False, na_position="last")
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
            "ACCUM_SCORE": st.column_config.ProgressColumn("Tape", min_value=0, max_value=100, format="%.0f"),
            "HEAT": st.column_config.ProgressColumn("Heat", min_value=0, max_value=100, format="%.0f"),
            "DELIV_PER": st.column_config.NumberColumn("Deliv %", format="%.1f"),
            "HAS_DEAL": st.column_config.CheckboxColumn("Deal"),
        },
    )
    rows = event.selection.rows if event and event.selection else []
    if rows:
        st.session_state["focus_symbol"] = str(display.iloc[rows[0]]["SYMBOL"])
        signal_badge(str(display.iloc[rows[0]].get("SIGNAL") or "Neutral"))
