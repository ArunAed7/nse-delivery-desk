from __future__ import annotations

import json
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from src.announcements import load_cached_announcements, refresh_announcements
from src.deals import load_cached_deals, refresh_deals
from src.nse_data import CACHE_DIR
from src.promoters import load_cached_promoters, refresh_promoters
from src.sectors import UNCLASSIFIED, attach_sectors, load_sectors
from src.sentiment import rolling_sentiment

TRACKER_STATE = CACHE_DIR / "tracker_refresh.json"
FLOW_WINDOW_DAYS = 90


def _z(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    std = s.std(skipna=True)
    mean = s.mean(skipna=True)
    if std is None or pd.isna(std) or std == 0:
        return pd.Series(0.0, index=s.index)
    return (s - mean) / std


def _sum_by(df: pd.DataFrame, mask: pd.Series, col: str, name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["SYMBOL", name])
    part = df.loc[mask]
    if part.empty:
        return pd.DataFrame(columns=["SYMBOL", name])
    return part.groupby("SYMBOL", as_index=False)[col].sum().rename(columns={col: name})


def build_flow_book(
    snapshot: pd.DataFrame | None = None,
    as_of: date | None = None,
    window_days: int = FLOW_WINDOW_DAYS,
) -> pd.DataFrame:
    as_of = as_of or date.today()
    start = pd.Timestamp(as_of) - pd.Timedelta(days=window_days)
    deals = load_cached_deals()
    promoters = load_cached_promoters()
    news = load_cached_announcements()
    sectors = load_sectors()

    if not deals.empty and "DEAL_DATE" in deals.columns:
        deals = deals[pd.to_datetime(deals["DEAL_DATE"], errors="coerce") >= start].copy()
    if not promoters.empty and "DEAL_DATE" in promoters.columns:
        promoters = promoters[pd.to_datetime(promoters["DEAL_DATE"], errors="coerce") >= start].copy()
    if not news.empty and "ANN_DATE" in news.columns:
        news = news[pd.to_datetime(news["ANN_DATE"], errors="coerce") >= start].copy()

    symbols = pd.Index([], dtype=object)
    for frame in (deals, promoters):
        if frame is not None and not frame.empty and "SYMBOL" in frame.columns:
            symbols = symbols.union(frame["SYMBOL"].dropna().unique())
    # Do not add the whole universe: names with no prints stay NA on the snapshot.
    book = pd.DataFrame({"SYMBOL": symbols.astype(str)}).drop_duplicates()
    if book.empty:
        return book

    if not deals.empty and "VALUE_CR" in deals.columns:
        bulk = _sum_by(deals, deals["DEAL_TYPE"].eq("BULK"), "VALUE_CR", "NET_BULK_CR")
        block = _sum_by(deals, deals["DEAL_TYPE"].eq("BLOCK"), "VALUE_CR", "NET_BLOCK_CR")
        mf = _sum_by(deals, deals["CLIENT_TYPE"].eq("MUTUAL_FUND"), "VALUE_CR", "NET_MF_CR")
        mf_buy = _sum_by(
            deals,
            deals["CLIENT_TYPE"].eq("MUTUAL_FUND") & deals["VALUE_CR"].gt(0),
            "VALUE_CR",
            "MF_BUY_CR",
        )
        buy = deals[deals["VALUE_CR"].gt(0)].groupby("SYMBOL", as_index=False)["VALUE_CR"].sum()
        buy = buy.rename(columns={"VALUE_CR": "CUMULATIVE_DEAL_BUY_CR"})
        book = book.merge(bulk, on="SYMBOL", how="left")
        book = book.merge(block, on="SYMBOL", how="left")
        book = book.merge(mf, on="SYMBOL", how="left")
        book = book.merge(mf_buy, on="SYMBOL", how="left")
        book = book.merge(buy, on="SYMBOL", how="left")
    for col in ("NET_BULK_CR", "NET_BLOCK_CR", "NET_MF_CR", "MF_BUY_CR", "CUMULATIVE_DEAL_BUY_CR"):
        if col not in book.columns:
            book[col] = 0.0

    if not promoters.empty:
        prom = promoters.copy()
        if snapshot is not None and not snapshot.empty and "CLOSE_PRICE" in snapshot.columns:
            px = snapshot[["SYMBOL", "CLOSE_PRICE"]].drop_duplicates("SYMBOL")
            prom = prom.merge(px, on="SYMBOL", how="left")
            missing = prom["VALUE_CR"].isna() & prom["QUANTITY"].notna() & prom["CLOSE_PRICE"].notna()
            prom.loc[missing, "VALUE_CR"] = (
                pd.to_numeric(prom.loc[missing, "QUANTITY"], errors="coerce")
                * pd.to_numeric(prom.loc[missing, "CLOSE_PRICE"], errors="coerce")
                / 1e7
            )
            prom = prom.drop(columns=["CLOSE_PRICE"])
        if "VALUE_CR" in prom.columns:
            prom_net = prom.groupby("SYMBOL", as_index=False)["VALUE_CR"].sum().rename(
                columns={"VALUE_CR": "NET_PROMOTER_CR"}
            )
            prom_buy = (
                prom[pd.to_numeric(prom["VALUE_CR"], errors="coerce").gt(0)]
                .groupby("SYMBOL", as_index=False)["VALUE_CR"]
                .sum()
                .rename(columns={"VALUE_CR": "PROMOTER_BUY_CR"})
            )
            book = book.merge(prom_net, on="SYMBOL", how="left")
            book = book.merge(prom_buy, on="SYMBOL", how="left")
    if "NET_PROMOTER_CR" not in book.columns:
        book["NET_PROMOTER_CR"] = 0.0
    if "PROMOTER_BUY_CR" not in book.columns:
        book["PROMOTER_BUY_CR"] = 0.0

    numeric_cols = [
        "NET_BULK_CR",
        "NET_BLOCK_CR",
        "NET_MF_CR",
        "MF_BUY_CR",
        "CUMULATIVE_DEAL_BUY_CR",
        "NET_PROMOTER_CR",
        "PROMOTER_BUY_CR",
    ]
    for col in numeric_cols:
        book[col] = pd.to_numeric(book[col], errors="coerce").fillna(0.0)

    book["CUMULATIVE_BUY_CR"] = book["CUMULATIVE_DEAL_BUY_CR"] + book["PROMOTER_BUY_CR"]
    book["NET_DISCLOSED_CR"] = book["NET_BULK_CR"] + book["NET_BLOCK_CR"]
    no_print = (book["NET_BULK_CR"] == 0) & (book["NET_BLOCK_CR"] == 0)
    book.loc[no_print, "NET_DISCLOSED_CR"] = pd.NA

    sent = rolling_sentiment(news) if not news.empty else pd.DataFrame()
    if not sent.empty:
        book = book.merge(sent, on="SYMBOL", how="left")
    if "NEWS_SENTIMENT" not in book.columns:
        book["NEWS_SENTIMENT"] = 0.0
        book["NEWS_COUNT"] = 0
    book["NEWS_SENTIMENT"] = pd.to_numeric(book["NEWS_SENTIMENT"], errors="coerce").fillna(0.0)
    book["NEWS_COUNT"] = pd.to_numeric(book["NEWS_COUNT"], errors="coerce").fillna(0)

    if snapshot is not None and not snapshot.empty:
        extra = snapshot[
            [c for c in ["SYMBOL", "NAME", "ACCUM_SCORE", "SIGNAL", "CLOSE_PRICE", "MARKET_CAP_CR"] if c in snapshot.columns]
        ].drop_duplicates("SYMBOL")
        book = book.merge(extra, on="SYMBOL", how="left")
    if "ACCUM_SCORE" not in book.columns:
        book["ACCUM_SCORE"] = 0.0
    book["ACCUM_SCORE"] = pd.to_numeric(book["ACCUM_SCORE"], errors="coerce").fillna(0.0)

    book = attach_sectors(book, sectors)
    book["SECTOR"] = book.get("SECTOR", UNCLASSIFIED).fillna(UNCLASSIFIED)

    heat = (
        50
        + 18 * np.tanh(_z(book["NET_DISCLOSED_CR"]))
        + 0.25 * book["ACCUM_SCORE"]
        + 12 * book["NEWS_SENTIMENT"]
        + 8 * np.tanh(_z(book["CUMULATIVE_BUY_CR"]))
    )
    book["HEAT"] = heat.clip(0, 100)

    aligned = np.where(
        (book["NET_DISCLOSED_CR"] > 0) & (book["NEWS_SENTIMENT"] > 0.15),
        "Buy + constructive news",
        np.where(
            (book["NET_DISCLOSED_CR"] > 0) & (book["NEWS_SENTIMENT"] < -0.15),
            "Buy into stress",
            np.where(
                (book["NET_DISCLOSED_CR"] < 0) & (book["NEWS_SENTIMENT"] < -0.15),
                "Exit + negative news",
                "Mixed / quiet",
            ),
        ),
    )
    book["ALIGNMENT"] = aligned

    order = book.sort_values(["NET_DISCLOSED_CR", "CUMULATIVE_BUY_CR"], ascending=False).index
    book["FLOW_RANK"] = pd.Series(range(1, len(book) + 1), index=order)
    book["SECTOR_FLOW_RANK"] = book.groupby("SECTOR")["NET_DISCLOSED_CR"].rank(ascending=False, method="min")

    if not deals.empty and "CLIENT_TYPE" in deals.columns:
        mf_deals = deals[deals["CLIENT_TYPE"].eq("MUTUAL_FUND")].copy()
        if not mf_deals.empty:
            first = (
                mf_deals.assign(DEAL_DATE=pd.to_datetime(mf_deals["DEAL_DATE"], errors="coerce"))
                .groupby("SYMBOL")["DEAL_DATE"]
                .min()
            )
            recent_cut = pd.Timestamp(as_of) - pd.Timedelta(days=21)
            new_names = first[first >= recent_cut].index
            book["MF_NEW_ENTRY"] = book["SYMBOL"].isin(new_names)
        else:
            book["MF_NEW_ENTRY"] = False
    else:
        book["MF_NEW_ENTRY"] = False

    return book.sort_values(["HEAT", "NET_DISCLOSED_CR"], ascending=False).reset_index(drop=True)


def sector_rollup(book: pd.DataFrame) -> pd.DataFrame:
    if book is None or book.empty:
        return pd.DataFrame()
    g = book.groupby("SECTOR", as_index=False).agg(
        NET_DISCLOSED_CR=("NET_DISCLOSED_CR", "sum"),
        CUMULATIVE_BUY_CR=("CUMULATIVE_BUY_CR", "sum"),
        NET_MF_CR=("NET_MF_CR", "sum"),
        NET_PROMOTER_CR=("NET_PROMOTER_CR", "sum"),
        HEAT=("HEAT", "mean"),
        NAMES=("SYMBOL", "nunique"),
    )
    return g.sort_values("NET_DISCLOSED_CR", ascending=False).reset_index(drop=True)


def mf_ledger(as_of: date | None = None, window_days: int = FLOW_WINDOW_DAYS) -> pd.DataFrame:
    deals = load_cached_deals()
    if deals.empty or "CLIENT_TYPE" not in deals.columns:
        return deals
    as_of = as_of or date.today()
    start = pd.Timestamp(as_of) - pd.Timedelta(days=window_days)
    out = deals[
        deals["CLIENT_TYPE"].eq("MUTUAL_FUND")
        & (pd.to_datetime(deals["DEAL_DATE"], errors="coerce") >= start)
    ].copy()
    return attach_sectors(out)


def tracker_caches_stale(max_age_hours: int = 20) -> bool:
    paths = [
        CACHE_DIR / "deals_full.parquet",
        CACHE_DIR / "promoter_pit.parquet",
        CACHE_DIR / "announcements.parquet",
    ]
    if any(not p.exists() for p in paths):
        return True
    oldest = min(p.stat().st_mtime for p in paths)
    age_h = (datetime.now().timestamp() - oldest) / 3600
    return age_h >= max_age_hours


def should_refresh_institutional(retry_minutes: int = 20) -> bool:
    if not tracker_caches_stale():
        return False
    if not TRACKER_STATE.exists():
        return True
    try:
        state = json.loads(TRACKER_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    stamp = state.get("last_attempt_iso")
    if not stamp:
        return True
    try:
        last_try = datetime.fromisoformat(stamp)
    except ValueError:
        return True
    return datetime.now() - last_try >= timedelta(minutes=retry_minutes)


def refresh_institutional(from_date: date | None = None, to_date: date | None = None) -> dict:
    to_date = to_date or date.today()
    from_date = from_date or (to_date - timedelta(days=FLOW_WINDOW_DAYS))
    result: dict[str, int | str] = {
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "last_attempt_iso": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        deals = refresh_deals(from_date, to_date)
        result["deals"] = len(deals)
    except Exception as exc:
        result["deals_error"] = str(exc)
        result["deals"] = 0
    try:
        pit = refresh_promoters(from_date, to_date)
        result["promoters"] = len(pit)
    except Exception as exc:
        result["promoters_error"] = str(exc)
        result["promoters"] = 0
    try:
        news = refresh_announcements(from_date, to_date)
        result["announcements"] = len(news)
    except Exception as exc:
        result["announcements_error"] = str(exc)
        result["announcements"] = 0
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TRACKER_STATE.write_text(json.dumps(result, default=str, indent=2), encoding="utf-8")
    return result
