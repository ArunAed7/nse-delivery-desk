from __future__ import annotations

import re

import pandas as pd

_POS = [
    r"\bbuyback\b",
    r"\bdividend\b",
    r"\bbonus\b",
    r"\bsplit\b",
    r"\bqip\b",
    r"oversubscribed",
    r"order\s+(win|won|bagged|received)",
    r"\bupgrade\b",
    r"promoter\s+(buy|increase|acquire)",
    r"preferential\s+issue",
    r"\baward\b",
    r"capacity\s+expansion",
    r"\bprofit\b",
    r"beats?\s+estimate",
    r"\brecord\s+date\b",
    r"\bbuy[- ]back\b",
    r"increase.*shareholding",
    r"financial\s+results",
    r"outcome of board meeting",
    r"credit rating",
    r"\bacquisition\b",
    r"\ballotment\b",
]
_NEG = [
    r"\bdefault\b",
    r"\bsebi\b",
    r"pledge\s+(invoke|invoked|encumber)",
    r"promoter\s+(sell|sale|dispose|pledged)",
    r"qualified\s+opinion",
    r"\bdelay\b",
    r"\bfraud\b",
    r"\binvestigation\b",
    r"\bpenalty\b",
    r"\bshow\s+cause\b",
    r"\binsolvency\b",
    r"\bnclt\b",
    r"\bdown.?grade\b",
    r"loss\s+of",
    r"\bresign",
    r"\bforfeit",
    r"\bwinding\s+up\b",
    r"\blitigation\b",
    r"loss of share certificate",
]

_POS_RE = [re.compile(p, re.I) for p in _POS]
_NEG_RE = [re.compile(p, re.I) for p in _NEG]


def score_text(text: object) -> float:
    blob = str(text or "")
    if not blob.strip():
        return 0.0
    pos = sum(1 for rx in _POS_RE if rx.search(blob))
    neg = sum(1 for rx in _NEG_RE if rx.search(blob))
    if pos == 0 and neg == 0:
        return 0.0
    raw = (pos - neg) / (pos + neg)
    return float(max(-1.0, min(1.0, raw)))


def sentiment_label(score: float) -> str:
    if score >= 0.25:
        return "Positive"
    if score <= -0.25:
        return "Negative"
    return "Neutral"


def annotate_headlines(df: pd.DataFrame, text_col: str = "HEADLINE") -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    out["SENTIMENT"] = out[text_col].map(score_text)
    out["SENTIMENT_LABEL"] = out["SENTIMENT"].map(sentiment_label)
    return out


def rolling_sentiment(df: pd.DataFrame, window_days: int = 7) -> pd.DataFrame:
    if df is None or df.empty or "SYMBOL" not in df.columns:
        return pd.DataFrame(columns=["SYMBOL", "NEWS_SENTIMENT", "NEWS_COUNT"])
    work = df.copy()
    work["ANN_DATE"] = pd.to_datetime(work.get("ANN_DATE"), errors="coerce")
    cutoff = work["ANN_DATE"].max()
    if pd.isna(cutoff):
        grouped = work.groupby("SYMBOL").agg(NEWS_SENTIMENT=("SENTIMENT", "mean"), NEWS_COUNT=("SENTIMENT", "size"))
        return grouped.reset_index()
    recent = work[work["ANN_DATE"] >= cutoff - pd.Timedelta(days=window_days)]
    if recent.empty:
        recent = work
    grouped = recent.groupby("SYMBOL").agg(
        NEWS_SENTIMENT=("SENTIMENT", "mean"),
        NEWS_COUNT=("SENTIMENT", "size"),
    )
    return grouped.reset_index()
