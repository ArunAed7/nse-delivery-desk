from __future__ import annotations

import pandas as pd
import streamlit as st

from src.announcements import load_cached_announcements
from src.desk import snapshot_row, symbol_history
from src.insights import thesis_for_row
from src.promoters import load_cached_promoters
from src.ui import build_price_chart, checklist_html, desk, empty_state, fmt_num, page_header, pick_symbol, signal_badge


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    page_header(
        "Markets · name-level",
        "Thesis",
        "What the tape says, what would kill the idea, and how much liquidity allows you to buy.",
    )
    if not symbol:
        empty_state("Nothing pinned", "Use Jump, Search, the screener, or Open thesis on Command.")
        return
    row = snapshot_row(d, symbol)
    if row is None:
        st.warning(f"{symbol} is not on the current board (series/sector filters).")
        return
    thesis = thesis_for_row(row, as_of=d.get("last_dt"))
    signal_badge(thesis["signal"])
    st.subheader(f"{thesis['symbol']}  ·  {thesis['name']}")
    st.write(thesis["headline"])
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Setup quality", fmt_num(row.get("SETUP_QUALITY"), "{:.0f}"))
    k2.metric("RS 20D %ile", fmt_num(row.get("RS_20D_PCT"), "{:.0f}"))
    net = row.get("NET_DISCLOSED_CR")
    k3.metric("Bulk/block net", "—" if pd.isna(net) else f"₹{float(net):.1f} Cr")
    k4.metric("Close", f"{float(row['CLOSE_PRICE']):.2f}" if pd.notna(row.get("CLOSE_PRICE")) else "—")
    s1, s2 = st.columns(2)
    s1.metric("Max size (liquidity)", fmt_num(row.get("SIZE_CAP_CR"), "₹{:.2f} Cr"))
    s2.write("**Invalidation**")
    s2.write(str(row.get("INVALIDATION") or "—"))
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("**Why this print**")
        for line in thesis["why"]:
            st.write(f"- {line}")
        st.markdown("**Risks**")
        for line in thesis["risks"]:
            st.write(f"- {line}")
        st.info(thesis["action"])
    with right:
        st.markdown("**Checklist**")
        checklist_html(thesis["checks"])
        st.caption(f"Conviction: {row.get('CONVICTION') or '—'} · PE vs sector {fmt_num(row.get('PE_VS_SECTOR'), '{:.2f}×')}")
    hist = symbol_history(d, symbol)
    if not hist.empty:
        st.plotly_chart(build_price_chart(hist, symbol), width="stretch")
    deals = d.get("deals", pd.DataFrame())
    stock_deals = deals[deals["SYMBOL"] == symbol] if deals is not None and not deals.empty else pd.DataFrame()
    pit = load_cached_promoters()
    stock_pit = pit[pit["SYMBOL"] == symbol] if pit is not None and not pit.empty else pd.DataFrame()
    news = load_cached_announcements()
    stock_news = news[news["SYMBOL"] == symbol] if news is not None and not news.empty else pd.DataFrame()
    with st.expander("90-day disclosed flow and headlines", expanded=True):
        if stock_deals.empty and stock_pit.empty and stock_news.empty:
            st.caption("No bulk/block, SAST or announcements in the cached window.")
        if not stock_deals.empty:
            st.markdown("**Bulk / block**")
            keep = [c for c in ["DEAL_DATE", "DEAL_TYPE", "CLIENT_NAME", "CLIENT_TYPE", "SIDE", "QUANTITY", "PRICE", "VALUE_CR"] if c in stock_deals.columns]
            st.dataframe(stock_deals.sort_values("DEAL_DATE", ascending=False)[keep], width="stretch", hide_index=True)
        if not stock_pit.empty:
            st.markdown("**Promoter SAST**")
            st.dataframe(stock_pit.sort_values("DEAL_DATE", ascending=False), width="stretch", hide_index=True)
        if not stock_news.empty:
            st.markdown("**NSE announcements**")
            keep = [c for c in ["ANN_DATE", "SUBJECT", "DETAILS", "SENTIMENT_LABEL", "ATTACHMENT"] if c in stock_news.columns]
            st.dataframe(
                stock_news.sort_values("ANN_DATE", ascending=False)[keep].head(20),
                width="stretch",
                hide_index=True,
                column_config={"ATTACHMENT": st.column_config.LinkColumn("PDF")},
            )
