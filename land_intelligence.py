import time
import requests
import json
from bs4 import BeautifulSoup
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
            "acres": "GIS_Deeded_Acres",
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

    public_owner_keywords = [
        "STATE OF NORTH CAROLINA",
        "STATE OF NC",
        "CLEVELAND COUNTY",
        "GASTON COUNTY",
        "MECKLENBURG COUNTY",
        "COUNTY OF",
        "CITY OF",
        "TOWN OF",
        "BOARD OF EDUCATION",
        "DUKE ENERGY",
        "DUKE POWER"
    ]

    is_public_owner = any(keyword in owner_upper for keyword in public_owner_keywords)

    if is_public_owner:
        return 2, False

    if owner_upper in ["UNKNOWN", "", "NONE"]:
        acres = float(acres or 0)

        if acres >= 300:
            return 3, False
        elif acres >= 100:
            return 2, False
        else:
            return 1, False

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
    seen_ids = set()

    for feature in data.get("features", []):
        attr = feature.get("attributes", {})

        pid = attr.get(fields["pid"])
        parcel_key = f"{county}-{pid}"

        if parcel_key in seen_ids:
            continue

        seen_ids.add(parcel_key)

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
            "pid": pid,
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

def get_mecklenburg_centroid(geometry):
    points = []

    for ring in geometry.get("rings", []):
        for point in ring:
            if len(point) >= 2:
                points.append(point)

    if not points:
        return None, None

    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)

    return lat, lon


def get_mecklenburg_owner(pid):
    try:
        url = f"https://polaris3g.mecklenburgcountync.gov/pid/{pid}"
        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        for table in soup.find_all("table"):
            text = table.get_text(" | ", strip=True)

            if "Owner Name" in text:
                parts = [p.strip() for p in text.split("|")]
                if len(parts) >= 3:
                    return parts[2]

    except Exception:
        pass

    return "Unknown"


def fetch_mecklenburg_land():
    url = "https://gis.charlottenc.gov/arcgis/rest/services/CountyData/Parcels/MapServer/0/query"

    params = {
        "where": "Shape.STArea() >= 1089000",
        "outFields": "PID,NC_PIN,Shape.STArea()",
        "returnGeometry": "true",
        "f": "json",
        "resultRecordCount": 100,
        "outSR": "4326",
        "orderByFields": "Shape.STArea() DESC"
    }

    response = requests.get(url, params=params)
    data = response.json()

    parcels = []
    seen_ids = set()

    for feature in data.get("features", []):
        attr = feature.get("attributes", {})
        geometry = feature.get("geometry", {})

        pid = attr.get("PID")

        if not pid or pid in seen_ids:
            continue

        seen_ids.add(pid)

        area_sqft = attr.get("Shape.STArea()") or 0
        acres = round(area_sqft / 43560, 2)

        lat, lon = get_mecklenburg_centroid(geometry)

        owner = get_mecklenburg_owner(pid)

        watch_score, llc_flag = calculate_watch_score(owner, acres)

        parcels.append({
            "county": "Mecklenburg",
            "owner": owner,
            "owner2": "",
            "pid": pid,
            "pin": attr.get("NC_PIN"),
            "acres": acres,
            "x": lon,
            "y": lat,
            "lat": lat,
            "lon": lon,
            "llc_flag": llc_flag,
            "watch_score": watch_score,
            "acreage_source": "Shape.STArea / 43560",
            "owner_source": "POLARIS"
        })

    return parcels

def get_union_owner_and_acres(pid, session):
    search_url = "https://unionnc.devnetwedge.com/search/quick"

    try:
        search_html = session.get(
            search_url,
            params={"q": pid},
            timeout=8
        ).text

        search_soup = BeautifulSoup(search_html, "html.parser")

        owner = "Unknown"
        address = ""

        for table in search_soup.find_all("table"):
            parts = [
                p.strip()
                for p in table.get_text("|", strip=True).split("|")
            ]

            if pid not in parts:
                continue

            try:
                number_index = parts.index(pid)
                owner = parts[number_index + 1]
                address = parts[number_index + 2]
            except:
                pass

            break

        detail_url = "https://unionnc.devnetwedge.com/search/ViewQuickSearchResult"

        detail_params = {
            "row": "1",
            "property_key": pid,
            "year": "2025",
            "property_type": "Parcel"
        }

        detail_html = session.get(
            detail_url,
            params=detail_params,
            timeout=8
        ).text

        detail_soup = BeautifulSoup(detail_html, "html.parser")
        detail_text = detail_soup.get_text("|", strip=True)

        acres = 0
        parts = [p.strip() for p in detail_text.split("|")]

        for i, part in enumerate(parts):
            if part == "Deeded Acres":
                try:
                    acres = float(parts[i + 1])
                except:
                    acres = 0
                break

        return owner, address, acres

    except Exception as e:
        print(f"Union lookup failed for {pid}: {e}")
        return "Unknown", "", 0


def fetch_union_land():
    url = "https://gis.unioncountync.gov/server/rest/services/ParcelCentroids/MapServer/0/query"

    params = {
        "where": "1=1",
        "outFields": "PID,MuniAdmin,CountyZoning,ZoningAdmin,FireDistrict",
        "returnGeometry": "true",
        "f": "json",
        "resultRecordCount": 10,
        "outSR": "4326"
    }

    response = requests.get(url, params=params, timeout=8)
    data = response.json()

    parcels = []
    seen_ids = set()

    session = requests.Session()

    for feature in data.get("features", []):
        attr = feature.get("attributes", {})
        geom = feature.get("geometry", {})

        pid = attr.get("PID")

        if not pid or pid in seen_ids:
            continue

        seen_ids.add(pid)

        owner, address, acres = get_union_owner_and_acres(pid, session)

        time.sleep(2)

        if acres < 2:
            continue

        lat = geom.get("y")
        lon = geom.get("x")

        watch_score, llc_flag = calculate_watch_score(owner, acres)

        parcels.append({
            "county": "Union",
            "owner": owner,
            "owner2": "",
            "pid": pid,
            "pin": pid,
            "address": address,
            "acres": round(acres, 2),
            "x": lon,
            "y": lat,
            "lat": lat,
            "lon": lon,
            "zoning": attr.get("CountyZoning"),
            "zoning_admin": attr.get("ZoningAdmin"),
            "fire_district": attr.get("FireDistrict"),
            "llc_flag": llc_flag,
            "watch_score": watch_score,
            "acreage_source": "DEVNET Deeded Acres",
            "owner_source": "DEVNET"
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

print("Scanning Mecklenburg...")

mecklenburg_parcels = fetch_mecklenburg_land()

print(f"Found {len(mecklenburg_parcels)} parcels.")

all_parcels.extend(mecklenburg_parcels)

print("Scanning Union...")

union_parcels = fetch_union_land()

print(f"Found {len(union_parcels)} parcels.")

all_parcels.extend(union_parcels)

with open("land_intelligence.json", "w") as file:
    json.dump(all_parcels, file, indent=4)

print("\nSaved land intelligence data.")
print("Total tracked parcels:", len(all_parcels))