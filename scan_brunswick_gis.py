import json
import requests
from datetime import datetime

OUTPUT_FILE = "brunswick_gis.json"

SOURCE_URL = "https://bcgis.brunswickcountync.gov/arcgis/rest/services/Layers/TaxParcels/MapServer/0/query"

params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "outSR": "4326",
    "f": "json",
    "resultRecordCount": 100
}

def get_polygon_centroid(geometry):
    rings = geometry.get("rings", [])
    if not rings or not rings[0]:
        return None, None

    points = rings[0]
    xs = [p[0] for p in points if len(p) >= 2]
    ys = [p[1] for p in points if len(p) >= 2]

    if not xs or not ys:
        return None, None

    return sum(ys) / len(ys), sum(xs) / len(xs)

print("Conduit — Brunswick GIS Parcel Scanner")
print("-------------------------------------")

response = requests.get(SOURCE_URL, params=params, timeout=30)
print("Status:", response.status_code)

data = response.json()
features = data.get("features", [])

records = []

for feature in features:
    attrs = feature.get("attributes", {})
    geom = feature.get("geometry", {})

    lat, lon = get_polygon_centroid(geom)

    records.append({
        "county": "Brunswick",
        "layer_type": "Tax Parcel",
        "pid": attrs.get("PIN") or attrs.get("ParcelNumber") or "",
        "parcel_number": attrs.get("ParcelNumber") or "",
        "owner": attrs.get("Name1") or attrs.get("OWNER") or "",
        "legal_description": attrs.get("LegalDescription") or "",
        "acres": attrs.get("Acres") or attrs.get("ACRES") or "",
        "lat": lat,
        "lon": lon,
        "source_url": SOURCE_URL,
        "last_scanned": datetime.now().strftime("%Y-%m-%d")
    })

with open(OUTPUT_FILE, "w") as file:
    json.dump(records, file, indent=2)

print("GIS parcel records saved:", len(records))
print("Saved:", OUTPUT_FILE)