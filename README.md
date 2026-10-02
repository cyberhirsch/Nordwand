# NORDWAND

Alpine terrain-aware AR orientation system. Point your phone at the mountains and see which peaks, huts, passes and lift stations are actually in line of sight — plus the skyline, ridgelines, sun path, ridge-sunset time and live weather.

**Live:** https://cyberhirsch.github.io/Nordwand/

- 100% static: one HTML file, everything computed on-device
- Terrain: AWS Terrarium elevation tiles · POIs: OpenStreetMap · Weather: Open-Meteo
- Desktop simulation: `?lat=46.5853&lon=7.9614&h=120&p=8` (h = heading, p = pitch)

Refresh the offline POI database: `python3 tools/build_pois.py` → writes `pois.json`.
Without `pois.json` the app falls back to live Overpass queries.
