#!/usr/bin/env python3
"""Build pois.json from a Geofabrik extract (complete, no rate limits).

  curl -LO https://download.geofabrik.de/europe/alps-latest.osm.pbf   -> tools/data/
  brew install osmium-tool
  python3 tools/build_pois_pbf.py

Keeps EVERY peak (named or not, with or without ele); the app fills missing
elevations from the DEM and labels unnamed peaks as spot heights ("P. 2847").
Output: {"t":[types], "p":[[name,lat,lon,ele|null,typeIdx],...]}
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PBF = os.path.join(HERE, "data", "alps-latest.osm.pbf")
FILT = os.path.join(HERE, "data", "pois.osm.pbf")
OUT = os.path.join(HERE, "..", "docs", "pois.json")
TYPES = ["peak", "hut", "pass", "lift"]

subprocess.run(["osmium", "tags-filter", "--overwrite", "-o", FILT, PBF,
    "n/natural=peak,volcano",
    "nw/tourism=alpine_hut,wilderness_hut",
    "n/natural=saddle", "n/mountain_pass=yes",
    "nw/aerialway=station"], check=True)
geo = subprocess.run(["osmium", "export", "-f", "geojsonseq", "-x", "print_record_separator=false",
    "--geometry-types=point,linestring,polygon", FILT],
    check=True, capture_output=True, text=True).stdout

def centre(g):
    t, c = g["type"], g["coordinates"]
    if t == "Point": return c
    ring = c if t == "LineString" else c[0] if t == "Polygon" else c[0][0]
    return [sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)]

def ele_of(s):
    try: return round(float(s.replace(",", ".").replace("m", "").split()[0].split(";")[0]))
    except Exception: return None

out, seen = [], set()
counts = dict.fromkeys(TYPES, 0)
for line in geo.splitlines():
    if not line.strip(): continue
    f = json.loads(line); t = f["properties"]
    if t.get("natural") in ("peak", "volcano"): typ = 0
    elif t.get("tourism") in ("alpine_hut", "wilderness_hut"): typ = 1
    elif t.get("aerialway") == "station": typ = 3
    else: typ = 2
    name = t.get("name") or t.get("name:de") or t.get("name:it") or t.get("name:fr") or ""
    if typ != 0 and not name: continue           # only peaks may be unnamed
    lon, lat = centre(f["geometry"])
    key = (typ, round(lat, 4), round(lon, 4))
    if key in seen: continue
    seen.add(key)
    ele = ele_of(t.get("ele", ""))
    if ele is not None and not (-50 < ele < 4900): ele = None  # junk values
    out.append([name, round(lat, 5), round(lon, 5), ele, typ]); counts[TYPES[typ]] += 1

json.dump({"t": TYPES, "p": out}, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print("counts:", counts, "unnamed peaks:", sum(1 for p in out if p[4] == 0 and not p[0]))
print(f"wrote {len(out)} POIs, {os.path.getsize(OUT)/1e6:.2f} MB -> {os.path.normpath(OUT)}")
