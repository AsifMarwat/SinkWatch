"""
SinkWatch - Seeing the ground move from space.
Streamlit web app for NASA Space Apps 2026 (Dancing with the SARs). v2: story-style layout.

Run:
  python -m streamlit run app_v2.py
"""

import io
import base64
from datetime import datetime

import numpy as np
import streamlit as st
import folium
from folium.plugins import Fullscreen, MousePosition
from branca.element import MacroElement
from jinja2 import Template
import json
from streamlit_folium import st_folium
import streamlit.components.v1 as components
import plotly.graph_objects as go
from pyproj import Transformer
from PIL import Image

ICON_PATH = "assets/sinkwatch_icon.png"
try:
    _ICON = Image.open(ICON_PATH)
    with open(ICON_PATH, "rb") as _f:
        ICON_B64 = base64.b64encode(_f.read()).decode()
except OSError:
    _ICON, ICON_B64 = "🛰️", ""

st.set_page_config(page_title="SinkWatch · NASA Space Apps 2026 · Dancing with the SARs", page_icon=_ICON,
                   layout="wide", initial_sidebar_state="collapsed")


def H(html):
    """Render an HTML block safely (no blank lines or indentation, which would break Streamlit's markdown)."""
    st.markdown("\n".join(l.strip() for l in html.splitlines() if l.strip()), unsafe_allow_html=True)

APP_DATA = "app_data/sinkwatch_quetta.npz"
CENTRE = (30.19, 67.01)  # Quetta city centre (lat, lon)
VMAX = 15.0               # colour scale limit, cm/yr
ACCENT = "#0b63ce"
RED = "#d92d20"


# ------------------------------------------------------------------ style (v2) with light / dark mode
LIGHT = st.toggle("Light mode", value=False, key="light")
DARK = not LIGHT
THEME = {
    False: dict(bg="#05080f", text="#c9d4e3", head="#ffffff", muted="#93a3ba", muted2="#8798b0", faint="#6f8098",
                line="rgba(255,255,255,.08)", card="linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.015))",
                cardb="rgba(255,255,255,.08)", nav="rgba(5,8,15,.72)", link="#9fb0c8", hot="#ff8a7a", accent="#f97066",
                glow1="rgba(124,58,237,.20)", glow2="rgba(14,165,233,.14)", stars=".55", input="#0d1524",
                quote="rgba(249,112,102,.07)", quoteb="rgba(249,112,102,.2)", chipb="rgba(255,255,255,.1)", ring="#05080f"),
    True: dict(bg="#f6f8fb", text="#334155", head="#0b1220", muted="#52627a", muted2="#64748b", faint="#7a8aa0",
               line="rgba(15,23,42,.08)", card="#ffffff", cardb="rgba(15,23,42,.08)", nav="rgba(255,255,255,.82)",
               link="#475569", hot="#e5484d", accent="#e5484d", glow1="rgba(124,58,237,.10)", glow2="rgba(14,165,233,.12)",
               stars="0", input="#ffffff", quote="rgba(229,72,77,.06)", quoteb="rgba(229,72,77,.22)",
               chipb="rgba(15,23,42,.12)", ring="#f6f8fb"),
}[LIGHT]
H("<style>:root{" + "".join(f"--{k}:{v};" for k, v in THEME.items()) + "}</style>")
H("""
<style>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap");
#MainMenu, header[data-testid="stHeader"], footer {visibility:hidden; height:0;}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none;}
.stApp, [data-testid="stAppViewContainer"] {background:var(--bg) !important; transition:background-color .5s ease;}
.block-container {padding:0 0 3rem 0 !important; max-width:100% !important; position:relative;}
html, body, .stApp, .stApp p, .stApp li, .stApp label, [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] span
  {font-family:"Inter","Segoe UI",system-ui,sans-serif; color:var(--text);}
[data-testid="stIconMaterial"], .material-symbols-rounded {font-family:"Material Symbols Rounded" !important;}
.card, .nav, .quote, .chip, .stat .n, .h1, .h2, .card .t, .lead, .sub {transition:background .5s ease, color .5s ease, border-color .5s ease;}
a, a:hover, a:visited {color:var(--accent); text-decoration:none !important;}
.wrap {max-width:1180px; margin:0 auto; padding:0 28px;}
/* style-only blocks take no space */
div[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style:only-child) {display:none;}
/* theme toggle sits in the nav bar */
.st-key-light {position:absolute; top:20px; right:max(28px, calc((100% - 1180px)/2 + 28px)); z-index:60; width:auto !important;}
.st-key-light label p {color:var(--link) !important; font-size:14px !important;}
/* nav */
.nav {position:relative; z-index:50; backdrop-filter:blur(12px); background:var(--nav); border-bottom:1px solid var(--line);}
.nav .wrap {display:flex; align-items:center; justify-content:space-between; height:64px;}
.brand {display:flex; align-items:center; gap:12px; color:var(--head); font-weight:700; font-size:19px; letter-spacing:-.01em;}
.brand img {width:36px; height:36px; border-radius:9px;}
.links {display:flex; gap:28px; font-size:14px; margin-right:150px;}
.links a {color:var(--link) !important;} .links a:hover {color:var(--head) !important;}
/* hero */
.hero {position:relative; overflow:hidden; padding:92px 0 84px;
  background:radial-gradient(900px 520px at 78% 30%, var(--glow1), transparent 60%),
             radial-gradient(800px 500px at 15% 10%, var(--glow2), transparent 60%), var(--bg);}
.hero:before {content:""; position:absolute; inset:0; opacity:var(--stars);
  background-image:radial-gradient(1.2px 1.2px at 10% 20%, #fff, transparent), radial-gradient(1px 1px at 30% 70%, #cfd8e6, transparent),
  radial-gradient(1.3px 1.3px at 55% 15%, #fff, transparent), radial-gradient(1px 1px at 70% 60%, #cfd8e6, transparent),
  radial-gradient(1.2px 1.2px at 85% 35%, #fff, transparent), radial-gradient(1px 1px at 92% 80%, #cfd8e6, transparent),
  radial-gradient(1px 1px at 20% 90%, #fff, transparent), radial-gradient(1.4px 1.4px at 45% 45%, #fff, transparent);}
.hero .wrap.plain {display:block;}
.hero .wrap:not(.plain) {position:relative; display:grid; grid-template-columns:1.25fr .75fr; gap:48px; align-items:center;}
.eyebrow {font-size:12.5px; font-weight:600; letter-spacing:.18em; text-transform:uppercase; color:var(--accent);}
.h1 {font-size:60px; line-height:1.05; font-weight:800; letter-spacing:-.035em; color:var(--head); margin:18px 0 22px;}
.grad {background:linear-gradient(90deg,#ff8a7a,#f43f5e); -webkit-background-clip:text; background-clip:text;
  color:transparent !important; -webkit-text-fill-color:transparent;}
.lead {font-size:19px; line-height:1.6; color:var(--muted); max-width:620px;}
.cta {display:inline-block; margin-top:32px; padding:14px 26px; border-radius:999px; background:#f97066; color:#fff !important;
  font-weight:600; font-size:15px; box-shadow:0 10px 30px rgba(249,112,102,.35); transition:transform .2s;}
.cta:hover {transform:translateY(-2px);}
.cta2 {margin-left:14px; color:var(--text) !important; font-size:15px; font-weight:500;}
.hero-art {display:flex; justify-content:center;}
.hero-art img {width:360px; max-width:100%; border-radius:36px; box-shadow:0 0 120px rgba(249,112,102,.28), 0 0 0 1px var(--line);
  animation:float 6s ease-in-out infinite;}
@keyframes float {0%,100% {transform:translateY(0)} 50% {transform:translateY(-12px)}}
.stats {display:grid; grid-template-columns:repeat(3,1fr); gap:24px; margin-top:64px; border-top:1px solid var(--line);}
.stat {padding:28px 0 0;}
.stat .n {white-space:nowrap; font-size:44px; font-weight:800; letter-spacing:-.03em; color:var(--head); line-height:1;}
.stat .n.hot {color:var(--hot);}
.stat .l {font-size:14px; color:var(--muted2); margin-top:10px; line-height:1.45;}
/* sections */
.sec {padding:96px 0 28px;}
.kicker {font-size:12.5px; font-weight:600; letter-spacing:.18em; text-transform:uppercase; color:var(--accent);}
.h2 {font-size:42px; font-weight:800; letter-spacing:-.03em; color:var(--head); margin:12px 0 14px; line-height:1.1;}
.sub {font-size:17px; color:var(--muted); max-width:720px; line-height:1.6;}
.grid3 {display:grid; grid-template-columns:repeat(3,1fr); gap:22px; margin-top:40px;}
.grid4 {display:grid; grid-template-columns:repeat(4,1fr); gap:22px; margin-top:40px;}
.card {background:var(--card); border:1px solid var(--cardb); border-radius:20px; padding:28px;
  transition:transform .25s, border-color .25s, background .5s; box-shadow:0 1px 2px rgba(15,23,42,.04);}
.card:hover {transform:translateY(-4px); border-color:rgba(249,112,102,.45);}
.card .ic {font-size:30px;}
.card .t {font-size:19px; font-weight:700; color:var(--head); margin:14px 0 8px;}
.card .d {font-size:15px; color:var(--muted); line-height:1.6;}
.card .big {font-size:44px; font-weight:800; color:var(--hot); letter-spacing:-.03em; line-height:1;}
.card .small {font-size:13px; color:var(--muted2); margin-top:10px;}
.card .small b {color:var(--head);}
.step-n {font-size:12px; font-weight:700; color:var(--accent); letter-spacing:.14em;}
.quote {margin-top:44px; padding:30px 34px; border-radius:20px; background:var(--quote); border:1px solid var(--quoteb);
  font-size:22px; color:var(--head); font-weight:600; letter-spacing:-.01em;}
.quote span {display:block; font-size:13px; font-weight:400; color:var(--muted2); margin-top:10px;}
.legend {display:flex; align-items:center; gap:14px; font-size:13px; color:var(--muted2);}
.legend .bar {width:220px; height:8px; border-radius:4px; background:linear-gradient(90deg,#7f1d1d,#dc2626,#fca5a5,#f1f5f9); border:1px solid var(--line);}
.maphead {display:flex; justify-content:space-between; align-items:flex-end; gap:20px; flex-wrap:wrap;}
.mini {display:flex; gap:34px; margin-top:22px; flex-wrap:wrap;}
.mini div {font-size:13px; color:var(--muted2);} .mini b {display:block; font-size:26px; font-weight:800; color:var(--head); letter-spacing:-.02em;}
.mini b.hot {color:var(--hot);}
.timeline {display:grid; grid-template-columns:repeat(4,1fr); gap:0; margin-top:40px; position:relative;}
.timeline:before {content:""; position:absolute; left:8px; right:8px; top:9px; height:2px; background:linear-gradient(90deg,#f97066,rgba(249,112,102,.15));}
.tl {position:relative; padding:34px 18px 0 0;}
.tl:before {content:""; position:absolute; top:2px; left:0; width:16px; height:16px; border-radius:50%; background:var(--ring); border:3px solid #f97066;}
.tl .w {font-size:12px; font-weight:700; letter-spacing:.14em; color:var(--accent); text-transform:uppercase;}
.tl .x {font-size:15px; color:var(--text); margin-top:6px; line-height:1.55;}
.foot {margin-top:110px; border-top:1px solid var(--line); padding:34px 0; font-size:13px; color:var(--faint);}
.foot .row {display:flex; justify-content:space-between; gap:20px; flex-wrap:wrap;}
.chip {display:inline-block; font-size:12px; padding:4px 10px; border-radius:999px; border:1px solid var(--chipb); color:var(--muted2); margin:0 6px 6px 0;}
.si {font-size:12px; color:var(--faint); margin-top:14px;}
.note {font-size:13px; color:var(--faint);}
/* streamlit widgets follow the theme */
[data-testid="stExpander"] details {background:var(--card) !important; border:1px solid var(--cardb) !important; border-radius:14px !important;}
[data-testid="stExpander"] summary p {color:var(--head) !important; font-weight:600;}
[data-testid="stPopover"] button, .stDownloadButton button {background:var(--card) !important; color:var(--head) !important;
  border:1px solid var(--cardb) !important; border-radius:999px !important;}
[data-testid="stPopover"] button p, .stDownloadButton button p {color:var(--head) !important;}
div[data-baseweb="popover"] > div {background:var(--input) !important; border:1px solid var(--cardb) !important; border-radius:14px !important;}
[data-testid="stSelectbox"] [data-baseweb="select"] > div, div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li
  {background:var(--input) !important; color:var(--head) !important; border-color:var(--cardb) !important;}
[data-testid="stFileUploaderDropzone"] {background:var(--card) !important; border:1px dashed var(--chipb) !important;}
[data-testid="stWidgetLabel"] p, [data-testid="stRadio"] label p {color:var(--muted) !important;}
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"], [data-testid="stSliderThumbValue"] {color:var(--muted) !important;}
iframe {border-radius:20px;}
@media (max-width: 900px) {.hero .wrap:not(.plain), .grid3, .grid4, .timeline, .stats {grid-template-columns:1fr;} .h1 {font-size:40px;} .links {display:none;}}
@media (prefers-reduced-motion: no-preference) {.reveal {animation:rise .8s ease both;} @keyframes rise {from {opacity:0; transform:translateY(16px);} to {opacity:1; transform:none;}}}
</style>
""")


# ------------------------------------------------------------------ data
@st.cache_resource
def load_data():
    d = np.load(APP_DATA)
    data = {k: d[k] for k in d.files}
    data["dates"] = [str(x) for x in data["dates"]]
    t = data["utm_transform"]
    data["to_utm"] = Transformer.from_crs(4326, int(data["utm_epsg"]), always_xy=True)
    data["px_km2"] = abs(t[0] * t[4]) / 1e6
    data["valley_utm"] = data["valley_utm"].astype(bool)
    data["valley_latlon"] = data["valley_latlon"].astype(bool)
    data["has_pop"] = bool(np.isfinite(data["pop_utm"]).any() and np.nansum(data["pop_utm"]) > 0)
    return data


_PANEL = [0]


def panel():
    """Bordered card with a stable CSS hook (works across Streamlit versions)."""
    _PANEL[0] += 1
    return st.container(border=True, key=f"panel_{_PANEL[0]}")


def colorize(vel, threshold, opacity):
    stops = np.array([-VMAX, -10, -5, 0, 5, 10, VMAX])
    cols = np.array([[127, 29, 29], [220, 38, 38], [252, 165, 165], [248, 250, 252],
                     [147, 197, 253], [37, 99, 235], [30, 58, 138]], dtype=float)
    v = np.clip(np.nan_to_num(vel, nan=0.0), -VMAX, VMAX)
    rgb = np.stack([np.interp(v, stops, cols[:, i]) for i in range(3)], axis=-1)
    alpha = np.full(v.shape, int(255 * opacity), dtype=float)
    alpha[~np.isfinite(vel) | (np.abs(vel) < threshold)] = 0
    return np.dstack([rgb, alpha]).astype(np.uint8)


@st.cache_data
def overlay_png(threshold, opacity, sinking_only, valley_only):
    data = load_data()
    vel = data["vel_latlon"].copy()
    if valley_only:
        vel[~data["valley_latlon"]] = np.nan
    if sinking_only:
        vel[vel > 0] = np.nan
    img = Image.fromarray(colorize(vel, threshold, opacity), "RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def latlon_to_rc(data, lat, lon):
    x, y = data["to_utm"].transform(lon, lat)
    t = data["utm_transform"]
    col, row = int((x - t[2]) / t[0]), int((y - t[5]) / t[4])
    h, w = data["vel_utm"].shape
    return (row, col) if (0 <= row < h and 0 <= col < w) else None


def point_stats(data, lat, lon):
    rc = latlon_to_rc(data, lat, lon)
    if rc is None:
        return None
    r, c = rc
    win = (slice(max(r - 1, 0), r + 2), slice(max(c - 1, 0), c + 2))
    n = len(data["dates"])
    series = np.nanmedian(data["stack_utm"][:, win[0], win[1]].reshape(n, -1), axis=1)
    pwin = (slice(max(r - 3, 0), r + 4), slice(max(c - 3, 0), c + 4))
    days = np.array([(datetime.strptime(d, "%Y%m%d") - datetime.strptime(data["dates"][0], "%Y%m%d")).days
                     for d in data["dates"]], dtype=float)
    ok = np.isfinite(series)
    r2 = 0.0
    if ok.sum() >= 4 and np.nanstd(series[ok]) > 0:
        r2 = float(np.corrcoef(days[ok], series[ok])[0, 1] ** 2)
    return {
        "r2": r2,
        "vel": float(np.nanmedian(data["vel_utm"][win])),
        "elev": float(np.nanmedian(data["dem_utm"][win])),
        "valley": bool(data["valley_utm"][r, c]),
        "series": series,
        "people": float(np.nansum(data["pop_utm"][pwin])) if data["has_pop"] else None,
    }


def fmt_date(s, f="%d %b %Y"):
    return datetime.strptime(s, "%Y%m%d").strftime(f)


def stat_rows(rows):
    html = "".join(f"<div class='sw-stat'><span class='k'>{k}</span><span class='v {c}'>{v}</span></div>"
                   for k, v, c in rows)
    st.markdown(html, unsafe_allow_html=True)


def clean_fig(fig, height):
    grid = "#1f2a40" if DARK else "#f0f2f5"
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=8, b=8),
                      template="plotly_dark" if DARK else "plotly_white",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(size=11, color="#8ea0b8" if DARK else "#475467"), showlegend=False)
    fig.update_xaxes(gridcolor=grid)
    fig.update_yaxes(gridcolor=grid)
    return fig


@st.cache_data
def hud_payload(step=3):
    """Small lat/lon lookup grids for the in-map (fullscreen) inspector."""
    data = load_data()
    s, w, n, e = [float(v) for v in data["latlon_bounds"]]
    ny, nx = [int(v // step) for v in data["vel_latlon"].shape]
    lats = n - (np.arange(ny) + 0.5) * (n - s) / ny
    lons = w + (np.arange(nx) + 0.5) * (e - w) / nx
    LON, LAT = np.meshgrid(lons, lats)
    X, Y = data["to_utm"].transform(LON, LAT)
    t = data["utm_transform"]
    H, W = data["vel_utm"].shape
    col = np.clip(((X - t[2]) / t[0]).astype(int), 0, W - 1)
    row = np.clip(((Y - t[5]) / t[4]).astype(int), 0, H - 1)
    inside = ((X - t[2]) / t[0] >= 0) & ((X - t[2]) / t[0] < W) & ((Y - t[5]) / t[4] >= 0) & ((Y - t[5]) / t[4] < H)
    # people within ~500 m: 7x7 box sum via integral image
    pop = np.nan_to_num(data["pop_utm"]) if data["has_pop"] else np.zeros((H, W))
    ii = np.pad(pop, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    r0, r1 = np.clip(row - 3, 0, H), np.clip(row + 4, 0, H)
    c0, c1 = np.clip(col - 3, 0, W), np.clip(col + 4, 0, W)
    pop500 = ii[r1, c1] - ii[r0, c1] - ii[r1, c0] + ii[r0, c0]

    def enc(a, dtype, nodata):
        a = np.where(np.isfinite(a) & inside, a, nodata).astype(dtype)
        return base64.b64encode(a.tobytes()).decode()

    # 3x3 median (240 m) so the hover value matches what the map shows, not one noisy pixel
    v = data["vel_utm"]
    vp = np.pad(v, 1, constant_values=np.nan)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            v3 = np.nanmedian(np.stack([vp[i:i + H, j:j + W] for i in range(3) for j in range(3)]), axis=0)
    vel = v3[row, col]
    stack = data["stack_utm"][:, row, col]
    return {
        "bounds": [s, w, n, e], "ny": ny, "nx": nx, "dates": data["dates"],
        "vel": enc(vel * 10, "<i2", -32768),
        "elev": enc(data["dem_utm"][row, col], "<i2", -32768),
        "pop": enc(np.clip(pop500, 0, 32000), "<i2", -32768),
        "valley": enc(data["valley_utm"][row, col].astype(float), "u1", 0),
        "series": enc(np.clip(stack, -3000, 3000), "<i2", -32768),
        "has_pop": data["has_pop"],
    }

@st.cache_data
def timelapse_frames(opacity, valley_only, cm_max=6.0):
    """One transparent PNG per date: cumulative vertical sinking since the first pass."""
    data = load_data()
    s, w, n, e = [float(v) for v in data["latlon_bounds"]]
    ny, nx = data["vel_latlon"].shape
    lats = n - (np.arange(ny) + 0.5) * (n - s) / ny
    lons = w + (np.arange(nx) + 0.5) * (e - w) / nx
    LON, LAT = np.meshgrid(lons, lats)
    X, Y = data["to_utm"].transform(LON, LAT)
    t = data["utm_transform"]
    H, W = data["vel_utm"].shape
    fc, fr = (X - t[2]) / t[0], (Y - t[5]) / t[4]
    inside = (fc >= 0) & (fc < W) & (fr >= 0) & (fr < H)
    col, row = np.clip(fc.astype(int), 0, W - 1), np.clip(fr.astype(int), 0, H - 1)
    keep = inside & (data["valley_utm"][row, col] if valley_only else True)
    stops = np.array([-cm_max, -cm_max * 0.6, -cm_max * 0.3, -1.0])
    cols = np.array([[127, 29, 29], [220, 38, 38], [249, 112, 102], [254, 205, 202]], dtype=float)
    frames = []
    for k in range(data["stack_utm"].shape[0]):
        cm = data["stack_utm"][k][row, col] / 10.0
        v = np.clip(np.nan_to_num(cm, nan=0.0), -cm_max, 0)
        rgb = np.stack([np.interp(v, stops, cols[:, i]) for i in range(3)], axis=-1)
        a = np.where(keep & np.isfinite(cm) & (cm <= -1.0), int(255 * opacity), 0)
        img = Image.fromarray(np.dstack([rgb, a]).astype(np.uint8), "RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        frames.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    return {"frames": frames, "bounds": [[s, w], [n, e]], "cm_max": cm_max}


class TimeLapse(MacroElement):
    """Play button that animates cumulative sinking date by date on the map."""
    _template = Template("""
{% macro script(this, kwargs) %}
(function(){
  var map = {{ this._parent.get_name() }};
  var D = {{ this.payload }};
  var css=document.createElement('style');
  css.innerHTML=".sw-tl{font-family:Inter,Segoe UI,system-ui,sans-serif;background:rgba(15,27,45,.92);color:#e6ecf5;border-radius:12px;padding:8px 12px;display:flex;align-items:center;gap:10px;box-shadow:0 6px 18px rgba(0,0,0,.3);border:1px solid #2c3e5a;min-width:330px}"+
   ".sw-tl button{background:#d92d20;border:none;color:#fff;width:34px;height:34px;border-radius:50%;font-size:14px;cursor:pointer}"+
   ".sw-tl .lbl{font-size:12px;line-height:1.3}.sw-tl .lbl b{font-size:14px}"+
   ".sw-tl .bar{flex:1;height:5px;background:#2c3e5a;border-radius:3px;overflow:hidden}.sw-tl .fill{height:100%;background:#f97066;width:0;transition:width .5s}"+
   ".sw-pin{width:14px;height:14px;border-radius:50%;background:#d92d20;border:2px solid #fff;animation:swPinP 1.8s infinite}"+
   "@keyframes swPinP{0%{box-shadow:0 0 0 0 rgba(217,45,32,.6)}70%{box-shadow:0 0 0 16px rgba(217,45,32,0)}100%{box-shadow:0 0 0 0 rgba(217,45,32,0)}}";
  document.head.appendChild(css);
  var ov=null, k=0, timer=null, M=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  function fmt(d){return parseInt(d.slice(6))+' '+M[parseInt(d.slice(4,6))-1]+' '+d.slice(0,4);}
  var c=L.control({position:'bottomright'});
  c.onAdd=function(){var d=L.DomUtil.create('div','sw-tl');
    d.innerHTML="<button title='Play time-lapse'>&#9654;</button><div class='lbl'><div>Time-lapse · cumulative sinking</div><b class='dt'>Press play</b></div><div class='bar'><div class='fill'></div></div>";
    L.DomEvent.disableClickPropagation(d); return d;};
  c.addTo(map);
  var box=c.getContainer(), btn=box.querySelector('button'), dt=box.querySelector('.dt'), fill=box.querySelector('.fill');
  var base=[]; map.eachLayer(function(l){ if(l instanceof L.ImageOverlay) base.push(l); });
  function step(){ if(!ov){ov=L.imageOverlay(D.frames[0],D.bounds,{opacity:1,interactive:false}).addTo(map);}
    ov.setUrl(D.frames[k]); dt.textContent=fmt(D.dates[k]); fill.style.width=(k/(D.frames.length-1)*100)+'%';
    k=(k+1)%D.frames.length;}
  function stop(){clearInterval(timer); timer=null; btn.innerHTML='&#9654;';
    if(ov){map.removeLayer(ov); ov=null;} base.forEach(function(l){l.setOpacity(1)}); dt.textContent='Press play'; fill.style.width='0';}
  btn.onclick=function(){ if(timer){stop(); return;}
    base.forEach(function(l){l.setOpacity(0)}); k=0; step(); timer=setInterval(step,750); btn.innerHTML='&#10074;&#10074;';};
})();
{% endmacro %}
""")

    def __init__(self, frames, dates):
        super().__init__()
        self._name = "TimeLapse"
        self.payload = json.dumps({**frames, "dates": dates})



class MapHUD(MacroElement):
    """Dashboard cards drawn inside the map, shown only in fullscreen."""
    _template = Template("""
{% macro script(this, kwargs) %}
(function(){
  var map = {{ this._parent.get_name() }};
  var P = {{ this.payload }};
  var S = {{ this.summary }};
  function dec(b, T){var s=atob(b), u=new Uint8Array(s.length); for(var i=0;i<s.length;i++)u[i]=s.charCodeAt(i); return new T(u.buffer);}
  var vel=dec(P.vel,Int16Array), elev=dec(P.elev,Int16Array), pop=dec(P.pop,Int16Array),
      valley=dec(P.valley,Uint8Array), ser=dec(P.series,Int16Array), N=P.ny*P.nx, T=P.dates.length;
  var css=document.createElement('style');
  css.innerHTML=".sw-hud{font-family:Inter,Segoe UI,system-ui,sans-serif;background:rgba(15,27,45,.93);color:#e6ecf5;border-radius:14px;padding:14px 16px;box-shadow:0 8px 24px rgba(0,0,0,.35);border:1px solid #2c3e5a;display:none}"+
  ".sw-hud .h{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#8ea0b8;margin-bottom:6px}"+
  ".sw-hud .big{font-size:38px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums}"+
  ".sw-hud .u{font-size:13px;color:#8ea0b8;margin-left:4px}"+
  ".sw-hud .row{display:flex;justify-content:space-between;font-size:12px;padding:5px 0;border-top:1px solid #23344f}"+
  ".sw-hud .row b{color:#fff;font-variant-numeric:tabular-nums}"+
  ".sw-hud .gauge{position:relative;height:8px;border-radius:4px;margin:10px 0 4px;background:linear-gradient(90deg,#7f1d1d,#dc2626,#fca5a5,#e5e7eb)}"+
  ".sw-hud .needle{position:absolute;top:-4px;width:3px;height:16px;background:#fff;border-radius:2px;transition:left .15s}"+
  ".sw-hud .gl{display:flex;justify-content:space-between;font-size:10px;color:#8ea0b8}"+
  ".sw-hud .badge{display:inline-block;font-size:11px;font-weight:600;padding:3px 8px;border-radius:6px;margin-top:8px}"+
  ".sw-hud .pin{font-size:10px;color:#8ea0b8;margin-top:6px}"+
  ".sw-tip{position:absolute;z-index:1000;pointer-events:none;display:none;font-family:Inter,Segoe UI,system-ui,sans-serif;"+
  "background:rgba(15,27,45,.94);color:#e6ecf5;border:1px solid #2c3e5a;border-radius:10px;padding:8px 11px;"+
  "box-shadow:0 6px 18px rgba(0,0,0,.35);white-space:nowrap;font-size:12px;line-height:1.35}"+
  ".sw-tip b{font-size:18px;font-variant-numeric:tabular-nums}.sw-tip .s{color:#8ea0b8;font-size:11px}";
  document.head.appendChild(css);

  function card(pos, w){var c=L.control({position:pos}); c.onAdd=function(){var d=L.DomUtil.create('div','sw-hud'); d.style.width=w+'px'; L.DomEvent.disableClickPropagation(d); L.DomEvent.disableScrollPropagation(d); return d;}; c.addTo(map); return c.getContainer();}
  var insp=card('topright',270), summ=card('bottomleft',250);

  summ.innerHTML="<div class='h'>Quetta · NISAR L-band</div>"+
    "<div class='row'><span>City centre</span><b style='color:#f97066'>"+S.city+" cm/yr</b></div>"+
    "<div class='row'><span>Fastest 1% (valley)</span><b style='color:#f97066'>"+S.fast+" cm/yr</b></div>"+
    "<div class='row'><span>Area sinking &gt; 5 cm/yr</span><b>"+S.area+" km²</b></div>"+
    "<div class='row'><span>People on that ground</span><b style='color:#f97066'>"+S.people+"</b></div>"+
    "<div class='pin'>"+P.dates[0].slice(6)+"/"+P.dates[0].slice(4,6)+" → "+P.dates[T-1].slice(6)+"/"+P.dates[T-1].slice(4,6)+"/"+P.dates[T-1].slice(0,4)+" · provisional data</div>";

  function idx(lat,lon){var b=P.bounds; if(lat<b[0]||lat>b[2]||lon<b[1]||lon>b[3])return -1;
    var r=Math.floor((b[2]-lat)/(b[2]-b[0])*P.ny), c=Math.floor((lon-b[1])/(b[3]-b[1])*P.nx);
    if(r<0||r>=P.ny||c<0||c>=P.nx)return -1; return r*P.nx+c;}
  function spark(i){var pts=[],mn=0,mx=0,v;
    for(var k=0;k<T;k++){v=ser[k*N+i]; if(v===-32768)return ''; v=v/10; pts.push(v); mn=Math.min(mn,v); mx=Math.max(mx,v);}
    var W=238,H=54,rg=(mx-mn)||1, d=pts.map(function(p,k){return (k*W/(T-1)).toFixed(1)+','+(4+(mx-p)/rg*(H-8)).toFixed(1)}).join(' ');
    var z=(4+mx/rg*(H-8)).toFixed(1);
    return "<div class='h' style='margin-top:10px'>Movement since "+P.dates[0].slice(6)+"/"+P.dates[0].slice(4,6)+" · cm</div>"+
      "<svg width='"+W+"' height='"+H+"'><line x1='0' y1='"+z+"' x2='"+W+"' y2='"+z+"' stroke='#4b5d78' stroke-dasharray='3 3'/>"+
      "<polyline fill='none' stroke='#f97066' stroke-width='2.2' points='"+d+"'/></svg>"+
      "<div class='gl'><span>Jun</span><span>"+pts[T-1].toFixed(1)+" cm</span><span>Oct</span></div>";}
  var pinned=false, pinMarker=null;
  function render(lat,lon){
    var i=idx(lat,lon), head="<div class='h'>"+(pinned?"Pinned point":"Live inspector")+" · "+lat.toFixed(4)+"°N "+lon.toFixed(4)+"°E</div>";
    if(i<0||vel[i]===-32768){insp.innerHTML=head+"<div style='font-size:13px;color:#8ea0b8'>Move over the analysis area</div>";return;}
    var v=vel[i]/10, col=v<=-8?'#f97066':(v<=-3?'#fdb022':'#75e0a7');
    var xs=[],ys=[]; for(var q=0;q<T;q++){var sv=ser[q*N+i]; if(sv!==-32768){xs.push(q);ys.push(sv);}}
    var r2=0; if(xs.length>=4){var mx_=xs.reduce(function(a,b){return a+b})/xs.length, my_=ys.reduce(function(a,b){return a+b})/ys.length, sxy=0,sxx=0,syy=0;
      for(q=0;q<xs.length;q++){sxy+=(xs[q]-mx_)*(ys[q]-my_);sxx+=(xs[q]-mx_)*(xs[q]-mx_);syy+=(ys[q]-my_)*(ys[q]-my_);} r2=(sxx>0&&syy>0)?sxy*sxy/(sxx*syy):0;}
    var badge=!valley[i]?["Bedrock / mountain","#1e3a5f","#93c5fd"]:(r2<0.3?["No clear trend · within noise","#1e3a5f","#93c5fd"]:(v<=-8?["High risk · fast sinking","#4a1414","#fda29b"]:(v<=-3?["Moderate sinking","#4a3510","#fedf89"]:["No significant sinking","#0f3d2a","#75e0a7"])));
    var left=Math.max(0,Math.min(100,(v+15)/15*100));
    insp.innerHTML=head+"<div><span class='big' style='color:"+col+"'>"+(v>0?'+':(v<0?'−':''))+Math.abs(v).toFixed(1)+"</span><span class='u'>cm / year</span></div>"+
      "<div class='gauge'><div class='needle' style='left:calc("+left+"% - 1px)'></div></div><div class='gl'><span>−15 fast</span><span>0</span></div>"+
      "<span class='badge' style='background:"+badge[1]+";color:"+badge[2]+"'>"+badge[0]+"</span>"+
      "<div class='row' style='margin-top:10px'><span>Elevation</span><b>"+(elev[i]===-32768?'–':elev[i].toLocaleString()+' m')+"</b></div>"+
      "<div class='row'><span>People within 500 m</span><b>"+(P.has_pop&&pop[i]!==-32768?pop[i].toLocaleString():'n/a')+"</b></div>"+
      "<div class='row'><span>Trend confidence</span><b>"+(r2>=0.6?'High':(r2>=0.3?'Medium':'Low'))+" · R² "+r2.toFixed(2)+"</b></div>"+
      spark(i)+"<div class='pin'>"+(pinned?"Click to move the pin · double-click to go live":"Click the map to pin a point")+"</div>";}
  var tip=L.DomUtil.create('div','sw-tip',map.getContainer());
  function tipAt(e){
    var i=idx(e.latlng.lat,e.latlng.lng);
    if(i<0||vel[i]===-32768){tip.style.display='none';return;}
    var v=vel[i]/10, col=v<=-8?'#f97066':(v<=-3?'#fdb022':(v>=3?'#93c5fd':'#e6ecf5'));
    var word=!valley[i]?'Bedrock / mountain':(v<=-8?'Fast sinking':(v<=-3?'Sinking':(v>=3?'Rising / noise':'Stable')));
    var ppl=(P.has_pop&&pop[i]!==-32768)?pop[i].toLocaleString()+' people nearby':'';
    tip.innerHTML="<b style='color:"+col+"'>"+(v>0?'+':(v<0?'\u2212':''))+Math.abs(v).toFixed(1)+"</b> cm/yr"+
      "<div class='s'>"+word+(ppl?' · '+ppl:'')+"</div>";
    var pt=e.containerPoint, W=map.getSize().x, H=map.getSize().y, tw=tip.offsetWidth||180, th=tip.offsetHeight||44;
    var x=pt.x+18, y=pt.y+18; if(x+tw>W-8)x=pt.x-tw-14; if(y+th>H-8)y=pt.y-th-14;
    tip.style.left=x+'px'; tip.style.top=y+'px'; tip.style.display='block';
  }
  map.on('mousemove',function(e){tipAt(e); if(!pinned)render(e.latlng.lat,e.latlng.lng);});
  map.on('mouseout',function(){tip.style.display='none';});
  map.on('dblclick',function(e){pinned=false; if(pinMarker){map.removeLayer(pinMarker);pinMarker=null;} render(e.latlng.lat,e.latlng.lng);});
  map.on('click',function(e){pinned=true; if(pinMarker)map.removeLayer(pinMarker);
    pinMarker=L.circleMarker(e.latlng,{radius:7,color:'#fff',weight:2,fillColor:'#f97066',fillOpacity:1}).addTo(map);
    render(e.latlng.lat,e.latlng.lng);});
  var bounds=[[P.bounds[0],P.bounds[1]],[P.bounds[2],P.bounds[3]]];
  function show(on){summ.style.display=on?'block':'none';
    if(on){setTimeout(function(){map.invalidateSize(); map.fitBounds(bounds,{padding:[20,20]});},250); render({{ this.lat0 }},{{ this.lon0 }});}
    else {setTimeout(function(){map.invalidateSize();},250);}}
  insp.style.display='block'; render({{ this.lat0 }},{{ this.lon0 }});
  map.on('enterFullscreen',function(){show(true)});
  map.on('exitFullscreen',function(){show(false)});
})();
{% endmacro %}
""")

    def __init__(self, payload, summary, lat0, lon0):
        super().__init__()
        self._name = "MapHUD"
        self.payload = json.dumps(payload)
        self.summary = json.dumps(summary)
        self.lat0, self.lon0 = lat0, lon0


data = load_data()
dates = data["dates"]
vel_all, valley = data["vel_utm"], data["valley_utm"]
vel = np.where(valley, vel_all, np.nan)
lat0, lon0 = CENTRE
r0, c0 = latlon_to_rc(data, lat0, lon0)
city_vel = float(np.nanmedian(vel_all[max(r0 - 25, 0):r0 + 25, max(c0 - 25, 0):c0 + 25]))
fastest = float(np.nanpercentile(vel, 1))
px = data["px_km2"]
def area(t): return float((vel <= -t).sum() * px)
def people(t): return float(np.nansum(data["pop_utm"][vel <= -t])) if data["has_pop"] else 0.0
icon_src = ("data:image/png;base64," + ICON_B64) if ICON_B64 else ""


def section_space(px_=0):
    st.markdown(f"<div style='height:{px_}px'></div>", unsafe_allow_html=True)


def center_cols():
    """Streamlit widgets in the same 1180 px column as the HTML sections."""
    a, b, c = st.columns([0.06, 0.88, 0.06])
    return b


# ------------------------------------------------------------------ nav + hero
H(f"""
<div class="nav"><div class="wrap">
  <div class="brand"><img src="{icon_src}" alt="">SinkWatch</div>
  <div class="links"><a href="#map">Map</a><a href="#impact">Impact</a><a href="#how">How it works</a>
    <a href="#analyze">Analyze your data</a><a href="#about">About</a></div>
</div></div>

<div class="hero"><div class="wrap">
  <div class="reveal">
    <div class="eyebrow">NASA Space Apps 2026 · Dancing with the SARs</div>
    <div class="h1">Cities are sinking. <span class="grad">Now we can see it</span> from space.</div>
    <div class="lead">From Jakarta to Tehran to Quetta, groundwater pumping is making cities sink, often unnoticed until
      buildings crack. SinkWatch turns free NASA–ISRO NISAR radar into a map anyone can read: where the ground is sinking,
      how fast, and who lives on it.</div>
    <a class="cta" href="#quetta">Explore the first map ↓</a><a class="cta2" href="#how">How it works →</a>
  </div>
  <div class="hero-art reveal"><img src="{icon_src}" alt="SinkWatch"></div>
</div>
<div class="wrap plain"><div class="stats reveal">
  <div class="stat"><div class="n hot">1 in 5</div><div class="l">people may live on sinking ground by 2040<br>(Science, 2021)</div></div>
  <div class="stat"><div class="n">12 days</div><div class="l">for NISAR to scan the whole planet, free and open</div></div>
  <div class="stat"><div class="n hot">Any city</div><div class="l">the same pipeline works wherever NISAR passes</div></div>
</div></div></div>
""")

# ------------------------------------------------------------------ map
H(f"""
<div class="sec" id="quetta"><div class="wrap">
  <div class="maphead">
    <div><div class="kicker">First city · Quetta, Pakistan</div>
      <div class="h2">Quetta is sinking up to <span class="grad">{abs(fastest):.1f} cm</span> a year.</div>
      <div class="sub">Red is sinking. Hover anywhere for the speed and the people nearby, click to pin a point,
        press ▶ for the time-lapse, or ⛶ for a fullscreen dashboard.</div>
      <div class="mini"><div><b class="hot">{abs(city_vel):.1f} cm/yr</b>city centre</div><div><b>{area(5):,.0f} km²</b>sinking &gt; 5 cm/yr</div>
        <div><b class="hot">{people(5):,.0f}</b>people on that ground</div><div><b>{fmt_date(dates[0], '%b')}–{fmt_date(dates[-1], '%b %Y')}</b>9 NISAR radar pairs</div></div></div>
    <div class="legend"><span>−15 cm/yr</span><div class="bar"></div><span>0</span></div>
  </div>
</div></div>
""")

H('<div id="map" style="position:relative; top:-12px"></div>')
with center_cols():
    sp, settings = st.columns([0.8, 0.2])
    with settings:
        with st.popover("⚙  Map settings", use_container_width=True):
            basemap = st.selectbox("Basemap", ["Dark", "Light", "Satellite", "Streets"], index=0 if DARK else 1)
            threshold = st.slider("Hide motion below (cm/yr)", 0.0, 10.0, 3.0, 0.5)
            opacity = st.slider("Opacity", 0.2, 1.0, 0.8, 0.05)
            valley_only = st.toggle("Valley floor only", value=True,
                                    help="Groundwater subsidence happens in soft valley sediments; signal on bedrock is treated as noise.")
            sinking_only = st.toggle("Sinking only", value=True)
    s, w, n, e = [float(v) for v in data["latlon_bounds"]]
    tiles = {
        "Light": ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                  "Esri, HERE, Garmin, OpenStreetMap contributors"),
        "Satellite": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "Esri World Imagery"),
        "Streets": ("OpenStreetMap", None),
        "Dark": ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                 "Esri, HERE, Garmin, OpenStreetMap contributors"),
    }[basemap]
    m = folium.Map(location=[30.20, lon0 + 0.10], zoom_start=11.5, zoom_snap=0.25, tiles=None, control_scale=True)
    folium.TileLayer(tiles=tiles[0], attr=tiles[1], name=basemap).add_to(m)
    folium.raster_layers.ImageOverlay(image=overlay_png(threshold, opacity, sinking_only, valley_only),
                                      bounds=[[s, w], [n, e]], interactive=False).add_to(m)
    folium.Marker([lat0, lon0], tooltip="Quetta city centre", icon=folium.DivIcon(
        icon_size=(18, 18), icon_anchor=(9, 9), html="<div class='sw-pin'></div>")).add_to(m)
    TimeLapse(timelapse_frames(opacity, valley_only), dates).add_to(m)
    Fullscreen(title="Fullscreen dashboard", title_cancel="Exit fullscreen").add_to(m)
    MapHUD(hud_payload(), {"city": f"{abs(city_vel):.1f}", "fast": f"{abs(fastest):.1f}",
                           "area": f"{area(5):,.0f}", "people": f"{people(5):,.0f}"}, lat0, lon0).add_to(m)
    st_folium(m, key=f"v2_map_{basemap}", height=680, use_container_width=True, returned_objects=[])

# ------------------------------------------------------------------ impact
rows = [(t, area(t), people(t)) for t in (2, 5, 8, 10)]
cards = "".join(f"<div class='card'><div class='big'>{p/1000:,.0f}k</div><div class='t'>people</div>"
                f"<div class='small'>on ground sinking faster than <b>{t} cm/yr</b> · {a:,.0f} km²</div></div>"
                for t, a, p in rows)
H(f"""
<div class="sec" id="impact"><div class="wrap">
  <div class="kicker">The impact</div>
  <div class="h2">Who lives on sinking ground</div>
  <div class="sub">Cracked walls, broken pipes and worse flooding come long after the ground starts to drop.
    Knowing <i>where</i> and <i>who</i> lets a city act first.</div>
  <div class="grid4">{cards}</div>
  <div class="grid3">
    <div class="card"><div class="ic">🏘️</div><div class="t">Protect neighbourhoods</div><div class="d">See which streets and buildings to inspect first.</div></div>
    <div class="card"><div class="ic">💧</div><div class="t">Manage groundwater</div><div class="d">Find where pumping is making the city sink.</div></div>
    <div class="card"><div class="ic">🚨</div><div class="t">Early warning</div><div class="d">Catch fast sinking before floods and damage.</div></div>
  </div>
</div></div>

<div class="sec"><div class="wrap">
  <div class="kicker">Why it matters</div>
  <div class="h2">One problem, many cities</div>
  <div class="grid3">
    <div class="card"><div class="t">Jakarta</div><div class="d">Sinking so fast that Indonesia is moving its capital city.</div></div>
    <div class="card"><div class="t">Tehran</div><div class="d">Among the fastest-sinking capitals on Earth, driven by groundwater pumping.</div></div>
    <div class="card"><div class="t">Quetta</div><div class="d">Parts of the valley have dropped about 2.7 m since 2003, and it is still going: up to {abs(fastest):.1f} cm a year.</div></div>
  </div>
  <div class="quote">By 2040, nearly 1 in 5 people may live where the ground can sink.
    <span>Herrera-García et al., Science (2021)</span></div>
</div></div>

<div class="sec" id="how"><div class="wrap">
  <div class="kicker">How it works</div>
  <div class="h2">From radar in orbit to a map in your browser</div>
  <div class="grid4">
    <div class="card"><div class="step-n">STEP 1</div><div class="ic" style="margin-top:10px">🛰️</div><div class="t">Radar from space</div>
      <div class="d">NASA–ISRO NISAR's L-band radar sees the ground through clouds, day and night, every 12 days.</div></div>
    <div class="card"><div class="step-n">STEP 2</div><div class="ic" style="margin-top:10px">🧹</div><div class="t">Clean the signal</div>
      <div class="d">Remove the ionosphere and the weather that follows the mountains.</div></div>
    <div class="card"><div class="step-n">STEP 3</div><div class="ic" style="margin-top:10px">📏</div><div class="t">Measure the sinking</div>
      <div class="d">Stack 9 radar pairs (Jun–Oct 2026) into centimetres per year for every 80 m.</div></div>
    <div class="card"><div class="step-n">STEP 4</div><div class="ic" style="margin-top:10px">🏘️</div><div class="t">Count the people</div>
      <div class="d">Overlay WorldPop population to see who lives on the sinking ground.</div></div>
  </div>
</div></div>
""")

with center_cols():
    section_space(18)
    with st.expander("The full method, for scientists"):
        st.markdown(
            "1. **Data:** 9 consecutive NISAR L2 GUNW interferograms (12-day pairs), track 041 ascending, frame 017, "
            f"{fmt_date(dates[0])} → {fmt_date(dates[-1])}, streamed from NASA's ASF DAAC (no 20 GB download).\n"
            "2. **Ionosphere:** NISAR's split-spectrum ionosphere phase screen is subtracted from every pair.\n"
            "3. **Troposphere + tilt:** fit a·row + b·col + c·elevation + d against Copernicus GLO-30, using only data "
            "outside an 8 km circle around the city, and remove it.\n"
            "4. **Stack:** sum the 9 cleaned pairs; displacement = −λ/4π · phase, λ = 24.2 cm.\n"
            "5. **Vertical:** line-of-sight ÷ cos(45.1°). Valley floor = elevation < 1,900 m and slope < 5°.\n"
            "6. **Exposure:** WorldPop 2020 (constrained, UN-adjusted) summed on the same 80 m grid.\n"
            "7. **Trust:** every point gets an R² trend-confidence score, so noisy points are flagged.")
    with st.expander("Checked against published studies"):
        refs = [("SinkWatch · city centre (NISAR 2026)", abs(city_vel), "#f97066"),
                ("SinkWatch · fastest 1% (NISAR 2026)", abs(fastest), "#f97066"),
                ("Kakar et al. 2025 · max after 2016 (InSAR)", 16.0, "#94a3b8"),
                ("Kakar et al. 2024 · central GNSS after 2016", 16.6, "#94a3b8"),
                ("Kakar et al. 2024 · valley minimum (InSAR)", 3.2, "#cbd5e1")]
        fig = go.Figure(go.Bar(y=[r[0] for r in refs], x=[r[1] for r in refs], orientation="h",
                               marker_color=[r[2] for r in refs], text=[f"{r[1]:.1f} cm/yr" for r in refs],
                               textposition="outside"))
        clean_fig(fig, 300).update_yaxes(autorange="reversed")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.markdown("Published Sentinel-1 InSAR and GPS studies report **3.2–16 cm/yr** across the Quetta valley, "
                    "fastest in the centre. SinkWatch finds the same hotspot with consistent rates from only 120 days "
                    "of NISAR data. *Kakar et al. (2025) Natural Hazards, doi:10.1007/s11069-025-07226-y; "
                    "Kakar et al. (2024) Remote Sensing 16(9):1521.*")
    with st.expander("Limitations"):
        st.markdown("- Provisional NISAR products (calibrated, still being validated)\n"
                    "- 120-day record, so the yearly rate is an estimate that will sharpen with more passes\n"
                    "- One viewing direction, so vertical motion is assumed\n"
                    "- Some leftover atmosphere away from the valley\n"
                    "- Exposure shows who lives on sinking ground; it is not a building-damage model")

# ------------------------------------------------------------------ analyze your data
# ================================================================== ANALYZE YOUR DATA
SAMPLE_TIF = "app_data/sample_quetta_velocity_cm_yr.tif"
UNIT_TO_CM = {"cm/yr": 1.0, "mm/yr": 0.1, "m/yr": 100.0}


@st.cache_data(max_entries=4, show_spinner="Reading your map…")
def analyze_raster(raw, unit, flip, inc_deg, max_px=1200):
    """Read any single-band velocity GeoTIFF, convert to vertical cm/yr, and reproject for display."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import calculate_default_transform, reproject
    from rasterio.transform import Affine

    with rasterio.MemoryFile(raw) as mf, mf.open() as src:
        if src.crs is None:
            raise ValueError("This file has no map projection (CRS), so SinkWatch can't place it on the map.")
        f = max(src.width / max_px, src.height / max_px, 1.0)
        h, w = int(round(src.height / f)), int(round(src.width / f))
        arr = src.read(1, out_shape=(h, w), resampling=Resampling.average, masked=True)
        arr = np.ma.filled(arr.astype("float64"), np.nan)
        tr = src.transform * Affine.scale(src.width / w, src.height / h)
        crs = src.crs

    arr[~np.isfinite(arr)] = np.nan
    vel = arr * UNIT_TO_CM[unit]
    if flip:
        vel = -vel
    if inc_deg:
        vel = vel / np.cos(np.radians(inc_deg))
    if np.isfinite(vel).sum() < 10:
        raise ValueError("The file has almost no valid pixels.")

    # pixel area in km² (works for metre and degree grids)
    if crs.is_geographic:
        lat = tr.f + (np.arange(h) + 0.5) * tr.e
        row_km2 = abs(tr.a * tr.e) * (111.32 ** 2) * np.cos(np.radians(lat))
        px_km2 = np.repeat(row_km2[:, None], w, axis=1)
    else:
        px_km2 = np.full((h, w), abs(tr.a * tr.e) / 1e6)

    # reproject to WGS84 for the web map
    dst_tr, dw, dh = calculate_default_transform(crs, "EPSG:4326", w, h,
                                                 *rasterio.transform.array_bounds(h, w, tr))
    vel_ll = np.full((dh, dw), np.nan)
    reproject(vel, vel_ll, src_transform=tr, src_crs=crs, dst_transform=dst_tr, dst_crs="EPSG:4326",
              resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
    s, wst, n, e = (dst_tr.f + dh * dst_tr.e, dst_tr.c, dst_tr.f, dst_tr.c + dw * dst_tr.a)
    return {"vel": vel, "vel_ll": vel_ll, "px_km2": px_km2, "tr": tuple(tr)[:6], "crs": crs.to_wkt(),
            "bounds": (s, wst, n, e), "shape": (h, w), "crs_name": crs.to_string()}


class ClickInspect(MacroElement):
    """Click anywhere on an uploaded map to see the value at that point (runs in the browser)."""
    _template = Template("""
{% macro script(this, kwargs) %}
(function(){
              var map = {{ this._parent.get_name() }}, G = {{ this.grid }}, S={{ this.s }}, W={{ this.w }}, N={{ this.n }}, E={{ this.e }};
              var ny = G.length, nx = G[0].length;
              map.on('click', function(ev){
                var la = ev.latlng.lat, lo = ev.latlng.lng, msg;
                if (la<S||la>N||lo<W||lo>E){ msg = 'Outside your map'; }
                else {
                  var r = Math.min(ny-1, Math.floor((N-la)/(N-S)*ny));
                  var c = Math.min(nx-1, Math.floor((lo-W)/(E-W)*nx));
                  var v = G[r][c];
                  if (v===null){ msg = 'No data here'; }
                  else {
                    var word = v < -0.5 ? 'Sinking' : (v > 0.5 ? 'Rising' : 'Stable');
                    var col = v < -0.5 ? '#d92d20' : (v > 0.5 ? '#2563eb' : '#475467');
                    msg = '<div style="font:600 15px system-ui;color:'+col+'">'+(v>0?'+':'')+v.toFixed(1).replace('-','\u2212')+' cm/yr</div>'+
                          '<div style="font:12px system-ui;color:#475467">'+word+' · '+la.toFixed(4)+', '+lo.toFixed(4)+'</div>';
                  }
                }
                L.popup().setLatLng(ev.latlng).setContent(msg).openOn(map);
              });
            })();
{% endmacro %}
""")

    def __init__(self, grid_json, s, w, n, e):
        super().__init__()
        self._name = "ClickInspect"
        self.grid, self.s, self.w, self.n, self.e = grid_json, s, w, n, e



H("""
<div class="sec" id="analyze"><div class="wrap">
  <div class="kicker">Analyze your data</div>
  <div class="h2">Bring any city's ground-motion map</div>
  <div class="sub">Upload a velocity GeoTIFF (from SinkWatch, ASF HyP3, LiCSBAS, MintPy…) and get the same analysis instantly.
    Files stay in your session and are not stored.</div>
</div></div>
""")

with center_cols():
    section_space(10)
    a_l, a_r = st.columns([0.3, 0.7], gap="large")
    with a_l:
        src_mode = st.radio("Source", ["Try the Quetta sample", "Upload a GeoTIFF"], label_visibility="collapsed")
        raw = None
        if src_mode == "Upload a GeoTIFF":
            up = st.file_uploader("Velocity GeoTIFF", type=["tif", "tiff"], label_visibility="collapsed")
            if up is not None:
                raw = up.getvalue()
        else:
            try:
                with open(SAMPLE_TIF, "rb") as fh:
                    raw = fh.read()
            except OSError:
                st.warning("Sample file not found.")
        with st.popover("⚙  Units & display", use_container_width=True):
            unit = st.selectbox("Velocity units", list(UNIT_TO_CM), index=0)
            flip = st.toggle("Positive values mean sinking", value=False)
            is_los = st.toggle("Values are line-of-sight", value=False)
            inc = st.slider("Incidence angle (°)", 20.0, 50.0, 39.0, 0.5) if is_los else 0.0
            u_thr = st.slider("Hide motion below (cm/yr) ", 0.0, 10.0, 2.0, 0.5)
            u_op = st.slider("Opacity ", 0.2, 1.0, 0.8, 0.05)
        try:
            with open(SAMPLE_TIF, "rb") as fh:
                st.download_button("Download sample .tif", fh.read(), file_name="sample_quetta_velocity_cm_yr.tif",
                                   mime="image/tiff", use_container_width=True)
        except OSError:
            pass
        res, err = None, None
        if raw is not None:
            try:
                res = analyze_raster(raw, unit, flip, inc)
            except Exception as ex:
                err = str(ex) or "Could not read this file. Is it a GeoTIFF?"
        if err:
            st.error(err)
        if res is not None:
            v, pa = res["vel"], res["px_km2"]
            ok = np.isfinite(v)
            H(f"""
<div class="card" style="margin-top:14px;padding:22px">
  <div class="big">{abs(min(np.nanpercentile(v, 1), 0)):.1f}<span style="font-size:16px;color:var(--muted2)"> cm/yr</span></div>
  <div class="small">fastest 1% of your map</div>
  <div style="height:14px"></div>
  <div class="t" style="margin:0">{float(pa[ok & (v <= -5)].sum()):,.1f} km²</div><div class="small" style="margin-top:2px">sinking faster than 5 cm/yr</div>
  <div style="height:10px"></div>
  <div class="t" style="margin:0">{float(pa[ok].sum()):,.0f} km²</div><div class="small" style="margin-top:2px">area covered</div>
</div>""")
    with a_r:
        if res is None:
            st.markdown("<div class='card' style='height:520px;display:flex;align-items:center;justify-content:center'>"
                        "<div class='d'>Choose the sample or upload a GeoTIFF.</div></div>", unsafe_allow_html=True)
        else:
            s2, w2, n2, e2 = res["bounds"]
            span = max(e2 - w2, (n2 - s2) * 1.3, 1e-4)
            zoom = int(np.clip(np.floor(np.log2(800 * 360 / (256 * span))), 2, 16))
            um = folium.Map(location=[(s2 + n2) / 2, (w2 + e2) / 2], zoom_start=zoom, tiles=None, control_scale=True)
            folium.TileLayer(tiles=f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_{'Dark' if DARK else 'Light'}_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}",
                             attr="Esri, HERE, Garmin, OpenStreetMap contributors").add_to(um)
            shown = np.where(res["vel_ll"] > 0, np.nan, res["vel_ll"])
            img = Image.fromarray(colorize(shown, u_thr, u_op), "RGBA")
            buf = io.BytesIO(); img.save(buf, format="PNG")
            folium.raster_layers.ImageOverlay(image="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
                                              bounds=[[s2, w2], [n2, e2]], interactive=False).add_to(um)
            g = res["vel_ll"]; stp = max(1, int(np.ceil(max(g.shape) / 300))); gs = g[::stp, ::stp]
            grid = [[None if not np.isfinite(x) else round(float(x), 1) for x in row] for row in gs]
            ClickInspect(json.dumps(grid), s2, w2, n2, e2).add_to(um)
            components.html(um.get_root().render(), height=520)
            st.markdown("<div class='note'>Click anywhere on the map to read the speed at that point.</div>",
                        unsafe_allow_html=True)

# ------------------------------------------------------------------ about + footer
H(f"""
<div class="sec" id="about"><div class="wrap">
  <div class="kicker">What's next</div>
  <div class="h2">From one city to every city</div>
  <div class="timeline">
    <div class="tl"><div class="w">Now</div><div class="x">Quetta from NISAR, plus <i>Analyze your data</i> for any velocity map.</div></div>
    <div class="tl"><div class="w">Next</div><div class="x">Jakarta, Tehran and Mexico City through the same pipeline.</div></div>
    <div class="tl"><div class="w">Then</div><div class="x">Pick any city on Earth; SinkWatch processes the latest NISAR pass automatically.</div></div>
    <div class="tl"><div class="w">Later</div><div class="x">Alerts when a neighbourhood starts sinking faster.</div></div>
  </div>

  <div class="foot"><div class="row">
    <div><div class="brand" style="font-size:16px"><img src="{icon_src}" alt="" style="width:28px;height:28px">SinkWatch</div>
      <div style="margin-top:10px">Built solo by Muhammad Asif (Pakistan) for the NASA Space Apps Challenge 2026 · Dancing with the SARs.</div>
      <div class="si">Code and visuals created with SI assistance (Claude by Anthropic); all results come from real NISAR data.</div></div>
    <div style="max-width:520px">
      <span class="chip">NASA-ISRO NISAR · L2 GUNW (provisional)</span><span class="chip">Track 041 asc · frame 017 · 80 m</span>
      <span class="chip">{fmt_date(dates[0], '%d %b')} → {fmt_date(dates[-1])}</span><span class="chip">Copernicus GLO-30 DEM</span>
      <span class="chip">WorldPop 2020</span><span class="chip">Esri basemaps</span>
      <div style="margin-top:8px"><a href="https://github.com/AsifMarwat/SinkWatch">GitHub</a> · <a href="https://youtu.be/uisDu4dTS_8">Demo video</a></div>
    </div>
  </div></div>
</div></div>
""")
