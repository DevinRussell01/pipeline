import requests

url = "https://gis.gastoncountync.gov/publicgis/rest/services/PublicGIS/Parcels/MapServer/11?f=pjson"

response = requests.get(url)
data = response.json()

print("Status:", response.status_code)
print("\nALL FIELDS:\n")

for field in data.get("fields", []):
    print(field.get("name"))