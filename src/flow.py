from __future__ import annotations

import re

import pandas as pd

CLIENT_TYPES = (
    "MUTUAL_FUND",
    "INSURANCE",
    "FPI_FII",
    "PROMOTER",
    "BANK_DII",
    "OTHER",
)

_MF = re.compile(
    r"MUTUAL\s*FUND|\bAMC\b|\bMF\b|SBI FUNDS|HDFC MUTUAL|ICICI PRUDENTIAL(?!\s+LIFE)"
    r"|NIPPON INDIA|UTI AMC|KOTAK MAHINDRA MUTUAL|ADITYA BIRLA SUN|DSP MUTUAL"
    r"|AXIS MUTUAL|TATA MUTUAL|MIRAE ASSET|MOTILAL OSWAL MUTUAL|PPFAS|PARAG PARIKH"
    r"|QUANT MUTUAL|EDELWEISS MUTUAL|INVESCO MUTUAL|FRANKLIN TEMPLETON|CANARA ROBECO"
    r"|BANDHAN MUTUAL|HSBC MUTUAL|BARODA BNP|MAHINDRA MANULIFE|WHITEOAK|360 ONE MUTUAL"
    r"|GROWW MUTUAL|SUNDARAM MUTUAL|TAURUS MUTUAL|NAVI MUTUAL|PGIM|JM FINANCIAL MUTUAL"
    r"|TRUST MUTUAL|SAMCO MUTUAL|ZERODHA MUTUAL|NJ MUTUAL|HELIOS MUTUAL|OLD BRIDGE",
    re.I,
)
_INS = re.compile(
    r"LIFE INSURANCE|\bLIC\b|INSURANCE|NEW INDIA ASSURANCE|ORIENTAL INSURANCE"
    r"|UNITED INDIA|NATIONAL INSURANCE|\bGIC\b|HDFC LIFE|SBI LIFE|ICICI PRUDENTIAL LIFE"
    r"|MAX LIFE|BAJAJ ALLIANZ|STAR HEALTH|GENERAL INSURANCE|REINSURANCE",
    re.I,
)
_FPI = re.compile(
    r"\bFPI\b|\bFII\b|FOREIGN PORTFOLIO|FOREIGN INSTITUTIONAL|GOVERNMENT OF SINGAPORE"
    r"|NORGES BANK|VANGUARD|BLACKROCK|\bISHARES\b|MORGAN STANLEY|GOLDMAN SACHS"
    r"|MERRILL LYNCH|\bUBS\b|\bNOMURA\b|JPMORGAN|JP MORGAN|CITIGROUP|\bBARCLAYS\b"
    r"|SOCIETE GENERALE|CREDIT SUISSE|GOLDMAN SACHS|HSBC BANK \(MAURITIUS\)"
    r"|THE MTBDIL|CUSTODY|LUXEMBOURG|CAYMAN|IRELAND|SINGAPORE",
    re.I,
)
_PROM = re.compile(r"PROMOTER|PROMOTER GROUP|PERSON ACTING IN CONCERT|\bPAC\b", re.I)
_DII = re.compile(
    r"\bBANK\b|PENSION|PROVIDENT|\bEPFO\b|\bNPS\b|NATIONAL PENSION|UNIT TRUST"
    r"|LIFE CORPORATION|STATE BANK OF INDIA(?! FUNDS)|CANARA BANK|BANK OF BARODA"
    r"|PUNJAB NATIONAL|UNION BANK|INDIAN BANK|BANK OF INDIA",
    re.I,
)


def classify_client(name: object) -> str:
    text = str(name or "").strip()
    if not text:
        return "OTHER"
    if _MF.search(text):
        return "MUTUAL_FUND"
    if _INS.search(text):
        return "INSURANCE"
    if _PROM.search(text):
        return "PROMOTER"
    if _FPI.search(text):
        return "FPI_FII"
    if _DII.search(text):
        return "BANK_DII"
    return "OTHER"


def signed_value_cr(qty, price, side) -> float:
    q = pd.to_numeric(qty, errors="coerce")
    p = pd.to_numeric(price, errors="coerce")
    if pd.isna(q) or pd.isna(p):
        return float("nan")
    sign = -1.0 if str(side or "").strip().upper().startswith("S") else 1.0
    return sign * q * p / 1e7


def annotate_deals(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    out = df.copy()
    out["CLIENT_TYPE"] = out.get("CLIENT_NAME", pd.Series("", index=out.index)).map(classify_client)
    side = out.get("SIDE", pd.Series("", index=out.index))
    out["VALUE_CR"] = [
        signed_value_cr(q, p, s)
        for q, p, s in zip(out.get("QUANTITY", 0), out.get("PRICE", 0), side)
    ]
    out["BUY_CR"] = out["VALUE_CR"].clip(lower=0)
    out["SELL_CR"] = (-out["VALUE_CR"]).clip(lower=0)
    return out
