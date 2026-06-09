import json
from datetime import datetime

OUTPUT_FILE = "projects.json"

print("Summit Atlas County Scanner")
print("---------------------------")

new_projects = [
    {
        "county": "Gaston",
        "case_number": "AUTO-TEST-001",
        "address": "Belmont / Gastonia Growth Corridor",
        "acreage": "",
        "owner": "",
        "applicant": "Summit Atlas Test Scan",
        "zoning_change": "Automated scanner test project",
        "source_url": "https://www.gastongov.com/",
        "last_scanned": datetime.now().strftime("%Y-%m-%d")
    }
]

try:
    with open(OUTPUT_FILE, "r") as file:
        existing_projects = json.load(file)
except FileNotFoundError:
    existing_projects = []

existing_keys = {
    (p.get("county"), p.get("case_number"), p.get("address"))
    for p in existing_projects
}

added = 0

for project in new_projects:
    key = (
        project.get("county"),
        project.get("case_number"),
        project.get("address")
    )

    if key not in existing_keys:
        existing_projects.append(project)
        added += 1

with open(OUTPUT_FILE, "w") as file:
    json.dump(existing_projects, file, indent=2)

print("Existing projects before scan:", len(existing_projects) - added)
print("New projects added:", added)
print("Total projects:", len(existing_projects))
print("Scan timestamp:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("County scan complete.")