from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from src.nse_api import nse_json, records_to_frame
from src.nse_data import CACHE_DIR, persist_parquet
from src.sectors import attach_sectors, normalize_symbol
from src.sentiment import annotate_headlines

ANN_PATH = CACHE_DIR / "announcements.parquet"
ANN_ORIGIN = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
ANN_URL = (
    "https://www.nseindia.com/api/corporate-announcements"
    "?index=equities&from_date={start}&to_date={end}"
)
CHUNK_DAYS = 7


def _empty() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "SYMBOL",
            "COMPANY",
            "ANN_DATE",
            "SUBJECT",
            "DETAILS",
            "HEADLINE",
            "CATEGORY",
            "ATTACHMENT",
            "SEQ_ID",
            "SOURCE",
            "SENTIMENT",
            "SENTIMENT_LABEL",
        ]
    )


def _normalize_announcements(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return _empty()
    cols = {str(c).strip(): c for c in df.columns}

    def pick(*names: str) -> str | None:
        wanted = {n.lower() for n in names}
        for raw, orig in cols.items():
            if raw.lower() in wanted:
                return orig
        return None

    symbol_col = pick("symbol")
    if symbol_col is None:
        return _empty()
    company_col = pick("sm_name")
    date_col = pick("sort_date", "an_dt", "exchdisstime")
    subject_col = pick("desc")
    details_col = pick("attchmntText")
    file_col = pick("attchmntFile")
    seq_col = pick("seq_id")
    out = pd.DataFrame(
        {
            "SYMBOL": df[symbol_col].map(normalize_symbol),
            "COMPANY": df[company_col].astype(str).str.strip() if company_col else "",
            "ANN_DATE": pd.to_datetime(df[date_col], errors="coerce", dayfirst=True, format="mixed")
            if date_col
            else pd.NaT,
            "SUBJECT": df[subject_col].astype(str).str.strip() if subject_col else "",
            "DETAILS": df[details_col].astype(str).str.strip() if details_col else "",
            "ATTACHMENT": df[file_col].astype(str).str.strip() if file_col else "",
            "SEQ_ID": df[seq_col].astype(str) if seq_col else "",
            "SOURCE": "NSE_ANNOUNCEMENT",
        }
    )
    out["CATEGORY"] = out["SUBJECT"]
    out["HEADLINE"] = (out["SUBJECT"].fillna("") + " — " + out["DETAILS"].fillna("")).str.strip(" —")
    out = out[out["SYMBOL"].ne("") & out["HEADLINE"].ne("") & ~out["HEADLINE"].isin(["nan", "nan — nan"])]
    return annotate_headlines(out, text_col="HEADLINE")


def _date_chunks(from_date: date, to_date: date, size: int = CHUNK_DAYS) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    cursor = from_date
    while cursor <= to_date:
        end = min(cursor + timedelta(days=size - 1), to_date)
        chunks.append((cursor, end))
        cursor = end + timedelta(days=1)
    return chunks


def load_cached_announcements() -> pd.DataFrame:
    if not ANN_PATH.exists():
        return _empty()
    df = pd.read_parquet(ANN_PATH)
    if "SYMBOL" in df.columns:
        df["SYMBOL"] = df["SYMBOL"].map(normalize_symbol)
    if "HEADLINE" not in df.columns and "DETAILS" in df.columns:
        df["HEADLINE"] = (df.get("SUBJECT", "").fillna("") + " — " + df["DETAILS"].fillna("")).str.strip(" —")
    return df


def refresh_announcements(from_date: date, to_date: date) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for start, end in _date_chunks(from_date, to_date):
        url = ANN_URL.format(start=start.strftime("%d-%m-%Y"), end=end.strftime("%d-%m-%Y"))
        try:
            payload = nse_json(url, ANN_ORIGIN)
            frames.append(_normalize_announcements(records_to_frame(payload)))
        except Exception:
            continue
    if not frames:
        news = _empty()
    else:
        news = pd.concat(frames, ignore_index=True)
        if "SEQ_ID" in news.columns:
            news = news.drop_duplicates(subset=["SEQ_ID"], keep="first")
        else:
            news = news.drop_duplicates(subset=["SYMBOL", "ANN_DATE", "HEADLINE"], keep="first")
    news = attach_sectors(news)
    news, _status = persist_parquet(ANN_PATH, news)
    return news
