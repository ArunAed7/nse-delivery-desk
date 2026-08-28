from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.desk import assemble_desk
from src.fundamentals import refresh_market_caps, refresh_pe_ratios
from src.nse_data import auto_update_if_stale, latest_cached_date, refresh_history
from src.sectors import load_sectors
from src.trackers import FLOW_WINDOW_DAYS, refresh_institutional, should_refresh_institutional
from src.universe import load_universe
from views import (
    backtest,
    compliance,
    derivatives,
    fundamentals,
    governance,
    home,
    macro,
    ml,
    playbook,
    portfolio,
    rs,
    screener,
    technical,
    thesis,
    trackers,
)

st.set_page_config(
    page_title="NSE delivery desk",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.markdown("### :material/query_stats: Delivery desk")
    st.caption("Delivery, volume and disclosed flow — not named FII/DII.")
    lookback = st.selectbox("Lookback", [30, 90, 180, 365], index=1, help="Trading sessions for averages. 3M needs ~63 days.")
    series = st.multiselect(
        "Series",
        ["EQ", "BE"],
        default=["EQ", "BE"],
        help="BE is trade-to-trade. T2T delivery is treated as 100% of traded quantity.",
    )
    if not series:
        series = ["EQ", "BE"]
    sector_map = load_sectors()
    sector_options = sorted(sector_map["SECTOR"].dropna().unique().tolist()) if not sector_map.empty else []
    picked_sectors = st.multiselect("Sectors", sector_options, default=[], help="From nse_stocks.csv. Empty = all.")
    refresh = st.button("Refresh market data", type="primary", width="stretch")
    refresh_mcap = st.button("Refresh market caps", width="stretch")
    st.markdown("**Decision filters**")
    investable_only = st.toggle("Investable names only", value=True)
    preset = st.selectbox("Setup", ["None", "Delivery accumulation", "Delivery spike vs average", "Uptrend, not overbought"])
    signal_filter = st.selectbox(
        "Signal",
        [
            "All",
            "Strong accumulation",
            "Quiet accumulation",
            "Dip absorption",
            "Overheated",
            "Speculative",
            "Distribution risk",
            "T2T volume surge",
            "T2T (delivery n/a)",
            "Thin tape",
            "Illiquid",
            "Neutral",
        ],
    )
    with st.expander("Fine-tune"):
        min_deliv = st.slider("Min delivery %", 0, 100, 0)
        max_deliv = st.slider("Max delivery %", 0, 100, 100)
        min_deliv_vs = st.number_input("Min delivery vs 20D", 0.0, 10.0, 0.0, 0.1)
        min_vol_vs = st.number_input("Min volume vs 20D", 0.0, 20.0, 0.0, 0.1)
        min_dq_vs = st.number_input("Min delivery qty vs 20D", 0.0, 20.0, 0.0, 0.1)
        min_turn = st.number_input("Min turnover (₹ lakh)", 0.0, 1_000_000.0, 0.0, 50.0)
        min_mcap = st.number_input("Min market cap (₹ Cr)", 0.0, 50_000_000.0, 0.0, 100.0)
        rsi_range = st.slider("RSI(14)", 0, 100, (0, 100))
        chg5 = st.slider("5D price change %", -50, 50, (-50, 50))
        above_sma20 = st.checkbox("Above 20DMA")
        above_sma50 = st.checkbox("Above 50DMA")
        sma_cross = st.checkbox("20DMA above 50DMA")
        deals_only = st.checkbox("Bulk/block deals only")

if not refresh and not refresh_mcap and not st.session_state.get("_bootstrapped"):
    with st.spinner("Checking NSE for today's bhavcopy…"):
        auto = auto_update_if_stale()
        need_flow = should_refresh_institutional()
    if (auto.get("ran") and auto.get("fetched")) or need_flow:
        last = latest_cached_date() or date.today()
        if auto.get("ran") and auto.get("fetched"):
            try:
                refresh_pe_ratios(last)
            except Exception:
                pass
        try:
            with st.spinner("Updating 90-day disclosed flow…"):
                refresh_institutional(last - timedelta(days=FLOW_WINDOW_DAYS), last)
        except Exception:
            pass
        st.session_state["_bootstrapped"] = True
        st.cache_data.clear()
        st.rerun()
    st.session_state["_bootstrapped"] = True

if refresh:
    bar = st.progress(0, text="Starting NSE download…")

    def _progress(frac: float, text: str) -> None:
        bar.progress(min(max(frac, 0.0), 1.0), text=text)

    symbols = load_universe(series=series)["SYMBOL"].tolist()
    with st.status("Downloading daily bhav copies…", expanded=True) as status:
        result = refresh_history(trading_days=max(int(lookback), 63), progress=_progress)
        st.write(result)
        last = latest_cached_date()
        if last:
            try:
                pe = refresh_pe_ratios(last)
                st.write(f"PE rows: {len(pe)}")
            except Exception as exc:
                st.write(f"PE skipped: {exc}")
            try:
                inst = refresh_institutional(last - timedelta(days=FLOW_WINDOW_DAYS), last)
                st.write(inst)
            except Exception as exc:
                st.write(f"Institutional trackers skipped: {exc}")
            try:
                caps = refresh_market_caps(symbols, progress=_progress)
                st.write(f"Market caps: {int(caps['MARKET_CAP'].notna().sum())} / {len(caps)}")
            except Exception as exc:
                st.write(f"Market cap skipped: {exc}")
        status.update(state="complete", label="Refresh finished")
    st.cache_data.clear()
    st.rerun()

if refresh_mcap:
    bar = st.progress(0, text="Fetching market caps…")

    def _mcap_progress(frac: float, text: str) -> None:
        bar.progress(min(max(frac, 0.0), 1.0), text=text)

    symbols = load_universe(series=series)["SYMBOL"].tolist()
    with st.status("Yahoo Finance market caps…", expanded=True) as status:
        caps = refresh_market_caps(symbols, progress=_mcap_progress)
        st.write(f"Filled {int(caps['MARKET_CAP'].notna().sum())} of {len(caps)}")
        status.update(state="complete", label="Market caps updated")
    st.cache_data.clear()
    st.rerun()

desk = assemble_desk(int(lookback), series)
last_dt = desk.get("last_dt")
if last_dt and last_dt < date.today():
    st.sidebar.caption(f"Cache {last_dt:%d %b %Y}. NSE posts the full bhavcopy after hours.")

snapshot = desk.get("snapshot", pd.DataFrame())
with st.sidebar:
    st.markdown("**Focus**")
    search = st.text_input("Search", placeholder="RELIANCE, Infosys…", key="stock_search_query")
    jump_labels: list[str] = []
    label_to_symbol: dict[str, str] = {}
    if not snapshot.empty:
        catalog = snapshot.sort_values("SYMBOL", kind="mergesort")
        jump_labels = (catalog["SYMBOL"].astype(str) + " — " + catalog["NAME"].astype(str)).tolist()
        label_to_symbol = dict(zip(jump_labels, catalog["SYMBOL"].astype(str).tolist()))
    jumped_label = st.selectbox("Jump", options=jump_labels, index=None, placeholder="Jump to a stock", key="stock_jump_select")
    if jumped_label:
        st.session_state["focus_symbol"] = label_to_symbol.get(jumped_label)
    elif search and search.strip() and not snapshot.empty:
        q = search.strip().upper()
        hit = snapshot[snapshot["SYMBOL"].eq(q)]
        if hit.empty:
            hit = snapshot[snapshot["SYMBOL"].str.contains(q, na=False, regex=False)]
        if hit.empty:
            hit = snapshot[snapshot["NAME"].astype(str).str.upper().str.contains(q, na=False, regex=False)]
        if not hit.empty:
            st.session_state["focus_symbol"] = str(hit.iloc[0]["SYMBOL"])
    pinned = st.session_state.get("focus_symbol")
    if pinned:
        st.badge(str(pinned), color="blue")

st.session_state["desk"] = desk
st.session_state["filters"] = {
    "min_deliv": min_deliv,
    "max_deliv": max_deliv,
    "min_deliv_vs": min_deliv_vs,
    "min_vol_vs": min_vol_vs,
    "min_dq_vs": min_dq_vs,
    "min_turn": min_turn,
    "min_mcap": min_mcap,
    "rsi": rsi_range,
    "chg5": chg5,
    "above_sma20": above_sma20,
    "above_sma50": above_sma50,
    "sma_cross": sma_cross,
    "deals_only": deals_only,
    "investable_only": investable_only,
    "signal_filter": signal_filter,
    "preset": preset,
    "picked_sectors": picked_sectors,
}

pg = st.navigation(
    {
        "Markets": [
            st.Page(home.page, title="Command", icon=":material/dashboard:", url_path="command", default=True),
            st.Page(screener.page, title="Screener", icon=":material/table_view:", url_path="screener"),
            st.Page(trackers.page, title="Disclosed flow", icon=":material/account_balance:", url_path="flow"),
            st.Page(thesis.page, title="Thesis", icon=":material/article:", url_path="thesis"),
            st.Page(playbook.page, title="How to decide", icon=":material/menu_book:", url_path="playbook"),
        ],
        "Research": [
            st.Page(technical.page, title="Technical Pro", icon=":material/show_chart:", url_path="technical"),
            st.Page(fundamentals.page, title="Fundamentals", icon=":material/analytics:", url_path="fundamentals"),
            st.Page(rs.page, title="Relative strength", icon=":material/trending_up:", url_path="rs"),
            st.Page(derivatives.page, title="Derivatives", icon=":material/candlestick_chart:", url_path="derivatives"),
            st.Page(governance.page, title="Governance", icon=":material/gavel:", url_path="governance"),
            st.Page(ml.page, title="ML forecast", icon=":material/psychology:", url_path="ml"),
        ],
        "Portfolio": [
            st.Page(portfolio.page, title="Construction", icon=":material/pie_chart:", url_path="portfolio"),
            st.Page(backtest.page, title="Backtest", icon=":material/history:", url_path="backtest"),
            st.Page(compliance.page, title="Compliance", icon=":material/verified_user:", url_path="compliance"),
        ],
        "Macro": [
            st.Page(macro.page, title="Regime & liquidity", icon=":material/public:", url_path="macro"),
        ],
    }
)
pg.run()
