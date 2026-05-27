import requests
import pdfplumber
import re
import json
from io import BytesIO

# PDF STAFF REPORT URL
pdf_url = "https://www.iredellcountync.gov/AgendaCenter/ViewFile/Item/954?fileID=61507"

# Browser headers
headers = {
    "User-Agent": "Mozilla/5.0"
}

# Download PDF
response = requests.get(pdf_url, headers=headers)

print("Status:", response.status_code)
print("Content Type:", response.headers.get("Content-Type"))

# Extract PDF text
with pdfplumber.open(BytesIO(response.content)) as pdf:

    text = ""

    for page in pdf.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

# -----------------------------------
# DATA EXTRACTION
# -----------------------------------

print("\nEXTRACTED DATA:\n")

# CASE NUMBER
case_match = re.search(
    r'REZONING CASE\s*#?\s*(\d{4}-\d+)',
    text,
    re.IGNORECASE
)

if case_match:
    print("Case Number:", case_match.group(1))

# ADDRESS
address_match = re.search(
    r'ADDRESS/LOCATION:\s*(.*?)(?:SURROUNDING LAND USE|SIZE:)',
    text,
    re.IGNORECASE | re.DOTALL
)

if address_match:

    clean_address = " ".join(address_match.group(1).split())

    print("Address:", clean_address)

# ACREAGE
acre_match = re.search(
    r'(?:approximately|includes)\s*([\d\.]+)\s*acres',
    text,
    re.IGNORECASE
)

if acre_match:
    print("Acreage:", acre_match.group(1), "acres")

# OWNER
owner_match = re.search(
    r'OWNER:\s*(.+)',
    text
)

if owner_match:
    print("Owner:", owner_match.group(1).strip())

# APPLICANT
applicant_match = re.search(
    r'APPLICANT:\s*(.+)',
    text
)

if applicant_match:
    print("Applicant:", applicant_match.group(1).strip())

# ZONING CHANGE
zoning_match = re.search(
    r'from\s+([A-Za-z0-9\-\(\)\s]+)\s+to\s+([A-Za-z0-9\-\(\)\s]+)',
    text,
    re.IGNORECASE
)

if zoning_match:

    old_zone = zoning_match.group(1).strip()
    new_zone = zoning_match.group(2).strip()

    # Prevent grabbing meeting times
    if "pm" not in old_zone.lower() and "pm" not in new_zone.lower():

        print(
            "Zoning Change:",
            old_zone,
            "→",
            new_zone
        )
        # -----------------------------------
# CREATE PROJECT OBJECT
# -----------------------------------

project = {
    "county": "Iredell",
    "case_number": case_match.group(1) if case_match else "",
    "address": clean_address if address_match else "",
    "acreage": acre_match.group(1) if acre_match else "",
    "owner": owner_match.group(1).strip() if owner_match else "",
    "applicant": applicant_match.group(1).strip() if applicant_match else "",
    "zoning_change": f"{old_zone} -> {new_zone}" if zoning_match else "",
    "source_url": pdf_url
}

# -----------------------------------
# SAVE TO JSON FILE
# -----------------------------------

with open("projects.json", "w") as json_file:

    json.dump(
        project,
        json_file,
        indent=4
    )

print("\nSaved to projects.json")