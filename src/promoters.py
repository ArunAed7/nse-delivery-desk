from __future__ import annotations

from datetime import date
from io import BytesIO

import pandas as pd
from nselib.libutil import nse_urlfetch

from src.nse_api import nse_json, records_to_frame
from src.nse_data import CACHE_DIR
from src.sectors import normalize_symbol

PIT_PATH = CACHE_DIR / "promoter_pit.parquet"
PIT_ORIGIN = "https://www.nseindia.com/companies-listing/corporate-filings-insider-trading"
PIT_URL = "https://www.nseindia.com/api/corporates-pit?index=equities&from_date={start}&to_date={end}"
SAST_ORIGIN = "https://www.nseindia.com/companies-listing/corporate-filings-sast"
SAST_URL = "https://www.nseindia.com/api/corporate-sast-reg29?index=equities&from_date={start}&to_date={end}"


def _empty() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "SYMBOL",
            "DEAL_DATE",
            "ACQUIRER",
            "CATEGORY",
            "SIDE",
            "QUANTITY",
            "VALUE_CR",
            "BUY_CR",
            "SELL_CR",
            "SOURCE",
        ]
    )


def _col(df: pd.DataFrame, *names: str) -> str | None:
    lookup = {str(c).strip().lower().replace(" ", "").replace("\n", ""): c for c in df.columns}
    for name in names:
        key = name.lower().replace(" ", "")
        if key in lookup:
            return lookup[key]
    for col in df.columns:
        raw = str(col).lower().replace(" ", "").replace("\n", "")
        if any(n.lower().replace(" ", "") in raw for n in names):
            return col
    return None


def _is_promoter(category: object, name: object, promoter_flag: object = None) -> bool:
    flag = str(promoter_flag or "").strip().upper()
    if flag in {"Y", "YES", "TRUE", "1"}:
        return True
    blob = f"{category} {name}".upper()
    return "PROMOTER" in blob


def _finish(out: pd.DataFrame) -> pd.DataFrame:
    if out.empty:
        return _empty()
    out["BUY_CR"] = pd.to_numeric(out["VALUE_CR"], errors="coerce").clip(lower=0)
    out["SELL_CR"] = (-pd.to_numeric(out["VALUE_CR"], errors="coerce")).clip(lower=0)
    return out.dropna(subset=["SYMBOL"]).reset_index(drop=True)


def _normalize_pit(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return _empty()
    df = df.copy()
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    symbol_col = _col(df, "symbol")
    date_col = _col(df, "attDate", "broadcastdate", "intimDt", "DATE OF INITMATION", "BROADCASTE DATE")
    acq_col = _col(df, "acqName", "acquirer", "personName", "NAME OF THE ACQUIRER")
    cat_col = _col(df, "personCategory", "CATEGORY OF PERSON")
    side_col = _col(df, "tdpTransactionType", "transactionType", "ACQUISITION/DISPOSAL TRANSACTION TYPE")
    qty_col = _col(df, "secAcq", "NO. OF SECURITIES (ACQUIRED/DISPLOSED)")
    val_col = _col(df, "secVal", "VALUE OF SECURITY (ACQUIRED/DISPLOSED)")
    if symbol_col is None:
        return _empty()
    out = pd.DataFrame(
        {
            "SYMBOL": df[symbol_col].map(normalize_symbol),
            "DEAL_DATE": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True, format="mixed")
            if date_col
            else pd.NaT,
            "ACQUIRER": df[acq_col].astype(str).str.strip() if acq_col else "",
            "CATEGORY": df[cat_col].astype(str).str.strip() if cat_col else "",
            "SIDE": df[side_col].astype(str).str.strip().str.upper() if side_col else "",
            "QUANTITY": pd.to_numeric(
                df[qty_col].astype(str).str.replace(",", "", regex=False), errors="coerce"
            )
            if qty_col
            else pd.NA,
            "SOURCE": "PIT",
        }
    )
    mask = [_is_promoter(c, a) for c, a in zip(out["CATEGORY"], out["ACQUIRER"])]
    out = out.loc[mask].copy()
    if val_col:
        rupees = pd.to_numeric(df.loc[out.index, val_col].astype(str).str.replace(",", "", regex=False), errors="coerce")
        signed = rupees / 1e7
        sell = out["SIDE"].astype(str).str.contains("SELL|SALE|DISPOS", regex=True)
        out["VALUE_CR"] = signed.mask(sell, -signed.abs())
    else:
        out["VALUE_CR"] = pd.NA
    return _finish(out)


def _normalize_sast(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return _empty()
    symbol_col = _col(df, "symbol")
    if symbol_col is None:
        return _empty()
    date_col = _col(df, "timestamp", "sysTime", "time")
    acq_col = _col(df, "acquirerName")
    type_col = _col(df, "acqSaleType")
    acq_qty = _col(df, "noOfShareAcq")
    sale_qty = _col(df, "noOfShareSale")
    flag_col = _col(df, "promoterType")
    out = pd.DataFrame(
        {
            "SYMBOL": df[symbol_col].map(normalize_symbol),
            "DEAL_DATE": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True, format="mixed")
            if date_col
            else pd.NaT,
            "ACQUIRER": df[acq_col].astype(str).str.strip() if acq_col else "",
            "SIDE": df[type_col].astype(str).str.strip().str.upper() if type_col else "",
            "SOURCE": "SAST_29",
        }
    )
    if flag_col:
        is_p = df[flag_col].astype(str).str.upper().isin(["Y", "YES", "TRUE", "1"])
        out["CATEGORY"] = is_p.map({True: "Promoter", False: "Other"})
    else:
        out["CATEGORY"] = "Promoter"
    buy_q = pd.to_numeric(df[acq_qty], errors="coerce") if acq_qty else 0
    sell_q = pd.to_numeric(df[sale_qty], errors="coerce") if sale_qty else 0
    out["QUANTITY"] = buy_q.fillna(0) - sell_q.fillna(0)
    sell = out["SIDE"].str.contains("SELL|SALE", regex=True)
    buy = out["SIDE"].str.contains("ACQ|BUY|PURCH", regex=True)
    out.loc[sell, "QUANTITY"] = -out.loc[sell, "QUANTITY"].abs()
    out.loc[buy, "QUANTITY"] = out.loc[buy, "QUANTITY"].abs()
    out["VALUE_CR"] = pd.NA
    out = out.loc[out["CATEGORY"].eq("Promoter")].copy()
    return _finish(out)


def _fetch_pit_csv(start: str, end: str) -> pd.DataFrame:
    url = PIT_URL.format(start=start, end=end) + "&csv=true"
    resp = nse_urlfetch(url, origin_url=PIT_ORIGIN)
    if resp.status_code != 200 or not resp.content:
        return pd.DataFrame()
    df = pd.read_csv(BytesIO(resp.content))
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    return df


def load_cached_promoters() -> pd.DataFrame:
    if not PIT_PATH.exists():
        return _empty()
    df = pd.read_parquet(PIT_PATH)
    if "SYMBOL" in df.columns:
        df["SYMBOL"] = df["SYMBOL"].map(normalize_symbol)
    return df


def refresh_promoters(from_date: date, to_date: date) -> pd.DataFrame:
    start = from_date.strftime("%d-%m-%Y")
    end = to_date.strftime("%d-%m-%Y")
    frames: list[pd.DataFrame] = []
    try:
        payload = nse_json(PIT_URL.format(start=start, end=end), PIT_ORIGIN)
        frames.append(_normalize_pit(records_to_frame(payload)))
    except Exception:
        pass
    try:
        frames.append(_normalize_pit(_fetch_pit_csv(start, end)))
    except Exception:
        pass
    try:
        payload = nse_json(SAST_URL.format(start=start, end=end), SAST_ORIGIN)
        frames.append(_normalize_sast(records_to_frame(payload)))
    except Exception:
        pass
    if not frames:
        pit = _empty()
    else:
        pit = pd.concat(frames, ignore_index=True)
        pit = pit.drop_duplicates(subset=["SYMBOL", "DEAL_DATE", "ACQUIRER", "SIDE", "QUANTITY", "SOURCE"], keep="first")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pit.to_parquet(PIT_PATH, index=False)
    return pit
