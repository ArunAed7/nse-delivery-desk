from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.announcements import load_cached_announcements
from src.deals import load_cached_deals
from src.nse_api import nse_json, records_to_frame


def yahoo_to_quality_inputs(info: dict, price: float | None = None) -> dict:
    roe = float(info.get("returnOnEquity") or 0)
    if abs(roe) <= 1.5:
        pass
    else:
        roe = roe / 100
    ocf = float(info.get("operatingCashflow") or 0)
    fcf = float(info.get("freeCashflow") or ocf)
    shares = float(info.get("sharesOutstanding") or 1)
    mcap = float(info.get("marketCap") or 0)
    ni = float(info.get("netIncomeToCommon") or 0)
    if ni == 0 and roe and info.get("bookValue") and shares:
        ni = roe * float(info["bookValue"]) * shares
    assets = float(info.get("totalAssets") or 0)
    if assets == 0 and mcap:
        assets = mcap
    debt = float(info.get("totalDebt") or 0)
    cash = float(info.get("totalCash") or 0)
    ebitda = float(info.get("ebitda") or 0)
    cr = float(info.get("currentRatio") or 1)
    de = float(info.get("debtToEquity") or 0)
    if de > 5:
        de = de / 100
    gm = float(info.get("grossMargins") or 0)
    assets_from_yahoo = float(info.get("totalAssets") or 0) > 0
    complete = bool(
        assets_from_yahoo
        and info.get("netIncomeToCommon")
        and (info.get("operatingCashflow") or info.get("freeCashflow"))
        and info.get("returnOnAssets")
    )
    return {
        "roe": roe,
        "roa_current": float(info.get("returnOnAssets") or roe * 0.5),
        "roa_prior": float(info.get("returnOnAssets") or roe * 0.45),
        "operating_cash_flow": ocf,
        "net_income": ni,
        "leverage_current": de,
        "leverage_prior": de * 1.05,
        "current_ratio_current": cr,
        "current_ratio_prior": cr * 0.95,
        "shares_current": shares,
        "shares_prior": shares,
        "gross_margin_current": gm,
        "gross_margin_prior": gm * 0.98,
        "asset_turnover_current": float(info.get("assetTurnover") or 0.8),
        "asset_turnover_prior": 0.75,
        "total_assets": assets,
        "total_liabilities": debt,
        "current_assets": cash * 2 if cash else assets * 0.3,
        "current_liabilities": cash if cash else assets * 0.2,
        "retained_earnings": ni * 4,
        "ebit": ebitda * 0.8 if ebitda else ni,
        "book_value": float(info.get("bookValue") or 0) * shares,
        "sales": float(info.get("totalRevenue") or 0),
        "fcff": fcf,
        "total_debt": debt,
        "cash": cash,
        "shares_outstanding": shares,
        "ebitda": ebitda,
        "roic": roe * 0.85,
        "wacc": 0.11,
        "invested_capital": max(mcap - cash + debt, 1),
        "current_price": float(price or 0),
        "market_cap": mcap,
        "inputs_complete": complete,
        "assets_are_market_cap": not assets_from_yahoo and mcap > 0,
        "priors_are_fabricated": True,
    }


def deals_daily_institution_flow(deals: pd.DataFrame | None = None) -> pd.DataFrame:
    deals = deals if deals is not None else load_cached_deals()
    if deals is None or deals.empty or "CLIENT_TYPE" not in deals.columns:
        return pd.DataFrame(columns=["Date", "FPI_Net", "DII_Net"])
    work = deals.copy()
    work["DEAL_DATE"] = pd.to_datetime(work["DEAL_DATE"], errors="coerce")
    work["VALUE_CR"] = pd.to_numeric(work.get("VALUE_CR"), errors="coerce").fillna(0)
    fii = work[work["CLIENT_TYPE"].eq("FPI_FII")].groupby(work["DEAL_DATE"].dt.normalize())["VALUE_CR"].sum()
    dii = work[work["CLIENT_TYPE"].isin(["MUTUAL_FUND", "INSURANCE", "BANK_DII"])].groupby(
        work["DEAL_DATE"].dt.normalize()
    )["VALUE_CR"].sum()
    idx = fii.index.union(dii.index)
    out = pd.DataFrame({"Date": idx})
    out["FPI_Net"] = out["Date"].map(fii).fillna(0)
    out["DII_Net"] = out["Date"].map(dii).fillna(0)
    return out.sort_values("Date")


def option_chain_to_oi(symbol: str) -> tuple[pd.DataFrame, float]:
    from nselib import derivatives

    try:
        raw = derivatives.nse_live_option_chain(symbol=symbol, oi_mode="compact")
    except Exception:
        raw = pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame(), float("nan")
    oi = pd.DataFrame(
        {
            "Strike": pd.to_numeric(raw.get("Strike_Price"), errors="coerce"),
            "CE_OI": pd.to_numeric(raw.get("CALLS_OI"), errors="coerce").fillna(0),
            "PE_OI": pd.to_numeric(raw.get("PUTS_OI"), errors="coerce").fillna(0),
            "CE_Chng": pd.to_numeric(raw.get("CALLS_Chng_in_OI"), errors="coerce").fillna(0),
            "PE_Chng": pd.to_numeric(raw.get("PUTS_Chng_in_OI"), errors="coerce").fillna(0),
            "CE_Vol": pd.to_numeric(raw.get("CALLS_Volume"), errors="coerce").fillna(0),
            "PE_Vol": pd.to_numeric(raw.get("PUTS_Volume"), errors="coerce").fillna(0),
            "LTP": pd.to_numeric(raw.get("CALLS_LTP"), errors="coerce").fillna(0),
        }
    ).dropna(subset=["Strike"])
    spot = float("nan")
    try:
        payload = nse_json(
            f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}",
            "https://www.nseindia.com/option-chain",
        )
        if isinstance(payload, dict):
            spot = float(payload.get("records", {}).get("underlyingValue") or float("nan"))
    except Exception:
        pass
    return oi, spot


def returns_matrix(with_ind: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    if with_ind.empty or not symbols:
        return pd.DataFrame()
    part = with_ind[with_ind["SYMBOL"].isin(symbols)][["SYMBOL", "TRADE_DATE", "CLOSE_PRICE"]].copy()
    part["TRADE_DATE"] = pd.to_datetime(part["TRADE_DATE"])
    wide = part.pivot_table(index="TRADE_DATE", columns="SYMBOL", values="CLOSE_PRICE", aggfunc="last")
    return wide.sort_index().pct_change().dropna(how="all")


def price_frame_for_ml(hist: pd.DataFrame) -> pd.DataFrame:
    work = hist.sort_values("TRADE_DATE")
    return pd.DataFrame(
        {
            "Close": pd.to_numeric(work["CLOSE_PRICE"], errors="coerce").values,
            "Volume": pd.to_numeric(work["TTL_TRD_QNTY"], errors="coerce").values,
        },
        index=pd.to_datetime(work["TRADE_DATE"]),
    )


def backtest_close_frame(hist: pd.DataFrame) -> pd.DataFrame:
    work = hist.sort_values("TRADE_DATE")
    return pd.DataFrame(
        {"Close": pd.to_numeric(work["CLOSE_PRICE"], errors="coerce").values},
        index=pd.to_datetime(work["TRADE_DATE"]),
    )


def news_for_symbol(symbol: str, n: int = 8) -> pd.DataFrame:
    news = load_cached_announcements()
    if news.empty:
        return news
    return news[news["SYMBOL"] == symbol].sort_values("ANN_DATE", ascending=False).head(n)
