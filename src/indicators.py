from __future__ import annotations

import numpy as np
import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def add_indicators(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return history
    df = history.sort_values(["SYMBOL", "SERIES", "TRADE_DATE"]).copy()
    g = df.groupby(["SYMBOL", "SERIES"], sort=False)

    def roll(col: str, window: int, min_periods: int, how: str = "mean") -> pd.Series:
        r = g[col].rolling(window, min_periods=min_periods)
        out = r.mean() if how == "mean" else r.max()
        return out.droplevel([0, 1])

    df["SMA_20"] = roll("CLOSE_PRICE", 20, 10)
    df["SMA_50"] = roll("CLOSE_PRICE", 50, 20)
    df["DELIV_PER_AVG_1W"] = roll("DELIV_PER", 5, 3)
    df["DELIV_PER_AVG_5"] = df["DELIV_PER_AVG_1W"]
    df["DELIV_PER_AVG_20"] = roll("DELIV_PER", 20, 10)
    df["DELIV_PER_AVG_1M"] = roll("DELIV_PER", 21, 12)
    df["DELIV_PER_AVG_3M"] = roll("DELIV_PER", 63, 40)
    df["DELIV_QTY_AVG_1W"] = roll("DELIV_QTY", 5, 3)
    df["DELIV_QTY_AVG_20"] = roll("DELIV_QTY", 20, 10)
    df["DELIV_QTY_AVG_1M"] = roll("DELIV_QTY", 21, 12)
    df["DELIV_QTY_AVG_3M"] = roll("DELIV_QTY", 63, 40)
    df["VOL_AVG_1W"] = roll("TTL_TRD_QNTY", 5, 3)
    df["VOL_AVG_20"] = roll("TTL_TRD_QNTY", 20, 10)
    df["VOL_AVG_1M"] = roll("TTL_TRD_QNTY", 21, 12)
    df["VOL_AVG_3M"] = roll("TTL_TRD_QNTY", 63, 40)
    df["RSI_14"] = g["CLOSE_PRICE"].transform(_rsi)
    df["CHG_1D"] = g["CLOSE_PRICE"].pct_change(1) * 100
    df["CHG_5D"] = g["CLOSE_PRICE"].pct_change(5) * 100
    df["CHG_20D"] = g["CLOSE_PRICE"].pct_change(20) * 100
    df["HIGH_20"] = roll("HIGH_PRICE", 20, 10, how="max")
    df["HIGH_LOOKBACK"] = g["HIGH_PRICE"].expanding(min_periods=10).max().droplevel([0, 1])

    df["DELIV_VS_AVG"] = df["DELIV_PER"] / df["DELIV_PER_AVG_20"]
    df["DELIV_VS_1W"] = df["DELIV_PER"] / df["DELIV_PER_AVG_1W"]
    df["DELIV_VS_3M"] = df["DELIV_PER"] / df["DELIV_PER_AVG_3M"]
    df["DELIV_QTY_VS_AVG"] = df["DELIV_QTY"] / df["DELIV_QTY_AVG_20"]
    df["VOL_VS_AVG"] = df["TTL_TRD_QNTY"] / df["VOL_AVG_20"]
    df["VOL_VS_1W"] = df["TTL_TRD_QNTY"] / df["VOL_AVG_1W"]
    df["DELIV_VALUE_CR"] = df["DELIV_QTY"] * df["CLOSE_PRICE"] / 1e7
    df["TURNOVER_CR"] = df["TURNOVER_LACS"] / 100.0
    df["ABOVE_SMA20"] = df["CLOSE_PRICE"] >= df["SMA_20"]
    df["ABOVE_SMA50"] = df["CLOSE_PRICE"] >= df["SMA_50"]
    df["SMA20_GT_SMA50"] = df["SMA_20"] >= df["SMA_50"]
    df["PCT_VS_SMA20"] = (df["CLOSE_PRICE"] / df["SMA_20"] - 1) * 100
    df["PCT_FROM_HIGH"] = (df["CLOSE_PRICE"] / df["HIGH_LOOKBACK"] - 1) * 100
    df["PCT_FROM_20H"] = (df["CLOSE_PRICE"] / df["HIGH_20"] - 1) * 100
    trend = np.where(
        df["SMA20_GT_SMA50"] & df["ABOVE_SMA20"],
        "Uptrend",
        np.where(df["ABOVE_SMA20"], "Above 20DMA", "Below 20DMA"),
    )
    df["TREND"] = trend

    above_avg = (df["DELIV_PER"] >= df["DELIV_PER_AVG_20"]).fillna(False)
    group_key = df["SYMBOL"].astype(str) + "|" + df["SERIES"].astype(str)
    streak_block = (~above_avg).groupby(group_key, sort=False).cumsum()
    df["HIGH_DELIV_STREAK"] = above_avg.groupby([group_key, streak_block], sort=False).cumsum()

    deliv_leg = ((df["DELIV_PER"] - 40) / 40).clip(0, 1)
    deliv_spike = ((df["DELIV_VS_AVG"] - 1) / 1).clip(0, 1)
    vol_spike = ((df["VOL_VS_AVG"] - 1) / 1.5).clip(0, 1)
    price_ok = ((df["CHG_5D"]) / 8).clip(0, 1)
    df["ACCUM_SCORE"] = (
        30 * deliv_leg.fillna(0)
        + 25 * deliv_spike.fillna(0)
        + 25 * vol_spike.fillna(0)
        + 20 * price_ok.fillna(0)
    )
    return df


def latest_snapshot(history_with_indicators: pd.DataFrame) -> pd.DataFrame:
    if history_with_indicators.empty:
        return history_with_indicators
    df = history_with_indicators.sort_values(["SYMBOL", "SERIES", "TRADE_DATE"])
    snap = df.groupby(["SYMBOL", "SERIES"], as_index=False).tail(1).reset_index(drop=True)
    counts = df.groupby(["SYMBOL", "SERIES"]).size().rename("SESSIONS")
    snap = snap.merge(counts.reset_index(), on=["SYMBOL", "SERIES"], how="left")
    chg = (
        pd.to_numeric(snap["CHG_5D"], errors="coerce")
        if "CHG_5D" in snap.columns
        else pd.Series(np.nan, index=snap.index)
    )
    sessions = pd.to_numeric(snap.get("SESSIONS"), errors="coerce").fillna(0)
    snap["PRICE_UNRELIABLE"] = (chg.abs() > 40) | (sessions < 8)
    return snap
