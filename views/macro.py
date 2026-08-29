from __future__ import annotations

import pandas as pd
import streamlit as st

from src.bridges import deals_daily_institution_flow
from src.institutional_view import market_close_proxy, market_regime, sector_rotation
from src.macro_liquidity import LiquidityFlowAnalyzer, MacroRegimeDetector, analyze_macro_liquidity
from src.ui import desk, page_header


def page() -> None:
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    history = d.get("history", pd.DataFrame())
    page_header(
        "Macro · disclosed tags only",
        "Regime & liquidity",
        "Market-median close vs 50/200DMA. Flow is bulk/block tagged FPI vs MF/insurance/bank in ₹ Cr — not official FII/DII and not AMFI SIP.",
    )
    px = market_close_proxy(history)
    index_df = pd.DataFrame({"Close": px}) if not px.empty else pd.DataFrame()
    flow = deals_daily_institution_flow(d.get("deals"))
    if not index_df.empty and not flow.empty:
        report = analyze_macro_liquidity(index_df, flow)
    elif not index_df.empty:
        report = {
            "regime": MacroRegimeDetector().detect_regime(index_df) if len(index_df) >= 50 else market_regime(history),
            "fii_trend": "n/a",
            "liquidity_score": 50,
            "recommendation": "Need disclosed-deal history for a liquidity score",
        }
    else:
        report = {}
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Regime", str(report.get("regime") or market_regime(history)))
    k2.metric("Tagged FPI trend", str(report.get("fii_trend") or "—"))
    k3.metric("Liquidity score", str(report.get("liquidity_score") or "—"))
    k4.metric("Stance", str(report.get("recommendation") or "—"))
    if not flow.empty:
        st.subheader("Disclosed client-type net (₹ Cr)")
        cols = [c for c in ["FPI_Net", "DII_Net"] if c in flow.columns]
        chart = flow.set_index("Date")[cols]
        st.line_chart(chart)
        st.caption("Client type is a name regex on bulk/block prints. Not NSE FII/DII and not AMFI SIP.")
        analyzer = LiquidityFlowAnalyzer().load_flow_data(flow)
        st.write(analyzer.calculate_flow_trend())
    st.subheader("Sector rotation")
    rot = sector_rotation(snapshot, n=12)
    if rot.empty:
        st.info("No sector 20D data.")
    else:
        st.dataframe(rot, width="stretch", hide_index=True)
        perf = rot.set_index("SECTOR")[["CHG_20D"]].rename(columns={"CHG_20D": "20D"})
        perf["3M"] = perf["20D"]
        perf["6M"] = perf["20D"]
        tops = MacroRegimeDetector().get_sector_rotation_signal(perf)
        if tops:
            st.caption("Momentum overlay uses 20D twice as a 3M/6M stand-in: " + ", ".join(tops))
