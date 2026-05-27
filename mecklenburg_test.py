import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "https://www.charlottenc.gov/Growth-and-Development/Planning-and-Development/Rezoning/2026"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(url, headers=headers)

print("Status:", response.status_code)

soup = BeautifulSoup(response.text, "html.parser")

print("\nMecklenburg / Charlotte Rezoning Items Found:\n")

for heading in soup.find_all(["h2", "h3", "h4"]):
    text = heading.get_text(strip=True)

    if "2026-" in text or "2025-" in text:
        print(text)
        print("------")