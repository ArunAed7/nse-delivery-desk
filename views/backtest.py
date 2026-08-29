from __future__ import annotations

import pandas as pd
import streamlit as st

from src.backtesting_engine import BacktestEngine, simple_momentum_strategy
from src.bridges import backtest_close_frame
from src.desk import symbol_history
from src.grade import delivery_setup_signal
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    page_header(
        "Portfolio · next-bar test",
        "Backtest",
        "Default: long when delivery > 20D average, volume ≥ 1.2×, price > 20DMA. Signal at close, fill next bar. Costs 5+5 bps.",
    )
    if not symbol:
        empty_state("Pin a stock first", "Jump to a liquid name, then run the engine.")
        return
    hist = symbol_history(d, symbol)
    if hist.empty or len(hist) < 40:
        st.warning("Need more history in the lookback.")
        return
    mode = st.radio("Rule", ["Delivery setup", "Price > 20DMA"], horizontal=True)
    look = 20
    if mode == "Price > 20DMA":
        look = st.slider("MA lookback", 10, 60, 20)
    frame = backtest_close_frame(hist)
    engine = BacktestEngine(initial_capital=1_000_000)
    if mode == "Delivery setup":
        work = hist.sort_values("TRADE_DATE").copy()
        sig = delivery_setup_signal(work)

        def _rule(df: pd.DataFrame) -> pd.Series:
            return sig.reindex(df.index).fillna(0)

        result = engine.run(frame, _rule)
    else:
        result = engine.run(frame, lambda df: simple_momentum_strategy(df, lookback=look))
    metrics = engine.calculate_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAGR %", fmt_num(metrics.get("CAGR"), "{:.1f}"))
    c2.metric("Sharpe", fmt_num(metrics.get("Sharpe_Ratio"), "{:.2f}"))
    c3.metric("Max DD %", fmt_num(metrics.get("Max_Drawdown"), "{:.1f}"))
    c4.metric("Win rate %", fmt_num(metrics.get("Win_Rate"), "{:.1f}"))
    st.caption(
        f"Vol {fmt_num(metrics.get('Volatility'), '{:.1f}')}% · profit factor {fmt_num(metrics.get('Profit_Factor'), '{:.2f}')} "
        f"· days in position {metrics.get('Total_Trades')}"
    )
    chart = result[["cum_market", "cum_strategy"]].rename(columns={"cum_market": "Buy & hold", "cum_strategy": "Rule"})
    st.line_chart(chart)
    st.dataframe(result.tail(15).reset_index(), width="stretch", hide_index=True)
    st.caption("One name, one rule, cached sessions only. Not a live order.")
