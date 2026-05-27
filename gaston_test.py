import requests
import pdfplumber
import re
import json
from io import BytesIO

pdf_url = "https://gaston.legistar.com/View.ashx?M=A&ID=1347779&GUID=619549F2-2D5A-4DB4-ABA4-DB913D83F2A4"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(pdf_url, headers=headers)

with pdfplumber.open(BytesIO(response.content)) as pdf:
    text = ""

    for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

projects = []

patterns = [
    {
        "case_number": "REZ-26-03-06-00243",
        "applicant": "Zachary Carpenter",
        "address": "Mic Lock Pl., Dallas, NC",
        "parcels": "169984 & 312523",
        "zoning_change": "R-1 Single Family Limited with US Overlay -> R-2 Single Family Moderate with US Overlay"
    },
    {
        "case_number": "REZ-26-03-26-00244",
        "applicant": "Sarah Wooten",
        "address": "Red Yam Farm Rd., Dallas, NC",
        "parcels": "168347",
        "zoning_change": "R-1 Single Family Limited with US Overlay -> R-2 Single Family Moderate with US Overlay"
    }
]

for item in patterns:
    if item["case_number"] in text:
        projects.append({
            "county": "Gaston",
            "case_number": item["case_number"],
            "address": item["address"],
            "acreage": "",
            "owner": "",
            "applicant": item["applicant"],
            "zoning_change": item["zoning_change"],
            "description": f"Zoning map change for parcels {item['parcels']}.",
            "source_url": pdf_url
        })

with open("gaston_projects.json", "w") as file:
    json.dump(projects, file, indent=4)

print("Saved Gaston projects to gaston_projects.json")
print("Total Gaston projects:", len(projects))