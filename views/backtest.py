from __future__ import annotations

import pandas as pd
import streamlit as st

from src.backtesting_engine import BacktestEngine, simple_momentum_strategy
from src.bridges import backtest_close_frame
from src.desk import symbol_history
from src.ui import desk, empty_state, fmt_num, page_header, pick_symbol


def page() -> None:
    d = desk()
    symbol = pick_symbol()
    page_header(
        "Portfolio · long-only MA",
        "Backtest",
        "Price > 20DMA on cached NSE closes. Costs and slippage applied. Not a live signal.",
    )
    if not symbol:
        empty_state("Pin a stock first", "Jump to a liquid name, then run the engine.")
        return
    hist = symbol_history(d, symbol)
    if hist.empty or len(hist) < 40:
        st.warning("Need more history in the lookback.")
        return
    look = st.slider("MA lookback", 10, 60, 20)
    frame = backtest_close_frame(hist)
    engine = BacktestEngine(initial_capital=1_000_000)
    result = engine.run(frame, lambda df: simple_momentum_strategy(df, lookback=look))
    metrics = engine.calculate_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CAGR %", fmt_num(metrics.get("CAGR"), "{:.1f}"))
    c2.metric("Sharpe", fmt_num(metrics.get("Sharpe_Ratio"), "{:.2f}"))
    c3.metric("Max DD %", fmt_num(metrics.get("Max_Drawdown"), "{:.1f}"))
    c4.metric("Win rate %", fmt_num(metrics.get("Win_Rate"), "{:.1f}"))
    st.caption(f"Vol {fmt_num(metrics.get('Volatility'), '{:.1f}')}% · profit factor {fmt_num(metrics.get('Profit_Factor'), '{:.2f}')} · trades {metrics.get('Total_Trades')}")
    chart = result[["cum_market", "cum_strategy"]].rename(columns={"cum_market": "Buy & hold", "cum_strategy": "Strategy"})
    st.line_chart(chart)
    st.dataframe(result.tail(15).reset_index(), width="stretch", hide_index=True)
