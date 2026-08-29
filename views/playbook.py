from __future__ import annotations

import streamlit as st

from src.ui import page_header


def page() -> None:
    page_header(
        "Markets · playbook",
        "How to decide",
        "This desk is a delivery and disclosed-print scanner. It is not Bloomberg, not FII/DII, and not a buy list.",
    )
    cards = [
        (
            "1. Mandate first",
            "Investable = liquid turnover. Ignore 100% delivery on a thin book. T2T is not a delivery signal.",
        ),
        (
            "2. Setup quality ≥ 70",
            "Delivery ≥ 55%, vs 20D ≥ 1.15×, volume ≥ 1.3×, above 20DMA, RSI not overbought, 8+ sessions, no cache-gap 5D.",
        ),
        (
            "3. Size from liquidity",
            "Cap at 8% of one day's rupee turnover and 0.5% of mcap. If the cap is tiny, skip — you cannot get in or out.",
        ),
        (
            "4. Kill the idea",
            "Close below 20DMA, or delivery vs average < 0.95 for two sessions. Do not average down a broken tape.",
        ),
        (
            "5. Disclosed flow is extra",
            "Bulk/block client names and SAST are large-lot prints. They are not official stock-wise FII/DII.",
        ),
        (
            "6. Backtest is one name, one rule",
            "Next-bar delivery setup vs buy-and-hold. If it does not beat the stock with costs, do not pretend it will live.",
        ),
    ]
    rows = [cards[0:3], cards[3:6]]
    for row in rows:
        cols = st.columns(3, gap="small")
        for col, (title, body) in zip(cols, row):
            with col:
                st.markdown(
                    f'<div class="play"><h4>{title}</h4><p>{body}</p></div>',
                    unsafe_allow_html=True,
                )
    st.caption("Research pages that need filings (Piotroski, ESG, AMFI SIP) stay off the board until the inputs exist.")
