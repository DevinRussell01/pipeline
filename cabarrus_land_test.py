import requests
from bs4 import BeautifulSoup

def get_centroid(geometry):
    points = []

    for ring in geometry.get("rings", []):
        for point in ring:
            points.append(point)

    if not points:
        return None, None

    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)

    return lat, lon


def parse_cabarrus_tax_card(parcel14):
    url = f"https://tax.cabarruscounty.us/AppraisalCard.aspx?Parcel={parcel14}"

    html = requests.get(url, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")
    parts = [p.strip() for p in soup.get_text("|", strip=True).split("|")]

    owner = "Unknown"
    address = ""
    acres = 0

    if len(parts) > 4:
        owner = parts[3]

    if "Parcel:" in parts:
        parcel_index = parts.index("Parcel:")
        if parcel_index + 2 < len(parts):
            address = parts[parcel_index + 2]

    for i, part in enumerate(parts):
        if part == "AC" and i > 0:
            try:
                acres = float(parts[i - 1])
            except:
                acres = 0
            break

    return owner, address, acres


url = "https://location.cabarruscounty.us/arcgisservices/rest/services/DataExplorerDatasets/MapServer/3/query"

params = {
    "where": "Shape.STArea() >= 1089000",
    "outFields": "PIN,Shape.STArea()",
    "returnGeometry": "true",
    "f": "json",
    "resultRecordCount": 10,
    "outSR": "4326",
    "orderByFields": "Shape.STArea() DESC"
}

data = requests.get(url, params=params, timeout=15).json()

print("\nCabarrus Large Parcel Test:\n")

for feature in data.get("features", []):
    attr = feature.get("attributes", {})
    geom = feature.get("geometry", {})

    pin_raw = attr.get("PIN")
    pin10 = str(int(pin_raw)).zfill(10)
    parcel14 = pin10 + "0000"

    area_sqft = attr.get("Shape.STArea()") or 0
    calc_acres = round(area_sqft / 43560, 2)

    lat, lon = get_centroid(geom)

    owner, address, deeded_acres = parse_cabarrus_tax_card(parcel14)

    print("PIN:", pin10)
    print("Parcel14:", parcel14)
    print("Owner:", owner)
    print("Address:", address)
    print("GIS Acres:", calc_acres)
    print("Deeded Acres:", deeded_acres)
    print("Lat:", lat)
    print("Lon:", lon)
    print("------")