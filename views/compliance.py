from __future__ import annotations

import pandas as pd
import streamlit as st

from src.compliance_reporting import PreTradeCompliance, SEBIReporter
from src.insights import top_ideas
from src.ui import desk, empty_state, page_header, pick_symbol


def page() -> None:
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    symbol = pick_symbol()
    page_header(
        "Portfolio · mandate",
        "Compliance",
        "Pre-trade check on a hypothetical order. Sample book is equal-weight high-conviction names — not a live fund.",
    )
    ideas = top_ideas(snapshot, n=8) if not snapshot.empty else snapshot
    if ideas.empty:
        empty_state("No names to seed a book", "Need high-conviction names on the board.")
        return
    aum = st.number_input("AUM (₹)", 1_000_000.0, 10_000_000_000.0, 100_000_000.0, step=1_000_000.0)
    n = max(len(ideas), 1)
    holdings = {}
    sector_exposure = {}
    rows = []
    for _, row in ideas.iterrows():
        w = 1 / n
        val = aum * w
        holdings[row["SYMBOL"]] = {"value": val}
        sector = str(row.get("SECTOR") or "Unknown")
        sector_exposure[sector] = sector_exposure.get(sector, 0) + val
        rows.append({"Symbol": row["SYMBOL"], "Sector": sector, "Value": val, "Weight": w})
    book = pd.DataFrame(rows)
    reporter = SEBIReporter()
    report = reporter.generate_monthly_portfolio_report(book, pd.DataFrame())
    c1, c2, c3 = st.columns(3)
    c1.metric("Securities", report["number_of_securities"])
    c2.metric("AUM", f"₹{report['total_aum']:,.0f}")
    c3.metric("Turnover ratio", f"{report['turnover_ratio']}")
    st.dataframe(book, width="stretch", hide_index=True)
    st.subheader("Pre-trade check")
    default_sym = symbol if symbol else str(ideas.iloc[0]["SYMBOL"])
    order_sym = st.text_input("Order symbol", value=default_sym).upper()
    qty = st.number_input("Quantity", 1, 10_000_000, 100)
    row = snapshot[snapshot["SYMBOL"] == order_sym]
    px = float(row.iloc[0]["CLOSE_PRICE"]) if not row.empty and pd.notna(row.iloc[0].get("CLOSE_PRICE")) else 100.0
    sector = str(row.iloc[0].get("SECTOR") or "Unknown") if not row.empty else "Unknown"
    mcap = float(row.iloc[0].get("MARKET_CAP_CR") or 0) if not row.empty else 0.0
    price = st.number_input("Price", 0.01, 1_000_000.0, float(px))
    rules = {
        "max_single_stock_pct": st.slider("Max single stock %", 1, 25, 10),
        "max_sector_pct": st.slider("Max sector %", 5, 50, 25),
        "min_market_cap": st.number_input("Min mcap ₹ Cr", 0.0, 50_000.0, 500.0),
        "restricted_stocks": [],
    }
    if st.button("Run check", type="primary"):
        result = PreTradeCompliance(rules).check_order(
            {
                "symbol": order_sym,
                "quantity": int(qty),
                "price": float(price),
                "sector": sector,
                "market_cap_cr": mcap,
            },
            {"total_value": aum, "holdings": holdings, "sector_exposure": sector_exposure},
        )
        if result.get("approved"):
            st.success(result.get("reason"))
        else:
            st.error(result.get("reason"))
