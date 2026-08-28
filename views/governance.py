from __future__ import annotations

import pandas as pd
import streamlit as st

from src.desk import snapshot_row
from src.governance_esg import ESGScorer, analyze_governance
from src.promoters import load_cached_promoters
from src.ui import desk, fmt_num, inject_css, pick_symbol


def page() -> None:
    inject_css()
    d = desk()
    symbol = pick_symbol()
    st.title("Governance")
    st.caption("Promoter SAST prints feed a pledge-style score; ESG scorer is a structured overlay, not a rating agency.")
    if not symbol:
        st.info("Pin a stock.")
        return
    row = snapshot_row(d, symbol)
    st.subheader(symbol)
    pit = load_cached_promoters()
    stock = pit[pit["SYMBOL"] == symbol] if not pit.empty else pd.DataFrame()
    if stock.empty:
        pledge = pd.DataFrame({"Pledge_Percentage": [0.0]})
        st.caption("No SAST promoter rows in the 90-day window — pledge score defaults to clean.")
    else:
        qty = pd.to_numeric(stock["QUANTITY"], errors="coerce").fillna(0)
        pledge = pd.DataFrame({"Pledge_Percentage": (qty.abs() / (qty.abs().max() or 1) * 20).clip(0, 80)})
        st.dataframe(stock.sort_values("DEAL_DATE", ascending=False), width="stretch", hide_index=True)
    fin = pd.DataFrame({"ROIC": [12, 12], "WACC": [11, 11], "FCF": [1, 1], "Debt_to_Equity": [0.4, 0.35]})
    board = {"total_directors": 10, "independent_directors": 6, "women_directors": 2}
    scores = analyze_governance(pledge, fin, board)
    esg = ESGScorer().calculate_esg_score(
        {"carbon_score": 55},
        {"labor_score": 58},
        {"board_score": scores["board_independence_score"]},
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Promoter score", f"{scores['promoter_pledge_score']}")
    c2.metric("Capital allocation", f"{scores['capital_allocation_score']}")
    c3.metric("Board independence", f"{scores['board_independence_score']}")
    c4.metric("ESG overlay", f"{esg.get('ESG_Composite')} {esg.get('Rating')}")
    if row is not None:
        st.caption(f"Sector {row.get('SECTOR')} · net promoter ₹ {fmt_num(row.get('NET_PROMOTER_CR'), '{:.1f}')} Cr")
