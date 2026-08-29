from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
BHAV_PREFIX = "bhav_"
IST = ZoneInfo("Asia/Kolkata")


def nse_today() -> date:
    return datetime.now(IST).date()


def last_session_date(as_of: date | None = None) -> date:
    """Most recent weekday in IST. Holidays still look like sessions until a fetch fails."""
    cursor = as_of or nse_today()
    while cursor.weekday() >= 5:
        cursor -= timedelta(days=1)
    return cursor


def persist_parquet(path: Path, frame: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Write non-empty frames only. Keep the last good cache on a failed/empty fetch."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if frame is not None and not frame.empty:
        frame.to_parquet(path, index=False)
        return frame, "wrote"
    if path.exists():
        return pd.read_parquet(path), "kept"
    if frame is not None:
        frame.to_parquet(path, index=False)
        return frame, "empty"
    return pd.DataFrame(), "empty"

NUMERIC_COLS = [
    "PREV_CLOSE",
    "OPEN_PRICE",
    "HIGH_PRICE",
    "LOW_PRICE",
    "LAST_PRICE",
    "CLOSE_PRICE",
    "AVG_PRICE",
    "TTL_TRD_QNTY",
    "TURNOVER_LACS",
    "NO_OF_TRADES",
    "DELIV_QTY",
    "DELIV_PER",
]


def _to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .replace({"-": None, "": None, "nan": None, "None": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def normalize_bhav(df: pd.DataFrame, trade_date: date) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().upper().replace(" ", "_") for c in df.columns]
    aliases = {
        "DATE1": "TRADE_DATE",
        "DATE": "TRADE_DATE",
        "CLOSE": "CLOSE_PRICE",
        "OPEN": "OPEN_PRICE",
        "HIGH": "HIGH_PRICE",
        "LOW": "LOW_PRICE",
        "LAST": "LAST_PRICE",
        "TOTTRDQTY": "TTL_TRD_QNTY",
        "TOTAL_TRADED_QUANTITY": "TTL_TRD_QNTY",
        "DELIVERY_QTY": "DELIV_QTY",
        "DELIVERABLE_QTY": "DELIV_QTY",
        "DELIVERY_PER": "DELIV_PER",
        "%DELIVERABLE": "DELIV_PER",
        "DELIV_PERC": "DELIV_PER",
    }
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    if "TRADE_DATE" not in df.columns:
        df["TRADE_DATE"] = pd.Timestamp(trade_date)
    else:
        df["TRADE_DATE"] = pd.to_datetime(df["TRADE_DATE"], errors="coerce", dayfirst=True)
        df["TRADE_DATE"] = df["TRADE_DATE"].fillna(pd.Timestamp(trade_date))
    df["SYMBOL"] = df["SYMBOL"].astype(str).str.strip().str.upper()
    if "SERIES" in df.columns:
        df["SERIES"] = df["SERIES"].astype(str).str.strip().str.upper()
    else:
        df["SERIES"] = "EQ"
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = _to_number(df[col])
        else:
            df[col] = pd.NA
    keep = ["SYMBOL", "SERIES", "TRADE_DATE"] + NUMERIC_COLS
    return df[keep]


def bhav_path(trade_date: date) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{BHAV_PREFIX}{trade_date:%Y%m%d}.parquet"


def cached_bhav_dates() -> list[date]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dates: list[date] = []
    for path in CACHE_DIR.glob(f"{BHAV_PREFIX}*.parquet"):
        try:
            dates.append(datetime.strptime(path.stem.replace(BHAV_PREFIX, ""), "%Y%m%d").date())
        except ValueError:
            continue
    return sorted(dates)


def load_cached_bhav(trade_date: date) -> pd.DataFrame | None:
    path = bhav_path(trade_date)
    if not path.exists():
        return None
    return pd.read_parquet(path)


def fetch_bhav(trade_date: date) -> pd.DataFrame | None:
    from nselib import capital_market

    stamp = trade_date.strftime("%d-%m-%Y")
    try:
        raw = capital_market.bhav_copy_with_delivery(trade_date=stamp)
    except Exception:
        return None
    if raw is None or (isinstance(raw, pd.DataFrame) and raw.empty):
        return None
    return normalize_bhav(raw, trade_date)


def save_bhav(df: pd.DataFrame, trade_date: date) -> None:
    df.to_parquet(bhav_path(trade_date), index=False)


def load_history(as_of: date | None = None, trading_days: int = 90) -> pd.DataFrame:
    dates = [d for d in cached_bhav_dates() if as_of is None or d <= as_of]
    if not dates:
        return pd.DataFrame()
    dates = dates[-trading_days:]
    frames = [pd.read_parquet(bhav_path(d)) for d in dates]
    history = pd.concat(frames, ignore_index=True)
    history["TRADE_DATE"] = pd.to_datetime(history["TRADE_DATE"])
    history = fill_t2t_delivery(history)
    return history.sort_values(["SYMBOL", "SERIES", "TRADE_DATE"]).reset_index(drop=True)


def fill_t2t_delivery(df: pd.DataFrame) -> pd.DataFrame:
    """T2T (BE) trades are delivery-only; NSE often leaves DELIV_PER blank."""
    if df.empty or "SERIES" not in df.columns:
        return df
    out = df.copy()
    t2t = out["SERIES"].isin(["BE", "BT", "T"])
    missing = t2t & out["DELIV_PER"].isna()
    if missing.any():
        out.loc[missing, "DELIV_QTY"] = out.loc[missing, "TTL_TRD_QNTY"]
        out.loc[missing, "DELIV_PER"] = 100.0
    return out


def refresh_history(
    trading_days: int = 90,
    pause_s: float = 0.35,
    progress=None,
) -> dict:
    """Download missing daily bhav copies until `trading_days` files exist (or calendar limit)."""
    collected: list[date] = []
    fetched = 0
    skipped = 0
    failed: list[str] = []
    cursor = nse_today()
    attempts = 0
    max_attempts = trading_days * 3 + 40

    while len(collected) < trading_days and attempts < max_attempts:
        attempts += 1
        if cursor.weekday() >= 5:
            cursor -= timedelta(days=1)
            continue
        cached = load_cached_bhav(cursor)
        if cached is not None and not cached.empty:
            collected.append(cursor)
            cursor -= timedelta(days=1)
            continue
        if progress:
            progress(
                len(collected) / max(trading_days, 1),
                f"Fetching {cursor:%d-%b-%Y} ({len(collected) + 1}/{trading_days})",
            )
        frame = fetch_bhav(cursor)
        time.sleep(pause_s)
        if frame is None or frame.empty:
            skipped += 1
            failed.append(cursor.isoformat())
        else:
            save_bhav(frame, cursor)
            collected.append(cursor)
            fetched += 1
        cursor -= timedelta(days=1)

    dates = cached_bhav_dates()
    if progress:
        progress(1.0, "Done")
    return {
        "fetched": fetched,
        "skipped_or_holiday": skipped,
        "cached_days": len(dates),
        "first": dates[0].isoformat() if dates else None,
        "last": dates[-1].isoformat() if dates else None,
        "failed_sample": failed[:8],
    }


def latest_cached_date() -> date | None:
    dates = cached_bhav_dates()
    return dates[-1] if dates else None


def cache_fingerprint() -> str:
    dates = cached_bhav_dates()
    if not dates:
        return "none"
    last = dates[-1]
    mtimes = [bhav_path(d).stat().st_mtime for d in dates if bhav_path(d).exists()]
    stamp = int(max(mtimes)) if mtimes else 0
    return f"{len(dates)}|{last.isoformat()}|{stamp}"


AUTO_STATE_PATH = CACHE_DIR / "auto_refresh.json"
AUTO_RETRY_MINUTES = 20


def _auto_state() -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not AUTO_STATE_PATH.exists():
        return {}
    try:
        return json.loads(AUTO_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_auto_state(payload: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    AUTO_STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def cache_needs_latest(as_of: date | None = None) -> bool:
    expected = last_session_date(as_of)
    last = latest_cached_date()
    if last is None:
        return True
    return last < expected


def should_auto_refresh(as_of: date | None = None, retry_minutes: int = AUTO_RETRY_MINUTES) -> bool:
    as_of = as_of or nse_today()
    if not cache_needs_latest(as_of):
        return False
    state = _auto_state()
    if state.get("attempted_date") != as_of.isoformat():
        return True
    stamp = state.get("last_attempt_iso")
    if not stamp:
        return True
    try:
        last_try = datetime.fromisoformat(stamp)
    except ValueError:
        return True
    now = datetime.now(IST).replace(tzinfo=None)
    try_at = last_try.replace(tzinfo=None) if last_try.tzinfo else last_try
    return now - try_at >= timedelta(minutes=retry_minutes)


def refresh_latest(max_weekdays: int = 15, pause_s: float = 0.3) -> dict:
    """Fetch every missing weekday bhav in the lookback. Do not stop after the first hit."""
    fetched: list[str] = []
    missing: list[str] = []
    cursor = nse_today()
    checked = 0
    while checked < max_weekdays:
        if cursor.weekday() >= 5:
            cursor -= timedelta(days=1)
            continue
        checked += 1
        cached = load_cached_bhav(cursor)
        if cached is not None and not cached.empty:
            cursor -= timedelta(days=1)
            continue
        frame = fetch_bhav(cursor)
        time.sleep(pause_s)
        if frame is None or frame.empty:
            missing.append(cursor.isoformat())
        else:
            save_bhav(frame, cursor)
            fetched.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    last = latest_cached_date()
    expected = last_session_date()
    _write_auto_state(
        {
            "attempted_date": nse_today().isoformat(),
            "last_attempt_iso": datetime.now(IST).isoformat(timespec="seconds"),
            "fetched": fetched,
            "missing": missing,
            "data_through": last.isoformat() if last else None,
        }
    )
    return {
        "fetched": fetched,
        "missing": missing,
        "last": last.isoformat() if last else None,
        "current": last is not None and last >= expected,
    }


def auto_update_if_stale() -> dict:
    if not should_auto_refresh():
        last = latest_cached_date()
        expected = last_session_date()
        return {
            "ran": False,
            "fetched": [],
            "last": last.isoformat() if last else None,
            "current": last is not None and last >= expected,
        }
    result = refresh_latest()
    result["ran"] = True
    return result
