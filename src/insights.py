from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def market_pulse(history: pd.DataFrame) -> pd.Series:
    if history.empty or "TRADE_DATE" not in history.columns:
        return pd.Series(dtype=float)
    dates = pd.to_datetime(history["TRADE_DATE"])
    return history.groupby(dates.dt.normalize())["DELIV_PER"].median().sort_index()


def classify_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    turnover = pd.to_numeric(out.get("TURNOVER_CR"), errors="coerce").fillna(0)
    deliv_val = pd.to_numeric(out.get("DELIV_VALUE_CR"), errors="coerce").fillna(0)
    deliv = pd.to_numeric(out.get("DELIV_PER"), errors="coerce")
    vs20 = pd.to_numeric(out.get("DELIV_VS_AVG"), errors="coerce")
    vs3m = pd.to_numeric(out.get("DELIV_VS_3M"), errors="coerce")
    vol = pd.to_numeric(out.get("VOL_VS_AVG"), errors="coerce")
    chg5 = pd.to_numeric(out.get("CHG_5D"), errors="coerce")
    rsi = pd.to_numeric(out.get("RSI_14"), errors="coerce")
    streak = pd.to_numeric(out.get("HIGH_DELIV_STREAK"), errors="coerce").fillna(0)
    pe = pd.to_numeric(out.get("PE"), errors="coerce") if "PE" in out.columns else pd.Series(np.nan, index=out.index)

    liquid = (turnover >= 5) | (deliv_val >= 2)
    thin = (~liquid) & ((turnover >= 0.5) | (deliv_val >= 0.2))
    out["LIQUIDITY"] = np.where(liquid, "Liquid", np.where(thin, "Thin", "Illiquid"))

    pe_med = pe.median(skipna=True)
    out["PE_VS_MKT"] = pe / pe_med if pd.notna(pe_med) and pe_med else pd.NA

    strong = (
        liquid
        & deliv.ge(55)
        & vs20.ge(1.15)
        & vol.ge(1.3)
        & chg5.ge(0)
        & rsi.fillna(50).lt(70)
    )
    overheated = (
        liquid
        & deliv.ge(55)
        & vs20.ge(1.1)
        & vol.ge(1.2)
        & (rsi.ge(70) | chg5.ge(8))
    )
    quiet = liquid & deliv.ge(50) & streak.ge(3) & chg5.ge(-2) & ~strong & ~overheated
    dip = liquid & deliv.ge(55) & vol.ge(1.4) & chg5.lt(0) & chg5.ge(-8) & ~strong
    speculative = liquid & vol.ge(1.5) & vs20.fillna(1).lt(0.9) & chg5.gt(2)
    distribution = liquid & vol.ge(1.3) & deliv.lt(40) & chg5.gt(3)

    signal = np.full(len(out), "Neutral", dtype=object)
    signal = np.where(~thin & ~liquid, "Illiquid", signal)
    signal = np.where(thin, "Thin tape", signal)
    signal = np.where(speculative, "Speculative", signal)
    signal = np.where(distribution, "Distribution risk", signal)
    signal = np.where(dip, "Dip absorption", signal)
    signal = np.where(quiet, "Quiet accumulation", signal)
    signal = np.where(overheated, "Overheated", signal)
    signal = np.where(strong, "Strong accumulation", signal)
    be = out["SERIES"].eq("BE") if "SERIES" in out.columns else pd.Series(False, index=out.index)
    t2t_surge = be & liquid & vol.ge(1.4) & chg5.ge(0)
    t2t_book = be & ~t2t_surge
    signal = np.where(t2t_surge, "T2T volume surge", signal)
    signal = np.where(t2t_book, "T2T (delivery n/a)", signal)
    out["SIGNAL"] = signal

    fake_hundred = deliv.ge(99) & turnover.lt(5)
    score = pd.to_numeric(out.get("ACCUM_SCORE"), errors="coerce").fillna(0)
    score = score.mask(~liquid, score * 0.45)
    score = score.mask(fake_hundred, score * 0.25)
    score = score.mask(out["SIGNAL"].eq("Overheated"), score * 0.85)
    out["ACCUM_SCORE"] = score.clip(0, 100)
    out["INVESTABLE"] = liquid & ~fake_hundred
    return out


def _fmt(value, digits: int = 1, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)) or pd.isna(value):
        return "—"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "—"


def thesis_for_row(row: pd.Series, as_of: date | None = None) -> dict:
    signal = str(row.get("SIGNAL") or "Neutral")
    name = str(row.get("NAME") or "")
    symbol = str(row.get("SYMBOL") or "")
    liquidity = str(row.get("LIQUIDITY") or "")
    headline = {
        "Strong accumulation": "Delivery is elevated, volume confirms, and price is holding up — the tape looks like genuine buying, not just a thin-market print.",
        "Quiet accumulation": "Delivery has stayed above its recent average for several sessions without a blow-off move. Worth tracking, not chasing.",
        "Dip absorption": "Price is down while delivery and volume are high. That can be smart-money buying the dip — or forced selling. Size smaller until price stabilises.",
        "Overheated": "Delivery is strong but RSI/price has already run. Wait for a pause; chasing here has a worse risk/reward.",
        "Speculative": "Volume is up but delivery is weak. More likely short-term trading than institutional positioning.",
        "Distribution risk": "Price is rising on low delivery. Upside may be speculative; not a delivery-led setup.",
        "Thin tape": "Turnover is too light to trust delivery %. One large order can fake the signal.",
        "Illiquid": "Avoid as a core idea. Delivery % on illiquid names is not an institutional footprint.",
        "T2T volume surge": "This is trade-to-trade: every trade is delivery, so 100% delivery is not a signal. Volume is elevated and price is holding — watch the book, not delivery %.",
        "T2T (delivery n/a)": "NSE does not report a separate delivery % for T2T names. Use volume, price and deals. Delivery % here is filled as 100% of traded quantity.",
    }.get(signal, "Review the checklist before acting.")

    why: list[str] = []
    deliv = row.get("DELIV_PER")
    vs20 = row.get("DELIV_VS_AVG")
    vs3m = row.get("DELIV_VS_3M")
    vol = row.get("VOL_VS_AVG")
    chg5 = row.get("CHG_5D")
    dval = row.get("DELIV_VALUE_CR")
    turn = row.get("TURNOVER_CR")
    streak = row.get("HIGH_DELIV_STREAK")
    rsi = row.get("RSI_14")
    pe = row.get("PE")
    pe_vs = row.get("PE_VS_MKT")
    trend = row.get("TREND")
    deals = bool(row.get("HAS_DEAL"))
    t2t = str(row.get("SERIES") or "") == "BE"
    if t2t:
        why.append("T2T / BE series: NSE typically does not publish DELIV_PER. Traded quantity is treated as delivered (100%).")

    if pd.notna(deliv):
        why.append(f"Last delivery {float(deliv):.0f}% vs 20D {_fmt(row.get('DELIV_PER_AVG_20'), 0)}% and 3M {_fmt(row.get('DELIV_PER_AVG_3M'), 0)}%.")
    if pd.notna(vs20):
        why.append(f"Delivery is {float(vs20):.2f}× the 20-day average" + (f" and {float(vs3m):.2f}× the 3-month average." if pd.notna(vs3m) else "."))
    if pd.notna(vol):
        why.append(f"Volume is {float(vol):.2f}× the 20-day average — {'confirms' if float(vol) >= 1.3 else 'does not confirm'} the delivery spike.")
    if pd.notna(dval) and pd.notna(turn):
        why.append(f"₹{float(dval):.1f} Cr was delivered on ₹{float(turn):.1f} Cr turnover ({liquidity.lower()} book).")
    if pd.notna(chg5):
        why.append(f"5-day price {float(chg5):+.1f}% with trend marked {trend}.")
    if pd.notna(streak) and float(streak) >= 2:
        why.append(f"Delivery has been above its 20D average for {int(streak)} sessions in a row.")
    if pd.notna(rsi):
        why.append(f"RSI(14) is {float(rsi):.0f} ({'overbought — avoid chasing' if float(rsi) >= 70 else 'not stretched' if float(rsi) <= 60 else 'getting extended'}).")
    if pd.notna(pe):
        vs = f", {float(pe_vs):.2f}× universe median PE" if pd.notna(pe_vs) else ""
        why.append(f"NSE PE {float(pe):.1f}{vs}. Delivery strength does not replace valuation.")
    if deals:
        why.append("Bulk/block deals printed in the lookback — extra evidence of large-lot activity, still not named FII/DII.")

    risks: list[str] = []
    if liquidity != "Liquid":
        risks.append("Liquidity is too low for a core position; slippage can wipe the edge.")
    if pd.notna(deliv) and float(deliv) >= 99 and (pd.isna(turn) or float(turn) < 5):
        risks.append("Near-100% delivery on small turnover is often a data artefact, not institutions.")
    if pd.notna(rsi) and float(rsi) >= 70:
        risks.append("Momentum is extended; a pullback is the higher-probability entry.")
    if pd.notna(chg5) and float(chg5) <= -8:
        risks.append("Sharp 5-day decline — high delivery may be panic, not accumulation.")
    if pd.notna(pe_vs) and float(pe_vs) >= 1.8:
        risks.append("Expensive vs the market PE; demand a stronger business case.")
    if signal in {"Speculative", "Distribution risk"}:
        risks.append("Price is moving without delivery support — easier to get trapped.")
    if not risks:
        risks.append("This is a screening signal, not a buy order. Check results, shareholding, and news.")

    action = {
        "Strong accumulation": "Add to a shortlist. Confirm 2–3 more sessions of high delivery and no breakdown below 20DMA before sizing in.",
        "Quiet accumulation": "Watchlist. Buy weakness toward 20DMA if delivery stays elevated.",
        "Dip absorption": "Probe only a starter quantity if you already like the business; wait for a higher low.",
        "Overheated": "Do not chase. Set an alert for RSI cooling or a 3–5% dip with delivery still high.",
        "Speculative": "Skip for delivery-based investing.",
        "Distribution risk": "Skip. Look elsewhere.",
        "Thin tape": "Ignore unless you trade microcaps professionally.",
        "Illiquid": "Ignore.",
        "T2T volume surge": "Treat as a volume/price setup, not a delivery setup. T2T already forces delivery.",
        "T2T (delivery n/a)": "Do not use delivery % here. If you like the stock, judge volume, trend and fundamentals only.",
        "Neutral": "No action. Keep filters on and scan the board.",
    }.get(signal, "No action.")

    checks = {
        "Delivery": "n/a" if t2t else ("Pass" if pd.notna(deliv) and float(deliv) >= 50 else "Weak"),
        "vs 20D avg": "n/a" if t2t else ("Pass" if pd.notna(vs20) and float(vs20) >= 1.15 else "Weak"),
        "Volume": "Pass" if pd.notna(vol) and float(vol) >= 1.3 else "Weak",
        "Trend": "Pass" if str(trend) in {"Uptrend", "Above 20DMA"} else "Weak",
        "Liquidity": "Pass" if liquidity == "Liquid" else "Fail",
        "Valuation": (
            "Pass"
            if pd.notna(pe_vs) and float(pe_vs) <= 1.3
            else "Watch"
            if pd.notna(pe)
            else "n/a"
        ),
        "Large deals": "Pass" if deals else "n/a",
    }

    badge = {
        "Strong accumulation": ("green", "check_circle"),
        "Quiet accumulation": ("blue", "visibility"),
        "Dip absorption": ("orange", "trending_down"),
        "Overheated": ("orange", "local_fire_department"),
        "Speculative": ("red", "warning"),
        "Distribution risk": ("red", "arrow_downward"),
        "Thin tape": ("gray", "hourglass_empty"),
        "Illiquid": ("red", "block"),
        "T2T volume surge": ("orange", "swap_vert"),
        "T2T (delivery n/a)": ("gray", "info"),
        "Neutral": ("gray", "remove"),
    }.get(signal, ("gray", "info"))

    return {
        "symbol": symbol,
        "name": name,
        "signal": signal,
        "headline": headline,
        "why": why,
        "risks": risks,
        "action": action,
        "checks": checks,
        "badge_color": badge[0],
        "badge_icon": badge[1],
        "as_of": as_of,
    }


def top_ideas(df: pd.DataFrame, n: int = 6) -> pd.DataFrame:
    if df.empty or "SIGNAL" not in df.columns:
        return df.head(0)
    prefer = df[df["SIGNAL"].isin(["Strong accumulation", "Quiet accumulation", "Dip absorption", "T2T volume surge"])]
    if prefer.empty:
        prefer = df[df.get("INVESTABLE", True) == True]  # noqa: E712
    if "PRICE_UNRELIABLE" in prefer.columns:
        prefer = prefer[~prefer["PRICE_UNRELIABLE"].fillna(False)]
    if "SESSIONS" in prefer.columns:
        prefer = prefer[pd.to_numeric(prefer["SESSIONS"], errors="coerce").fillna(0) >= 8]
    return prefer.sort_values(["ACCUM_SCORE", "DELIV_VALUE_CR"], ascending=False).head(n)
