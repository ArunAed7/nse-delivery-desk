#!/usr/bin/env python3
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.flow import classify_client, signed_value_cr
from src.insights import top_ideas
from src.nse_data import last_session_date, persist_parquet, refresh_latest
from src.bridges import deals_daily_institution_flow, yahoo_to_quality_inputs


def test_weekend_session_date() -> None:
    sat = date(2026, 8, 29)  # Saturday
    assert last_session_date(sat) == date(2026, 8, 28)
    fri = date(2026, 8, 28)
    assert last_session_date(fri) == fri


def test_persist_keeps_last_good(tmp_path: Path | None = None) -> None:
    path = Path("/tmp/nse_desk_persist_test.parquet")
    if path.exists():
        path.unlink()
    good = pd.DataFrame({"SYMBOL": ["AAA"], "VALUE_CR": [1.0]})
    persist_parquet(path, good)
    kept, status = persist_parquet(path, pd.DataFrame())
    assert status == "kept"
    assert list(kept["SYMBOL"]) == ["AAA"]
    path.unlink()


def test_refresh_latest_fills_gaps(monkeypatch=None) -> None:
    from src import nse_data

    hits: list[date] = []

    def fake_fetch(d: date):
        hits.append(d)
        return pd.DataFrame({"SYMBOL": ["X"], "SERIES": ["EQ"]})

    def fake_cached(d: date):
        if d == date(2026, 8, 20):
            return pd.DataFrame({"SYMBOL": ["X"]})
        return None

    saved: list[date] = []

    def fake_save(df, d):
        saved.append(d)

    nse_data.fetch_bhav = fake_fetch
    nse_data.load_cached_bhav = fake_cached
    nse_data.save_bhav = fake_save
    nse_data.nse_today = lambda: date(2026, 8, 28)
    nse_data.time.sleep = lambda _s: None
    nse_data._write_auto_state = lambda _p: None
    nse_data.latest_cached_date = lambda: date(2026, 8, 28)
    nse_data.refresh_latest(max_weekdays=8)
    assert date(2026, 8, 28) in saved
    assert date(2026, 8, 21) in saved
    assert date(2026, 8, 20) not in saved


def test_client_tags_and_side() -> None:
    assert classify_client("RELIANCE CUSTODY SERVICES") != "FPI_FII"
    assert classify_client("GOVERNMENT OF SINGAPORE") == "FPI_FII"
    assert signed_value_cr(100, 10, "DISPOSAL") < 0
    assert signed_value_cr(100, 10, "BUY") > 0


def test_top_ideas_drops_gap_moves() -> None:
    df = pd.DataFrame(
        {
            "SIGNAL": ["Strong accumulation", "Strong accumulation"],
            "ACCUM_SCORE": [90, 80],
            "DELIV_VALUE_CR": [10, 9],
            "INVESTABLE": [True, True],
            "SESSIONS": [20, 20],
            "PRICE_UNRELIABLE": [True, False],
            "CHG_5D": [630.0, 2.0],
        }
    )
    out = top_ideas(df, n=6)
    assert len(out) == 1
    assert out.iloc[0]["CHG_5D"] == 2.0


def test_yahoo_incomplete_flag() -> None:
    fin = yahoo_to_quality_inputs({"marketCap": 1e12, "returnOnEquity": 0.2}, 100)
    assert fin["inputs_complete"] is False
    assert fin["assets_are_market_cap"] is True


def test_deals_flow_no_sip() -> None:
    deals = pd.DataFrame(
        {
            "CLIENT_TYPE": ["FPI_FII", "MUTUAL_FUND"],
            "DEAL_DATE": pd.to_datetime(["2026-08-01", "2026-08-01"]),
            "VALUE_CR": [10.0, 5.0],
        }
    )
    flow = deals_daily_institution_flow(deals)
    assert "SIP_Inflow" not in flow.columns
    assert "FPI_Net" in flow.columns
    assert float(flow["FPI_Net"].iloc[0]) == 10.0


def test_ml_alignment() -> None:
    from src.ml_models import run_ml_pipeline

    n = 120
    close = pd.Series(range(1, n + 1), dtype=float)
    df = pd.DataFrame({"Close": close, "High": close + 1, "Low": close - 1, "Volume": 1_000_000})
    out = run_ml_pipeline(df)
    assert "error" not in out
    assert "model_accuracy" in out


if __name__ == "__main__":
    test_weekend_session_date()
    test_persist_keeps_last_good()
    test_refresh_latest_fills_gaps()
    test_client_tags_and_side()
    test_top_ideas_drops_gap_moves()
    test_yahoo_incomplete_flag()
    test_deals_flow_no_sip()
    test_ml_alignment()
    print("integrity tests ok")
