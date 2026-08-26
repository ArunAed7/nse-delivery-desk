from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ScreenFilters:
    search: str = ""
    min_deliv_per: float | None = None
    max_deliv_per: float | None = None
    min_deliv_vs_avg: float | None = None
    min_vol_vs_avg: float | None = None
    min_deliv_qty_vs_avg: float | None = None
    min_turnover: float | None = None
    min_market_cap_cr: float | None = None
    rsi_min: float | None = None
    rsi_max: float | None = None
    min_chg_5d: float | None = None
    max_chg_5d: float | None = None
    above_sma20: bool = False
    above_sma50: bool = False
    sma20_gt_sma50: bool = False
    bulk_or_block_only: bool = False
    investable_only: bool = False
    signal: str = "All"
    preset: str = "None"
    sectors: tuple[str, ...] | None = None


def apply_preset(filters: ScreenFilters) -> ScreenFilters:
    preset = filters.preset
    if preset == "Delivery accumulation":
        filters.min_deliv_per = filters.min_deliv_per or 50
        filters.min_vol_vs_avg = filters.min_vol_vs_avg or 1.5
        filters.min_chg_5d = 0 if filters.min_chg_5d is None else filters.min_chg_5d
    elif preset == "Delivery spike vs average":
        filters.min_deliv_vs_avg = filters.min_deliv_vs_avg or 1.2
        filters.min_vol_vs_avg = filters.min_vol_vs_avg or 1.2
    elif preset == "Uptrend, not overbought":
        filters.above_sma20 = True
        filters.sma20_gt_sma50 = True
        filters.rsi_min = 30 if filters.rsi_min is None else filters.rsi_min
        filters.rsi_max = 55 if filters.rsi_max is None else filters.rsi_max
    return filters


def apply_filters(snapshot: pd.DataFrame, filters: ScreenFilters) -> pd.DataFrame:
    df = snapshot.copy()
    filters = apply_preset(filters)
    if filters.search:
        q = filters.search.strip().upper()
        name = df["NAME"].astype(str).str.upper() if "NAME" in df.columns else ""
        df = df[
            df["SYMBOL"].str.contains(q, na=False, regex=False)
            | name.str.contains(q, na=False, regex=False)
        ]
    if filters.min_deliv_per is not None:
        df = df[df["DELIV_PER"] >= filters.min_deliv_per]
    if filters.max_deliv_per is not None:
        df = df[df["DELIV_PER"] <= filters.max_deliv_per]
    if filters.min_deliv_vs_avg is not None:
        df = df[df["DELIV_VS_AVG"] >= filters.min_deliv_vs_avg]
    if filters.min_vol_vs_avg is not None:
        df = df[df["VOL_VS_AVG"] >= filters.min_vol_vs_avg]
    if filters.min_deliv_qty_vs_avg is not None:
        df = df[df["DELIV_QTY_VS_AVG"] >= filters.min_deliv_qty_vs_avg]
    if filters.min_turnover is not None:
        df = df[df["TURNOVER_LACS"] >= filters.min_turnover]
    if filters.min_market_cap_cr is not None and "MARKET_CAP_CR" in df.columns:
        df = df[df["MARKET_CAP_CR"] >= filters.min_market_cap_cr]
    if filters.rsi_min is not None:
        df = df[df["RSI_14"] >= filters.rsi_min]
    if filters.rsi_max is not None:
        df = df[df["RSI_14"] <= filters.rsi_max]
    if filters.min_chg_5d is not None:
        df = df[df["CHG_5D"] >= filters.min_chg_5d]
    if filters.max_chg_5d is not None:
        df = df[df["CHG_5D"] <= filters.max_chg_5d]
    if filters.above_sma20:
        df = df[df["ABOVE_SMA20"] == True]  # noqa: E712
    if filters.above_sma50:
        df = df[df["ABOVE_SMA50"] == True]  # noqa: E712
    if filters.sma20_gt_sma50:
        df = df[df["SMA20_GT_SMA50"] == True]  # noqa: E712
    if filters.bulk_or_block_only and "HAS_DEAL" in df.columns:
        df = df[df["HAS_DEAL"] == True]  # noqa: E712
    if filters.investable_only and "INVESTABLE" in df.columns:
        df = df[df["INVESTABLE"] == True]  # noqa: E712
    if filters.signal and filters.signal != "All" and "SIGNAL" in df.columns:
        df = df[df["SIGNAL"] == filters.signal]
    if filters.sectors and "SECTOR" in df.columns:
        wanted = {s for s in filters.sectors if s}
        if wanted:
            df = df[df["SECTOR"].isin(wanted)]
    return df.reset_index(drop=True)
