from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.announcements import load_cached_announcements
from src.deals import deal_flags, load_cached_deals
from src.fundamentals import (
    fetch_fundamentals,
    load_cached_market_caps,
    load_cached_pe,
    refresh_market_caps,
    refresh_pe_ratios,
)
from src.indicators import add_indicators, latest_snapshot
from src.institutional_view import analyze_symbol, market_close_proxy, market_regime, sector_rotation
from src.insights import classify_snapshot, market_pulse, thesis_for_row, top_ideas
from src.nse_data import auto_update_if_stale, cache_fingerprint, latest_cached_date, load_history, refresh_history
from src.promoters import load_cached_promoters
from src.screener import ScreenFilters, apply_filters
from src.sectors import attach_sectors, load_sectors
from src.trackers import (
    FLOW_WINDOW_DAYS,
    build_flow_book,
    mf_ledger,
    refresh_institutional,
    sector_rollup,
    should_refresh_institutional,
)
from src.universe import load_universe

st.set_page_config(
    page_title="NSE delivery desk",
    page_icon=":material/query_stats:",
    layout="wide",
    initial_sidebar_state="expanded",
)

BOARD_COLS = [
    "SYMBOL",
    "NAME",
    "SECTOR",
    "SIGNAL",
    "ACCUM_SCORE",
    "HEAT",
    "CLOSE_PRICE",
    "CHG_1D",
    "CHG_5D",
    "CHG_20D",
    "MARKET_CAP_CR",
    "PE",
    "TURNOVER_CR",
    "DELIV_PER",
    "DELIV_PER_AVG_20",
    "DELIV_VS_AVG",
    "DELIV_VS_3M",
    "DELIV_VALUE_CR",
    "VOL_VS_AVG",
    "HIGH_DELIV_STREAK",
    "TREND",
    "RSI_14",
    "PCT_VS_SMA20",
    "LIQUIDITY",
    "HAS_DEAL",
]


def delta_20d(row) -> str | None:
    v = row.get("DELIV_PER_AVG_20") if hasattr(row, "get") else None
    if v is None or pd.isna(v):
        return None
    return f"20D {float(v):.0f}%"


@st.cache_data(show_spinner=False)
def cached_universe(series: tuple[str, ...]) -> pd.DataFrame:
    return load_universe(series=list(series))


@st.cache_data(show_spinner=False)
def cached_history(trading_days: int, cache_sig: str) -> pd.DataFrame:
    _ = cache_sig
    return load_history(trading_days=trading_days)


@st.cache_data(show_spinner=False)
def cached_indicators(history: pd.DataFrame) -> pd.DataFrame:
    return add_indicators(history)


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
            row=1,
            col=1,
            secondary_y=False,
        )
    if "SMA_50" in hist.columns:
        fig.add_trace(
            go.Scatter(x=hist["TRADE_DATE"], y=hist["SMA_50"], name="50DMA", line=dict(width=1.5, color="#A78BFA")),
            row=1,
            col=1,
            secondary_y=False,
        )
    fig.add_trace(
        go.Scatter(x=hist["TRADE_DATE"], y=hist["DELIV_PER"], name="Delivery %", line=dict(width=2.2, color="#FBBF24")),
        row=1,
        col=1,
        secondary_y=True,
    )
    for col, label, color in (
        ("DELIV_PER_AVG_20", "20D avg", "#38BDF8"),
        ("DELIV_PER_AVG_3M", "3M avg", "#34D399"),
    ):
        if col in hist.columns:
            fig.add_trace(
                go.Scatter(x=hist["TRADE_DATE"], y=hist[col], name=label, line=dict(width=1.2, dash="dot", color=color)),
                row=1,
                col=1,
                secondary_y=True,
            )
    fig.add_trace(go.Bar(x=hist["TRADE_DATE"], y=hist["TTL_TRD_QNTY"], name="Volume", marker_color="#64748B"), row=2, col=1)
    fig.add_trace(go.Bar(x=hist["TRADE_DATE"], y=hist["DELIV_QTY"], name="Delivery qty", marker_color="#34D399"), row=3, col=1)
    fig.update_layout(
        title=f"{symbol} — price, delivery and volume",
        template="plotly_dark",
        height=640,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=48, r=16, t=56, b=24),
        paper_bgcolor="#0F172A",
        plot_bgcolor="#0F172A",
        font=dict(color="#F1F5F9", family="Inter"),
    )
    fig.update_yaxes(title_text="Price", row=1, col=1, secondary_y=False, gridcolor="#1E293B")
    fig.update_yaxes(title_text="Deliv %", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Volume", row=2, col=1, gridcolor="#1E293B")
    fig.update_yaxes(title_text="Deliv qty", row=3, col=1, gridcolor="#1E293B")
    fig.update_xaxes(gridcolor="#1E293B")
    return fig


def fmt_cap(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if n >= 1e12:
        return f"₹{n / 1e12:.2f} Tn"
    if n >= 1e7:
        return f"₹{n / 1e7:.2f} Cr"
    return f"₹{n:,.0f}"


def fmt_pct(value) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if abs(n) <= 1.5:
        n *= 100
    return f"{n:.1f}%"


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


with st.sidebar:
    st.markdown("### :material/query_stats: Delivery desk")
    st.caption("Find names where delivery, volume and price line up — a proxy for longer-term buying, not named FII/DII.")
    lookback = st.selectbox("Lookback", [30, 90, 180, 365], index=1, help="Trading sessions loaded for averages. 3M needs ~63 days.")
    series = st.multiselect(
        "Series",
        ["EQ", "BE"],
        default=["EQ", "BE"],
        help="BE is trade-to-trade (T2T). Names like STLTECH only appear if BE is selected. T2T delivery is treated as 100% of traded quantity.",
    )
    if not series:
        series = ["EQ", "BE"]
    sector_map = load_sectors()
    sector_options = sorted(sector_map["SECTOR"].dropna().unique().tolist()) if not sector_map.empty else []
    picked_sectors = st.multiselect(
        "Sectors",
        sector_options,
        default=[],
        help="From nse_stocks.csv. Leave empty to include every sector.",
    )
    refresh = st.button("Refresh market data", type="primary", width="stretch")
    refresh_mcap = st.button("Refresh market caps", width="stretch")
    st.markdown("**Decision filters**")
    investable_only = st.toggle("Investable names only", value=True, help="Hides illiquid prints and 100% delivery on tiny turnover.")
    preset = st.selectbox(
        "Setup",
        ["None", "Delivery accumulation", "Delivery spike vs average", "Uptrend, not overbought"],
    )
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

if not refresh and not refresh_mcap:
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
            with st.spinner("Updating 90-day disclosed flow (bulk, promoters, announcements)…"):
                refresh_institutional(last - timedelta(days=FLOW_WINDOW_DAYS), last)
        except Exception:
            pass
        st.cache_data.clear()
        st.rerun()


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
            start = last - timedelta(days=FLOW_WINDOW_DAYS)
            try:
                inst = refresh_institutional(start, last)
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

cache_sig = cache_fingerprint()
universe = cached_universe(("EQ", "BE"))
history_days = max(int(lookback), 63)
history = cached_history(history_days, cache_sig)

st.title("Where is delivery actually showing up?")
st.caption("Shortlist liquid names with rising delivery, confirmed volume, and a usable trend — then read the thesis before you size a trade.")
last_dt = latest_cached_date()
if last_dt and last_dt < date.today():
    st.info(
        f"Latest cached session is {last_dt:%d %b %Y}. NSE publishes the full bhavcopy after market hours; "
        "this page checks automatically when you open it and about every 20 minutes until today’s file appears."
    )
if history.empty:
    st.info("No cached market data yet. Click **Refresh market data** in the sidebar.")
    st.stop()

history = history.merge(universe[["SYMBOL", "SERIES", "NAME"]], on=["SYMBOL", "SERIES"], how="inner")
if history.empty:
    history = cached_history(history_days, cache_sig)
    history = history.merge(universe[["SYMBOL", "NAME"]], on="SYMBOL", how="inner")

with_ind = cached_indicators(history)
snapshot = latest_snapshot(with_ind)
pe = load_cached_pe()
if not pe.empty:
    snapshot = snapshot.merge(pe[["SYMBOL", "PE"]].drop_duplicates("SYMBOL"), on="SYMBOL", how="left")
else:
    snapshot["PE"] = pd.NA
mcaps = load_cached_market_caps()
if not mcaps.empty:
    snapshot = snapshot.merge(
        mcaps[["SYMBOL", "MARKET_CAP", "MARKET_CAP_CR"]].drop_duplicates("SYMBOL"),
        on="SYMBOL",
        how="left",
    )
else:
    snapshot["MARKET_CAP"] = pd.NA
    snapshot["MARKET_CAP_CR"] = pd.NA
deals = load_cached_deals()
flags = deal_flags(deals)
snapshot = snapshot.merge(flags, on="SYMBOL", how="left")
snapshot["HAS_DEAL"] = snapshot["HAS_DEAL"].fillna(False).astype(bool)
snapshot["DEAL_COUNT"] = snapshot["DEAL_COUNT"].fillna(0)
snapshot["DEAL_TYPES"] = snapshot["DEAL_TYPES"].fillna("")
snapshot = attach_sectors(snapshot)
if "ACCUM_SCORE" in snapshot.columns:
    snapshot["ACCUM_SCORE"] = snapshot["ACCUM_SCORE"].fillna(0) + snapshot["HAS_DEAL"].astype(float) * 8
    snapshot["ACCUM_SCORE"] = snapshot["ACCUM_SCORE"].clip(upper=100)
snapshot = classify_snapshot(snapshot)
flow_book = build_flow_book(snapshot, as_of=last_dt)
flow_cols = [
    c
    for c in [
        "SYMBOL",
        "HEAT",
        "NET_DISCLOSED_CR",
        "CUMULATIVE_BUY_CR",
        "NET_BULK_CR",
        "NET_BLOCK_CR",
        "NET_MF_CR",
        "NET_PROMOTER_CR",
        "FLOW_RANK",
        "SECTOR_FLOW_RANK",
        "NEWS_SENTIMENT",
        "NEWS_COUNT",
        "ALIGNMENT",
        "MF_NEW_ENTRY",
    ]
    if c in flow_book.columns
]
if not flow_book.empty:
    snapshot = snapshot.merge(flow_book[flow_cols], on="SYMBOL", how="left")
for col, fill in (("HEAT", 0.0), ("NET_DISCLOSED_CR", 0.0), ("CUMULATIVE_BUY_CR", 0.0), ("NEWS_SENTIMENT", 0.0)):
    if col not in snapshot.columns:
        snapshot[col] = fill
    else:
        snapshot[col] = snapshot[col].fillna(fill)

pulse = market_pulse(history)
pulse_vals = pulse.dropna().tail(20).tolist()
pulse_last = float(pulse.iloc[-1]) if not pulse.empty else None
pulse_prev = float(pulse.iloc[-2]) if len(pulse) > 1 else None
pulse_delta = None if pulse_last is None or pulse_prev is None else pulse_last - pulse_prev

catalog = snapshot.sort_values("SYMBOL", kind="mergesort")
jump_labels = (catalog["SYMBOL"].astype(str) + " — " + catalog["NAME"].astype(str)).tolist()
label_to_symbol = dict(zip(jump_labels, catalog["SYMBOL"].astype(str).tolist()))
s1, s2 = st.columns([1.4, 1])
with s1:
    search = st.text_input("Search", placeholder="RELIANCE, STLTECH, Infosys…", label_visibility="collapsed", key="stock_search_query")
with s2:
    jumped_label = st.selectbox(
        "Jump",
        options=jump_labels,
        index=None,
        placeholder="Jump to a stock",
        label_visibility="collapsed",
        key="stock_jump_select",
    )
jumped_symbol = label_to_symbol.get(jumped_label) if jumped_label else None

wanted_series = {s.upper() for s in series}
board = snapshot[snapshot["SERIES"].isin(wanted_series)].copy()
if search and search.strip():
    q = search.strip().upper()
    extra = snapshot[
        snapshot["SYMBOL"].eq(q)
        | snapshot["SYMBOL"].str.contains(q, na=False, regex=False)
        | snapshot["NAME"].astype(str).str.upper().str.contains(q, na=False, regex=False)
    ]
    board = pd.concat([board, extra]).drop_duplicates(["SYMBOL", "SERIES"])
if jumped_symbol and jumped_symbol not in set(board["SYMBOL"]):
    board = pd.concat([board, snapshot[snapshot["SYMBOL"] == jumped_symbol]]).drop_duplicates(["SYMBOL", "SERIES"])

filters = ScreenFilters(
    search=search,
    min_deliv_per=None if min_deliv <= 0 else float(min_deliv),
    max_deliv_per=None if max_deliv >= 100 else float(max_deliv),
    min_deliv_vs_avg=None if min_deliv_vs <= 0 else float(min_deliv_vs),
    min_vol_vs_avg=None if min_vol_vs <= 0 else float(min_vol_vs),
    min_deliv_qty_vs_avg=None if min_dq_vs <= 0 else float(min_dq_vs),
    min_turnover=None if min_turn <= 0 else float(min_turn),
    min_market_cap_cr=None if min_mcap <= 0 else float(min_mcap),
    rsi_min=None if rsi_range[0] <= 0 else float(rsi_range[0]),
    rsi_max=None if rsi_range[1] >= 100 else float(rsi_range[1]),
    min_chg_5d=None if chg5[0] <= -50 else float(chg5[0]),
    max_chg_5d=None if chg5[1] >= 50 else float(chg5[1]),
    above_sma20=above_sma20,
    above_sma50=above_sma50,
    sma20_gt_sma50=sma_cross,
    bulk_or_block_only=deals_only,
    investable_only=investable_only,
    signal=signal_filter,
    preset=preset,
    sectors=tuple(picked_sectors) if picked_sectors else None,
)
screened = apply_filters(board, filters)
ideas = top_ideas(screened if not screened.empty else snapshot, n=6)
strong_n = int((snapshot["SIGNAL"] == "Strong accumulation").sum())
quiet_n = int((snapshot["SIGNAL"] == "Quiet accumulation").sum())
invest_n = int(snapshot["INVESTABLE"].sum()) if "INVESTABLE" in snapshot.columns else 0

as_of = last_dt.strftime("%d %b %Y") if last_dt else "—"
kpi_kwargs = {"border": True}
with st.container(horizontal=True):
    st.metric("As of", as_of, **kpi_kwargs)
    st.metric(
        "Market delivery %",
        f"{pulse_last:.1f}" if pulse_last is not None else "—",
        f"{pulse_delta:+.1f} vs prior day" if pulse_delta is not None else None,
        chart_data=pulse_vals or None,
        chart_type="line",
        **kpi_kwargs,
    )
    st.metric("Investable names", f"{invest_n:,}", **kpi_kwargs)
    st.metric("Strong accumulation", f"{strong_n:,}", **kpi_kwargs)
    st.metric("Quiet accumulation", f"{quiet_n:,}", **kpi_kwargs)
    st.metric("Passing your filters", f"{len(screened):,}", **kpi_kwargs)

st.subheader("High-conviction tape")
st.caption("Liquid names where delivery, volume and price agree. Use Jump or the board to open a thesis.")
if ideas.empty:
    st.info("No high-conviction names under the current filters. Relax a setup or turn off Investable names only.")
else:
    for start in range(0, min(len(ideas), 6), 3):
        chunk = ideas.iloc[start : start + 3]
        cols = st.columns(len(chunk), border=True)
        for col, (_, idea) in zip(cols, chunk.iterrows()):
            with col:
                signal_badge(str(idea["SIGNAL"]))
                st.markdown(f"**{idea['SYMBOL']}**")
                st.caption(str(idea.get("NAME") or "")[:52])
                c1, c2, c3 = st.columns(3)
                c1.metric("Conviction", f"{float(idea['ACCUM_SCORE']):.0f}")
                c2.metric("Deliv %", f"{float(idea['DELIV_PER']):.0f}" if pd.notna(idea["DELIV_PER"]) else "—")
                chg = idea.get("CHG_5D")
                c3.metric("5D", f"{float(chg):+.1f}%" if pd.notna(chg) else "—")
                st.caption(thesis_for_row(idea, last_dt)["headline"])

show_cols = [c for c in BOARD_COLS if c in screened.columns]
display = screened[show_cols].copy()
display = display.sort_values(["ACCUM_SCORE", "DELIV_VALUE_CR"], ascending=False, na_position="last")
if jumped_symbol:
    hit = snapshot.loc[snapshot["SYMBOL"] == jumped_symbol, [c for c in show_cols if c in snapshot.columns]]
    rest = display[display["SYMBOL"] != jumped_symbol]
    display = pd.concat([hit, rest], ignore_index=True)

board_tab, trackers_tab, inst_tab, thesis_tab, guide_tab = st.tabs(
    [
        ":material/table_chart: Opportunity board",
        ":material/account_balance: Trackers",
        ":material/account_balance_wallet: Institutional",
        ":material/analytics: Stock thesis",
        ":material/menu_book: How to decide",
    ]
)

with board_tab:
    if search and search.strip():
        st.caption(f"{len(display):,} matches for “{search.strip()}”. Sort any column. Select a row, then open Stock thesis.")
    else:
        st.caption("Sorted by conviction. Accumulation on liquid names ranks above 100% delivery on thin stocks.")
    event = st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        height=520,
        column_config={
            "CLOSE_PRICE": st.column_config.NumberColumn("Close", format="%.2f"),
            "MARKET_CAP_CR": st.column_config.NumberColumn("MCap ₹ Cr", format="%.0f"),
            "PE": st.column_config.NumberColumn("PE", format="%.1f"),
            "TURNOVER_CR": st.column_config.NumberColumn("Turnover ₹ Cr", format="%.1f"),
            "DELIV_PER": st.column_config.NumberColumn("Deliv %", format="%.1f"),
            "DELIV_PER_AVG_20": st.column_config.NumberColumn("Deliv 20D", format="%.1f"),
            "DELIV_VS_AVG": st.column_config.NumberColumn("vs 20D", format="%.2f"),
            "DELIV_VS_3M": st.column_config.NumberColumn("vs 3M", format="%.2f"),
            "DELIV_VALUE_CR": st.column_config.NumberColumn("Deliv ₹ Cr", format="%.1f"),
            "VOL_VS_AVG": st.column_config.NumberColumn("Vol vs 20D", format="%.2f"),
            "HIGH_DELIV_STREAK": st.column_config.NumberColumn("Streak", format="%.0f"),
            "ACCUM_SCORE": st.column_config.ProgressColumn("Conviction", min_value=0, max_value=100, format="%.0f"),
            "HEAT": st.column_config.ProgressColumn("Flow heat", min_value=0, max_value=100, format="%.0f"),
            "RSI_14": st.column_config.NumberColumn("RSI", format="%.0f"),
            "PCT_VS_SMA20": st.column_config.NumberColumn("vs SMA20 %", format="%.1f"),
            "CHG_1D": st.column_config.NumberColumn("1D %", format="%.2f"),
            "CHG_5D": st.column_config.NumberColumn("5D %", format="%.2f"),
            "CHG_20D": st.column_config.NumberColumn("20D %", format="%.2f"),
            "HAS_DEAL": st.column_config.CheckboxColumn("Deal"),
        },
    )

with trackers_tab:
    st.caption(
        "Disclosed 90-day flow only — bulk/block client names, promoter PIT, and headline sentiment. "
        "This is not stock-wise FII/DII."
    )
    book = flow_book.copy()
    if picked_sectors:
        book = book[book["SECTOR"].isin(picked_sectors)]
    sectors_view = sector_rollup(book)
    net_all = float(book["NET_DISCLOSED_CR"].sum()) if not book.empty else 0.0
    mf_all = float(book["NET_MF_CR"].sum()) if not book.empty and "NET_MF_CR" in book.columns else 0.0
    prom_all = float(book["NET_PROMOTER_CR"].sum()) if not book.empty and "NET_PROMOTER_CR" in book.columns else 0.0
    top_sector = str(sectors_view.iloc[0]["SECTOR"]) if not sectors_view.empty else "—"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("90d net disclosed", f"₹{net_all:,.0f} Cr", border=True)
    k2.metric("Top sector by net", top_sector, border=True)
    k3.metric("MF-tagged net", f"₹{mf_all:,.0f} Cr", border=True)
    k4.metric("Promoter net", f"₹{prom_all:,.0f} Cr", border=True)

    heat_tab, bulk_tab, prom_tab, mf_tab, news_tab = st.tabs(
        ["Flow heatmap", "Bulk & block", "Promoter book", "MF entries", "Announcements"]
    )
    heat_cols = [
        c
        for c in [
            "FLOW_RANK",
            "SYMBOL",
            "NAME",
            "SECTOR",
            "SECTOR_FLOW_RANK",
            "NET_DISCLOSED_CR",
            "CUMULATIVE_BUY_CR",
            "NET_MF_CR",
            "NET_PROMOTER_CR",
            "ACCUM_SCORE",
            "NEWS_SENTIMENT",
            "ALIGNMENT",
            "HEAT",
        ]
        if c in book.columns
    ]
    with heat_tab:
        if sectors_view.empty:
            st.info("No disclosed flow cached yet. Click Refresh market data.")
        else:
            st.dataframe(
                sectors_view,
                width="stretch",
                hide_index=True,
                column_config={
                    "NET_DISCLOSED_CR": st.column_config.NumberColumn("Net ₹ Cr", format="%.1f"),
                    "CUMULATIVE_BUY_CR": st.column_config.NumberColumn("Cum. buys ₹ Cr", format="%.1f"),
                    "NET_MF_CR": st.column_config.NumberColumn("MF net ₹ Cr", format="%.1f"),
                    "NET_PROMOTER_CR": st.column_config.NumberColumn("Promoter net ₹ Cr", format="%.1f"),
                    "HEAT": st.column_config.ProgressColumn("Avg heat", min_value=0, max_value=100, format="%.0f"),
                },
            )
        ranked = book.sort_values(["NET_DISCLOSED_CR", "CUMULATIVE_BUY_CR"], ascending=False)
        st.dataframe(
            ranked[heat_cols] if heat_cols else ranked,
            width="stretch",
            hide_index=True,
            height=440,
            column_config={
                "NET_DISCLOSED_CR": st.column_config.NumberColumn("Net ₹ Cr", format="%.1f"),
                "CUMULATIVE_BUY_CR": st.column_config.NumberColumn("Cum. buys ₹ Cr", format="%.1f"),
                "NET_MF_CR": st.column_config.NumberColumn("MF net", format="%.1f"),
                "NET_PROMOTER_CR": st.column_config.NumberColumn("Promoter net", format="%.1f"),
                "ACCUM_SCORE": st.column_config.ProgressColumn("Tape", min_value=0, max_value=100, format="%.0f"),
                "NEWS_SENTIMENT": st.column_config.NumberColumn("News −1…+1", format="%.2f"),
                "HEAT": st.column_config.ProgressColumn("Heat", min_value=0, max_value=100, format="%.0f"),
                "FLOW_RANK": st.column_config.NumberColumn("Rank", format="%.0f"),
                "SECTOR_FLOW_RANK": st.column_config.NumberColumn("In sector", format="%.0f"),
            },
        )
    with bulk_tab:
        deal_view = deals.copy() if deals is not None else pd.DataFrame()
        if not deal_view.empty:
            deal_view = attach_sectors(deal_view)
            if picked_sectors:
                deal_view = deal_view[deal_view["SECTOR"].isin(picked_sectors)]
            sides = sorted(deal_view["SIDE"].dropna().astype(str).unique().tolist()) if "SIDE" in deal_view.columns else []
            types = (
                sorted(deal_view["CLIENT_TYPE"].dropna().astype(str).unique().tolist())
                if "CLIENT_TYPE" in deal_view.columns
                else []
            )
            f1, f2 = st.columns(2)
            side_pick = f1.multiselect("Buy / Sell", sides, default=sides)
            type_pick = f2.multiselect("Client type", types, default=types)
            if side_pick and "SIDE" in deal_view.columns:
                deal_view = deal_view[deal_view["SIDE"].isin(side_pick)]
            if type_pick and "CLIENT_TYPE" in deal_view.columns:
                deal_view = deal_view[deal_view["CLIENT_TYPE"].isin(type_pick)]
            show = deal_view.sort_values("DEAL_DATE", ascending=False)
            keep = [
                c
                for c in [
                    "DEAL_DATE",
                    "SYMBOL",
                    "SECTOR",
                    "DEAL_TYPE",
                    "CLIENT_NAME",
                    "CLIENT_TYPE",
                    "SIDE",
                    "QUANTITY",
                    "PRICE",
                    "VALUE_CR",
                ]
                if c in show.columns
            ]
            st.dataframe(show[keep], width="stretch", hide_index=True, height=360)
            if "CLIENT_NAME" in show.columns and "VALUE_CR" in show.columns:
                leaders = (
                    show.groupby(["CLIENT_NAME", "CLIENT_TYPE"], as_index=False)["VALUE_CR"]
                    .sum()
                    .sort_values("VALUE_CR", ascending=False)
                    .head(25)
                )
                st.caption("Client leaderboard (net ₹ Cr in the filtered set)")
                st.dataframe(
                    leaders,
                    width="stretch",
                    hide_index=True,
                    column_config={"VALUE_CR": st.column_config.NumberColumn("Net ₹ Cr", format="%.2f")},
                )
        else:
            st.info("No bulk/block rows in cache.")
    with prom_tab:
        pit = load_cached_promoters()
        pit = attach_sectors(pit) if pit is not None and not pit.empty else pit
        if pit is None or pit.empty:
            st.info("No promoter PIT rows in the 90-day window.")
        else:
            if picked_sectors:
                pit = pit[pit["SECTOR"].isin(picked_sectors)]
            st.dataframe(
                pit.sort_values("DEAL_DATE", ascending=False),
                width="stretch",
                hide_index=True,
                height=360,
                column_config={
                    "VALUE_CR": st.column_config.NumberColumn("Value ₹ Cr", format="%.2f"),
                    "BUY_CR": st.column_config.NumberColumn("Buy ₹ Cr", format="%.2f"),
                    "SELL_CR": st.column_config.NumberColumn("Sell ₹ Cr", format="%.2f"),
                },
            )
            acq = (
                pit.groupby("ACQUIRER", as_index=False)["VALUE_CR"]
                .sum()
                .sort_values("VALUE_CR", ascending=False)
                .head(20)
            )
            st.caption("Largest acquirers (net ₹ Cr)")
            st.dataframe(
                acq,
                width="stretch",
                hide_index=True,
                column_config={"VALUE_CR": st.column_config.NumberColumn("Net ₹ Cr", format="%.2f")},
            )
    with mf_tab:
        mf = mf_ledger(as_of=last_dt)
        if mf is None or mf.empty:
            st.info("No mutual-fund-tagged bulk/block clients in this window.")
        else:
            if picked_sectors:
                mf = mf[mf["SECTOR"].isin(picked_sectors)]
            new_syms = set(book.loc[book.get("MF_NEW_ENTRY", False) == True, "SYMBOL"]) if "MF_NEW_ENTRY" in book.columns else set()
            mf = mf.copy()
            mf["NEW_ENTRY"] = mf["SYMBOL"].isin(new_syms)
            st.caption("Client names tagged as mutual funds on NSE bulk/block prints. New entry = first MF print in the last 21 days of this window.")
            keep = [
                c
                for c in [
                    "DEAL_DATE",
                    "SYMBOL",
                    "SECTOR",
                    "CLIENT_NAME",
                    "SIDE",
                    "QUANTITY",
                    "PRICE",
                    "VALUE_CR",
                    "NEW_ENTRY",
                    "DEAL_TYPE",
                ]
                if c in mf.columns
            ]
            st.dataframe(
                mf.sort_values("DEAL_DATE", ascending=False)[keep],
                width="stretch",
                hide_index=True,
                height=420,
                column_config={
                    "VALUE_CR": st.column_config.NumberColumn("₹ Cr", format="%.2f"),
                    "NEW_ENTRY": st.column_config.CheckboxColumn("New"),
                },
            )
    with news_tab:
        news = load_cached_announcements()
        if news is None or news.empty:
            st.info("No announcements cached yet.")
        else:
            news = attach_sectors(news)
            if picked_sectors:
                news = news[news["SECTOR"].isin(picked_sectors)]
            keep = [
                c
                for c in [
                    "ANN_DATE",
                    "SYMBOL",
                    "COMPANY",
                    "SECTOR",
                    "SUBJECT",
                    "DETAILS",
                    "SENTIMENT_LABEL",
                    "SENTIMENT",
                    "ATTACHMENT",
                ]
                if c in news.columns
            ]
            subjects = sorted(news["SUBJECT"].dropna().astype(str).unique().tolist()) if "SUBJECT" in news.columns else []
            subject_pick = st.multiselect("Subject (NSE category)", subjects[:80], default=[])
            view = news
            if subject_pick and "SUBJECT" in view.columns:
                view = view[view["SUBJECT"].isin(subject_pick)]
            st.caption(
                "Direct from [NSE corporate filings — announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements). "
                "Showing the latest 1,500. Sentiment is a keyword score on subject + details."
            )
            st.dataframe(
                view.sort_values("ANN_DATE", ascending=False)[keep].head(1500),
                width="stretch",
                hide_index=True,
                height=520,
                column_config={
                    "ANN_DATE": st.column_config.DatetimeColumn("Broadcast"),
                    "COMPANY": st.column_config.TextColumn("Company"),
                    "SUBJECT": st.column_config.TextColumn("Subject"),
                    "DETAILS": st.column_config.TextColumn("Details"),
                    "SENTIMENT": st.column_config.NumberColumn("Score", format="%.2f"),
                    "ATTACHMENT": st.column_config.LinkColumn("Attachment"),
                },
            )

rows = event.selection.rows if event and event.selection else []
selected_symbol = str(display.iloc[rows[0]]["SYMBOL"]) if rows else None
if not selected_symbol and jumped_symbol:
    selected_symbol = jumped_symbol
if not selected_symbol and search and search.strip():
    q = search.strip().upper()
    exact = snapshot.loc[snapshot["SYMBOL"] == q, "SYMBOL"]
    if len(exact):
        selected_symbol = str(exact.iloc[0])
    elif len(display) == 1:
        selected_symbol = str(display.iloc[0]["SYMBOL"])

detail_options = display["SYMBOL"].tolist() if not display.empty else snapshot["SYMBOL"].tolist()
if not selected_symbol:
    if not ideas.empty:
        selected_symbol = str(ideas.iloc[0]["SYMBOL"])
    elif "RELIANCE" in snapshot["SYMBOL"].values:
        selected_symbol = "RELIANCE"
    elif detail_options:
        selected_symbol = detail_options[0]
if selected_symbol and selected_symbol not in detail_options:
    detail_options = [selected_symbol] + [s for s in detail_options if s != selected_symbol]

with inst_tab:
    st.caption(
        "Phase 1 institutional suite on live NSE history for the selected name — momentum, volatility, "
        "relative strength, and risk. Not a recommendation."
    )
    regime = market_regime(history)
    rot = sector_rotation(snapshot)
    k1, k2, k3 = st.columns(3)
    k1.metric("Market regime", regime, border=True)
    k2.metric("Focus stock", selected_symbol or "—", border=True)
    top_sec = str(rot.iloc[0]["SECTOR"]) if rot is not None and not rot.empty else "—"
    k3.metric("Hottest 20D sector", top_sec, border=True)
    if rot is not None and not rot.empty:
        st.dataframe(
            rot,
            width="stretch",
            hide_index=True,
            column_config={
                "CHG_20D": st.column_config.NumberColumn("Median 20D %", format="%.2f"),
                "HEAT": st.column_config.ProgressColumn("Avg heat", min_value=0, max_value=100, format="%.0f"),
            },
        )
    hist_sym = with_ind[with_ind["SYMBOL"] == selected_symbol].sort_values("TRADE_DATE") if selected_symbol else pd.DataFrame()
    if hist_sym.empty:
        st.info("Pick a stock on the board or Jump, then open this tab.")
    else:
        with st.spinner("Computing institutional indicators…"):
            report = analyze_symbol(hist_sym, market_close_proxy(history))
        if not report.get("ok"):
            st.warning(report.get("reason", "Could not compute."))
        else:
            last = report["last"]
            sig = report["signals"]
            stage = report["stage"]
            tech_t, rs_t, risk_t = st.tabs(["Momentum & vol", "Relative strength", "Risk"])
            with tech_t:
                def _m(val, fmt: str) -> str:
                    try:
                        n = float(val)
                    except (TypeError, ValueError):
                        return "—"
                    if pd.isna(n):
                        return "—"
                    return fmt.format(n)

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Connors RSI", _m(last.get("mom_crsi"), "{:.1f}"))
                c2.metric("ADX", _m(last.get("adx_adx"), "{:.1f}"))
                c3.metric("CMF", _m(last.get("cmf"), "{:.2f}"))
                c4.metric("Vol regime", str(last.get("vol_regime") or "—"))
                d1, d2, d3 = st.columns(3)
                d1.metric("Momentum score", _m(sig.get("momentum_score"), "{:+.1f}"))
                vol20 = last.get("vol_hist_20")
                d2.metric("Hist vol 20D", _m(None if pd.isna(vol20) else float(vol20) * 100, "{:.1f}%") if pd.notna(vol20) else "—")
                d3.metric("Long stop (ATR)", _m(last.get("long_stop"), "{:.2f}"))
                chart_cols = [c for c in ["close", "bb_upper", "bb_lower", "kc_upper", "kc_lower"] if c in report["tech"].columns]
                if chart_cols:
                    plot_df = report["tech"][["date"] + chart_cols].tail(60).set_index("date")
                    st.line_chart(plot_df)
            with rs_t:
                st.markdown(f"**Stage:** {stage.get('stage', '—')} · {stage.get('signal', '')}")
                rs = report.get("rs") or {}
                if rs.get("error"):
                    st.caption(f"RS vs market median skipped: {rs['error']}")
                else:
                    r1, r2, r3, r4 = st.columns(4)
                    r1.metric("RS grade", str(rs.get("rs_grade") or "—"))
                    r2.metric("RS rating", f"{float(rs.get('rs_rating') or 0):.0f}")
                    r3.metric("RS 20D", f"{float(rs.get('rs_20d') or 0):+.1f}%")
                    r4.metric("RS momentum", f"{float(rs.get('rs_momentum_score') or 0):.0f}")
            with risk_t:
                risk = report.get("risk") or {}
                if not risk:
                    st.info("Not enough returns for risk metrics.")
                else:
                    e1, e2, e3, e4 = st.columns(4)
                    e1.metric("Sharpe", f"{float(risk.get('sharpe_ratio') or 0):.2f}")
                    e2.metric("Sortino", f"{float(risk.get('sortino_ratio') or 0):.2f}")
                    e3.metric("Max DD", f"{float(risk.get('max_drawdown') or 0)*100:.1f}%")
                    e4.metric("Win rate", f"{float(risk.get('win_rate') or 0)*100:.0f}%")

with thesis_tab:
    t_left, t_right = st.columns([2, 1])
    with t_left:
        pick = st.selectbox(
            "Stock",
            options=detail_options or [""],
            index=detail_options.index(selected_symbol) if selected_symbol in detail_options else 0,
        )
    with t_right:
        load_funda = st.button("Load full fundamentals", width="stretch")

    if pick and pick in snapshot["SYMBOL"].values:
        row = snapshot.loc[snapshot["SYMBOL"] == pick].iloc[0]
        thesis = thesis_for_row(row, last_dt)
        head_l, head_r = st.columns([3, 1])
        with head_l:
            st.markdown(f"## {pick}")
            st.caption(thesis["name"])
            signal_badge(thesis["signal"])
        with head_r:
            st.metric("Conviction", f"{float(row['ACCUM_SCORE']):.0f}" if pd.notna(row.get("ACCUM_SCORE")) else "—", border=True)

        st.info(thesis["headline"])
        st.markdown(f"**What to do:** {thesis['action']}")

        kcols = st.columns(4, border=True)
        kcols[0].metric(
            "Delivery",
            f"{float(row['DELIV_PER']):.0f}%" if pd.notna(row.get("DELIV_PER")) else "—",
            delta_20d(row),
        )
        kcols[1].metric("Deliv value", f"₹{float(row['DELIV_VALUE_CR']):.1f} Cr" if pd.notna(row.get("DELIV_VALUE_CR")) else "—")
        kcols[2].metric("Volume", f"{float(row['VOL_VS_AVG']):.2f}×" if pd.notna(row.get("VOL_VS_AVG")) else "—")
        kcols[3].metric(
            "5D / RSI",
            f"{float(row['CHG_5D']):+.1f}%" if pd.notna(row.get("CHG_5D")) else "—",
            f"RSI {float(row['RSI_14']):.0f}" if pd.notna(row.get("RSI_14")) else None,
        )

        c_why, c_risk, c_check = st.columns(3, border=True)
        with c_why:
            st.markdown("**Why this prints**")
            for line in thesis["why"]:
                st.markdown(f"- {line}")
        with c_risk:
            st.markdown("**What can go wrong**")
            for line in thesis["risks"]:
                st.markdown(f"- {line}")
        with c_check:
            st.markdown("**Checklist**")
            for label, status in thesis["checks"].items():
                if status == "Pass":
                    mark = ":green-badge[Pass]"
                elif status == "Fail":
                    mark = ":red-badge[Fail]"
                elif status == "n/a":
                    mark = ":blue-badge[n/a]"
                else:
                    mark = ":orange-badge[Watch]"
                st.markdown(f"{mark} {label}")

        hist = with_ind[with_ind["SYMBOL"] == pick].sort_values("TRADE_DATE")
        if hist.empty:
            st.warning("No history in the current lookback.")
        else:
            st.plotly_chart(build_price_chart(hist, pick), width="stretch")
            with st.expander("Last 20 sessions"):
                tail = hist.tail(20)[
                    [
                        c
                        for c in [
                            "TRADE_DATE",
                            "CLOSE_PRICE",
                            "CHG_1D",
                            "DELIV_PER",
                            "DELIV_PER_AVG_20",
                            "DELIV_VS_AVG",
                            "VOL_VS_AVG",
                            "RSI_14",
                        ]
                        if c in hist.columns
                    ]
                ].copy()
                tail["TRADE_DATE"] = pd.to_datetime(tail["TRADE_DATE"]).dt.date
                st.dataframe(tail, width="stretch", hide_index=True)

        if load_funda:
            with st.spinner(f"Yahoo {pick}.NS…"):
                try:
                    info = fetch_fundamentals(pick)
                except Exception as exc:
                    info = {"error": str(exc)}
            if not info or "error" in info:
                st.warning(info.get("error", "No fundamentals returned."))
            else:
                f1, f2, f3, f4 = st.columns(4)
                f1.metric("Market cap", fmt_cap(info.get("marketCap")), border=True)
                f2.metric("Trailing PE", f"{info['trailingPE']:.1f}" if info.get("trailingPE") else "—", border=True)
                f3.metric("P/B", f"{info['priceToBook']:.2f}" if info.get("priceToBook") else "—", border=True)
                f4.metric("ROE", fmt_pct(info.get("returnOnEquity")), border=True)
                g1, g2, g3, g4 = st.columns(4)
                g1.metric("Profit margin", fmt_pct(info.get("profitMargins")))
                g2.metric("Op. margin", fmt_pct(info.get("operatingMargins")))
                g3.metric("52w high", f"{info['fiftyTwoWeekHigh']:.2f}" if info.get("fiftyTwoWeekHigh") else "—")
                g4.metric("52w low", f"{info['fiftyTwoWeekLow']:.2f}" if info.get("fiftyTwoWeekLow") else "—")
                st.caption(f"{info.get('sector', '')} · {info.get('industry', '')}")

        stock_deals = deals[deals["SYMBOL"] == pick] if not deals.empty else deals
        pit = load_cached_promoters()
        stock_pit = pit[pit["SYMBOL"] == pick] if pit is not None and not pit.empty else pd.DataFrame()
        news = load_cached_announcements()
        stock_news = news[news["SYMBOL"] == pick] if news is not None and not news.empty else pd.DataFrame()
        with st.expander("90-day disclosed flow and headlines"):
            f1, f2, f3, f4 = st.columns(4)
            f1.metric("Net disclosed", f"₹{float(row.get('NET_DISCLOSED_CR') or 0):.1f} Cr")
            f2.metric("Cumulative buys", f"₹{float(row.get('CUMULATIVE_BUY_CR') or 0):.1f} Cr")
            f3.metric("Promoter net", f"₹{float(row.get('NET_PROMOTER_CR') or 0):.1f} Cr")
            f4.metric("News sentiment", f"{float(row.get('NEWS_SENTIMENT') or 0):+.2f}")
            st.caption(str(row.get("ALIGNMENT") or "Mixed / quiet"))
            if stock_deals is not None and not stock_deals.empty:
                st.markdown("**Bulk / block**")
                show = stock_deals.sort_values("DEAL_DATE", ascending=False)
                keep = [
                    c
                    for c in ["DEAL_DATE", "DEAL_TYPE", "CLIENT_NAME", "CLIENT_TYPE", "SIDE", "QUANTITY", "PRICE", "VALUE_CR"]
                    if c in show.columns
                ]
                st.dataframe(show[keep], width="stretch", hide_index=True)
            if not stock_pit.empty:
                st.markdown("**Promoter PIT**")
                st.dataframe(stock_pit.sort_values("DEAL_DATE", ascending=False), width="stretch", hide_index=True)
            if not stock_news.empty:
                st.markdown("**Latest NSE announcements**")
                heads = stock_news.sort_values("ANN_DATE", ascending=False).head(5)
                keep = [
                    c
                    for c in ["ANN_DATE", "SUBJECT", "DETAILS", "SENTIMENT_LABEL", "ATTACHMENT"]
                    if c in heads.columns
                ]
                st.dataframe(
                    heads[keep],
                    width="stretch",
                    hide_index=True,
                    column_config={"ATTACHMENT": st.column_config.LinkColumn("Attachment")},
                )
    else:
        st.info("Pick a stock from search, jump, or the board.")

with guide_tab:
    st.markdown(
        """
**Read the tape, then the business.** High delivery % only matters if the stock is liquid and volume confirms.

1. **Strong accumulation** — delivery around 55%+, above its 20-day average, volume ≥ 1.3×, price not falling, RSI not overbought. Shortlist.
2. **Quiet accumulation** — several sessions of above-average delivery without a blow-off. Watch for a dip toward the 20DMA.
3. **Dip absorption** — price is down, delivery and volume are up. Could be buying the dip or panic. Starter size only.
4. **Overheated / speculative / distribution** — do not chase. Delivery without volume, or volume without delivery, is a trap.
5. **Illiquid / thin tape** — ignore 100% delivery on tiny turnover. That is not institutions.

Conviction blends delivery level, delivery vs average, volume, 5-day price, and bulk/block deals, then **penalises illiquid names**.

**Trackers** rank *disclosed* buying (bulk/block client, promoter SAST, MF-tagged names) plus [NSE corporate announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements) with keyword sentiment. That is not official FII/DII stock-wise data.

This is a research screen, not a recommendation. Check results, shareholding, and news before you invest.

**Institutional tab** adds Connors RSI, ADX, CMF, ATR stops, RS grade vs the market median, Weinstein stage, and Sharpe/Sortino on the selected stock’s cached NSE history.
        """
    )
