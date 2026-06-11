import requests

url = "https://gis.charlottenc.gov/arcgis/rest/services/CountyData/Parcels/MapServer"

params = {
    "f": "json"
}

response = requests.get(url, params=params)
data = response.json()

print("\nMecklenburg Parcel Service Layers:\n")

for layer in data.get("layers", []):
    print(layer.get("id"), "-", layer.get("name"))
    