import requests

url = "https://gis.clevelandcounty.com/arcgis/rest/services/Tax/Tax/FeatureServer/1/query"

params = {
    "where": "GIS_Calculated_Acres >= 25",
    "outFields": "GIS_PID,GIS_PIN,GIS_Owner1,GIS_Owner2,GIS_Calculated_Acres,GIS_Deeded_Acres,GIS_X_Coord,GIS_Y_Coord",
    "returnGeometry": "false",
    "f": "json",
    "resultRecordCount": 25,
    "orderByFields": "GIS_Calculated_Acres DESC"
}

response = requests.get(url, params=params)
data = response.json()

print("\nLargest Cleveland Parcels:\n")

for feature in data.get("features", []):
    attr = feature.get("attributes", {})

    print("Owner:", attr.get("GIS_Owner1"))
    print("PID:", attr.get("GIS_PID"))
    print("PIN:", attr.get("GIS_PIN"))
    print("Acres:", attr.get("GIS_Calculated_Acres"))
    print("X:", attr.get("GIS_X_Coord"))
    print("Y:", attr.get("GIS_Y_Coord"))
    print("------")