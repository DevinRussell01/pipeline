import requests

base = "https://gis.unioncountync.gov/server/rest/services"

folders = [
    "LandRecordsPro",
    "Property_Tax_Live",
    "PropertyTaxLive_May"
]

for folder in folders:
    url = f"{base}/{folder}"
    data = requests.get(url, params={"f": "json"}).json()

    print(f"\nFOLDER: {folder}")
    print("-------------------")

    for service in data.get("services", []):
        print(service.get("name"), "-", service.get("type"))