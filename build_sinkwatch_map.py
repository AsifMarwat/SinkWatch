"""
SinkWatch - Step 3: Turn the 9 pairs into ONE clean "how much is Quetta sinking" map.

Plain-words version of what happens:
  1. Remove the ionosphere effect NASA measured for each pair (the upper atmosphere
     bends the radar and fakes "movement").
  2. Remove weather that follows the mountains: air above high peaks is thinner and
     drier, which fakes movement that looks like the terrain. We compare each pair to
     a terrain height map (Copernicus DEM) and subtract whatever matches the terrain.
  3. Remove any leftover smooth tilt across the whole box (orbit / large-scale weather).
  4. Add all 9 pairs together -> total movement June 17 -> Oct 15 (120 days).
  5. Convert line-of-sight movement into vertical sinking (assumes motion is vertical,
     which is the standard assumption for groundwater subsidence).
  6. Turn it into a speed: cm per year.

Only the Quetta part of the DEM is streamed (a few MB) - no big downloads.

Outputs in data/quetta_041A/results/:
  cumulative_los_mm.tif        total LOS movement Jun 17 -> Oct 15
  cumulative_vertical_mm.tif   same, converted to vertical
  velocity_vertical_cm_yr.tif  sinking speed (cm/year), negative = sinking
  dem_on_grid.tif              terrain height on the same grid (for QGIS context)
  timeseries_centre.csv        cumulative vertical movement at Quetta centre per date
  overview.png                 picture of the result
  pair_correction_report.csv   what was removed from each pair

Run:
  C:\\Users\\muham\\AppData\\Local\\Programs\\Python\\Python311\\python.exe build_sinkwatch_map.py
"""

import os
import glob
import json
import math
import csv

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from pyproj import Transformer

DATA_DIR = os.path.join("data", "quetta_041A")
OUT_DIR = os.path.join(DATA_DIR, "results")

# Quetta city centre (used for the time-series point and to keep the city out of the
# correction fits, so we never "correct away" the real sinking signal)
CENTRE_LON, CENTRE_LAT = 67.01, 30.19
CITY_RADIUS_KM = 8.0
MIN_COHERENCE = 0.3

DEM_TILES = [
    "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N30_00_E066_00_DEM/Copernicus_DSM_COG_10_N30_00_E066_00_DEM.tif",
    "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N30_00_E067_00_DEM/Copernicus_DSM_COG_10_N30_00_E067_00_DEM.tif",
]

# Sign: True means the script treats positive phase as motion AWAY from the satellite.
# Checked visually: if Quetta's valley shows UPLIFT after running, flip this to False.
PHASE_POSITIVE_IS_AWAY = True


def load_dem_on_grid(profile):
    """Stream the Quetta part of Copernicus GLO-30 and resample it onto our 80 m grid."""
    dem = np.full((profile["height"], profile["width"]), np.nan, dtype="float32")
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("AWS_NO_SIGN_REQUEST", "YES")
    for url in DEM_TILES:
        part = np.full_like(dem, np.nan)
        with rasterio.open("/vsicurl/" + url) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=part,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=profile["transform"],
                dst_crs=profile["crs"],
                dst_nodata=np.nan,
                resampling=Resampling.average,
            )
        dem = np.where(np.isfinite(part), part, dem)
    return dem


def write_tif(path, arr, profile, description):
    p = profile.copy()
    p.update(count=1, dtype="float32", nodata=np.nan, compress="deflate")
    with rasterio.open(path, "w", **p) as dst:
        dst.write(arr.astype("float32"), 1)
        dst.set_band_description(1, description)


def vertical_factor(geometry_file):
    """cos(incidence) at Quetta's elevation (~1.5-2 km) from the radar geometry cube."""
    g = np.load(geometry_file)
    heights = g["heights"]
    layer = int(np.argmin(np.abs(heights - 1700)))
    inc = float(np.nanmedian(g["incidenceAngle"][layer]))
    return math.cos(math.radians(inc)), inc


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = sorted(glob.glob(os.path.join(DATA_DIR, "pair_*_*.tif")))
    files = [f for f in files if os.path.basename(f).count("_") == 2]
    if not files:
        raise SystemExit("No pair_*.tif files found. Run extract_quetta.py first.")

    with open(files[0].replace(".tif", "_meta.json"), encoding="utf-8") as f:
        meta = json.load(f)
    wavelength = meta["wavelength_m"]
    sign = 1.0 if PHASE_POSITIVE_IS_AWAY else -1.0
    # LOS displacement (mm), positive = TOWARD the satellite (standard convention)
    phase_to_mm = -sign * wavelength / (4 * math.pi) * 1000.0

    with rasterio.open(files[0]) as src:
        profile = src.profile.copy()
        H, W = src.height, src.width
        transform = src.transform

    # pixel grid + distance from Quetta centre
    to_utm = Transformer.from_crs(4326, profile["crs"], always_xy=True)
    cx, cy = to_utm.transform(CENTRE_LON, CENTRE_LAT)
    ccol, crow = ~transform * (cx, cy)
    rows, cols = np.mgrid[0:H, 0:W].astype("float64")
    dist_km = np.hypot((rows - crow) * abs(transform.e), (cols - ccol) * transform.a) / 1000.0
    city = dist_km < 2.0

    print("Streaming terrain height (Copernicus DEM) for the Quetta box...")
    dem = load_dem_on_grid(profile)
    write_tif(os.path.join(OUT_DIR, "dem_on_grid.tif"), dem, profile, "elevation_m")
    print(f"  DEM range in box: {np.nanmin(dem):.0f} - {np.nanmax(dem):.0f} m")

    cum = np.zeros((H, W))
    epochs = [cum.copy()]
    valid_all = np.ones((H, W), bool)
    dates = []
    centre_series = [0.0]
    report = []

    for f in files:
        name = os.path.basename(f)[5:-4]
        ref, sec = name.split("_")
        if not dates:
            dates.append(ref)
        dates.append(sec)
        with rasterio.open(f) as src:
            _, phase, coh, cc, iono, _ = src.read()

        ok = np.isfinite(phase) & (cc > 0) & np.isfinite(iono) & np.isfinite(dem)
        valid_all &= ok
        d = (phase - iono) * phase_to_mm  # ionosphere removed

        # fit: tilt (rows, cols) + terrain-linked weather (elevation), outside the city
        fit = ok & (coh > MIN_COHERENCE) & (dist_km > CITY_RADIUS_KM)
        A = np.column_stack([rows[fit], cols[fit], dem[fit], np.ones(fit.sum())])
        coef, *_ = np.linalg.lstsq(A, d[fit], rcond=None)
        model = coef[0] * rows + coef[1] * cols + coef[2] * dem + coef[3]
        d_clean = d - model

        before = np.nanstd(d[fit])
        after = np.nanstd(d_clean[fit])
        centre_val = float(np.nanmedian(d_clean[city & ok]))
        report.append([ref, sec, round(before, 1), round(after, 1),
                       round(coef[2] * 1000, 2), round(centre_val, 1)])
        print(f"  {ref}->{sec}: noise outside city {before:5.1f} -> {after:5.1f} mm, "
              f"terrain term {coef[2]*1000:+.1f} mm/km, centre {centre_val:+.1f} mm")

        cum += np.nan_to_num(d_clean)
        epochs.append(cum.copy())
        centre_series.append(centre_series[-1] + centre_val)

    cum[~valid_all] = np.nan

    cos_inc, inc_deg = vertical_factor(files[0].replace(".tif", "_geometry.npz"))
    stack = np.array(epochs, dtype="float32") / cos_inc
    stack[:, ~valid_all] = np.nan
    np.savez_compressed(os.path.join(OUT_DIR, "stack_vertical_mm.npz"),
                        stack=stack, dates=np.array(dates), incidence_deg=inc_deg)
    vertical = cum / cos_inc
    days = (np.datetime64(f"{dates[-1][:4]}-{dates[-1][4:6]}-{dates[-1][6:]}")
            - np.datetime64(f"{dates[0][:4]}-{dates[0][4:6]}-{dates[0][6:]}")).astype(int)
    velocity_cm_yr = vertical / days * 365.25 / 10.0

    write_tif(os.path.join(OUT_DIR, "cumulative_los_mm.tif"), cum, profile, "cumulative_LOS_mm_toward_sat_positive")
    write_tif(os.path.join(OUT_DIR, "cumulative_vertical_mm.tif"), vertical, profile, "cumulative_vertical_mm_up_positive")
    write_tif(os.path.join(OUT_DIR, "velocity_vertical_cm_yr.tif"), velocity_cm_yr, profile, "vertical_velocity_cm_per_yr")

    with open(os.path.join(OUT_DIR, "timeseries_centre.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "cumulative_vertical_mm_city_centre"])
        for dt, v in zip(dates, centre_series):
            w.writerow([dt, round(v / cos_inc, 2)])
    with open(os.path.join(OUT_DIR, "pair_correction_report.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["reference", "secondary", "noise_before_mm", "noise_after_mm",
                    "terrain_term_mm_per_km", "city_centre_los_mm"])
        w.writerows(report)

    centre_v = float(np.nanmedian(velocity_cm_yr[city]))
    print(f"\nIncidence angle used: {inc_deg:.1f} deg  (vertical = LOS / {cos_inc:.3f})")
    print(f"Period: {dates[0]} -> {dates[-1]} ({days} days)")
    print(f"Quetta centre (2 km radius) vertical speed: {centre_v:+.1f} cm/yr")
    print(f"Fastest 1% of pixels: {np.nanpercentile(velocity_cm_yr, 1):+.1f} cm/yr")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(15, 7))
        ax[0].imshow(dem, cmap="terrain")
        ax[0].set_title("Terrain (m)")
        lim = np.nanpercentile(np.abs(velocity_cm_yr), 98)
        im = ax[1].imshow(velocity_cm_yr, cmap="RdBu", vmin=-lim, vmax=lim)
        ax[1].set_title(f"Vertical speed (cm/yr), {dates[0]}-{dates[-1]}\nred = sinking, blue = rising")
        for a in ax:
            a.plot(ccol, crow, "k+", ms=16, mew=2)
            a.axis("off")
        fig.colorbar(im, ax=ax[1], fraction=0.046)
        fig.savefig(os.path.join(OUT_DIR, "overview.png"), dpi=110, bbox_inches="tight")
        plt.close(fig)
    except ImportError:
        pass
    print(f"\nSaved results to {OUT_DIR}")


if __name__ == "__main__":
    main()
