"""Standalone institutional demo. Live NSE tape lives in app.py → Institutional tab."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src.institutional_view import analyze_symbol
from src.technical_pro import add_momentum_indicators, add_volatility_indicators

st.set_page_config(page_title="NSE Institutional (demo)", page_icon=":material/account_balance:", layout="wide")
st.title("Institutional modules")
st.caption("Demo on synthetic prices. For live NSE delivery + these models, run `streamlit run app.py` and open the Institutional tab.")

rng = np.random.default_rng(42)
n = 300
rets = rng.normal(0.0004, 0.018, n)
close = 100 * np.cumprod(1 + rets)
hist = pd.DataFrame(
    {
        "TRADE_DATE": pd.date_range("2025-01-01", periods=n, freq="B"),
        "SYMBOL": "DEMO",
        "OPEN_PRICE": close * (1 + rng.normal(0, 0.003, n)),
        "HIGH_PRICE": close * (1 + np.abs(rng.normal(0.008, 0.004, n))),
        "LOW_PRICE": close * (1 - np.abs(rng.normal(0.008, 0.004, n))),
        "CLOSE_PRICE": close,
        "TTL_TRD_QNTY": rng.integers(1_000_000, 8_000_000, n),
    }
)
report = analyze_symbol(hist)
if not report.get("ok"):
    st.warning(report.get("reason"))
    st.stop()
last = report["last"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Connors RSI", f"{float(last.get('mom_crsi') or 0):.1f}")
c2.metric("ADX", f"{float(last.get('adx_adx') or 0):.1f}")
c3.metric("CMF", f"{float(last.get('cmf') or 0):.2f}")
c4.metric("Momentum", f"{float(report['signals'].get('momentum_score') or 0):+.1f}")
tech = add_volatility_indicators(add_momentum_indicators(report["ohlcv"]))
st.line_chart(tech.set_index("date")[["close", "bb_upper", "bb_lower"]].tail(80))
st.json({k: v for k, v in report["stage"].items() if k != "ma_30w"})
