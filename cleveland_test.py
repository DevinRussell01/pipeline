import requests
import pdfplumber
import json
from urllib.parse import quote
from io import BytesIO

pdf_url = "https://www.clevelandcounty.com/main/06032025%20Regular%20Meeting.pdf?t=202604221037300"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/137.0.0.0 Safari/537.36"
    )
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

if "PLANNING DEPARTMENT CASE 25-05" in text:
    projects.append({
        "county": "Cleveland",
        "case_number": "25-05",
        "address": "128 Corinth Church Road",
        "acreage": "",
        "owner": "",
        "applicant": "",
        "zoning_change": "Residential (R) -> Rural Residential (RU)",
        "description": "Request to rezone 128 Corinth Church Road from Residential to Rural Residential.",
        "source_url": pdf_url
    })

with open("cleveland_projects.json", "w") as file:
    json.dump(projects, file, indent=4)

print("Saved Cleveland projects to cleveland_projects.json")
print("Total Cleveland projects:", len(projects))