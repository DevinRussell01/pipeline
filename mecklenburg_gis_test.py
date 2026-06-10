import requests

url = "https://gis.charlottenc.gov/arcgis/rest/services/PLN/Subdivisions/MapServer/0?f=pjson"

r = requests.get(url, timeout=15)
data = r.json()

print("Status:", r.status_code)
print("\nFIELDS:\n")

for field in data.get("fields", []):
    print(field.get("name"), "-", field.get("type"))