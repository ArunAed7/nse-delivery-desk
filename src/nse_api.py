from __future__ import annotations

import json
from typing import Any

import pandas as pd


def nse_json(url: str, origin: str) -> Any:
    from nselib.libutil import nse_urlfetch

    resp = nse_urlfetch(url, origin_url=origin)
    if resp.status_code != 200:
        raise RuntimeError(f"NSE {resp.status_code} for {url[:80]}")
    text = resp.content.decode("utf-8", errors="replace").strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def records_to_frame(payload: Any) -> pd.DataFrame:
    if payload is None:
        return pd.DataFrame()
    if isinstance(payload, pd.DataFrame):
        return payload
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if isinstance(payload, dict):
        for key in ("data", "Data", "records", "corporateAnnouncements", "announcements"):
            if key in payload and isinstance(payload[key], list):
                return pd.DataFrame(payload[key])
        if payload:
            return pd.DataFrame([payload])
    return pd.DataFrame()
