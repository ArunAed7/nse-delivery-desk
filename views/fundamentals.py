from __future__ import annotations

import pandas as pd
import streamlit as st

from src.bridges import yahoo_to_quality_inputs
from src.desk import snapshot_row
from src.fundamentals import fetch_fundamentals
from src.fundamentals_deep import calculate_earnings_quality_metrics, calculate_profitability_metrics, comprehensive_fundamental_analysis
from src.fundamentals_institutional import comprehensive_valuation, free_cash_flow_yield, roic_vs_wacc
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    page_header(
        "Research · Yahoo + last close",
        "Fundamentals",
        "Yahoo snapshot only. Missing balance-sheet fields are not filled in as if they were filings.",
    )
    if not symbol:
        empty_state("Pin a stock first", "Use Jump or the screener.")
        return
    row = snapshot_row(d, symbol)
    st.subheader(symbol)
    if st.button("Fetch Yahoo fundamentals", type="primary"):
        with st.spinner(f"Yahoo {symbol}.NS"):
            try:
                info = fetch_fundamentals(symbol)
            except Exception as exc:
                st.error(str(exc))
                return
        if not info or "error" in info:
            st.warning("No Yahoo snapshot.")
            return
        price = float(row["CLOSE_PRICE"]) if row is not None and pd.notna(row.get("CLOSE_PRICE")) else None
        fin = yahoo_to_quality_inputs(info, price)
        if not fin.get("inputs_complete"):
            st.warning(
                "Yahoo did not return a full balance sheet. This page will not print Piotroski, Altman, or DCF."
            )
            st.caption("Raw Yahoo keys with values: " + ", ".join(sorted(k for k, v in info.items() if v not in (None, "", 0, 0.0)))[:400])
            return
        eq = calculate_earnings_quality_metrics(fin)
        prof = calculate_profitability_metrics(fin)
        try:
            full = comprehensive_fundamental_analysis(fin)
        except Exception:
            full = {}
        val = comprehensive_valuation({"current_price": price or 0}, fin)
        fcf = free_cash_flow_yield(fin, float(fin.get("market_cap") or 1))
        spread = roic_vs_wacc(fin)
        a, b, c, dcol = st.columns(4)
        a.metric("Piotroski F", fmt_num(eq.get("piotroski_f_score"), "{:.0f}"))
        b.metric("Altman Z", fmt_num(eq.get("altman_z_score"), "{:.2f}"))
        c.metric("FCF yield", fmt_num(fcf.get("fcf_yield_percent") if isinstance(fcf, dict) else fcf, "{:.1f}%"))
        dcol.metric("Fair value", fmt_num(val.get("average_fair_value"), "{:.1f}"))
        st.caption(f"ROIC vs WACC: {spread}")
        st.caption(f"Consensus: {val.get('consensus_recommendation')} · MoS {fmt_num(val.get('overall_margin_of_safety'), '{:.0%}')}")
        st.json({"earnings_quality": eq, "profitability": prof, "deep": {k: full[k] for k in list(full)[:8]} if full else {}, "valuation": val})
        st.caption("Even with a complete Yahoo snapshot these models are not a substitute for annual reports.")
    else:
        st.info("Click fetch to run the fundamental engine on this name.")
