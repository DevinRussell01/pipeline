import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

OUTPUT_FILE = "projects.json"

SOURCE_URL = "https://www.brunswickcountync.gov/381/Planning-Community-Enforcement"

headers = {
    "User-Agent": "Mozilla/5.0"
}

print("Summit Atlas — Brunswick Project Scanner")
print("---------------------------------------")

response = requests.get(SOURCE_URL, headers=headers, timeout=15)
print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

matches = []

keywords = [
    "rezoning",
    "subdivision",
    "development",
    "site plan",
    "plat",
    "conditional zoning",
    "zoning",
    "planned development",
    "major subdivision",
    "preliminary plat"
]

text = soup.get_text(" ", strip=True)

for keyword in keywords:
    if keyword.lower() in text.lower():
        matches.append(keyword)

try:
    with open(OUTPUT_FILE, "r") as file:
        existing_projects = json.load(file)
except FileNotFoundError:
    existing_projects = []

new_projects = []

if matches:
    new_projects.append({
        "county": "Brunswick",
        "case_number": "BRUNSWICK-PLANNING-ZONING-SCAN",
        "address": "Brunswick County Planning and Zoning",
        "acreage": "",
        "owner": "",
        "applicant": "Automated County Scanner",
        "zoning_change": "Detected planning/zoning activity: " + ", ".join(matches),
        "source_url": SOURCE_URL,
        "last_scanned": datetime.now().strftime("%Y-%m-%d")
    })

existing_keys = {
    (p.get("county"), p.get("case_number"), p.get("address"))
    for p in existing_projects
}

added = 0

for project in new_projects:
    key = (project.get("county"), project.get("case_number"), project.get("address"))

    if key not in existing_keys:
        existing_projects.append(project)
        added += 1

with open(OUTPUT_FILE, "w") as file:
    json.dump(existing_projects, file, indent=2)

print("Keywords detected:", matches)
print("New projects added:", added)
print("Total projects:", len(existing_projects))
print("Scan complete.")