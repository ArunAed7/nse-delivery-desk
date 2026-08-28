from __future__ import annotations

import pandas as pd
import streamlit as st

from src.desk import snapshot_row, symbol_history
from src.institutional_view import analyze_symbol, market_close_proxy
from src.ui import build_price_chart, desk, fmt_num, inject_css, pick_symbol


def page() -> None:
    inject_css()
    d = desk()
    symbol = pick_symbol()
    st.title("Technical Pro")
    st.caption("Connors RSI, MACD, ADX, CMF, ATR stops, Bollinger/Keltner, vol regime — on cached NSE prints.")
    if not symbol:
        st.info("Pin a stock from Jump or the screener.")
        return
    hist = symbol_history(d, symbol)
    row = snapshot_row(d, symbol)
    st.subheader(symbol)
    if row is not None:
        st.caption(str(row.get("NAME") or ""))
    report = analyze_symbol(hist, market_close_proxy(d.get("history", pd.DataFrame())))
    if not report.get("ok"):
        st.warning(report.get("reason", "Need more history."))
        return
    last, sig = report["last"], report["signals"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Connors RSI", fmt_num(last.get("mom_crsi"), "{:.1f}"))
    c2.metric("ADX", fmt_num(last.get("adx_adx"), "{:.1f}"))
    c3.metric("CMF", fmt_num(last.get("cmf"), "{:.2f}"))
    c4.metric("Momentum", fmt_num(sig.get("momentum_score"), "{:+.1f}"))
    c5.metric("Vol regime", str(last.get("vol_regime") or "—"))
    d1, d2, d3 = st.columns(3)
    vol20 = last.get("vol_hist_20")
    d1.metric("Hist vol 20D", fmt_num(None if pd.isna(vol20) else float(vol20) * 100, "{:.1f}%") if pd.notna(vol20) else "—")
    d2.metric("Long stop", fmt_num(last.get("long_stop"), "{:.2f}"))
    d3.metric("Short stop", fmt_num(last.get("short_stop"), "{:.2f}"))
    if not hist.empty:
        st.plotly_chart(build_price_chart(hist, symbol), width="stretch")
    tech = report["tech"]
    cols = [c for c in ["close", "bb_upper", "bb_lower", "kc_upper", "kc_lower"] if c in tech.columns]
    if cols and "date" in tech.columns:
        st.line_chart(tech[["date"] + cols].tail(80).set_index("date"))
    st.dataframe(tech.tail(12), width="stretch", hide_index=True)
