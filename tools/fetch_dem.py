#!/usr/bin/env python3
"""Download AWS Terrarium DEM tiles covering the Alps (+180 km view margin) into docs/tiles/{z}/{x}/{y}.png"""
import math, os, time, urllib.request, concurrent.futures as cf
Z = 9
S, W, N, E = 42.6, 3.0, 49.8, 18.6
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "tiles")
def xy(lat, lon):
    n = 2**Z
    return int((lon+180)/360*n), int((1-math.log(math.tan(math.radians(lat))+1/math.cos(math.radians(lat)))/math.pi)/2*n)
x0, y0 = xy(N, W); x1, y1 = xy(S, E)
jobs = [(x, y) for x in range(x0, x1+1) for y in range(y0, y1+1)]
def get(t):
    x, y = t; p = os.path.join(OUT, str(Z), str(x), f"{y}.png")
    if os.path.exists(p): return 0
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for i in range(5):
        try: data = urllib.request.urlopen(f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{Z}/{x}/{y}.png", timeout=60).read(); break
        except Exception:
            if i == 4: raise
            time.sleep(2 * (i + 1))
    open(p, "wb").write(data); return len(data)
with cf.ThreadPoolExecutor(4) as ex: total = sum(ex.map(get, jobs))
print(f"{len(jobs)} tiles, +{total/1e6:.1f} MB")
