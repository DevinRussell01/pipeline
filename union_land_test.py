import requests
import time
from bs4 import BeautifulSoup


def get_union_owner_and_acres(pid):

    search_url = "https://unionnc.devnetwedge.com/search/quick"

    try:
        search_html = requests.get(
            search_url,
            params={"q": pid},
            timeout=20
        ).text

        search_soup = BeautifulSoup(search_html, "html.parser")

        owner = "Unknown"
        address = ""

        for table in search_soup.find_all("table"):

            parts = [
                p.strip()
                for p in table.get_text("|", strip=True).split("|")
            ]

            if pid not in parts:
                continue

            try:
                number_index = parts.index(pid)
                owner = parts[number_index + 1]
                address = parts[number_index + 2]
            except:
                pass

            break

        detail_url = (
            "https://unionnc.devnetwedge.com/"
            "search/ViewQuickSearchResult"
        )

        detail_params = {
            "row": "1",
            "property_key": pid,
            "year": "2025",
            "property_type": "Parcel"
        }

        detail_html = requests.get(
            detail_url,
            params=detail_params,
            timeout=20
        ).text

        detail_soup = BeautifulSoup(detail_html, "html.parser")

        detail_text = detail_soup.get_text("|", strip=True)

        acres = 0

        parts = [
            p.strip()
            for p in detail_text.split("|")
        ]

        for i, part in enumerate(parts):

            if part == "Deeded Acres":

                try:
                    acres = float(parts[i + 1])
                except:
                    acres = 0

                break

        return owner, address, acres

    except Exception as e:

        print(f"Lookup failed for {pid}: {e}")

        return "Unknown", "", 0


centroid_url = (
    "https://gis.unioncountync.gov/server/rest/services/"
    "ParcelCentroids/MapServer/0/query"
)

params = {
    "where": "1=1",
    "outFields": "PID,MuniAdmin,CountyZoning,ZoningAdmin,FireDistrict",
    "returnGeometry": "true",
    "f": "json",
    "resultRecordCount": 10,
    "outSR": "4326"
}

data = requests.get(
    centroid_url,
    params=params,
    timeout=20
).json()

print("\nUnion Land Intelligence Test:\n")

for feature in data.get("features", []):

    attr = feature.get("attributes", {})
    geom = feature.get("geometry", {})

    pid = attr.get("PID")

    owner, address, acres = get_union_owner_and_acres(pid)

    print("PID:", pid)
    print("Owner:", owner)
    print("Address:", address)
    print("Acres:", acres)
    print("Zoning:", attr.get("CountyZoning"))
    print("Lat:", geom.get("y"))
    print("Lon:", geom.get("x"))
    print("------")

    time.sleep(1)