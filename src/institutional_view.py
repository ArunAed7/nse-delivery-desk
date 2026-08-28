from __future__ import annotations

import pandas as pd

from src.macro_liquidity import MacroRegimeDetector
from src.portfolio_risk import calculate_risk_metrics
from src.relative_strength_pro import generate_rs_report, stage_analysis
from src.technical_pro import add_momentum_indicators, add_volatility_indicators, generate_momentum_signals


def history_to_ohlcv(hist: pd.DataFrame) -> pd.DataFrame:
    work = hist.copy().sort_values("TRADE_DATE")
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(work["TRADE_DATE"]),
            "open": pd.to_numeric(work["OPEN_PRICE"], errors="coerce"),
            "high": pd.to_numeric(work["HIGH_PRICE"], errors="coerce"),
            "low": pd.to_numeric(work["LOW_PRICE"], errors="coerce"),
            "close": pd.to_numeric(work["CLOSE_PRICE"], errors="coerce"),
            "volume": pd.to_numeric(work["TTL_TRD_QNTY"], errors="coerce"),
        }
    )
    return out.dropna(subset=["close"]).reset_index(drop=True)


def market_close_proxy(history: pd.DataFrame) -> pd.Series:
    if history.empty:
        return pd.Series(dtype=float)
    dates = pd.to_datetime(history["TRADE_DATE"])
    return (
        history.assign(_dt=dates.dt.normalize())
        .groupby("_dt")["CLOSE_PRICE"]
        .median()
        .sort_index()
    )


def analyze_symbol(hist: pd.DataFrame, market: pd.Series | None = None) -> dict:
    ohlcv = history_to_ohlcv(hist)
    if ohlcv.empty or len(ohlcv) < 30:
        return {"ok": False, "reason": "Need at least 30 sessions of price history."}
    tech = add_momentum_indicators(ohlcv)
    tech = add_volatility_indicators(tech)
    signals = generate_momentum_signals(tech)
    last = tech.iloc[-1]
    sig = signals.iloc[-1]
    stage = stage_analysis(ohlcv["close"], ohlcv["volume"])
    rs = {}
    if market is not None and len(market) >= 20:
        aligned = ohlcv.set_index("date")["close"]
        bench = market.reindex(aligned.index).ffill()
        try:
            rs = generate_rs_report(
                str(hist["SYMBOL"].iloc[0]) if "SYMBOL" in hist.columns else "",
                ohlcv.set_index("date"),
                bench,
            )
        except Exception as exc:
            rs = {"error": str(exc)}
    rets = ohlcv["close"].pct_change().dropna()
    risk = calculate_risk_metrics(rets) if len(rets) > 10 else {}
    return {
        "ok": True,
        "ohlcv": ohlcv,
        "tech": tech,
        "last": last,
        "signals": sig,
        "stage": stage,
        "rs": rs,
        "risk": risk,
    }


def market_regime(history: pd.DataFrame) -> str:
    px = market_close_proxy(history)
    if len(px) < 50:
        return "Insufficient history"
    frame = pd.DataFrame({"Close": px})
    try:
        return MacroRegimeDetector().detect_regime(frame)
    except Exception:
        return "Unknown"


def sector_rotation(snapshot: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    if snapshot.empty or "SECTOR" not in snapshot.columns or "CHG_20D" not in snapshot.columns:
        return pd.DataFrame()
    agg = {
        "CHG_20D": ("CHG_20D", "median"),
        "NAMES": ("SYMBOL", "nunique"),
    }
    if "HEAT" in snapshot.columns:
        agg["HEAT"] = ("HEAT", "mean")
    g = snapshot.groupby("SECTOR", as_index=False).agg(**agg)
    return g.sort_values("CHG_20D", ascending=False).head(n)
