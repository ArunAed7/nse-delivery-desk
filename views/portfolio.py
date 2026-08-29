from __future__ import annotations

import pandas as pd
import streamlit as st

from src.bridges import returns_matrix
from src.insights import top_ideas
from src.portfolio_risk import (
    calculate_factor_exposures,
    calculate_risk_metrics,
    hierarchical_risk_parity,
    mean_variance_optimization,
    risk_parity_allocation,
    style_box_classification,
)
from src.ui import desk, empty_state, fmt_num, page_header


def page() -> None:
    d = desk()
    snapshot = d.get("snapshot", pd.DataFrame())
    with_ind = d.get("with_ind", pd.DataFrame())
    page_header(
        "Portfolio · live board",
        "Construction",
        "Factor tilts, then mean-variance / risk-parity on high-conviction names.",
    )
    if snapshot.empty:
        empty_state("No snapshot", "Load market data from the sidebar.")
        return
    indexed = snapshot.set_index("SYMBOL")
    expo = calculate_factor_exposures(indexed)
    styled = style_box_classification(expo)
    show = styled.reset_index()
    if "index" in show.columns:
        show = show.rename(columns={"index": "SYMBOL"})
    if "SYMBOL" in show.columns:
        show = show.merge(snapshot[["SYMBOL", "NAME", "SECTOR", "ACCUM_SCORE"]], on="SYMBOL", how="left")
    st.subheader("Style box")
    st.dataframe(show.head(40), width="stretch", hide_index=True)
    ideas = top_ideas(snapshot, n=8)
    names = ideas["SYMBOL"].tolist() if not ideas.empty else snapshot.nlargest(8, "ACCUM_SCORE")["SYMBOL"].tolist()
    rets = returns_matrix(with_ind, names)
    if rets.empty or rets.shape[1] < 2:
        st.warning("Need more overlapping history to optimize.")
        return
    mu = rets.mean() * 252
    cov = rets.cov() * 252
    mv = mean_variance_optimization(mu, cov)
    rp = risk_parity_allocation(cov)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Max-Sharpe weights**")
        w = mv.get("weights") if isinstance(mv, dict) else None
        if w is not None:
            wf = pd.Series(w, index=mu.index).sort_values(ascending=False)
            st.bar_chart(wf)
            st.caption(f"Sharpe {fmt_num(mv.get('sharpe_ratio'), '{:.2f}')} · vol {fmt_num(mv.get('volatility'), '{:.1%}')}")
    with c2:
        st.markdown("**Risk parity**")
        rw = rp.get("weights") if isinstance(rp, dict) else None
        if rw is not None:
            rws = pd.Series(rw, index=mu.index).sort_values(ascending=False)
            st.bar_chart(rws)
    try:
        hrp = hierarchical_risk_parity(rets.dropna(how="any"))
    except Exception:
        hrp = {}
    hw = hrp.get("weights")
    if hw is not None and "error" not in hrp:
        st.markdown("**Hierarchical risk parity**")
        order = hrp.get("asset_order") or list(mu.index)
        st.bar_chart(pd.Series(hw, index=order).sort_values(ascending=False))
    eq = rets.mean(axis=1)
    risk = calculate_risk_metrics(eq)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Equal-weight Sharpe", fmt_num(risk.get("sharpe_ratio"), "{:.2f}"))
    k2.metric("Sortino", fmt_num(risk.get("sortino_ratio"), "{:.2f}"))
    k3.metric("Max DD", fmt_num(risk.get("max_drawdown"), "{:.1%}"))
    k4.metric("Win rate", fmt_num(risk.get("win_rate"), "{:.0%}"))
