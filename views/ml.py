from __future__ import annotations

import pandas as pd
import streamlit as st

from src.announcements import load_cached_announcements
from src.bridges import price_frame_for_ml
from src.desk import symbol_history
from src.ml_models import SentimentAnalyzer, run_ml_pipeline
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    page_header(
        "Research · hold-out slice",
        "ML forecast",
        "Gradient boosting on lagged returns/RSI. Directional accuracy only — not a recommendation.",
    )
    if not symbol:
        empty_state("Pin a stock first", "Need a name with a long lookback (180/365).")
        return
    hist = symbol_history(d, symbol)
    st.subheader(symbol)
    if hist.empty or len(hist) < 80:
        st.warning("Need a longer lookback (try 180/365) for a train/test split.")
        return
    if st.button("Train on this name", type="primary"):
        frame = price_frame_for_ml(hist)
        with st.spinner("Fitting…"):
            out = run_ml_pipeline(frame)
        if out.get("error"):
            st.error(out["error"])
            return
        c1, c2 = st.columns(2)
        c1.metric("Directional accuracy", f"{out.get('model_accuracy')}%")
        c2.metric("Latest predicted next-day return", fmt_num(out.get("latest_prediction"), "{:+.2%}"))
        imp = out.get("feature_importance") or {}
        if imp:
            st.bar_chart(pd.Series(imp).sort_values(ascending=False))
    news = load_cached_announcements()
    stock = news[news["SYMBOL"] == symbol] if not news.empty else pd.DataFrame()
    if not stock.empty:
        st.subheader("Headline lexicon (module scorer)")
        text_col = "SUBJECT" if "SUBJECT" in stock.columns else stock.columns[0]
        batch = stock.rename(columns={text_col: "Headline"})[["Headline"]].head(15)
        scored = SentimentAnalyzer().analyze_news_batch(batch)
        st.dataframe(scored, width="stretch", hide_index=True)
    else:
        st.caption("No announcements in cache for this symbol.")
