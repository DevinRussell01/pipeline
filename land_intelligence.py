import requests
import json

url = "https://gis.clevelandcounty.com/arcgis/rest/services/Tax/Tax/FeatureServer/1/query"

params = {
    "where": "GIS_Calculated_Acres >= 25",
    "outFields": (
        "GIS_PID,"
        "GIS_PIN,"
        "GIS_Owner1,"
        "GIS_Owner2,"
        "GIS_Calculated_Acres,"
        "GIS_Deeded_Acres,"
        "GIS_X_Coord,"
        "GIS_Y_Coord"
    ),
    "returnGeometry": "false",
    "f": "json",
    "resultRecordCount": 50,
    "orderByFields": "GIS_Calculated_Acres DESC"
}

response = requests.get(url, params=params)

data = response.json()

projects = []

for feature in data.get("features", []):

    attr = feature.get("attributes", {})

    owner = str(attr.get("GIS_Owner1", "")).upper()

    watch_score = 0

    # acreage scoring
    acres = attr.get("GIS_Calculated_Acres") or 0

    if acres >= 300:
        watch_score += 5
    elif acres >= 100:
        watch_score += 4
    elif acres >= 50:
        watch_score += 3
    elif acres >= 25:
        watch_score += 2

    # LLC / holdings signals
    keywords = [
        "LLC",
        "HOLDINGS",
        "PROPERTIES",
        "DEVELOPMENT",
        "INVESTMENTS",
        "VENTURES"
    ]

    llc_flag = any(k in owner for k in keywords)

    if llc_flag:
        watch_score += 4

    projects.append({
        "county": "Cleveland",
        "owner": attr.get("GIS_Owner1"),
        "pid": attr.get("GIS_PID"),
        "pin": attr.get("GIS_PIN"),
        "acres": round(acres, 2),
        "x": attr.get("GIS_X_Coord"),
        "y": attr.get("GIS_Y_Coord"),
        "llc_flag": llc_flag,
        "watch_score": watch_score
    })

with open("land_intelligence.json", "w") as file:
    json.dump(projects, file, indent=4)

print("Saved land intelligence data.")
print("Total tracked parcels:", len(projects))