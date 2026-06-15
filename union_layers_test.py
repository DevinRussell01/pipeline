import requests

url = "https://gis.unioncountync.gov/server/rest/services/Property_Tax_Live/Parcels/MapServer"

data = requests.get(url, params={"f": "json"}).json()

print("\nUnion Property Tax Live Parcels Layers:\n")

for layer in data.get("layers", []):
    print(layer.get("id"), "-", layer.get("name"))