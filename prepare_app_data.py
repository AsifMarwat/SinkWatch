"""
SinkWatch - Step 4: Prepare everything the web app needs.

  1. Streams the Quetta part of WorldPop (people per ~100 m pixel) and places it
     on our 80 m grid -> "how many people live on each pixel".
  2. Re-projects the sinking-speed map to latitude/longitude so it sits exactly on a
     web map.
  3. Saves one small bundle: app_data/sinkwatch_quetta.npz (+ a JSON summary).

Run after build_sinkwatch_map.py:
  C:\\Users\\muham\\AppData\\Local\\Programs\\Python\\Python311\\python.exe prepare_app_data.py
"""

import os
import json

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform

VALLEY_MAX_ELEV = 1900   # m
VALLEY_MAX_SLOPE = 5     # degrees
RES_DIR = os.path.join("data", "quetta_041A", "results")
APP_DIR = "app_data"

POP_DIR = os.path.join("data", "population")
WORLDPOP_URLS = [
    # WorldPop 2020, constrained, UN-adjusted (people only where buildings exist), 100 m, ~18 MB
    "https://worldpop-public-data.soton.ac.uk/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/PAK/pak_ppp_2020_UNadj_constrained.tif",
    "https://worldpop-public-data.soton.ac.uk/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/PAK/pak_ppp_2020_constrained.tif",
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/PAK/pak_ppp_2020_constrained.tif",
]


def download(url, path):
    import requests
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(path + ".part", "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r    {done / 1e6:5.1f} / {total / 1e6:.1f} MB", end="")
    print()
    os.replace(path + ".part", path)


def stream_population(profile):
    """Sum WorldPop people onto our grid. Returns (array, source_url) or (None, None)."""
    os.makedirs(POP_DIR, exist_ok=True)
    for url in WORLDPOP_URLS:
        local = os.path.join(POP_DIR, url.rsplit("/", 1)[-1])
        try:
            if not os.path.exists(local):
                print(f"  downloading {url} ...")
                download(url, local)
            out = np.zeros((profile["height"], profile["width"]), dtype="float32")
            with rasterio.open(local) as src:
                src_nodata = src.nodata
                reproject(
                    source=rasterio.band(src, 1),
                    destination=out,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=src_nodata,
                    dst_transform=profile["transform"],
                    dst_crs=profile["crs"],
                    dst_nodata=0,
                    resampling=Resampling.sum,
                )
                # true total inside our box, read straight from WorldPop pixels
                from rasterio.warp import transform_bounds
                from rasterio.windows import from_bounds
                bounds = rasterio.transform.array_bounds(profile["height"], profile["width"], profile["transform"])
                wb = transform_bounds(profile["crs"], src.crs, *bounds)
                raw = src.read(1, window=from_bounds(*wb, transform=src.transform)).astype("float64")
                if src_nodata is not None:
                    raw[raw == src_nodata] = 0
                raw[~np.isfinite(raw) | (raw < 0)] = 0
                true_total = raw.sum()
            out[~np.isfinite(out) | (out < 0)] = 0
            # resampling 100 m -> 80 m can over/under count; rescale to the true total
            if out.sum() > 0 and true_total > 0:
                out *= true_total / out.sum()
            print(f"  OK - {out.sum():,.0f} people in the box")
            return out, url
        except Exception as e:
            print(f"  failed: {e}")
    return None, None


def to_latlon(arr, profile, resampling=Resampling.nearest):
    dst_crs = "EPSG:4326"
    transform, width, height = calculate_default_transform(
        profile["crs"], dst_crs, profile["width"], profile["height"],
        *rasterio.transform.array_bounds(profile["height"], profile["width"], profile["transform"])
    )
    out = np.full((height, width), np.nan, dtype="float32")
    reproject(
        source=arr.astype("float32"), destination=out,
        src_transform=profile["transform"], src_crs=profile["crs"], src_nodata=np.nan,
        dst_transform=transform, dst_crs=dst_crs, dst_nodata=np.nan, resampling=resampling,
    )
    west, north = transform.c, transform.f
    east = west + transform.a * width
    south = north + transform.e * height
    return out, [south, west, north, east]


def main():
    os.makedirs(APP_DIR, exist_ok=True)
    with rasterio.open(os.path.join(RES_DIR, "velocity_vertical_cm_yr.tif")) as src:
        vel = src.read(1)
        profile = src.profile.copy()
    with rasterio.open(os.path.join(RES_DIR, "dem_on_grid.tif")) as src:
        dem = src.read(1)
    st = np.load(os.path.join(RES_DIR, "stack_vertical_mm.npz"))
    stack, dates = st["stack"], [str(d) for d in st["dates"]]

    print("Streaming population (WorldPop) for the Quetta box...")
    pop, pop_src = stream_population(profile)
    if pop is None:
        print("  !! population not available - the app will run without it")
        pop = np.full(vel.shape, np.nan, dtype="float32")

    # Valley floor = where groundwater subsidence can happen (soft sediments, flat, low).
    # Mountains are bedrock: any "movement" there is leftover weather noise.
    gy, gx = np.gradient(dem, abs(profile["transform"].e), profile["transform"].a)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    valley = (dem < VALLEY_MAX_ELEV) & (slope < VALLEY_MAX_SLOPE)

    print("Re-projecting sinking map for the web map...")
    vel_ll, bounds = to_latlon(vel, profile)
    valley_ll, _ = to_latlon(valley.astype("float32"), profile)

    t = profile["transform"]
    np.savez_compressed(
        os.path.join(APP_DIR, "sinkwatch_quetta.npz"),
        vel_utm=vel.astype("float32"),
        dem_utm=dem.astype("float32"),
        pop_utm=pop.astype("float32"),
        stack_utm=stack.astype("float32"),
        dates=np.array(dates),
        utm_transform=np.array([t.a, t.b, t.c, t.d, t.e, t.f]),
        utm_epsg=np.array(profile["crs"].to_epsg()),
        vel_latlon=vel_ll,
        valley_utm=valley,
        valley_latlon=(valley_ll > 0.5),
        latlon_bounds=np.array(bounds),
    )

    pixel_km2 = abs(t.a * t.e) / 1e6
    summary = {
        "dates": dates,
        "pixel_km2": pixel_km2,
        "population_source": pop_src,
        "latlon_bounds": bounds,
        "valley_floor_km2": round(float(valley.sum() * pixel_km2), 1),
    }
    for thr in [2, 5, 8, 10]:
        m = (vel <= -thr) & valley
        summary[f"area_km2_faster_than_{thr}cm"] = round(float(m.sum() * pixel_km2), 2)
        if np.isfinite(pop).any():
            summary[f"people_faster_than_{thr}cm"] = int(np.nansum(pop[m]))
    with open(os.path.join(APP_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    print(f"\nSaved app bundle to {APP_DIR}/")


if __name__ == "__main__":
    main()
