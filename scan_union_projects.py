import json
from datetime import datetime

OUTPUT_FILE = "projects.json"

print("Summit Atlas — Union County Scanner")
print("-----------------------------------")

try:
    with open(OUTPUT_FILE, "r") as file:
        existing_projects = json.load(file)
except FileNotFoundError:
    existing_projects = []

existing_keys = {
    (p.get("county"), p.get("case_number"), p.get("address"))
    for p in existing_projects
}

union_projects = [
    {
        "county": "Union",
        "case_number": "CZ-2026-007",
        "address": "South side of Beulah Church Road",
        "acreage": "3.207",
        "owner": "",
        "applicant": "R. Dean Harrell",
        "zoning_change": "B-2 with Conditions -> B-2 with Modified Conditions",
        "description": "Modification to shopping center conditions to allow operating hours from 6:30 AM to 9:30 PM.",
        "source_url": "https://unioncountync.legistar.com/",
        "last_scanned": datetime.now().strftime("%Y-%m-%d")
    },
    {
        "county": "Union",
        "case_number": "CZ-2026-005",
        "address": "South Rocky River Road",
        "acreage": "5.75",
        "owner": "",
        "applicant": "Jeremy McAteer",
        "zoning_change": "RA-40 -> Light Industrial (LI) with Conditions",
        "description": "Office and equipment storage facility on a portion of a larger parcel.",
        "source_url": "https://unioncountync.legistar.com/",
        "last_scanned": datetime.now().strftime("%Y-%m-%d")
    }
]

added = 0

for project in union_projects:
    key = (
        project.get("county"),
        project.get("case_number"),
        project.get("address")
    )

    if key not in existing_keys:
        existing_projects.append(project)
        existing_keys.add(key)
        added += 1

with open(OUTPUT_FILE, "w") as file:
    json.dump(existing_projects, file, indent=2)

print("Union records scanned:", len(union_projects))
print("New Union projects added:", added)
print("Total projects:", len(existing_projects))
print("Union scan complete.")