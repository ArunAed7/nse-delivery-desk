from __future__ import annotations

import pandas as pd
import streamlit as st

from src.bridges import option_chain_to_oi
from src.derivatives_intelligence import DerivativesIntelligence
from src.desk import snapshot_row
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    symbol = pick_symbol()
    d = desk()
    page_header(
        "Research · F&O",
        "Derivatives",
        "Live NSE option chain. PCR is put/call OI. Max pain iterates every strike as a candidate settlement. OI change is vs that strike's OI, not LTP across the chain.",
    )
    if not symbol:
        empty_state("Pin an F&O name", "Try RELIANCE or INFY from Jump.")
        return
    row = snapshot_row(d, symbol)
    spot_px = float(row["CLOSE_PRICE"]) if row is not None and pd.notna(row.get("CLOSE_PRICE")) else None
    st.subheader(symbol)
    if st.button("Load option chain", type="primary"):
        with st.spinner("NSE option chain…"):
            oi, spot = option_chain_to_oi(symbol)
        if oi.empty:
            st.warning("No chain returned. The name may not be in F&O, or NSE blocked the session.")
            return
        if pd.isna(spot) and spot_px:
            spot = spot_px
        engine = DerivativesIntelligence().load_oi_data(oi)
        pcr_oi = engine.calculate_pcr("oi")
        pcr_vol = engine.calculate_pcr("volume")
        pain = engine.identify_max_pain(float(spot or 0))
        buildup = engine.detect_oi_buildup()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Spot", fmt_num(spot, "{:.2f}"))
        c2.metric("PCR (OI)", fmt_num(pcr_oi, "{:.2f}"))
        c3.metric("PCR (vol)", fmt_num(pcr_vol, "{:.2f}"))
        c4.metric("Max pain", fmt_num(pain, "{:.0f}"))
        st.caption("Writer-loss minimising expiry strike from the current chain. Not a price target.")
        st.dataframe(oi.sort_values("Strike"), width="stretch", hide_index=True, height=360)
        if buildup is not None and not buildup.empty:
            st.subheader("OI buildup")
            st.dataframe(buildup.head(40), width="stretch", hide_index=True)
    else:
        st.info("Click load to pull the live chain.")
