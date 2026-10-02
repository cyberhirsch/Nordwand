#!/usr/bin/env python3
"""Build an HD terrain pack from Bavarian DGM5 (5 m XYZ, EPSG:25832) -> Terrarium z13 PNG tiles.

  python3 -m venv tools/.venv && tools/.venv/bin/pip install numpy pillow
  tools/.venv/bin/python tools/build_hd_pack.py chiemgau "Chiemgau HD" tools/data/dgm5/zip

Data: Bayerische Vermessungsverwaltung, www.geodaten.bayern.de, CC BY 4.0.
Pixels without source data are written fully transparent; the app falls back to the base DEM there.
"""
import io, json, math, os, sys, zipfile
import numpy as np
from PIL import Image

pack_id, title, src = sys.argv[1], sys.argv[2], sys.argv[3]
Z, RES = 13, 10.0  # output zoom, mosaic resolution (m)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "packs")
OUT = os.path.join(ROOT, pack_id)

# ---- 1. mosaic 1 km tiles into a 10 m UTM grid (2x2 mean of 5 m cells) ----
zips = sorted(f for f in os.listdir(src) if f.endswith(".zip"))
kms = [tuple(map(int, f[:-4].split("_"))) for f in zips]
e0, n0 = min(k[0] for k in kms), min(k[1] for k in kms)
e1, n1 = max(k[0] for k in kms) + 1, max(k[1] for k in kms) + 1
cpk = int(1000 / RES)
mos = np.full(((n1 - n0) * cpk, (e1 - e0) * cpk), np.nan, np.float32)
for i, (f, (ek, nk)) in enumerate(zip(zips, kms)):
    with zipfile.ZipFile(os.path.join(src, f)) as z:
        a = np.loadtxt(io.BytesIO(z.read(z.namelist()[0])), dtype=np.float64)
    g = np.full((200, 200), np.nan, np.float32)
    c = ((a[:, 0] - ek * 1000) // 5).astype(int); r = ((a[:, 1] - nk * 1000) // 5).astype(int)
    ok = (c >= 0) & (c < 200) & (r >= 0) & (r < 200)
    g[r[ok], c[ok]] = a[ok, 2]
    g = np.nanmean(g.reshape(cpk, 2, cpk, 2), axis=(1, 3)) if np.isfinite(g).any() else g[::2, ::2]
    y = (nk - n0) * cpk; x = (ek - e0) * cpk
    mos[y:y + cpk, x:x + cpk] = g  # row 0 = southern edge
    if i % 250 == 0: print(f"mosaic {i}/{len(zips)}", flush=True)

# ---- 2. WGS84 -> UTM32 (Krüger series, vectorised) ----
def utm32(lat, lon):
    a, f, k0, lon0 = 6378137.0, 1 / 298.257223563, 0.9996, math.radians(9)
    n = f / (2 - f); A = a / (1 + n) * (1 + n**2 / 4 + n**4 / 64)
    al = [n/2 - 2*n**2/3 + 5*n**3/16, 13*n**2/48 - 3*n**3/5, 61*n**3/240]
    phi, lam = np.radians(lat), np.radians(lon) - lon0
    e = 2 * math.sqrt(n) / (1 + n)
    t = np.sinh(np.arctanh(np.sin(phi)) - e * np.arctanh(e * np.sin(phi)))
    xi, eta = np.arctan2(t, np.cos(lam)), np.arctanh(np.sin(lam) / np.sqrt(1 + t * t))
    E = eta + sum(al[j] * np.cos(2*(j+1)*xi) * np.sinh(2*(j+1)*eta) for j in range(3))
    N = xi + sum(al[j] * np.sin(2*(j+1)*xi) * np.cosh(2*(j+1)*eta) for j in range(3))
    return 500000 + k0 * A * E, k0 * A * N

def inv_utm_bbox():  # rough lat/lon bbox of the mosaic (for tile range)
    lat0 = (n0 * 1000) / 111320; lat1 = (n1 * 1000) / 111320
    return lat0 - 0.05, lat1 + 0.05

# ---- 3. render Terrarium z13 tiles ----
def tile_bounds(x, y):
    n = 2**Z
    lon = lambda xx: xx / n * 360 - 180
    lat = lambda yy: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * yy / n))))
    return lon, lat

n = 2**Z
lat_s, lat_n = inv_utm_bbox()
# lon range from mosaic corners at mid-latitude
def lon_of(e, lat):  # adequate for range finding only
    return 9 + math.degrees((e - 500000) / (6378137 * 0.9996 * math.cos(math.radians(lat))))
lon_w, lon_e = lon_of(e0 * 1000, lat_n) - 0.05, lon_of(e1 * 1000, lat_s) + 0.05
tx0, tx1 = int((lon_w + 180) / 360 * n), int((lon_e + 180) / 360 * n)
ty = lambda lat: int((1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
ty0, ty1 = ty(lat_n), ty(lat_s)

H, W = mos.shape
written, total_bytes = [], 0
px = (np.arange(256) + 0.5) / 256
for tx in range(tx0, tx1 + 1):
    for tyy in range(ty0, ty1 + 1):
        lon = (tx + px) / n * 360 - 180
        lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * (tyy + px) / n))))
        LON, LAT = np.meshgrid(lon, lat)
        E, N = utm32(LAT, LON)
        fx = (E - e0 * 1000) / RES - 0.5; fy = (N - n0 * 1000) / RES - 0.5
        x0 = np.floor(fx).astype(int); y0 = np.floor(fy).astype(int)
        inside = (x0 >= 0) & (y0 >= 0) & (x0 < W - 1) & (y0 < H - 1)
        if not inside.any(): continue
        x0c, y0c = np.clip(x0, 0, W - 2), np.clip(y0, 0, H - 2)
        dx, dy = fx - x0c, fy - y0c
        q = lambda oy, ox: mos[y0c + oy, x0c + ox]
        h = q(0,0)*(1-dx)*(1-dy) + q(0,1)*dx*(1-dy) + q(1,0)*(1-dx)*dy + q(1,1)*dx*dy
        valid = inside & np.isfinite(h)
        if not valid.any(): continue
        v = np.where(valid, h, 0) + 32768
        rgba = np.zeros((256, 256, 4), np.uint8)
        rgba[..., 0] = (v // 256).astype(np.uint8)
        rgba[..., 1] = (np.floor(v) % 256).astype(np.uint8)
        rgba[..., 2] = ((v - np.floor(v)) * 256).astype(np.uint8)
        rgba[..., 3] = np.where(valid, 255, 0)
        p = os.path.join(OUT, str(Z), str(tx), f"{tyy}.png"); os.makedirs(os.path.dirname(p), exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(p, optimize=True)
        written.append([tx, tyy]); total_bytes += os.path.getsize(p)

# ---- 4. manifest ----
bb = [round(lat_s, 4), round(lon_w, 4), round(lat_n, 4), round(lon_e, 4)]
json.dump({"id": pack_id, "title": title, "z": Z, "res_m": RES, "bbox": bb, "tiles": written,
           "attribution": "Bayerische Vermessungsverwaltung – www.geodaten.bayern.de (CC BY 4.0)"},
          open(os.path.join(OUT, "pack.json"), "w"), separators=(",", ":"))
idx_p = os.path.join(ROOT, "index.json")
idx = json.load(open(idx_p)) if os.path.exists(idx_p) else []
idx = [p for p in idx if p["id"] != pack_id] + [{"id": pack_id, "title": title, "bbox": bb, "z": Z}]
json.dump(idx, open(idx_p, "w"), indent=1)
print(f"{len(written)} tiles, {total_bytes/1e6:.1f} MB -> {os.path.normpath(OUT)}")
