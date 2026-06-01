import requests
import json
from pyproj import Transformer

# =====================================================
# COUNTY CONFIG
# =====================================================

COUNTIES = [
    {
        "county": "Cleveland",
        "url": "https://gis.clevelandcounty.com/arcgis/rest/services/Tax/Tax/FeatureServer/1/query",
        "state_plane_epsg": "EPSG:2264",
        "min_acres": 25,
        "fields": {
            "pid": "GIS_PID",
            "pin": "GIS_PIN",
            "owner1": "GIS_Owner1",
            "owner2": "GIS_Owner2",
            "acres": "GIS_Calculated_Acres",
            "x": "GIS_X_Coord",
            "y": "GIS_Y_Coord"
        }
    },

     {
        "county": "Gaston",
        "url": "https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Parcels/MapServer/11/query",
        "state_plane_epsg": "EPSG:2264",
        "min_acres": 25,
        "fields": {
            "pid": "PID",
            "pin": "PIN",
            "owner1": "CURR_NAME1",
            "owner2": "CURR_NAME2",
            "acres": "CALCAC",
            "x": "Longitude",
            "y": "Latitude"
        }
    }

]

# =====================================================
# HELPERS
# =====================================================

def calculate_watch_score(owner, acres):
    owner_upper = str(owner or "").upper()

    score = 0

    if acres >= 300:
        score += 5
    elif acres >= 100:
        score += 4
    elif acres >= 50:
        score += 3
    elif acres >= 25:
        score += 2

    keywords = [
    "LLC",
    "INC",
    "CORP",
    "CORPORATION",
    "CO",
    "COMPANY",
    "HOLDINGS",
    "PROPERTIES",
    "PROPERTY",
    "DEVELOPMENT",
    "DEVELOPERS",
    "INVESTMENTS",
    "VENTURES",
    "LAND",
    "REALTY",
    "REAL ESTATE",
    "HOMES",
    "BUILDERS",
    "BUILDER",
    "CONSTRUCTION"
    ]

    llc_flag = any(word in owner_upper for word in keywords)

    if llc_flag:
        score += 4

    return score, llc_flag


def fetch_county_land(config):
    county = config["county"]
    fields = config["fields"]

    transformer = Transformer.from_crs(
        config["state_plane_epsg"],
        "EPSG:4326",
        always_xy=True
    )

    out_fields = ",".join(fields.values())

    params = {
        "where": f"{fields['acres']} >= {config['min_acres']}",
        "outFields": out_fields,
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 100,
        "orderByFields": f"{fields['acres']} DESC"
    }

    response = requests.get(config["url"], params=params)
    data = response.json()

    parcels = []

    for feature in data.get("features", []):
        attr = feature.get("attributes", {})

        owner = attr.get(fields["owner1"])
        acres = attr.get(fields["acres"]) or 0
        x = attr.get(fields["x"])
        y = attr.get(fields["y"])

        lat = None
        lon = None
        if county == "Gaston":
            lat = y
            lon = x
        elif x and y:
            lon, lat = transformer.transform(x, y)

        watch_score, llc_flag = calculate_watch_score(owner, acres)

        parcels.append({
            "county": county,
            "owner": owner,
            "owner2": attr.get(fields["owner2"]),
            "pid": attr.get(fields["pid"]),
            "pin": attr.get(fields["pin"]),
            "acres": round(acres, 2),
            "x": x,
            "y": y,
            "lat": lat,
            "lon": lon,
            "llc_flag": llc_flag,
            "watch_score": watch_score
        })

    return parcels


# =====================================================
# MAIN
# =====================================================

all_parcels = []

for county_config in COUNTIES:
    print(f"Scanning {county_config['county']}...")

    parcels = fetch_county_land(county_config)

    print(f"Found {len(parcels)} parcels.")

    all_parcels.extend(parcels)

with open("land_intelligence.json", "w") as file:
    json.dump(all_parcels, file, indent=4)

print("\nSaved land intelligence data.")
print("Total tracked parcels:", len(all_parcels))