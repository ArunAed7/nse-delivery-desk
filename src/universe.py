from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from dateutil import parser as date_parser

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "EQUITY_L.csv"


def _parse_listing_date(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date_parser.parse(text, dayfirst=True).date()
    except (ValueError, OverflowError, TypeError):
        return None


def load_universe(
    csv_path: Path | None = None,
    series: list[str] | None = None,
    as_of: date | None = None,
) -> pd.DataFrame:
    path = csv_path or DEFAULT_CSV
    df = pd.read_csv(path)
    df.columns = [str(c).strip().upper() for c in df.columns]
    rename = {
        "NAME OF COMPANY": "NAME",
        "SERIES": "SERIES",
        "DATE OF LISTING": "LISTING_DATE",
        "PAID UP VALUE": "PAID_UP_VALUE",
        "MARKET LOT": "MARKET_LOT",
        "ISIN NUMBER": "ISIN",
        "FACE VALUE": "FACE_VALUE",
    }
    df = df.rename(columns=rename)
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip().str.upper()
    df["SERIES"] = df["SERIES"].astype(str).str.strip().str.upper()
    df["NAME"] = df["NAME"].astype(str).str.strip()
    as_of = as_of or date.today()
    listing = df["LISTING_DATE"].map(_parse_listing_date)
    df["LISTING_DT"] = listing
    df = df[listing.isna() | (listing <= as_of)].copy()
    wanted = [s.upper() for s in (series or ["EQ", "BE"])]
    df = df[df["SERIES"].isin(wanted)].copy()
    return df.reset_index(drop=True)
