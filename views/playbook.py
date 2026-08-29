from __future__ import annotations

import streamlit as st

from src.ui import inject_css


def page() -> None:
    inject_css()
    st.title("How to decide")
    st.markdown(
        """
**Read the tape, then the business.** High delivery % only matters if the stock is liquid and volume confirms.

1. **Strong accumulation** — delivery around 55%+, above its 20-day average, volume ≥ 1.3×, price not falling, RSI not overbought. Shortlist.
2. **Quiet accumulation** — several sessions of above-average delivery without a blow-off. Watch for a dip toward the 20DMA.
3. **Dip absorption** — price is down, delivery and volume are up. Could be buying the dip or panic. Starter size only.
4. **Overheated / speculative / distribution** — do not chase. Delivery without volume, or volume without delivery, is a trap.
5. **Illiquid / thin tape** — ignore 100% delivery on tiny turnover. That is not institutions.

Conviction blends delivery level, delivery vs average, volume, 5-day price, and bulk/block deals, then **penalises illiquid names**.

**Disclosed flow** ranks bulk/block client names, promoter SAST, MF-tagged prints, plus [NSE corporate announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements) with keyword sentiment. That is **not** official FII/DII stock-wise data.

**Research pages** (Technical Pro, Fundamentals, RS, Derivatives, ML) run on cached NSE history, Yahoo snapshots, and the live option chain. Incomplete filings stay labelled as directional.

**Portfolio / backtest / compliance** are research tools on this desk's universe — not a live mandate.
"""
    )
