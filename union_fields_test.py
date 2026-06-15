import requests

url = "https://gis.unioncountync.gov/server/rest/services/Property_Tax_Live/Parcels/MapServer/0"

data = requests.get(url, params={"f": "json"}).json()

print("\nUnion Tax Parcel Field List:\n")

for field in data.get("fields", []):
    print(field.get("name"), "-", field.get("type"), "-", field.get("alias"))