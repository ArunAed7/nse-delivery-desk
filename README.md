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

**If you still see the old UI** (blue-slate theme, tabs such as Opportunity board / Trackers / Institutional, browser title “NSE delivery desk”):

1. You are looking at a **Streamlit process that was started before the restyle**. Theme in `.streamlit/config.toml` does **not** apply until you stop that process and start a new one.
2. On Windows, close every terminal that is running Streamlit, then in Task Manager end leftover `streamlit` / `python` jobs still bound to port 8501. A new copy of the app will not replace the old one if 8501 is already taken — the old page keeps serving.
3. Pull the latest `main` (the amber restyle is merged as PR #4). Run **`streamlit run app.py`**, not `app_institutional.py`.
4. Hard-refresh the browser (Ctrl+Shift+R). The sidebar should show a gold **NSE** mark, a copper **Amber terminal** stamp, left nav groups (Markets / Research / Portfolio / Macro), and the tab title **NSE desk · Amber**.

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
