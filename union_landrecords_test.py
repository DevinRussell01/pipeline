import requests

urls = [
    "https://gis.unioncountync.gov/server/rest/services/LandRecordsPro/Parcels/MapServer",
    "https://gis.unioncountync.gov/server/rest/services/LandRecordsPro/ParcelCentroids/MapServer",
    "https://gis.unioncountync.gov/server/rest/services/LandRecordsPro/LandRecords/MapServer",
]

for url in urls:
    print("\nTesting:", url)
    data = requests.get(url, params={"f": "json"}).json()

    if "error" in data:
        print("ERROR:", data["error"])
        continue

    for layer in data.get("layers", []):
        print(layer.get("id"), "-", layer.get("name"))