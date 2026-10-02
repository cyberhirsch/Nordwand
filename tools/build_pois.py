#!/usr/bin/env python3
"""Build alps-ar/pois.json from OpenStreetMap (Overpass). Re-run any time to refresh.
Compact format: {"t":["peak","hut","pass","lift"], "p":[[name,lat,lon,ele|null,typeIdx],...]}"""
import json, time, urllib.request, urllib.parse, os, sys
EPS = ["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter","https://overpass.private.coffee/api/interpreter"]
TYPES = ["peak","hut","pass","lift"]
OUT = os.path.join(os.path.dirname(__file__), "..", "pois.json")
CACHE = os.path.join(os.path.dirname(__file__), ".cache"); os.makedirs(CACHE, exist_ok=True)
S,W,N,E = 43.6,5.0,48.4,16.8   # Alpine arc
STEP = 1.0

def query(bb):
    q = f"""[out:json][timeout:90];(
      node["natural"="peak"]["name"]({bb});
      node["natural"="volcano"]["name"]({bb});
      node["tourism"="alpine_hut"]({bb});
      node["tourism"="wilderness_hut"]["name"]({bb});
      node["natural"="saddle"]["name"]({bb});
      node["mountain_pass"="yes"]["name"]({bb});
      node["aerialway"="station"]["name"]({bb}););out body qt;"""
    for attempt in range(6):
        for ep in EPS:
            try:
                req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(),
                                             headers={"User-Agent": "alps-ar-poi-builder/1.0"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.load(r)["elements"]
            except Exception as e:
                print(f"   {ep.split('/')[2]}: {e}", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError("all endpoints failed")

out, seen = [], set()
lat = S
while lat < N:
    lon = W
    while lon < E:
        bb = f"{lat:.2f},{lon:.2f},{lat+STEP:.2f},{lon+STEP:.2f}"
        cf = os.path.join(CACHE, bb.replace(",", "_") + ".json")
        if os.path.exists(cf):
            els = json.load(open(cf))
        else:
            print("tile", bb, flush=True)
            els = query(bb); json.dump(els, open(cf, "w")); time.sleep(2)
        for e in els:
            if e["id"] in seen: continue
            seen.add(e["id"]); t = e.get("tags", {}); name = t.get("name")
            if not name: continue
            typ = 0 if t.get("natural") in ("peak","volcano") else 1 if t.get("tourism") else 3 if t.get("aerialway") else 2
            try: ele = round(float(t.get("ele","").replace(",",".").split()[0].rstrip("m")))
            except Exception: ele = None
            if typ == 0 and (ele is None or ele < 1000): continue  # drop low hills/unknown-height peaks
            out.append([name, round(e["lat"],5), round(e["lon"],5), ele, typ])
        lon += STEP
    lat += STEP

json.dump({"t": TYPES, "p": out}, open(OUT, "w"), ensure_ascii=False, separators=(",",":"))
print(f"wrote {len(out)} POIs, {os.path.getsize(OUT)/1e6:.2f} MB -> {OUT}")
