from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from src.flow import annotate_deals
from src.nse_data import CACHE_DIR
from src.sectors import normalize_symbol

DEALS_PATH = CACHE_DIR / "deals_full.parquet"
LEGACY_PATH = CACHE_DIR / "deals.parquet"


def _pick(df: pd.DataFrame, *names: str) -> str | None:
    upper = {str(c).strip().upper().replace(" ", "").replace("/", "").replace(".", ""): c for c in df.columns}
    for name in names:
        key = name.upper().replace(" ", "").replace("/", "").replace(".", "")
        if key in upper:
            return upper[key]
    for col in df.columns:
        raw = str(col).upper()
        if any(n.upper() in raw.replace(" ", "") for n in names):
            return col
    return None


def _normalize_deals(df: pd.DataFrame, deal_type: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "SYMBOL",
                "DEAL_DATE",
                "DEAL_TYPE",
                "SECURITY_NAME",
                "CLIENT_NAME",
                "SIDE",
                "QUANTITY",
                "PRICE",
                "REMARKS",
            ]
        )
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    symbol_col = _pick(out, "Symbol", "SYMBOL")
    date_col = _pick(out, "Date", "DEAL_DATE")
    name_col = _pick(out, "SecurityName", "SECURITYNAME")
    client_col = _pick(out, "ClientName", "CLIENTNAME")
    side_col = _pick(out, "BuySell", "Buy/Sell")
    qty_col = _pick(out, "QuantityTraded", "QUANTITY")
    price_col = _pick(out, "TradePriceWghtAvgPrice", "TradePrice", "PRICE")
    remarks_col = _pick(out, "Remarks")
    if symbol_col is None:
        return _normalize_deals(pd.DataFrame(), deal_type)
    frame = pd.DataFrame(
        {
            "SYMBOL": out[symbol_col].map(normalize_symbol),
            "DEAL_DATE": pd.to_datetime(out[date_col], errors="coerce", dayfirst=True, format="mixed")
            if date_col
            else pd.NaT,
            "DEAL_TYPE": deal_type,
            "SECURITY_NAME": out[name_col].astype(str).str.strip() if name_col else "",
            "CLIENT_NAME": out[client_col].astype(str).str.strip() if client_col else "",
            "SIDE": out[side_col].astype(str).str.strip().str.upper() if side_col else "",
            "QUANTITY": pd.to_numeric(
                out[qty_col].astype(str).str.replace(",", "", regex=False) if qty_col else None,
                errors="coerce",
            )
            if qty_col
            else pd.NA,
            "PRICE": pd.to_numeric(
                out[price_col].astype(str).str.replace(",", "", regex=False) if price_col else None,
                errors="coerce",
            )
            if price_col
            else pd.NA,
            "REMARKS": out[remarks_col].astype(str) if remarks_col else "",
        }
    )
    frame = frame[frame["SYMBOL"].ne("")].dropna(subset=["SYMBOL"])
    return annotate_deals(frame)


def deals_cache_path() -> Path:
    return DEALS_PATH


def load_cached_deals() -> pd.DataFrame:
    path = DEALS_PATH if DEALS_PATH.exists() else LEGACY_PATH
    if not path.exists():
        return _normalize_deals(pd.DataFrame(), "BULK")
    df = pd.read_parquet(path)
    if "CLIENT_TYPE" not in df.columns and "CLIENT_NAME" in df.columns:
        df = annotate_deals(df)
    if "VALUE_CR" not in df.columns and "CLIENT_NAME" in df.columns:
        df = annotate_deals(df)
    if "SYMBOL" in df.columns:
        df["SYMBOL"] = df["SYMBOL"].map(normalize_symbol)
    return df


def refresh_deals(from_date: date, to_date: date) -> pd.DataFrame:
    from nselib import capital_market

    start = from_date.strftime("%d-%m-%Y")
    end = to_date.strftime("%d-%m-%Y")
    frames = []
    try:
        bulk = capital_market.bulk_deal_data(from_date=start, to_date=end)
        frames.append(_normalize_deals(bulk, "BULK"))
    except Exception:
        pass
    try:
        block = capital_market.block_deals_data(from_date=start, to_date=end)
        frames.append(_normalize_deals(block, "BLOCK"))
    except Exception:
        pass
    if not frames:
        deals = _normalize_deals(pd.DataFrame(), "BULK")
    else:
        deals = pd.concat(frames, ignore_index=True)
        deals = deals.drop_duplicates(
            subset=["SYMBOL", "DEAL_DATE", "DEAL_TYPE", "CLIENT_NAME", "SIDE", "QUANTITY", "PRICE"],
            keep="first",
        )
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    deals.to_parquet(DEALS_PATH, index=False)
    deals[["SYMBOL", "DEAL_DATE", "DEAL_TYPE"]].to_parquet(LEGACY_PATH, index=False)
    return deals


def deal_flags(deals: pd.DataFrame) -> pd.DataFrame:
    if deals is None or deals.empty:
        return pd.DataFrame(columns=["SYMBOL", "HAS_DEAL", "DEAL_COUNT", "DEAL_TYPES"])
    grouped = deals.groupby("SYMBOL").agg(
        DEAL_COUNT=("DEAL_TYPE", "size"),
        DEAL_TYPES=("DEAL_TYPE", lambda s: ",".join(sorted(set(s.astype(str))))),
    )
    grouped["HAS_DEAL"] = True
    return grouped.reset_index()
