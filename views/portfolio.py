from __future__ import annotations

import pandas as pd
import streamlit as st

from src.bridges import returns_matrix
from src.grade import suggest_book
from src.portfolio_risk import calculate_risk_metrics
from src.screener import apply_filters, filters_from_state
from src.ui import desk, empty_state, fmt_num, page_header


def page() -> None:
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    with_ind = d.get("with_ind", pd.DataFrame())
    page_header(
        "Portfolio · liquidity book",
        "Construction",
        "Equal-weight, then cap each name at 8% of one-day turnover and 15% of a 100 Cr book. No optimiser theatre.",
    )
    if snapshot.empty:
        empty_state("No snapshot", "Load market data from the sidebar.")
        return
    capital = st.number_input("Book size (₹ Cr)", min_value=1.0, max_value=10_000.0, value=100.0, step=10.0)
    board = apply_filters(snapshot, filters_from_state(st.session_state.get("filters") or {}))
    book = suggest_book(board if not board.empty else snapshot, n=8, capital_cr=float(capital))
    if book.empty:
        empty_state("No names to size", "Need Act/Watch names with a liquidity cap.")
        return
    cash = float(book.attrs.get("cash_weight") or max(0.0, 1.0 - float(book["WEIGHT"].sum())))
    st.caption(f"Cash {cash:.0%}. Weights are not a live mandate.")
    st.dataframe(
        book.drop(columns=["INVALIDATION"], errors="ignore"),
        width="stretch",
        hide_index=True,
        column_config={
            "WEIGHT": st.column_config.NumberColumn("Weight", format="%.1%"),
            "SETUP_QUALITY": st.column_config.NumberColumn("Setup", format="%.0f"),
        },
    )
    st.bar_chart(book.set_index("SYMBOL")["WEIGHT"])
    names = book["SYMBOL"].tolist()
    rets = returns_matrix(with_ind, names)
    if rets.empty or rets.shape[1] < 2:
        st.caption("Need overlapping history for a trailing risk snapshot of this book.")
        return
    w = book.set_index("SYMBOL")["WEIGHT"]
    aligned = rets[w.index.intersection(rets.columns)].fillna(0)
    w = w.reindex(aligned.columns).fillna(0)
    if w.sum() > 0:
        w = w / w.sum()
    port = aligned.dot(w)
    risk = calculate_risk_metrics(port)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Trailing Sharpe", fmt_num(risk.get("sharpe_ratio"), "{:.2f}"))
    k2.metric("Sortino", fmt_num(risk.get("sortino_ratio"), "{:.2f}"))
    k3.metric("Max DD", fmt_num(risk.get("max_drawdown"), "{:.1%}"))
    k4.metric("Win days", fmt_num(risk.get("win_rate"), "{:.0%}"))
    st.caption("Risk stats are the historical path of this weight vector on cached closes — not a forecast.")
    if "INVALIDATION" in book.columns:
        st.markdown("**Kill switches**")
        st.dataframe(book[["SYMBOL", "INVALIDATION"]], width="stretch", hide_index=True)
