import requests
import pdfplumber
import re
import json
from io import BytesIO

pdf_url = "https://unioncountync.legistar.com/View.ashx?M=PA&ID=1379629&GUID=ACEC038F-9A9B-4BF3-865B-1347DA8991A7"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(pdf_url, headers=headers)

print("Status:", response.status_code)
print("Content Type:", response.headers.get("Content-Type"))

with pdfplumber.open(BytesIO(response.content)) as pdf:
    text = ""

    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

projects = []

case_pattern = re.compile(
    r'(CZ-\d{4}-\d{3}|2026-CZ-\d{3}).{0,80}?(Beulah Church|McAteer)',
    re.IGNORECASE | re.DOTALL
)

matches = case_pattern.findall(text)

print("\nUNION CASES FOUND:\n")

for match in matches:
    case_number = match[0]
    project_name = match[1]

    print(case_number, "-", project_name)

# Manual structured records from the packet text we successfully extracted
projects.append({
    "county": "Union",
    "case_number": "CZ-2026-007",
    "address": "South side of Beulah Church Road",
    "acreage": "3.207",
    "owner": "",
    "applicant": "R. Dean Harrell",
    "zoning_change": "B-2 with Conditions -> B-2 with Modified Conditions",
    "description": "Modification to shopping center conditions to allow operating hours from 6:30 AM to 9:30 PM.",
    "source_url": pdf_url
})

projects.append({
    "county": "Union",
    "case_number": "CZ-2026-005",
    "address": "South Rocky River Road",
    "acreage": "5.75",
    "owner": "",
    "applicant": "Jeremy McAteer",
    "zoning_change": "RA-40 -> Light Industrial (LI) with Conditions",
    "description": "Office and equipment storage facility on a portion of a larger parcel.",
    "source_url": pdf_url
})

with open("union_projects.json", "w") as file:
    json.dump(projects, file, indent=4)

print("\nSaved Union projects to union_projects.json")