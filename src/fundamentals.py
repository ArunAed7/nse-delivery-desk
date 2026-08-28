from __future__ import annotations

import time
from datetime import date, datetime, timezone

import pandas as pd

from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"

MCAP_PATH = CACHE_DIR / "market_cap.parquet"


def fetch_fundamentals(symbol: str) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(f"{symbol}.NS")
    info = ticker.info or {}
    keys = [
        "shortName",
        "longName",
        "sector",
        "industry",
        "marketCap",
        "trailingPE",
        "forwardPE",
        "priceToBook",
        "returnOnEquity",
        "returnOnAssets",
        "profitMargins",
        "operatingMargins",
        "revenueGrowth",
        "earningsGrowth",
        "debtToEquity",
        "currentRatio",
        "fiftyTwoWeekHigh",
        "fiftyTwoWeekLow",
        "averageVolume",
        "volume",
        "beta",
        "dividendYield",
        "bookValue",
        "sharesOutstanding",
        "operatingCashflow",
        "freeCashflow",
        "netIncomeToCommon",
        "totalAssets",
        "totalDebt",
        "totalCash",
        "ebitda",
        "grossMargins",
        "totalRevenue",
    ]
    return {k: info.get(k) for k in keys if info.get(k) is not None}


def load_cached_pe() -> pd.DataFrame:
    path = CACHE_DIR / "pe_ratio.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["SYMBOL", "PE"])
    return pd.read_parquet(path)


def refresh_pe_ratios(trade_date: date) -> pd.DataFrame:
    from nselib import capital_market

    stamp = trade_date.strftime("%d-%m-%Y")
    try:
        raw = capital_market.pe_ratio(trade_date=stamp)
    except Exception:
        return pd.DataFrame(columns=["SYMBOL", "PE"])
    if raw is None or raw.empty:
        return pd.DataFrame(columns=["SYMBOL", "PE"])
    df = raw.copy()
    df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]
    symbol_col = "SYMBOL" if "SYMBOL" in df.columns else next(
        (c for c in df.columns if c in {"SECURITY", "SCRIP_CODE"}), None
    )
    pe_candidates = [
        "SYMBOLP/E",
        "SYMBOL_P/E",
        "P/E",
        "PE",
        "PE_RATIO",
        "ADJUSTEDP/E",
        "ADJUSTED_P/E",
    ]
    pe_col = next((c for c in pe_candidates if c in df.columns), None)
    if pe_col is None:
        pe_col = next((c for c in df.columns if "P/E" in c or c.endswith("_PE")), None)
    if symbol_col is None:
        return pd.DataFrame(columns=["SYMBOL", "PE"])
    out = pd.DataFrame()
    out["SYMBOL"] = df[symbol_col].astype(str).str.strip().str.upper()
    out["PE"] = pd.to_numeric(df[pe_col], errors="coerce") if pe_col else pd.NA
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE_DIR / "pe_ratio.parquet", index=False)
    return out


def load_cached_market_caps() -> pd.DataFrame:
    if not MCAP_PATH.exists():
        return pd.DataFrame(columns=["SYMBOL", "MARKET_CAP", "MARKET_CAP_CR"])
    df = pd.read_parquet(MCAP_PATH)
    if "MARKET_CAP" in df.columns and "MARKET_CAP_CR" not in df.columns:
        df["MARKET_CAP_CR"] = pd.to_numeric(df["MARKET_CAP"], errors="coerce") / 1e7
    return df


def refresh_market_caps(symbols: list[str], progress=None, chunk_size: int = 80) -> pd.DataFrame:
    from yfinance.data import YfData

    unique = sorted({str(s).strip().upper() for s in symbols if str(s).strip()})
    data = YfData()
    rows: list[dict] = []
    total = max(len(unique), 1)
    for start in range(0, len(unique), chunk_size):
        batch = unique[start : start + chunk_size]
        if progress:
            progress(start / total, f"Market cap {start + 1}–{min(start + chunk_size, len(unique))} of {len(unique)}")
        ysyms = ",".join(f"{s}.NS" for s in batch)
        try:
            payload = data.get_raw_json(
                "https://query1.finance.yahoo.com/v7/finance/quote?",
                params={"symbols": ysyms, "formatted": "false"},
            )
            quotes = (payload or {}).get("quoteResponse", {}).get("result", []) or []
        except Exception:
            quotes = []
        found: dict[str, float | None] = {}
        for quote in quotes:
            ysym = str(quote.get("symbol") or "")
            nse = ysym.removesuffix(".NS").removesuffix(".ns").upper()
            cap = quote.get("marketCap")
            found[nse] = float(cap) if cap is not None else None
        for symbol in batch:
            rows.append({"SYMBOL": symbol, "MARKET_CAP": found.get(symbol)})
        time.sleep(0.15)
    out = pd.DataFrame(rows)
    out["MARKET_CAP"] = pd.to_numeric(out["MARKET_CAP"], errors="coerce")
    out["MARKET_CAP_CR"] = out["MARKET_CAP"] / 1e7
    out["FETCHED_AT"] = datetime.now(timezone.utc).isoformat()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(MCAP_PATH, index=False)
    if progress:
        progress(1.0, f"Market cap saved ({out['MARKET_CAP'].notna().sum()} of {len(out)})")
    return out
