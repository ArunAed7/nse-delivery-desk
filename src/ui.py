from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

INK = "#07090C"
PANEL = "#12161C"
LINE = "#2A241C"
AMBER = "#E8B86D"
MINT = "#3DDC97"
ROSE = "#FF6B7A"
PAPER = "#EDE8DF"
MUTED = "#8A8175"

DESK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Outfit:wght@500;600;700&display=swap');

[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.15rem; padding-bottom: 3rem; max-width: 1400px; }

[data-testid="stSidebar"] { min-width: 19.5rem; }
[data-testid="stSidebar"] [data-testid="stSidebarNav"] { padding-top: 0.2rem; }
[data-testid="stSidebarNav"] li a {
  border-radius: 8px;
  border-left: 3px solid transparent;
  margin: 1px 0;
}
[data-testid="stSidebarNav"] li a:hover { background: #12161C; }
[data-testid="stSidebarNav"] li a span { font-weight: 500; }
[data-testid="stSidebarNav"] li a[aria-current="page"] {
  background: #16110C;
  border-left-color: #E8B86D;
}

[data-testid="stMetric"] {
  background: linear-gradient(180deg, #161B22 0%, #10141A 100%);
  border: 1px solid #2A241C;
  border-radius: 12px;
  padding: 10px 14px 8px;
  box-shadow: inset 0 1px 0 rgba(232,184,109,0.06);
}
[data-testid="stMetric"] label { letter-spacing: 0.06em; text-transform: uppercase; font-size: 0.7rem !important; color: #8A8175 !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"] { font-family: "IBM Plex Mono", monospace; font-weight: 600; }

div[data-testid="stTabs"] button[role="tab"] {
  font-family: Outfit, sans-serif;
  letter-spacing: 0.02em;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: #E8B86D !important;
}

.brand {
  display: flex; gap: 12px; align-items: center;
  padding: 4px 2px 14px; margin-bottom: 6px;
  border-bottom: 1px solid #2A241C;
}
.brand-mark {
  width: 40px; height: 40px; border-radius: 10px;
  background: linear-gradient(145deg, #E8B86D, #B8863A);
  color: #07090C; font-family: Outfit, sans-serif; font-weight: 700;
  display: flex; align-items: center; justify-content: center; font-size: 13px;
  letter-spacing: 0.04em;
}
.brand-name { font-family: Outfit, sans-serif; font-weight: 700; font-size: 1.05rem; line-height: 1.1; color: #EDE8DF; }
.brand-sub { font-size: 0.72rem; color: #8A8175; margin-top: 2px; letter-spacing: 0.04em; text-transform: uppercase; }
.desk-version {
  font-family: "IBM Plex Mono", monospace; font-size: 0.68rem; letter-spacing: 0.18em;
  text-transform: uppercase; color: #07090C; background: #E8B86D;
  display: inline-block; padding: 3px 8px; border-radius: 4px; margin-top: 8px;
}

.desk-hero { margin: 0 0 1.1rem; }
.desk-kicker {
  font-family: "IBM Plex Mono", monospace; font-size: 0.72rem; letter-spacing: 0.16em;
  text-transform: uppercase; color: #E8B86D; margin-bottom: 6px;
}
.desk-hero h1 {
  font-family: Outfit, sans-serif; font-size: 2rem; font-weight: 700;
  margin: 0 0 8px; letter-spacing: -0.03em; line-height: 1.15;
}
.desk-hero p { color: #8A8175; margin: 0; max-width: 46rem; line-height: 1.45; }

.tape-roll {
  overflow: hidden; white-space: nowrap;
  border: 1px solid #2A241C; border-radius: 999px;
  background: #0C1016; padding: 8px 0; margin: 0 0 1rem;
  mask-image: linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent);
}
.tape-roll .inner {
  display: inline-block; animation: tape 42s linear infinite;
  font-family: "IBM Plex Mono", monospace; font-size: 0.78rem; color: #C4B8A8;
}
.tape-roll b { color: #EDE8DF; font-weight: 600; }
.tape-roll .up { color: #3DDC97; }
.tape-roll .dn { color: #FF6B7A; }
.tape-roll .dot { color: #2A241C; margin: 0 0.85rem; }
@keyframes tape { from { transform: translateX(0); } to { transform: translateX(-50%); } }

.idea {
  background: linear-gradient(180deg, #161B22, #10141A);
  border: 1px solid #2A241C; border-radius: 14px; padding: 12px 14px 10px;
  min-height: 148px;
}
.idea .sym { font-family: Outfit, sans-serif; font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; }
.idea .nm { color: #8A8175; font-size: 0.78rem; min-height: 2.1em; margin: 4px 0 10px; }
.idea .row { display: flex; gap: 8px; }
.idea .cell { flex: 1; background: #0C1016; border-radius: 8px; padding: 6px 8px; }
.idea .lbl { font-size: 0.65rem; letter-spacing: 0.08em; text-transform: uppercase; color: #8A8175; }
.idea .val { font-family: "IBM Plex Mono", monospace; font-weight: 600; font-size: 0.95rem; }
.idea .up { color: #3DDC97; }
.idea .dn { color: #FF6B7A; }

.check-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.check {
  display: flex; justify-content: space-between; align-items: center;
  background: #12161C; border: 1px solid #2A241C; border-radius: 8px; padding: 8px 10px;
  font-size: 0.85rem;
}
.check .ok { color: #3DDC97; font-family: "IBM Plex Mono", monospace; }
.check .weak { color: #F0A05A; font-family: "IBM Plex Mono", monospace; }
.check .fail { color: #FF6B7A; font-family: "IBM Plex Mono", monospace; }
.check .na { color: #8A8175; font-family: "IBM Plex Mono", monospace; }

.empty {
  border: 1px dashed #2A241C; border-radius: 14px; padding: 28px 20px; text-align: center;
  color: #8A8175; background: #0C1016;
}
.empty strong { color: #EDE8DF; display: block; margin-bottom: 6px; font-family: Outfit, sans-serif; }

.focus-strip {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: #16110C; border: 1px solid #3A2F20; border-radius: 10px;
  padding: 8px 12px; margin-bottom: 12px; font-size: 0.85rem;
}
.focus-strip .tag {
  font-family: "IBM Plex Mono", monospace; color: #E8B86D; font-weight: 600;
}
.play {
  background: #12161C; border: 1px solid #2A241C; border-radius: 12px;
  padding: 12px 14px; height: 100%;
}
.play h4 { margin: 0 0 6px; font-family: Outfit, sans-serif; }
.play p { margin: 0; color: #8A8175; font-size: 0.88rem; line-height: 1.45; }
</style>
"""


def inject_css() -> None:
    if st.session_state.get("_desk_css"):
        return
    st.markdown(DESK_CSS, unsafe_allow_html=True)
    st.session_state["_desk_css"] = True


def brand_sidebar() -> None:
    st.markdown(
        """
<div class="brand">
  <div class="brand-mark">NSE</div>
  <div>
    <div class="brand-name">Delivery desk</div>
    <div class="brand-sub">Tape · disclosed flow</div>
    <div class="desk-version">Amber terminal</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, blurb: str) -> None:
    inject_css()
    st.markdown(
        f'<div class="desk-hero"><div class="desk-kicker">{html.escape(kicker)}</div>'
        f"<h1>{html.escape(title)}</h1><p>{html.escape(blurb)}</p></div>",
        unsafe_allow_html=True,
    )


def empty_state(title: str, body: str) -> None:
    st.markdown(
        f'<div class="empty"><strong>{html.escape(title)}</strong>{html.escape(body)}</div>',
        unsafe_allow_html=True,
    )


def focus_strip() -> None:
    symbol = pick_symbol()
    if not symbol:
        return
    d = desk()
    from src.desk import snapshot_row

    row = snapshot_row(d, symbol)
    name = ""
    signal = ""
    if row is not None:
        name = str(row.get("NAME") or "")
        signal = str(row.get("SIGNAL") or "")
    extra = f" · {html.escape(name)}" if name else ""
    sig = f'<span class="tag">{html.escape(signal)}</span>' if signal else ""
    st.markdown(
        f'<div class="focus-strip"><span class="tag">{html.escape(symbol)}</span>'
        f"{extra} pinned for research pages {sig}</div>",
        unsafe_allow_html=True,
    )


def tape_roll(ideas: pd.DataFrame) -> None:
    if ideas is None or ideas.empty:
        return
    bits = []
    for _, row in ideas.iterrows():
        chg = row.get("CHG_5D")
        flag = row.get("PRICE_UNRELIABLE", False)
        unreliable = False if pd.isna(flag) else bool(flag)
        if unreliable:
            chg_s = "5D n/a"
            cls = "dn"
        else:
            cls = "up" if pd.notna(chg) and float(chg) >= 0 else "dn"
            chg_s = fmt_num(chg, "{:+.1f}%")
        bits.append(
            f"<b>{html.escape(str(row['SYMBOL']))}</b> "
            f"<span class='{cls}'>{html.escape(chg_s)}</span> "
            f"{html.escape(str(row.get('SIGNAL') or ''))}"
        )
    line = "<span class='dot'>·</span>".join(bits)
    st.markdown(
        f'<div class="tape-roll"><div class="inner">{line}<span class="dot">·</span>{line}</div></div>',
        unsafe_allow_html=True,
    )


def idea_card_html(row: pd.Series) -> str:
    flag = row.get("PRICE_UNRELIABLE", False)
    unreliable = False if pd.isna(flag) else bool(flag)
    chg = row.get("CHG_5D")
    chg_cls = "up" if pd.notna(chg) and float(chg) >= 0 else "dn"
    chg_txt = "n/a" if unreliable else fmt_num(chg, "{:+.1f}%")
    return (
        '<div class="idea">'
        f'<div class="sym">{html.escape(str(row.get("SYMBOL") or ""))}</div>'
        f'<div class="nm">{html.escape(str(row.get("NAME") or "")[:52])}</div>'
        '<div class="row">'
        f'<div class="cell"><div class="lbl">Setup</div><div class="val">{html.escape(fmt_num(row.get("SETUP_QUALITY"), "{:.0f}"))}</div></div>'
        f'<div class="cell"><div class="lbl">RS</div><div class="val">{html.escape(fmt_num(row.get("RS_20D_PCT"), "{:.0f}"))}</div></div>'
        f'<div class="cell"><div class="lbl">5D</div><div class="val {chg_cls}">{html.escape(chg_txt)}</div></div>'
        "</div></div>"
    )


def checklist_html(checks: dict) -> None:
    cells = []
    for name, status in checks.items():
        key = {"Pass": "ok", "Weak": "weak", "Fail": "fail"}.get(str(status), "na")
        cells.append(
            f'<div class="check"><span>{html.escape(str(name))}</span>'
            f'<span class="{key}">{html.escape(str(status))}</span></div>'
        )
    st.markdown(f'<div class="check-grid">{"".join(cells)}</div>', unsafe_allow_html=True)


def signal_badge(signal: str) -> None:
    color = {
        "Strong accumulation": "green",
        "Quiet accumulation": "blue",
        "Dip absorption": "orange",
        "Overheated": "orange",
        "Speculative": "red",
        "Distribution risk": "red",
        "T2T volume surge": "orange",
        "T2T (delivery n/a)": "gray",
        "Thin tape": "gray",
        "Illiquid": "red",
        "Neutral": "gray",
    }.get(signal, "gray")
    st.badge(signal, color=color)


def fmt_num(value, fmt: str = "{:.1f}", empty: str = "—") -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return empty
    if pd.isna(n):
        return empty
    return fmt.format(n)


def _chart_layout(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor=INK,
        plot_bgcolor=INK,
        font=dict(color=PAPER, family="IBM Plex Sans"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=12, t=36, b=20),
        xaxis_rangeslider_visible=False,
    )
    fig.update_yaxes(gridcolor="#1A1E24", zerolinecolor=LINE)
    fig.update_xaxes(gridcolor="#1A1E24")
    return fig


def sector_bar_chart(rot: pd.DataFrame) -> go.Figure:
    work = rot.sort_values("CHG_20D")
    colors = [MINT if v >= 0 else ROSE for v in work["CHG_20D"].fillna(0)]
    fig = go.Figure(
        go.Bar(
            x=work["CHG_20D"],
            y=work["SECTOR"],
            orientation="h",
            marker_color=colors,
            hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>",
        )
    )
    fig.update_layout(xaxis_title="Median 20D %", yaxis_title="")
    return _chart_layout(fig, height=max(280, 28 * len(work) + 80))


def build_price_chart(hist: pd.DataFrame, symbol: str) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.52, 0.24, 0.24],
        specs=[[{"secondary_y": True}], [{}], [{}]],
    )
    fig.add_trace(
        go.Candlestick(
            x=hist["TRADE_DATE"],
            open=hist["OPEN_PRICE"],
            high=hist["HIGH_PRICE"],
            low=hist["LOW_PRICE"],
            close=hist["CLOSE_PRICE"],
            name="Price",
            increasing_line_color=MINT,
            decreasing_line_color=ROSE,
        ),
        row=1,
        col=1,
        secondary_y=False,
    )
    if "SMA_20" in hist.columns:
        fig.add_trace(
            go.Scatter(x=hist["TRADE_DATE"], y=hist["SMA_20"], name="20DMA", line=dict(width=1.5, color="#7DD3FC")),
            row=1,
            col=1,
            secondary_y=False,
        )
    if "DELIV_PER" in hist.columns:
        fig.add_trace(
            go.Scatter(x=hist["TRADE_DATE"], y=hist["DELIV_PER"], name="Delivery %", line=dict(width=2, color=AMBER)),
            row=1,
            col=1,
            secondary_y=True,
        )
    fig.add_trace(go.Bar(x=hist["TRADE_DATE"], y=hist["TTL_TRD_QNTY"], name="Volume", marker_color="#3F3A34"), row=2, col=1)
    if "DELIV_QTY" in hist.columns:
        fig.add_trace(go.Bar(x=hist["TRADE_DATE"], y=hist["DELIV_QTY"], name="Delivery qty", marker_color=MINT), row=3, col=1)
    fig.update_layout(title=f"{symbol} — price, delivery, volume")
    return _chart_layout(fig, height=620)


def desk() -> dict:
    return st.session_state.get("desk") or {}


def pick_symbol() -> str | None:
    return st.session_state.get("focus_symbol")
