import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

OUTPUT_FILE = "projects.json"
GASTON_SEED_FILE = "gaston_projects.json"

SOURCE_URL = "https://gaston.granicus.com/boards/w/611252dc4b79d0a7/boards/52857"

PARCEL_QUERY_URL = (
    "https://gis.gastoncountync.gov/publicgis/rest/services/"
    "PublicGIS/Parcels/MapServer/11/query"
)

print("Conduit — Gaston Project Scanner")
print("--------------------------------")


def load_json(path):
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def extract_parcel_ids(project):
    text = " ".join([
        str(project.get("description") or ""),
        str(project.get("address") or ""),
    ])

    return re.findall(r"\b\d{6}\b", text)


def lookup_parcel(pid):
    params = {
        "where": f"PID='{pid}'",
        "outFields": (
            "PID,PIN,WHOLE_ADDRESS,CURR_NAME1,CURR_NAME2,"
            "CALCAC,DEEDAC,Latitude,Longitude"
        ),
        "returnGeometry": "false",
        "f": "json",
    }

    response = requests.get(
        PARCEL_QUERY_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    features = data.get("features", [])

    if not features:
        return None

    return features[0].get("attributes", {})


def enrich_project(project):
    parcel_ids = extract_parcel_ids(project)

    if not parcel_ids:
        return project

    parcel_records = []

    for pid in parcel_ids:
        try:
            record = lookup_parcel(pid)

            if record:
                parcel_records.append(record)
                print(f"  Parcel {pid}: MATCH")
            else:
                print(f"  Parcel {pid}: NO MATCH")

        except Exception as error:
            print(f"  Parcel {pid}: ERROR: {error}")

    if not parcel_records:
        return project

    valid_coords = [
        (
            float(record["Latitude"]),
            float(record["Longitude"]),
        )
        for record in parcel_records
        if record.get("Latitude") not in (None, "")
        and record.get("Longitude") not in (None, "")
    ]

    if valid_coords:
        project["lat"] = sum(x[0] for x in valid_coords) / len(valid_coords)
        project["lon"] = sum(x[1] for x in valid_coords) / len(valid_coords)

    acreage_values = []

    for record in parcel_records:
        acres = record.get("CALCAC")

        if acres in (None, "", 0):
            acres = record.get("DEEDAC")

        if acres not in (None, ""):
            try:
                acreage_values.append(float(acres))
            except (TypeError, ValueError):
                pass

    if acreage_values:
        project["acreage"] = round(sum(acreage_values), 2)

    owners = []

    for record in parcel_records:
        owner_parts = [
            str(record.get("CURR_NAME1") or "").strip(),
            str(record.get("CURR_NAME2") or "").strip(),
        ]

        owner = " ".join(x for x in owner_parts if x)

        if owner and owner not in owners:
            owners.append(owner)

    if owners:
        project["owner"] = " / ".join(owners)

    addresses = [
        str(record.get("WHOLE_ADDRESS") or "").strip()
        for record in parcel_records
        if record.get("WHOLE_ADDRESS")
    ]

    if addresses:
        project["gis_address"] = addresses[0]

    project["parcel_ids"] = parcel_ids
    project["gis_source"] = (
        "Gaston County PublicGIS Parcels MapServer"
    )

    return project


existing_projects = load_json(OUTPUT_FILE)
gaston_projects = load_json(GASTON_SEED_FILE)

print("Seed Gaston projects:", len(gaston_projects))

enriched_projects = []

for project in gaston_projects:
    print()
    print(
        "Processing:",
        project.get("case_number"),
        "-",
        project.get("address"),
    )

    enriched_projects.append(
        enrich_project(dict(project))
    )


existing_by_case = {
    (p.get("county"), p.get("case_number")): index
    for index, p in enumerate(existing_projects)
    if p.get("case_number")
}

added = 0
updated = 0

for project in enriched_projects:
    key = (
        project.get("county"),
        project.get("case_number"),
    )

    project["last_scanned"] = datetime.now().strftime("%Y-%m-%d")

    if key in existing_by_case:
        index = existing_by_case[key]

        existing_projects[index].update(project)

        updated += 1
    else:
        existing_projects.append(project)
        existing_by_case[key] = len(existing_projects) - 1
        added += 1


# Keep the broad planning-board monitor as a separate scanner record.
try:
    response = requests.get(
        SOURCE_URL,
        timeout=15,
    )

    print()
    print("Planning board status:", response.status_code)

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    text = soup.get_text(" ", strip=True)

    keywords = [
        "rezoning",
        "subdivision",
        "development",
        "site plan",
        "plat",
        "conditional zoning",
        "zoning",
    ]

    matches = [
        keyword
        for keyword in keywords
        if keyword.lower() in text.lower()
    ]

    if matches:
        scan_record = {
            "county": "Gaston",
            "case_number": "GASTON-PLANNING-ZONING-SCAN",
            "address": "Gaston County Planning and Zoning Board",
            "acreage": "",
            "owner": "",
            "applicant": "Automated County Scanner",
            "zoning_change": (
                "Detected planning/zoning activity: "
                + ", ".join(matches)
            ),
            "source_url": SOURCE_URL,
            "last_scanned": datetime.now().strftime("%Y-%m-%d"),
        }

        key = (
            scan_record["county"],
            scan_record["case_number"],
        )

        if key in existing_by_case:
            existing_projects[
                existing_by_case[key]
            ].update(scan_record)
        else:
            existing_projects.append(scan_record)
            added += 1

except Exception as error:
    print("Planning board scan warning:", error)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        existing_projects,
        file,
        indent=2,
        ensure_ascii=False,
    )


print()
print("--------------------------------")
print("Gaston scan complete.")
print("Projects enriched:", len(enriched_projects))
print("Existing records updated:", updated)
print("New records added:", added)
print("Total projects:", len(existing_projects))
