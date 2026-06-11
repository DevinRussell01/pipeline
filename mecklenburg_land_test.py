import requests
from bs4 import BeautifulSoup

parcel_url = "https://gis.charlottenc.gov/arcgis/rest/services/CountyData/Parcels/MapServer/0/query"

params = {
    "where": "Shape.STArea() >= 1089000",
    "outFields": "PID,NC_PIN,Shape.STArea()",
    "returnGeometry": "true",
    "f": "json",
    "resultRecordCount": 10,
    "outSR": "4326",
    "orderByFields": "Shape.STArea() DESC"
}

def get_centroid(geometry):
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

def get_owner(pid):
    try:
        polaris_url = f"https://polaris3g.mecklenburgcountync.gov/pid/{pid}"
        html = requests.get(polaris_url, timeout=10).text
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

response = requests.get(parcel_url, params=params)
data = response.json()

print("\nMecklenburg Large Parcel Test:\n")

for feature in data.get("features", []):
    attrs = feature.get("attributes", {})
    geometry = feature.get("geometry", {})

    pid = attrs.get("PID")
    nc_pin = attrs.get("NC_PIN")
    area_sqft = attrs.get("Shape.STArea()") or 0
    acres = round(area_sqft / 43560, 2)

    lat, lon = get_centroid(geometry)
    owner = get_owner(pid)

    print("PID:", pid)
    print("NC PIN:", nc_pin)
    print("Owner:", owner)
    print("Acres:", acres)
    print("Lat:", lat)
    print("Lon:", lon)
    print("------")