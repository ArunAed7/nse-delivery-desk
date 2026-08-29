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


def filters_from_state(f: dict | None, search: str = "") -> ScreenFilters:
    f = f or {}
    return ScreenFilters(
        search=search or "",
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
