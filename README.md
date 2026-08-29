# NSE delivery desk

Streamlit desk for the NSE equity universe: **delivery %**, volume/price tape, and **disclosed** institutional flow (bulk/block client names, promoter SAST, MF-tagged prints, corporate announcements).

NSE does **not** publish stock-wise FII/DII. Delivery and deal tags are not official FII/DII.

## Run

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # Windows: .\.venv\Scripts\pip
.venv/bin/streamlit run app.py              # Windows: .\.venv\Scripts\streamlit run app.py
```

Open http://localhost:8501. First load uses cached bhav copies under `data/cache/`. Use **Refresh market data** in the sidebar to pull NSE.

Universe: `data/EQUITY_L.csv`. Sectors: `data/nse_stocks.csv`.

## Pages

| Group | Pages |
|---|---|
| Markets | Command, Screener, Disclosed flow, Thesis, How to decide |
| Research | Technical Pro, Fundamentals, Relative strength, Derivatives, Governance, ML forecast |
| Portfolio | Construction, Backtest, Compliance |
| Macro | Regime & liquidity |

Pin a stock with **Jump** or **Search** (or a screener row) before Thesis / Technical / Fundamentals / option chain / ML.

## Stack

Python 3.12+, Streamlit 1.57+, nselib, yfinance, pandas, plotly, scipy, scikit-learn.
