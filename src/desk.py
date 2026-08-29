from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.deals import deal_flags, load_cached_deals
from src.fundamentals import load_cached_market_caps, load_cached_pe
from src.indicators import add_indicators, latest_snapshot
from src.insights import classify_snapshot, market_pulse
from src.nse_data import cache_fingerprint, latest_cached_date, load_history
from src.sectors import attach_sectors
from src.trackers import build_flow_book
from src.universe import load_universe

FLOW_COLS = [
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


def assemble_desk(lookback: int, series: list[str]) -> dict:
    cache_sig = cache_fingerprint()
    universe = cached_universe(("EQ", "BE"))
    history_days = max(int(lookback), 63)
    history = cached_history(history_days, cache_sig)
    last_dt = latest_cached_date()
    empty = {
        "universe": universe,
        "history": history,
        "with_ind": pd.DataFrame(),
        "snapshot": pd.DataFrame(),
        "deals": pd.DataFrame(),
        "flow_book": pd.DataFrame(),
        "last_dt": last_dt,
        "pulse": pd.Series(dtype=float),
        "series": series,
    }
    if history.empty:
        return empty
    history = history.merge(universe[["SYMBOL", "SERIES", "NAME"]], on=["SYMBOL", "SERIES"], how="inner")
    if history.empty:
        history = cached_history(history_days, cache_sig).merge(universe[["SYMBOL", "NAME"]], on="SYMBOL", how="inner")
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
    span = with_ind.groupby("SYMBOL")["CLOSE_PRICE"].agg(["first", "last"])
    span["CHG_LOOKBACK"] = span["last"] / span["first"] - 1
    snapshot = snapshot.merge(span[["CHG_LOOKBACK"]].reset_index(), on="SYMBOL", how="left")
    snapshot["CHG_1Y"] = snapshot["CHG_LOOKBACK"]
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
    keep = [c for c in FLOW_COLS if c in flow_book.columns]
    if not flow_book.empty and keep:
        snapshot = snapshot.merge(flow_book[keep], on="SYMBOL", how="left")
    for col in ("HEAT", "NEWS_SENTIMENT"):
        if col not in snapshot.columns:
            snapshot[col] = 0.0
        else:
            snapshot[col] = snapshot[col].fillna(0)
    # Leave NET_DISCLOSED_CR / CUMULATIVE_BUY_CR as NA when the name has no disclosed prints.
    if series:
        wanted = {s.upper() for s in series}
        snapshot = snapshot[snapshot["SERIES"].isin(wanted)].copy() if "SERIES" in snapshot.columns else snapshot
    pulse = market_pulse(history)
    return {
        "universe": universe,
        "history": history,
        "with_ind": with_ind,
        "snapshot": snapshot,
        "deals": deals,
        "flow_book": flow_book,
        "last_dt": last_dt,
        "pulse": pulse,
        "series": series,
    }


def symbol_history(desk: dict, symbol: str) -> pd.DataFrame:
    hist = desk.get("with_ind", pd.DataFrame())
    if hist.empty or not symbol:
        return pd.DataFrame()
    return hist[hist["SYMBOL"] == symbol].sort_values("TRADE_DATE")


def snapshot_row(desk: dict, symbol: str) -> pd.Series | None:
    snap = desk.get("snapshot", pd.DataFrame())
    if snap.empty or not symbol or symbol not in snap["SYMBOL"].values:
        return None
    return snap.loc[snap["SYMBOL"] == symbol].iloc[0]
