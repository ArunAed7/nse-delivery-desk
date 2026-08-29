"""Investment-grade overlays on the NSE delivery snapshot.

Every score here is derived from bhavcopy, NSE PE, and disclosed bulk/block.
Nothing is labelled FII/DII or a filing-based F-score.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[col], errors="coerce")


def cross_sectional_percentile(series: pd.Series, mask: pd.Series | None = None) -> pd.Series:
    """1–99 rank among `mask` (default: all finite values). Others stay NA."""
    out = pd.Series(np.nan, index=series.index)
    s = pd.to_numeric(series, errors="coerce")
    use = s.notna() if mask is None else mask.fillna(False) & s.notna()
    if int(use.sum()) < 5:
        return out
    ranks = s[use].rank(method="average", pct=True)
    out.loc[use] = (ranks * 98 + 1).clip(1, 99)
    return out


def enrich_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    liquid = out.get("INVESTABLE", pd.Series(False, index=out.index)).fillna(False).astype(bool)
    unreliable = out.get("PRICE_UNRELIABLE", pd.Series(False, index=out.index)).fillna(False).astype(bool)
    t2t = out["SERIES"].eq("BE") if "SERIES" in out.columns else pd.Series(False, index=out.index)

    deliv = _num(out, "DELIV_PER")
    vs20 = _num(out, "DELIV_VS_AVG")
    vol = _num(out, "VOL_VS_AVG")
    rsi = _num(out, "RSI_14")
    streak = _num(out, "HIGH_DELIV_STREAK").fillna(0)
    turn = _num(out, "TURNOVER_CR")
    mcap = _num(out, "MARKET_CAP_CR")
    pe = _num(out, "PE")
    above20 = out.get("ABOVE_SMA20", pd.Series(False, index=out.index)).fillna(False)
    has_deal = out.get("HAS_DEAL", pd.Series(False, index=out.index)).fillna(False).astype(bool)
    signal = out.get("SIGNAL", pd.Series("", index=out.index)).astype(str)

    score = pd.Series(0.0, index=out.index)
    score = score + np.where(liquid, 20, 0)
    score = score + np.where(~t2t & deliv.ge(55), 15, np.where(~t2t & deliv.ge(50), 8, 0))
    score = score + np.where(~t2t & vs20.ge(1.15), 15, np.where(~t2t & vs20.ge(1.05), 6, 0))
    score = score + np.where(vol.ge(1.3), 15, np.where(vol.ge(1.1), 6, 0))
    score = score + np.where(above20, 10, 0)
    score = score + np.where(rsi.between(40, 65), 10, np.where(rsi.lt(70), 4, 0))
    score = score + np.where(~unreliable, 10, 0)
    score = score + np.where(has_deal, 8, 0)
    score = score + np.where(streak.ge(3), 5, 0)
    score = score - np.where(signal.eq("Overheated"), 18, 0)
    score = score - np.where(signal.isin(["Speculative", "Distribution risk"]), 15, 0)
    score = score - np.where(unreliable, 25, 0)
    out["SETUP_QUALITY"] = score.clip(0, 100)

    out["RS_20D_PCT"] = cross_sectional_percentile(_num(out, "CHG_20D"), liquid)

    def _sec_rank(s: pd.Series) -> pd.Series:
        m = liquid.reindex(s.index).fillna(False)
        return cross_sectional_percentile(s, m)

    if "SECTOR" in out.columns and "CHG_20D" in out.columns:
        out["RS_SECTOR_PCT"] = out.groupby("SECTOR", group_keys=False)["CHG_20D"].transform(_sec_rank)
    else:
        out["RS_SECTOR_PCT"] = pd.NA

    if "SECTOR" in out.columns and pe.notna().any():
        sec_pe = out.groupby("SECTOR")["PE"].transform("median")
        out["PE_VS_SECTOR"] = pe / sec_pe.replace(0, np.nan)
    else:
        out["PE_VS_SECTOR"] = pd.NA

    liq_cap = (0.08 * turn).clip(lower=0)
    mcap_cap = (0.005 * mcap).where(mcap.gt(0), np.nan)
    size = pd.concat([liq_cap, mcap_cap], axis=1).min(axis=1)
    size = size.mask(~liquid | unreliable | t2t, 0)
    out["SIZE_CAP_CR"] = size.round(2)
    out["INVALIDATION"] = np.where(
        liquid,
        "Close below 20DMA, or delivery vs 20D average < 0.95 for two sessions",
        "Do not size — tape is not liquid.",
    )

    act = (
        liquid
        & ~unreliable
        & ~t2t
        & out["SETUP_QUALITY"].ge(70)
        & signal.isin(["Strong accumulation", "Quiet accumulation", "Dip absorption"])
    )
    watch = liquid & ~unreliable & out["SETUP_QUALITY"].ge(55) & ~act
    out["CONVICTION"] = np.where(act, "Act", np.where(watch, "Watch", "Avoid"))
    return out


def suggest_book(snapshot: pd.DataFrame, n: int = 8, max_weight: float = 0.15, capital_cr: float = 100.0) -> pd.DataFrame:
    """Equal-cap, liquidity-capped book from Act/Watch names."""
    if snapshot is None or snapshot.empty or "SETUP_QUALITY" not in snapshot.columns:
        return pd.DataFrame()
    work = snapshot.copy()
    if "PRICE_UNRELIABLE" in work.columns:
        work = work[~work["PRICE_UNRELIABLE"].fillna(False)]
    prefer = work[work["CONVICTION"].isin(["Act", "Watch"])] if "CONVICTION" in work.columns else work
    if prefer.empty:
        prefer = work[work.get("INVESTABLE", False) == True]  # noqa: E712
    prefer = prefer.sort_values(["SETUP_QUALITY", "ACCUM_SCORE"], ascending=False).head(n)
    if prefer.empty:
        return prefer
    caps = pd.to_numeric(prefer["SIZE_CAP_CR"], errors="coerce").fillna(0).clip(lower=0).to_numpy()
    equal = capital_cr / max(len(prefer), 1)
    notionals = np.minimum(caps, equal)
    notionals = np.minimum(notionals, max_weight * capital_cr)
    weights = notionals / capital_cr
    cols = [
        c
        for c in [
            "SYMBOL",
            "NAME",
            "SECTOR",
            "SIGNAL",
            "CONVICTION",
            "SETUP_QUALITY",
            "RS_20D_PCT",
            "SIZE_CAP_CR",
            "CLOSE_PRICE",
            "INVALIDATION",
        ]
        if c in prefer.columns
    ]
    out = prefer[cols].copy()
    out["WEIGHT"] = weights
    out["NOTIONAL_CR"] = notionals.round(2)
    out.attrs["cash_weight"] = max(0.0, 1.0 - float(out["WEIGHT"].sum()))
    return out.reset_index(drop=True)


def delivery_setup_signal(hist: pd.DataFrame) -> pd.Series:
    """Next-bar long when delivery > own 20D avg, volume confirms, price > 20DMA."""
    if hist is None or hist.empty:
        return pd.Series(dtype=float)
    work = hist.sort_values("TRADE_DATE") if "TRADE_DATE" in hist.columns else hist
    close = pd.to_numeric(work.get("CLOSE_PRICE", work.get("Close")), errors="coerce")
    sma = pd.to_numeric(work.get("SMA_20"), errors="coerce")
    if sma.isna().all():
        sma = close.rolling(20, min_periods=10).mean()
    deliv = pd.to_numeric(work.get("DELIV_PER"), errors="coerce")
    davg = pd.to_numeric(work.get("DELIV_PER_AVG_20"), errors="coerce")
    vol = pd.to_numeric(work.get("VOL_VS_AVG"), errors="coerce")
    ok = deliv.gt(davg) & vol.ge(1.2) & close.gt(sma)
    idx = pd.to_datetime(work["TRADE_DATE"]) if "TRADE_DATE" in work.columns else work.index
    return pd.Series(np.where(ok.fillna(False), 1, 0), index=idx)


def max_pain_strike(oi: pd.DataFrame) -> float:
    """Expiry max pain: strike K minimising call+put intrinsic × OI if spot settles at K."""
    if oi is None or oi.empty:
        return float("nan")
    strikes = pd.to_numeric(oi["Strike"], errors="coerce")
    ce = pd.to_numeric(oi.get("CE_OI"), errors="coerce").fillna(0).to_numpy()
    pe = pd.to_numeric(oi.get("PE_OI"), errors="coerce").fillna(0).to_numpy()
    k = strikes.to_numpy()
    valid = np.isfinite(k)
    k, ce, pe = k[valid], ce[valid], pe[valid]
    if len(k) == 0:
        return float("nan")
    pain = []
    for settle in k:
        call_payout = np.maximum(k - settle, 0) * ce
        put_payout = np.maximum(settle - k, 0) * pe
        pain.append(float(call_payout.sum() + put_payout.sum()))
    return float(k[int(np.argmin(pain))])


def oi_buildup(oi: pd.DataFrame, pct: float = 0.10) -> pd.DataFrame:
    """Call/put OI change vs existing OI — not LTP.pct_change across strikes."""
    if oi is None or oi.empty:
        return pd.DataFrame()
    df = oi.copy()
    ce_oi = pd.to_numeric(df.get("CE_OI"), errors="coerce").replace(0, np.nan)
    pe_oi = pd.to_numeric(df.get("PE_OI"), errors="coerce").replace(0, np.nan)
    ce_ch = pd.to_numeric(df.get("CE_Chng"), errors="coerce").fillna(0)
    pe_ch = pd.to_numeric(df.get("PE_Chng"), errors="coerce").fillna(0)
    ce_pct = ce_ch / ce_oi.abs()
    pe_pct = pe_ch / pe_oi.abs()
    df["CE_Signal"] = "Neutral"
    df.loc[ce_pct.gt(pct), "CE_Signal"] = "Call OI up"
    df.loc[ce_pct.lt(-pct), "CE_Signal"] = "Call OI down"
    df["PE_Signal"] = "Neutral"
    df.loc[pe_pct.gt(pct), "PE_Signal"] = "Put OI up"
    df.loc[pe_pct.lt(-pct), "PE_Signal"] = "Put OI down"
    keep = [c for c in ["Strike", "CE_OI", "PE_OI", "CE_Chng", "PE_Chng", "CE_Signal", "PE_Signal"] if c in df.columns]
    return df[keep]
