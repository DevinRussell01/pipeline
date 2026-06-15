import requests

base = "https://gis.unioncountync.gov/server/rest/services"

root = requests.get(base, params={"f": "json"}).json()

candidates = []

for service in root.get("services", []):
    name = service.get("name", "")
    service_type = service.get("type", "")

    if any(term.lower() in name.lower() for term in ["parcel", "property", "tax", "land"]):
        candidates.append((name, service_type))

for folder in root.get("folders", []):
    folder_url = f"{base}/{folder}"
    folder_data = requests.get(folder_url, params={"f": "json"}).json()

    for service in folder_data.get("services", []):
        name = service.get("name", "")
        service_type = service.get("type", "")

        if any(term.lower() in name.lower() for term in ["parcel", "property", "tax", "land"]):
            candidates.append((name, service_type))

print("\nCandidate Union Services:\n")

for name, service_type in candidates:
    print(name, "-", service_type)

print("\nInspecting Fields:\n")

for name, service_type in candidates:
    if service_type != "MapServer":
        continue

    url = f"{base}/{name}/MapServer"

    try:
        service_data = requests.get(url, params={"f": "json"}, timeout=10).json()
    except Exception as e:
        print("FAILED:", name, e)
        continue

    for layer in service_data.get("layers", []):
        layer_id = layer.get("id")
        layer_name = layer.get("name")

        layer_url = f"{url}/{layer_id}"
        layer_data = requests.get(layer_url, params={"f": "json"}).json()

        fields = layer_data.get("fields") or []
        field_names = [f.get("name") for f in fields]

        interesting = [
            f for f in field_names
            if any(term in f.lower() for term in ["owner", "acre", "area", "pid", "pin", "parcel", "name"])
        ]

        if interesting:
            print("\nSERVICE:", name)
            print("LAYER:", layer_id, "-", layer_name)
            print("FIELDS:", interesting)