from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "nse_stocks.csv"
UNCLASSIFIED = "Unclassified"


def normalize_symbol(raw: object) -> str:
    text = str(raw or "").strip().upper()
    if text.startswith("NSE:"):
        text = text[4:]
    return text.replace("_", "-")


def load_sectors(csv_path: Path | None = None) -> pd.DataFrame:
    path = csv_path or DEFAULT_CSV
    if not path.exists():
        return pd.DataFrame(columns=["SYMBOL", "SECTOR", "ANALYST_RATING"])
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    symbol_col = next((c for c in df.columns if c.lower() == "symbol"), df.columns[0])
    sector_col = next((c for c in df.columns if c.lower() == "sector"), None)
    rating_col = next((c for c in df.columns if "analyst" in c.lower()), None)
    out = pd.DataFrame(
        {
            "SYMBOL": df[symbol_col].map(normalize_symbol),
            "SECTOR": (
                df[sector_col].astype(str).str.strip().replace({"": UNCLASSIFIED, "nan": UNCLASSIFIED})
                if sector_col
                else UNCLASSIFIED
            ),
        }
    )
    if rating_col:
        out["ANALYST_RATING"] = pd.to_numeric(df[rating_col], errors="coerce")
    else:
        out["ANALYST_RATING"] = pd.NA
    out = out[out["SYMBOL"].ne("")].drop_duplicates("SYMBOL", keep="first")
    out.loc[out["SECTOR"].isin(["nan", "None", "NaN"]), "SECTOR"] = UNCLASSIFIED
    return out.reset_index(drop=True)


def attach_sectors(frame: pd.DataFrame, sectors: pd.DataFrame | None = None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return frame
    out = frame.copy()
    if "SYMBOL" not in out.columns:
        return out
    map_df = sectors if sectors is not None else load_sectors()
    if map_df.empty:
        if "SECTOR" not in out.columns:
            out["SECTOR"] = UNCLASSIFIED
        return out
    out["SYMBOL"] = out["SYMBOL"].map(normalize_symbol)
    keep = ["SYMBOL", "SECTOR"]
    if "ANALYST_RATING" in map_df.columns and "ANALYST_RATING" not in out.columns:
        keep.append("ANALYST_RATING")
    mapped = map_df[keep].rename(columns={"SECTOR": "_SECTOR_JOIN"})
    if "ANALYST_RATING" in mapped.columns:
        mapped = mapped.rename(columns={"ANALYST_RATING": "_RATING_JOIN"})
    out = out.merge(mapped, on="SYMBOL", how="left")
    if "SECTOR" not in out.columns:
        out["SECTOR"] = out["_SECTOR_JOIN"]
    else:
        missing = out["SECTOR"].isna() | out["SECTOR"].astype(str).str.strip().isin(["", "nan", UNCLASSIFIED])
        out.loc[missing, "SECTOR"] = out.loc[missing, "_SECTOR_JOIN"]
    out["SECTOR"] = out["SECTOR"].fillna(UNCLASSIFIED)
    drop = [c for c in ("_SECTOR_JOIN", "_RATING_JOIN") if c in out.columns]
    if "_RATING_JOIN" in out.columns and "ANALYST_RATING" not in frame.columns:
        out["ANALYST_RATING"] = out["_RATING_JOIN"]
    return out.drop(columns=drop)
