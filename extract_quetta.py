"""
SinkWatch - Step 2: Cut out Quetta from every NISAR GUNW pair (streaming, no big downloads).

For each of the 9 files in urls.txt it:
  1. Opens the file on NASA's server (streaming, only the Quetta part is fetched).
  2. Cuts a box around Quetta from the 80 m unwrapped-interferogram layers.
  3. Converts phase -> line-of-sight (LOS) movement in millimetres (quick look).
  4. Saves a small GeoTIFF per pair (open it in QGIS) + a quick-look PNG.
  5. Saves radar geometry (incidence angle, LOS vectors) for the vertical step later.

Output folder: data/quetta_041A/
  pair_YYYYMMDD_YYYYMMDD.tif   6 bands:
      1 los_mm               quick LOS displacement (mm), NaN where unreliable
      2 unwrappedPhase       radians (raw)
      3 coherence            0..1 (signal quality)
      4 connectedComponents  0 = unreliable unwrapping
      5 ionospherePhaseScreen radians
      6 mask                 product mask (raw)
  pair_..._geometry.npz        incidence angle + LOS unit vectors (coarse grid)
  pair_..._meta.json           dates, wavelength, EPSG, track/frame, etc.
  pair_..._quicklook.png       picture of los_mm

Safe to re-run: pairs already saved are skipped.

Setup (once):
  C:\\Users\\muham\\AppData\\Local\\Programs\\Python\\Python311\\python.exe -m pip install rasterio pyproj matplotlib
Run:
  C:\\Users\\muham\\AppData\\Local\\Programs\\Python\\Python311\\python.exe extract_quetta.py
"""

import os
import sys
import json
import math
import time

import numpy as np
import h5py
import earthaccess
from pyproj import Transformer
import rasterio
from rasterio.transform import from_origin

URL_FILE = "urls.txt"
OUT_DIR = os.path.join("data", "quetta_041A")

# Box around Quetta valley + surrounding hills (hills = stable reference ground)
LON_MIN, LON_MAX = 66.80, 67.20
LAT_MIN, LAT_MAX = 30.00, 30.40

G = "science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram"
RG = "science/LSAR/GUNW/metadata/radarGrid"
IDN = "science/LSAR/identification"
LAYERS = {
    "unwrappedPhase": f"{G}/HH/unwrappedPhase",
    "coherence": f"{G}/HH/coherenceMagnitude",
    "connectedComponents": f"{G}/HH/connectedComponents",
    "ionospherePhaseScreen": f"{G}/HH/ionospherePhaseScreen",
    "mask": f"{G}/mask",
}
SPEED_OF_LIGHT = 299792458.0


def read_scalar(h5, path):
    v = h5[path][()]
    if isinstance(v, bytes):
        v = v.decode()
    elif isinstance(v, np.generic):
        v = v.item()
    return v


def pair_dates(url):
    fname = url.rsplit("/", 1)[-1]
    stamps = [p for p in fname.split("_") if len(p) == 15 and p[8] == "T"]
    return stamps[0][:8], stamps[2][:8], fname


def index_range(coords, lo, hi, pad=0):
    idx = np.where((coords >= lo) & (coords <= hi))[0]
    if idx.size == 0:
        return None
    a = max(int(idx.min()) - pad, 0)
    b = min(int(idx.max()) + 1 + pad, coords.size)
    return a, b


def save_quicklook(los_mm, path, title):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    valid = los_mm[np.isfinite(los_mm)]
    if valid.size == 0:
        return
    lim = np.nanpercentile(np.abs(valid - np.nanmedian(valid)), 98)
    med = np.nanmedian(valid)
    fig, ax = plt.subplots(figsize=(7, 7))
    im = ax.imshow(los_mm, cmap="RdBu", vmin=med - lim, vmax=med + lim)
    ax.set_title(title)
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046, label="LOS displacement (mm, relative)")
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def extract_pair(fs, url):
    ref, sec, fname = pair_dates(url)
    base = os.path.join(OUT_DIR, f"pair_{ref}_{sec}")
    if os.path.exists(base + ".tif"):
        print(f"  already done, skipping: {ref} -> {sec}")
        return

    t0 = time.time()
    with fs.open(url, "rb", block_size=8 * 1024 * 1024, cache_type="blockcache") as remote:
        with h5py.File(remote, "r") as h5:
            # --- grid coordinates and projection
            x = h5[f"{G}/xCoordinates"][:]
            y = h5[f"{G}/yCoordinates"][:]
            epsg = int(read_scalar(h5, f"{G}/projection"))
            dx = float(read_scalar(h5, f"{G}/xCoordinateSpacing"))
            dy = float(read_scalar(h5, f"{G}/yCoordinateSpacing"))

            to_utm = Transformer.from_crs(4326, epsg, always_xy=True)
            xs, ys = to_utm.transform(
                [LON_MIN, LON_MAX, LON_MIN, LON_MAX],
                [LAT_MIN, LAT_MIN, LAT_MAX, LAT_MAX],
            )
            cr = index_range(x, min(xs), max(xs))
            rr = index_range(y, min(ys), max(ys))
            if cr is None or rr is None:
                print(f"  !! this frame does not cover the Quetta box: {fname}")
                return
            (c0, c1), (r0, r1) = cr, rr

            # --- read only the Quetta window of each layer
            data = {k: h5[p][r0:r1, c0:c1].astype("float32") for k, p in LAYERS.items()}

            # --- metadata
            f0 = float(read_scalar(h5, "science/LSAR/GUNW/grids/frequencyA/centerFrequency"))
            wavelength = SPEED_OF_LIGHT / f0
            meta = {
                "granule": fname,
                "reference_date": ref,
                "secondary_date": sec,
                "temporal_baseline_days": read_scalar(h5, "science/LSAR/GUNW/metadata/orbit/temporalBaseline"),
                "center_frequency_hz": f0,
                "wavelength_m": wavelength,
                "epsg": epsg,
                "track": read_scalar(h5, f"{IDN}/trackNumber"),
                "frame": read_scalar(h5, f"{IDN}/frameNumber"),
                "orbit_pass_direction": read_scalar(h5, f"{IDN}/orbitPassDirection"),
                "look_direction": read_scalar(h5, f"{IDN}/lookDirection"),
                "window_rows": [r0, r1],
                "window_cols": [c0, c1],
                "pixel_spacing_m": [dx, dy],
                "bbox_lonlat": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX],
            }
            for key in ["wetTroposphericCorrectionApplied", "hydrostaticTroposphericCorrectionApplied",
                        "rangeIonosphericCorrectionApplied", "azimuthIonosphericCorrectionApplied"]:
                try:
                    meta[key] = read_scalar(
                        h5, f"science/LSAR/GUNW/metadata/processingInformation/parameters/geocoding/{key}")
                except KeyError:
                    pass

            # --- coarse radar geometry for the same box (for vertical conversion later)
            gx = h5[f"{RG}/xCoordinates"][:]
            gy = h5[f"{RG}/yCoordinates"][:]
            gcr = index_range(gx, min(xs), max(xs), pad=1)
            grr = index_range(gy, min(ys), max(ys), pad=1)
            geometry = {"heights": h5[f"{RG}/heightAboveEllipsoid"][:]}
            if gcr and grr:
                (gc0, gc1), (gr0, gr1) = gcr, grr
                geometry["x"] = gx[gc0:gc1]
                geometry["y"] = gy[gr0:gr1]
                for name in ["incidenceAngle", "losUnitVectorX", "losUnitVectorY"]:
                    geometry[name] = h5[f"{RG}/{name}"][:, gr0:gr1, gc0:gc1]

    # --- make sure the image is north-up (row 0 = north)
    if y[1] > y[0]:
        for k in data:
            data[k] = data[k][::-1, :]
        north = y[r1 - 1] + abs(dy) / 2
    else:
        north = y[r0] + abs(dy) / 2
    west = x[c0] - abs(dx) / 2
    transform = from_origin(west, north, abs(dx), abs(dy))

    # --- quick LOS displacement in mm (sign convention checked later against known subsidence)
    phase = data["unwrappedPhase"]
    los_mm = (-wavelength / (4 * math.pi)) * phase * 1000.0
    unreliable = (data["connectedComponents"] == 0) | ~np.isfinite(phase) | (phase == 0)
    los_mm[unreliable] = np.nan

    bands = [
        ("los_mm", los_mm),
        ("unwrappedPhase", phase),
        ("coherence", data["coherence"]),
        ("connectedComponents", data["connectedComponents"]),
        ("ionospherePhaseScreen", data["ionospherePhaseScreen"]),
        ("mask", data["mask"]),
    ]
    h, w = phase.shape
    with rasterio.open(
        base + ".tif", "w", driver="GTiff", height=h, width=w, count=len(bands),
        dtype="float32", crs=f"EPSG:{epsg}", transform=transform, nodata=np.nan, compress="deflate",
    ) as dst:
        for i, (name, arr) in enumerate(bands, start=1):
            dst.write(arr.astype("float32"), i)
            dst.set_band_description(i, name)

    np.savez_compressed(base + "_geometry.npz", **geometry)
    with open(base + "_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)
    save_quicklook(los_mm, base + "_quicklook.png", f"Quetta LOS {ref} -> {sec}")

    valid = np.isfinite(los_mm).mean() * 100
    coh = np.nanmean(data["coherence"])
    print(f"  saved {ref} -> {sec}  size={w}x{h}px  valid={valid:.0f}%  mean coherence={coh:.2f}  "
          f"({time.time() - t0:.0f}s)")


def main():
    with open(URL_FILE, "r", encoding="utf-8") as f:
        urls = [u.strip() for u in f if u.strip().lower().endswith(".h5")]
    if not urls:
        sys.exit("No .h5 URLs in urls.txt")
    urls.sort(key=lambda u: pair_dates(u)[0])
    os.makedirs(OUT_DIR, exist_ok=True)

    earthaccess.login(persist=True)
    fs = earthaccess.get_fsspec_https_session()

    print(f"Extracting Quetta from {len(urls)} pairs into {OUT_DIR}\n")
    for i, url in enumerate(urls, 1):
        ref, sec, _ = pair_dates(url)
        print(f"[{i}/{len(urls)}] {ref} -> {sec}")
        for attempt in range(3):
            try:
                extract_pair(fs, url)
                break
            except Exception as e:  # network hiccups: retry
                print(f"  attempt {attempt + 1} failed: {e}")
                time.sleep(5)
        else:
            print("  !! giving up on this pair for now (re-run the script later to retry)")
    print("\nDone. Open the .tif files in QGIS or check the _quicklook.png images.")


if __name__ == "__main__":
    main()
