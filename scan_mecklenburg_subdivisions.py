import json
import requests
from datetime import datetime

OUTPUT_FILE = "projects.json"

URL = "https://gis.charlottenc.gov/arcgis/rest/services/PLN/Subdivisions/MapServer/0/query"

params = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "false",
    "f": "json",
    "resultRecordCount": 100
}

print("Summit Atlas — Mecklenburg Subdivision Scanner")
print("---------------------------------------------")

response = requests.get(URL, params=params, timeout=20)
print("Status:", response.status_code)

data = response.json()
features = data.get("features", [])

try:
    with open(OUTPUT_FILE, "r") as file:
        existing_projects = json.load(file)
except FileNotFoundError:
    existing_projects = []

existing_keys = {
    (p.get("county"), p.get("case_number"), p.get("address"))
    for p in existing_projects
}

added = 0

for feature in features:
    attr = feature.get("attributes", {})

    project = {
        "county": "Mecklenburg",
        "case_number": attr.get("AltID") or "",
        "address": attr.get("Address") or "",
        "acreage": attr.get("AcreSF") or "",
        "owner": "",
        "applicant": attr.get("Developer") or "",
        "zoning_change": f"Subdivision: {attr.get('ProjName') or ''} | SF Lots: {attr.get('SFLots') or ''} | Status: {attr.get('AppStatus') or ''}",
        "source_url": attr.get("Hyperlink") or "https://gis.charlottenc.gov/",
        "last_scanned": datetime.now().strftime("%Y-%m-%d")
    }

    key = (
        project.get("county"),
        project.get("case_number"),
        project.get("address")
    )

    if key not in existing_keys:
        existing_projects.append(project)
        added += 1

with open(OUTPUT_FILE, "w") as file:
    json.dump(existing_projects, file, indent=2)

print("Records scanned:", len(features))
print("New projects added:", added)
print("Total projects:", len(existing_projects))
print("Scan complete.")