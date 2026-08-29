from __future__ import annotations

import streamlit as st

from src.ui import page_header


def page() -> None:
    page_header(
        "Markets · playbook",
        "How to decide",
        "Read the tape, then the business. High delivery % only matters if the stock is liquid and volume confirms.",
    )
    cards = [
        ("1. Strong accumulation", "Delivery around 55%+, above its 20-day average, volume ≥ 1.3×, price not falling, RSI not overbought. Shortlist."),
        ("2. Quiet accumulation", "Several sessions of above-average delivery without a blow-off. Watch for a dip toward the 20DMA."),
        ("3. Dip absorption", "Price is down, delivery and volume are up. Could be buying the dip or panic. Starter size only."),
        ("4. Overheated / speculative", "Do not chase. Delivery without volume, or volume without delivery, is a trap."),
        ("5. Illiquid / thin tape", "Ignore 100% delivery on tiny turnover. That is not institutions."),
        ("Disclosed flow", "Bulk/block client names, promoter SAST, MF-tagged prints, NSE announcements. Not official stock-wise FII/DII."),
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
    st.caption(
        "Research pages run on cached NSE history, Yahoo snapshots, and the live option chain. "
        "Portfolio / backtest / compliance are research tools — not a live mandate."
    )
