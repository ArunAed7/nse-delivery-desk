from __future__ import annotations

import pandas as pd
import streamlit as st

from src.announcements import load_cached_announcements
from src.promoters import load_cached_promoters
from src.sectors import attach_sectors
from src.trackers import mf_ledger, sector_rollup
from src.ui import desk, empty_state, page_header


def page() -> None:
    d = desk()
    book = d.get("flow_book", pd.DataFrame()).copy()
    deals = d.get("deals", pd.DataFrame())
    last_dt = d.get("last_dt")
    picked = (st.session_state.get("filters") or {}).get("picked_sectors") or []
    page_header(
        "Markets · 90-day window",
        "Disclosed flow",
        "Bulk/block client names, promoter SAST, MF tags, NSE announcements. Not stock-wise FII/DII.",
    )
    if picked and not book.empty:
        book = book[book["SECTOR"].isin(picked)]
    sectors_view = sector_rollup(book)
    net_all = float(book["NET_DISCLOSED_CR"].sum()) if not book.empty else 0
    mf_all = float(book["NET_MF_CR"].sum()) if not book.empty and "NET_MF_CR" in book.columns else 0
    prom_all = float(book["NET_PROMOTER_CR"].sum()) if not book.empty and "NET_PROMOTER_CR" in book.columns else 0
    top_sector = str(sectors_view.iloc[0]["SECTOR"]) if not sectors_view.empty else "—"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Net disclosed", f"₹{net_all:,.0f} Cr", border=True)
    k2.metric("Top sector", top_sector, border=True)
    k3.metric("MF-tagged net", f"₹{mf_all:,.0f} Cr", border=True)
    k4.metric("Promoter net", f"₹{prom_all:,.0f} Cr", border=True)
    heat_tab, bulk_tab, prom_tab, mf_tab, news_tab = st.tabs(
        ["Heatmap", "Bulk & block", "Promoters", "MF entries", "Announcements"]
    )
    with heat_tab:
        if not sectors_view.empty:
            st.dataframe(sectors_view, width="stretch", hide_index=True)
        cols = [c for c in ["FLOW_RANK", "SYMBOL", "NAME", "SECTOR", "NET_DISCLOSED_CR", "CUMULATIVE_BUY_CR", "NET_MF_CR", "NET_PROMOTER_CR", "ACCUM_SCORE", "NEWS_SENTIMENT", "ALIGNMENT", "HEAT"] if c in book.columns]
        st.dataframe(book.sort_values(["NET_DISCLOSED_CR", "CUMULATIVE_BUY_CR"], ascending=False)[cols] if cols else book, width="stretch", hide_index=True, height=420)
    with bulk_tab:
        view = attach_sectors(deals) if deals is not None and not deals.empty else pd.DataFrame()
        if view.empty:
            empty_state("No bulk/block cache", "Refresh market data to pull NSE deal files.")
        else:
            if picked:
                view = view[view["SECTOR"].isin(picked)]
            keep = [c for c in ["DEAL_DATE", "SYMBOL", "SECTOR", "DEAL_TYPE", "CLIENT_NAME", "CLIENT_TYPE", "SIDE", "QUANTITY", "PRICE", "VALUE_CR"] if c in view.columns]
            st.dataframe(view.sort_values("DEAL_DATE", ascending=False)[keep], width="stretch", hide_index=True, height=400)
    with prom_tab:
        pit = attach_sectors(load_cached_promoters())
        if pit.empty:
            st.info("No promoter SAST rows.")
        else:
            if picked:
                pit = pit[pit["SECTOR"].isin(picked)]
            st.dataframe(pit.sort_values("DEAL_DATE", ascending=False), width="stretch", hide_index=True, height=400)
    with mf_tab:
        mf = mf_ledger(as_of=last_dt)
        if mf is None or mf.empty:
            st.info("No MF-tagged prints.")
        else:
            if picked:
                mf = mf[mf["SECTOR"].isin(picked)]
            st.dataframe(mf.sort_values("DEAL_DATE", ascending=False), width="stretch", hide_index=True, height=400)
    with news_tab:
        news = attach_sectors(load_cached_announcements())
        if news.empty:
            st.info("No announcements.")
        else:
            if picked:
                news = news[news["SECTOR"].isin(picked)]
            keep = [c for c in ["ANN_DATE", "SYMBOL", "COMPANY", "SECTOR", "SUBJECT", "DETAILS", "SENTIMENT_LABEL", "ATTACHMENT"] if c in news.columns]
            st.dataframe(news.sort_values("ANN_DATE", ascending=False)[keep].head(1500), width="stretch", hide_index=True, height=480, column_config={"ATTACHMENT": st.column_config.LinkColumn("PDF")})
