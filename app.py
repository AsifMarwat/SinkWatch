"""
SinkWatch - Seeing the ground move from space.
Streamlit web app for NASA Space Apps 2026 (Dancing with the SARs).

Run:
  python -m streamlit run app.py
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

APP_DATA = "app_data/sinkwatch_quetta.npz"
CENTRE = (30.19, 67.01)  # Quetta city centre (lat, lon)
VMAX = 15.0               # colour scale limit, cm/yr
ACCENT = "#0b63ce"
RED = "#d92d20"

# ------------------------------------------------------------------ theme toggle
DARK = st.toggle("Dark mode", value=False, key="dark")

# ------------------------------------------------------------------ style
st.markdown(
    f"""
<style>
#MainMenu, header[data-testid="stHeader"], footer {{visibility: hidden; height: 0;}}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{display: none;}}
.block-container {{padding: 0 1.2rem 1rem 1.2rem; max-width: 100%;}}
html, body, [class*="css"] {{font-family: "Inter", "Segoe UI", system-ui, sans-serif;}}

.sw-topbar {{display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:1rem;
  background:#0f1b2d; color:#fff; margin:0 -1.2rem .6rem -1.2rem; padding:.7rem 1.4rem;}}
.sw-brand {{display:flex; align-items:center; gap:.7rem;}}
.sw-logo {{width:54px; height:54px; border-radius:12px; background:{RED}; display:flex; overflow:hidden;
  align-items:center; justify-content:center; font-weight:700; font-size:16px; color:#fff;
  box-shadow:0 0 0 1px rgba(255,255,255,.15), 0 4px 14px rgba(249,112,102,.35);}}
.sw-logo img {{width:100%; height:100%; object-fit:cover; display:block;}}
.sw-title {{font-size:1.7rem; font-weight:700; letter-spacing:-.02em; line-height:1.1;}}
.sw-center {{text-align:center;}}
.sw-sub {{font-size:.78rem; color:#a9b6c8;}}
.sw-event {{font-size:.68rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:#f97066; margin-bottom:.15rem;}}
.sw-tag {{font-size:.82rem; color:#a9b6c8; margin-top:.1rem;}}
.sw-chips {{display:flex; gap:.35rem; flex-wrap:wrap; justify-content:flex-end; max-width:520px; justify-self:end;}}
.sw-chip {{font-size:.72rem; padding:.2rem .55rem; border-radius:999px; background:#1c2b42;
  border:1px solid #2c3e5a; color:#d7e0ec; white-space:nowrap;}}
.sw-chip.warn {{background:#3a2a0b; border-color:#6b4c12; color:#f6d38a;}}

div[data-baseweb="tab-list"] {{gap:0; border-bottom:1px solid #e3e8ef; background:#f7f9fc;
  margin:0 -1.2rem .8rem -1.2rem; padding:0 1.2rem;}}
button[data-baseweb="tab"] {{padding:.55rem 1.1rem; font-size:.88rem; color:#475467;}}
button[data-baseweb="tab"][aria-selected="true"] {{color:{ACCENT}; font-weight:600;}}
div[data-baseweb="tab-highlight"] {{background:{ACCENT}; height:2px;}}

[class*="st-key-panel_"] {{border-radius:10px !important; border:1px solid #e3e8ef !important;
  background:#ffffff; padding:.9rem 1rem !important;}}
.sw-panel-h {{font-size:.72rem; font-weight:650; text-transform:uppercase; letter-spacing:.07em;
  color:#667085; margin:.1rem 0 .5rem 0;}}
.sw-stat {{display:flex; justify-content:space-between; align-items:baseline; padding:.42rem 0;
  border-bottom:1px solid #f0f2f5;}}
.sw-stat:last-child {{border-bottom:none;}}
.sw-stat .k {{font-size:.8rem; color:#667085;}}
.sw-stat .v {{font-size:1.05rem; font-weight:650; color:#101828;}}
.sw-stat .v.hot {{color:{RED};}}
.sw-legend {{height:10px; border-radius:5px; margin:.3rem 0 .15rem 0;
  background:linear-gradient(90deg,#7f1d1d,#dc2626,#fca5a5,#f8fafc,#93c5fd,#2563eb,#1e3a8a);}}
.sw-legend-l {{display:flex; justify-content:space-between; font-size:.7rem; color:#667085;}}
.sw-badge {{display:inline-block; font-size:.78rem; font-weight:600; padding:.25rem .6rem; border-radius:6px;}}
.sw-badge.high {{background:#fef3f2; color:#b42318; border:1px solid #fecdca;}}
.sw-badge.mod {{background:#fffaeb; color:#b54708; border:1px solid #fedf89;}}
.sw-badge.ok {{background:#ecfdf3; color:#067647; border:1px solid #abefc6;}}
.sw-badge.info {{background:#eff8ff; color:#175cd3; border:1px solid #b2ddff;}}
.sw-status {{display:flex; gap:1.2rem; flex-wrap:wrap; font-size:.72rem; color:#667085;
  background:#f7f9fc; border:1px solid #e3e8ef; border-radius:8px; padding:.35rem .8rem; margin-top:.5rem;}}
.sw-status b {{color:#344054; font-weight:600;}}
.sw-hero-num {{font-size:2.1rem; font-weight:700; color:{RED}; line-height:1;}}
.sw-note {{font-size:.8rem; color:#667085;}}

@keyframes swFade {{from {{opacity:0; transform:translateY(8px);}} to {{opacity:1; transform:none;}}}}
@keyframes swPulse {{0% {{box-shadow:0 0 0 0 rgba(217,45,32,.55);}} 70% {{box-shadow:0 0 0 12px rgba(217,45,32,0);}} 100% {{box-shadow:0 0 0 0 rgba(217,45,32,0);}}}}
@keyframes swBlink {{0%,100% {{opacity:1;}} 50% {{opacity:.25;}}}}
@media (prefers-reduced-motion: no-preference) {{
  [class*="st-key-panel_"] {{animation: swFade .55s ease both;}}
  .sw-live {{animation: swBlink 1.6s infinite;}}
  .sw-hero-num {{animation: swFade .8s ease both;}}
}}
.sw-live {{display:inline-block; width:7px; height:7px; border-radius:50%; background:#32d583; margin-right:5px; vertical-align:middle;}}
.block-container {{position:relative;}}
.st-key-dark {{position:absolute; top:.35rem; right:1.4rem; z-index:1000; width:auto !important;}}
.st-key-dark label p {{color:#d7e0ec !important; font-size:.8rem !important;}}
.sw-topbar {{margin-top:-1rem !important; padding-top:1.6rem !important;}}
</style>
""",
    unsafe_allow_html=True,
)

if DARK:
    st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"] {background:#0b1220 !important;}
[class*="st-key-panel_"] {background:#121c30 !important; border:1px solid #24344f !important;}
.stApp, .stApp p, .stApp li, .stApp span, .stApp label, [data-testid="stWidgetLabel"] p,
[data-testid="stMarkdownContainer"] {color:#d7e0ec;}
.sw-stat {border-color:#1f2a40 !important;}
.sw-stat .v {color:#f1f5f9 !important;}
.sw-stat .v.hot, .sw-hero-num {color:#f97066 !important;}
.sw-panel-h, .sw-note, .sw-stat .k, .sw-legend-l {color:#8ea0b8 !important;}
div[data-baseweb="tab-list"] {background:#0f1729 !important; border-color:#1f2a40 !important;}
button[data-baseweb="tab"] p {color:#8ea0b8 !important;}
button[data-baseweb="tab"][aria-selected="true"] p {color:#60a5fa !important;}
div[data-baseweb="tab-highlight"] {background:#60a5fa !important;}
.sw-status {background:#0f1729 !important; border-color:#1f2a40 !important;}
.sw-status b {color:#d7e0ec !important;}
[data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stSelectbox"] [data-baseweb="select"] div,
div[data-baseweb="popover"] ul, div[data-baseweb="popover"] li {background:#0f1729 !important; color:#d7e0ec !important; border-color:#2c3e5a !important;}
[data-testid="stSelectbox"] svg {fill:#8ea0b8 !important;}
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"], [data-testid="stSliderThumbValue"] {color:#8ea0b8 !important;}
[data-testid="stTable"], [data-testid="stDataFrame"] {filter: invert(.9) hue-rotate(180deg);}
.sw-topbar {background:#060b14 !important; border-bottom:1px solid #1f2a40;}
.sw-badge.high {background:#3d1414 !important; color:#fda29b !important; border-color:#7a271a !important;}
.sw-badge.mod {background:#3d2a0a !important; color:#fedf89 !important; border-color:#7a4e0f !important;}
.sw-badge.ok {background:#0c3324 !important; color:#75e0a7 !important; border-color:#085d3a !important;}
.sw-badge.info {background:#102a4c !important; color:#84caff !important; border-color:#1849a9 !important;}
</style>""", unsafe_allow_html=True)


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

    vel = data["vel_utm"][row, col]
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



class FullscreenHUD(MacroElement):
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
  ".sw-hud .pin{font-size:10px;color:#8ea0b8;margin-top:6px}";
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
      spark(i)+"<div class='pin'>"+(pinned?"Click elsewhere to move the pin":"Click the map to pin a point")+"</div>";}
  map.on('mousemove',function(e){if(!pinned)render(e.latlng.lat,e.latlng.lng);});
  map.on('click',function(e){pinned=true; if(pinMarker)map.removeLayer(pinMarker);
    pinMarker=L.circleMarker(e.latlng,{radius:7,color:'#fff',weight:2,fillColor:'#f97066',fillOpacity:1}).addTo(map);
    render(e.latlng.lat,e.latlng.lng);});
  var bounds=[[P.bounds[0],P.bounds[1]],[P.bounds[2],P.bounds[3]]];
  function show(on){insp.style.display=on?'block':'none'; summ.style.display=on?'block':'none';
    if(on){setTimeout(function(){map.invalidateSize(); map.fitBounds(bounds,{padding:[20,20]});},250); render({{ this.lat0 }},{{ this.lon0 }});}
    else {setTimeout(function(){map.invalidateSize();},250);}}
  map.on('enterFullscreen',function(){show(true)});
  map.on('exitFullscreen',function(){show(false)});
})();
{% endmacro %}
""")

    def __init__(self, payload, summary, lat0, lon0):
        super().__init__()
        self._name = "FullscreenHUD"
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

# ------------------------------------------------------------------ top bar
st.markdown(
    f"""
<div class="sw-topbar">
  <div class="sw-brand">
    <div class="sw-logo">{('<img src="data:image/png;base64,' + ICON_B64 + '" alt="SinkWatch logo">') if ICON_B64 else 'S'}</div>
    <div class="sw-sub"><span class="sw-live"></span>Land subsidence monitor<br>Quetta, Pakistan</div>
  </div>
  <div class="sw-center">
    <div class="sw-event">NASA Space Apps Challenge 2026 · Dancing with the SARs</div>
    <div class="sw-title">SinkWatch</div>
    <div class="sw-tag">Seeing the ground move from space</div>
  </div>
  <div class="sw-chips">
    <span class="sw-chip">NASA-ISRO NISAR · L-band GUNW</span>
    <span class="sw-chip">{fmt_date(dates[0], '%d %b')} → {fmt_date(dates[-1])}</span>
    <span class="sw-chip">Track 041 asc · frame 017 · 80 m</span>
    <span class="sw-chip warn">Provisional data</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

tab_map, tab_exp, tab_up, tab_val, tab_method, tab_about = st.tabs(
    ["Map", "Exposure", "Analyze your data", "Validation", "Method", "About"])

# ================================================================== MAP
with tab_map:
    left, centre, right = st.columns([0.95, 2.7, 1.25], gap="small")

    with left:
        with panel():
            st.markdown("<div class='sw-panel-h'>Layers</div>", unsafe_allow_html=True)
            show_layer = st.checkbox("Subsidence velocity", value=True)
            valley_only = st.checkbox("Valley floor only", value=True,
                                      help="Groundwater subsidence happens in soft valley sediments. "
                                           "Signal on bedrock mountains is treated as weather noise.")
            sinking_only = st.checkbox("Sinking only", value=True)
            show_box = st.checkbox("Analysis extent", value=True)
        with panel():
            st.markdown("<div class='sw-panel-h'>Display</div>", unsafe_allow_html=True)
            threshold = st.slider("Hide motion below (cm/yr)", 0.0, 10.0, 3.0, 0.5)
            opacity = st.slider("Opacity", 0.2, 1.0, 0.75, 0.05)
            basemap = st.selectbox("Basemap", ["Light", "Satellite", "Streets", "Dark"], index=3 if DARK else 0)
        with panel():
            st.markdown("<div class='sw-panel-h'>Legend · vertical speed</div>", unsafe_allow_html=True)
            st.markdown("<div class='sw-legend'></div><div class='sw-legend-l'><span>−15</span>"
                        "<span>0</span><span>+15 cm/yr</span></div>"
                        "<div class='sw-note' style='margin-top:.35rem'>Red = sinking · blue = rising</div>",
                        unsafe_allow_html=True)

    with centre:
        s, w, n, e = [float(v) for v in data["latlon_bounds"]]
        tiles = {
            "Light": ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                      "Esri, HERE, Garmin, OpenStreetMap contributors"),
            "Satellite": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                          "Esri World Imagery"),
            "Streets": ("OpenStreetMap", None),
            "Dark": ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                     "Esri, HERE, Garmin, OpenStreetMap contributors"),
        }[basemap]
        m = folium.Map(location=[lat0, lon0], zoom_start=11, tiles=None, control_scale=True)
        folium.TileLayer(tiles=tiles[0], attr=tiles[1], name=basemap).add_to(m)
        if show_layer:
            folium.raster_layers.ImageOverlay(
                image=overlay_png(threshold, opacity, sinking_only, valley_only),
                bounds=[[s, w], [n, e]], interactive=False).add_to(m)
        if show_box:
            folium.Rectangle([[s, w], [n, e]], color="#667085", weight=1, fill=False, dash_array="4").add_to(m)
        folium.Marker([lat0, lon0], tooltip="Quetta city centre", icon=folium.DivIcon(
            icon_size=(18, 18), icon_anchor=(9, 9),
            html="<div class='sw-pin'></div>")).add_to(m)
        TimeLapse(timelapse_frames(opacity, valley_only), dates).add_to(m)
        Fullscreen(title="Fullscreen with live inspector", title_cancel="Exit fullscreen").add_to(m)
        _area5 = float((vel <= -5).sum() * data["px_km2"])
        _ppl5 = float(np.nansum(data["pop_utm"][vel <= -5])) if data["has_pop"] else None
        FullscreenHUD(hud_payload(), {
            "city": f"{abs(city_vel):.1f}", "fast": f"{abs(fastest):.1f}", "area": f"{_area5:,.0f}",
            "people": f"{_ppl5:,.0f}" if _ppl5 is not None else "n/a"}, lat0, lon0).add_to(m)
        MousePosition(position="bottomright", separator=" · ", num_digits=4, prefix="").add_to(m)
        out = st_folium(m, key="sw_map", height=640, use_container_width=True, returned_objects=["last_clicked"])
        st.markdown(
            "<div class='sw-status'><span><b>CRS</b> WGS84 / UTM 42N (EPSG:32642)</span>"
            "<span><b>Pixel</b> 80 m</span><span><b>Input</b> 9 NISAR GUNW pairs · 120 days</span>"
            "<span><b>Tip</b> click the map to inspect · ⛶ fullscreen shows a live inspector</span></div>",
            unsafe_allow_html=True)

    with right:
        with panel():
            st.markdown("<div class='sw-panel-h'>Quetta summary</div>", unsafe_allow_html=True)
            risk_area = float((vel <= -5).sum() * data["px_km2"])
            people5 = float(np.nansum(data["pop_utm"][vel <= -5])) if data["has_pop"] else None
            stat_rows([
                ("City centre", f"{abs(city_vel):.1f} cm/yr", "hot"),
                ("Fastest 1% (valley)", f"{abs(fastest):.1f} cm/yr", "hot"),
                ("Area sinking > 5 cm/yr", f"{risk_area:,.0f} km²", ""),
                ("People on that ground", f"{people5:,.0f}" if people5 is not None else "n/a", "hot"),
            ])

        with panel():
            st.markdown("<div class='sw-panel-h'>Inspector</div>", unsafe_allow_html=True)
            click = out.get("last_clicked") if out else None
            lat, lon = (click["lat"], click["lng"]) if click else (lat0, lon0)
            st.markdown(f"<div class='sw-note'>{'Selected point' if click else 'Quetta city centre'} · "
                        f"{lat:.4f}°N, {lon:.4f}°E</div>", unsafe_allow_html=True)
            ps = point_stats(data, lat, lon)
            if ps is None:
                st.info("Outside the analysis area.")
            else:
                stat_rows([
                    ("Vertical speed", f"{ps['vel']:+.1f} cm/yr", "hot" if ps["vel"] <= -3 else ""),
                    ("Elevation", f"{ps['elev']:,.0f} m", ""),
                    ("People within 500 m", f"{ps['people']:,.0f}" if ps["people"] is not None else "n/a", ""),
                    ("Trend confidence", ("High" if ps["r2"] >= 0.6 else "Medium" if ps["r2"] >= 0.3 else "Low · noisy")
                     + f" (R² {ps['r2']:.2f})", "" ),
                ])
                if not ps["valley"]:
                    badge = ("info", "Bedrock / mountain · not a subsidence zone")
                elif ps["r2"] < 0.3:
                    badge = ("info", "No clear trend · within noise")
                elif ps["vel"] <= -8:
                    badge = ("high", "High risk · fast sinking")
                elif ps["vel"] <= -3:
                    badge = ("mod", "Moderate sinking")
                else:
                    badge = ("ok", "No significant sinking")
                st.markdown(f"<div style='margin:.5rem 0'><span class='sw-badge {badge[0]}'>{badge[1]}</span></div>",
                            unsafe_allow_html=True)
                x = [datetime.strptime(d, "%Y%m%d") for d in dates]
                fig = go.Figure(go.Scatter(x=x, y=ps["series"] / 10.0, mode="lines+markers",
                                           line=dict(color=RED, width=2.5), marker=dict(size=6),
                                           hovertemplate="%{x|%d %b}: %{y:.1f} cm<extra></extra>"))
                fig.add_hline(y=0, line_dash="dot", line_color="#98a2b3")
                clean_fig(fig, 220).update_yaxes(title_text="cm since 17 Jun", title_font=dict(size=10))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ================================================================== EXPOSURE
with tab_exp:
    rows = []
    for thr in [2, 5, 8, 10]:
        mk = vel <= -thr
        rows.append((thr, float(mk.sum() * data["px_km2"]),
                     int(np.nansum(data["pop_utm"][mk])) if data["has_pop"] else None))
    k = st.columns(4)
    for col, (thr, area, ppl) in zip(k, rows):
        with col:
            with panel():
                st.markdown(f"<div class='sw-panel-h'>Sinking faster than {thr} cm/yr</div>"
                            f"<div class='sw-hero-num'>{(ppl or 0)/1000:,.0f}k</div>"
                            f"<div class='sw-note'>people · {area:,.0f} km² of valley floor</div>",
                            unsafe_allow_html=True)
    with panel():
        st.markdown("<div class='sw-panel-h'>People living on sinking ground</div>", unsafe_allow_html=True)
        fig = go.Figure(go.Bar(x=[f"> {r[0]} cm/yr" for r in rows], y=[r[2] or 0 for r in rows],
                               marker_color=["#fda29b", "#f04438", "#d92d20", "#912018"],
                               text=[f"{(r[2] or 0):,}" for r in rows], textposition="outside"))
        st.plotly_chart(clean_fig(fig, 320), width="stretch", config={"displayModeBar": False})
        st.markdown("<div class='sw-note'>Population: WorldPop 2020, constrained and UN-adjusted, summed on the "
                    "80 m grid. Exposure shows who lives on fast-sinking ground; it is not a building-damage model.</div>",
                    unsafe_allow_html=True)

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


with tab_up:
    st.markdown("<div class='sw-note' style='margin-bottom:.6rem'>Bring your own ground-motion map: any "
                "single-band GeoTIFF of velocity (from the SinkWatch pipeline, ASF HyP3, LiCSBAS, MintPy…). "
                "SinkWatch maps it, measures the sinking area and lets you inspect any point. "
                "Files stay in your browser session and are not stored.</div>", unsafe_allow_html=True)
    u_left, u_centre, u_right = st.columns([0.95, 2.7, 1.25], gap="small")
    with u_left:
        with panel():
            st.markdown("<div class='sw-panel-h'>1 · Data</div>", unsafe_allow_html=True)
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
            try:
                with open(SAMPLE_TIF, "rb") as fh:
                    st.download_button("Download sample .tif", fh.read(), file_name="sample_quetta_velocity_cm_yr.tif",
                                       mime="image/tiff", width="stretch")
            except OSError:
                pass
        with panel():
            st.markdown("<div class='sw-panel-h'>2 · Units</div>", unsafe_allow_html=True)
            unit = st.selectbox("Velocity units", list(UNIT_TO_CM), index=0)
            flip = st.checkbox("Positive values mean sinking", value=False,
                               help="SinkWatch uses negative = sinking. Tick this if your file uses the opposite sign.")
            is_los = st.checkbox("Values are line-of-sight (convert to vertical)", value=False)
            inc = st.slider("Incidence angle (°)", 20.0, 50.0, 39.0, 0.5) if is_los else 0.0
        with panel():
            st.markdown("<div class='sw-panel-h'>3 · Display</div>", unsafe_allow_html=True)
            u_thr = st.slider("Hide motion below (cm/yr) ", 0.0, 10.0, 2.0, 0.5)
            u_op = st.slider("Opacity ", 0.2, 1.0, 0.75, 0.05)
            u_sink = st.checkbox("Sinking only ", value=True)

    res, err = None, None
    if raw is not None:
        try:
            res = analyze_raster(raw, unit, flip, inc)
        except Exception as ex:  # keep the rest of the app alive whatever the file is
            err = str(ex) or "Could not read this file. Is it a GeoTIFF?"

    with u_centre:
        if err:
            st.error(err)
        if res is None:
            with panel():
                st.markdown("<div class='sw-panel-h'>Waiting for data</div>"
                            "<div class='sw-note'>Choose the sample or upload a GeoTIFF on the left.</div>",
                            unsafe_allow_html=True)
        else:
            s, w, n, e = res["bounds"]
            tile = ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
                    if DARK else
                    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}")
            span = max(e - w, (n - s) * 1.3, 1e-4)
            zoom = int(np.clip(np.floor(np.log2(800 * 360 / (256 * span))), 2, 16))
            um = folium.Map(location=[(s + n) / 2, (w + e) / 2], zoom_start=zoom, tiles=None, control_scale=True)
            folium.TileLayer(tiles=tile, attr="Esri, HERE, Garmin, OpenStreetMap contributors").add_to(um)
            shown = np.where(res["vel_ll"] > 0, np.nan, res["vel_ll"]) if u_sink else res["vel_ll"]
            img = Image.fromarray(colorize(shown, u_thr, u_op), "RGBA")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            folium.raster_layers.ImageOverlay(image="data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
                                              bounds=[[s, w], [n, e]], interactive=False).add_to(um)
            folium.Rectangle([[s, w], [n, e]], color="#667085", weight=1, fill=False, dash_array="4").add_to(um)
            Fullscreen().add_to(um)
            MousePosition(position="bottomright", separator=" · ", num_digits=4, prefix="").add_to(um)
            # click-to-inspect runs inside the map (works in any tab, no server round-trip)
            g = res["vel_ll"]
            stp = max(1, int(np.ceil(max(g.shape) / 300)))
            gs = g[::stp, ::stp]
            grid = [[None if not np.isfinite(x) else round(float(x), 1) for x in row] for row in gs]
            ClickInspect(json.dumps(grid), s, w, n, e).add_to(um)
            components.html(um.get_root().render(), height=560)
            h, wd = res["shape"]
            st.markdown(f"<div class='sw-status'><span><b>CRS</b> {res['crs_name']}</span>"
                        f"<span><b>Grid</b> {wd} × {h} px</span><span><b>Units</b> converted to vertical cm/yr</span>"
                        "<span><b>Tip</b> click anywhere on the map to read the speed</span></div>", unsafe_allow_html=True)

    with u_right:
        if res is not None:
            v, pa = res["vel"], res["px_km2"]
            ok = np.isfinite(v)
            a5 = float(pa[ok & (v <= -5)].sum())
            a10 = float(pa[ok & (v <= -10)].sum())
            with panel():
                st.markdown("<div class='sw-panel-h'>Summary</div>", unsafe_allow_html=True)
                stat_rows([
                    ("Fastest 1%", f"{abs(min(np.nanpercentile(v, 1), 0)):.1f} cm/yr", "hot"),
                    ("Median motion", f"{np.nanmedian(v):+.1f} cm/yr", ""),
                    ("Area sinking > 5 cm/yr", f"{a5:,.1f} km²", "hot"),
                    ("Area sinking > 10 cm/yr", f"{a10:,.1f} km²", ""),
                    ("Area covered", f"{float(pa[ok].sum()):,.0f} km²", ""),
                ])
            with panel():
                st.markdown("<div class='sw-panel-h'>Inspector</div><div class='sw-note'>Click anywhere on the map: "
                            "the vertical speed and status pop up right on the point.</div>", unsafe_allow_html=True)
            with panel():
                st.markdown("<div class='sw-panel-h'>Distribution</div>", unsafe_allow_html=True)
                vv = np.clip(v[ok], -VMAX, VMAX)
                fig = go.Histogram(x=vv, nbinsx=40, marker_color=RED)
                fig = go.Figure(fig)
                fig.add_vline(x=0, line_dash="dot", line_color="#98a2b3")
                clean_fig(fig, 200).update_xaxes(title_text="cm/yr (negative = sinking)", title_font=dict(size=10))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ================================================================== VALIDATION
with tab_val:
    c1, c2 = st.columns([1.5, 1])
    with c1:
        with panel():
            st.markdown("<div class='sw-panel-h'>SinkWatch vs independent measurements (cm/yr)</div>",
                        unsafe_allow_html=True)
            refs = [
                ("SinkWatch · city centre (NISAR 2026)", abs(city_vel), RED),
                ("SinkWatch · fastest 1% (NISAR 2026)", abs(fastest), RED),
                ("Kakar et al. 2025 · max after 2016 (InSAR)", 16.0, "#98a2b3"),
                ("Kakar et al. 2024 · central GNSS after 2016", 16.6, "#98a2b3"),
                ("Kakar et al. 2024 · valley minimum (InSAR)", 3.2, "#d0d5dd"),
            ]
            fig = go.Figure(go.Bar(y=[r[0] for r in refs], x=[r[1] for r in refs], orientation="h",
                                   marker_color=[r[2] for r in refs], text=[f"{r[1]:.1f}" for r in refs],
                                   textposition="outside"))
            clean_fig(fig, 300).update_yaxes(autorange="reversed")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with c2:
        with panel():
            st.markdown("<div class='sw-panel-h'>Verdict</div>", unsafe_allow_html=True)
            st.markdown(
                "Published Sentinel-1 InSAR and GPS studies report **3.2–16 cm/yr** across the Quetta valley, "
                "fastest in the centre. SinkWatch finds the **same hotspot at the same rates** from only "
                "120 days of NISAR data.\n\n"
                "Ascending/descending comparisons in the literature show negligible horizontal motion, "
                "supporting the line-of-sight → vertical conversion.")
            st.markdown("<div class='sw-note'>Kakar et al. (2025) Natural Hazards, doi:10.1007/s11069-025-07226-y · "
                        "Kakar et al. (2024) Remote Sensing 16(9):1521</div>", unsafe_allow_html=True)

# ================================================================== METHOD
with tab_method:
    steps = [
        ("1 · Data", "9 consecutive NISAR L-band GUNW interferograms (12-day pairs), track 041 ascending, "
                     "17 Jun → 15 Oct 2026."),
        ("2 · Streaming", "Only the Quetta window is read from NASA's ASF archive (earthaccess + h5py). "
                          "No 20 GB download."),
        ("3 · Ionosphere", "NISAR's split-spectrum ionosphere phase screen is subtracted from every pair."),
        ("4 · Troposphere + tilt", "Fit a·row + b·col + c·elevation + d against Copernicus GLO-30, outside an "
                                   "8 km circle around the city, and remove it."),
        ("5 · Stack", "Sum the 9 cleaned pairs. Displacement = −λ/4π · phase, λ = 24.2 cm."),
        ("6 · Vertical", "Line-of-sight ÷ cos(45.1°). Valley floor = elevation < 1,900 m and slope < 5°."),
        ("7 · Exposure", "WorldPop 2020 people summed on the same 80 m grid."),
    ]
    cols = st.columns(4)
    for i, (h, txt) in enumerate(steps):
        with cols[i % 4]:
            with panel():
                st.markdown(f"<div class='sw-panel-h' style='color:{ACCENT}'>{h}</div>"
                            f"<div style='font-size:.88rem;color:#344054'>{txt}</div>", unsafe_allow_html=True)

# ================================================================== ABOUT
with tab_about:
    a1, a2 = st.columns([1.3, 1])
    with a1:
        with panel():
            st.markdown("<div class='sw-panel-h'>Why it matters</div>", unsafe_allow_html=True)
            st.markdown(
                "Groundwater pumping is making cities sink, from Jakarta and Mexico City to Tehran and Quetta. "
                "Buildings crack, pipes break and floods worsen, usually unnoticed until it is too late. "
                "Most cities have no ground monitoring network.\n\n"
                "NISAR images every place on Earth every 12 days, free and open. SinkWatch turns that radar "
                "into a map a city engineer or disaster agency can act on, and the same pipeline works for "
                "any city NISAR covers.")
    with a2:
        with panel():
            st.markdown("<div class='sw-panel-h'>Limitations</div>", unsafe_allow_html=True)
            st.markdown(
                "- Provisional NISAR products (calibrated, still being validated)\n"
                "- 120-day record; annual rate is an estimate\n"
                "- One viewing direction; vertical motion assumed\n"
                "- Some residual atmosphere away from the valley\n"
                "- Exposure ≠ damage")
        with panel():
            st.markdown("<div class='sw-panel-h'>Roadmap</div>", unsafe_allow_html=True)
            st.markdown(
                "- **Now:** Quetta from NISAR, plus *Analyze your data* for any velocity GeoTIFF\n"
                "- **Next:** more cities (Jakarta, Tehran, Mexico City) run through the same pipeline\n"
                "- **Then:** pick any city on Earth and SinkWatch processes the latest NISAR pass automatically\n"
                "- **Later:** alerts when a neighbourhood starts sinking faster")
        st.markdown("<div class='sw-note'>Built solo for NASA Space Apps Challenge 2026 · Dancing with the SARs · "
                    "Data: NASA-ISRO NISAR (ASF DAAC), Copernicus GLO-30 DEM, WorldPop 2020.</div>",
                    unsafe_allow_html=True)
