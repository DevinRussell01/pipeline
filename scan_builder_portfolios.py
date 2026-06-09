import json
from datetime import datetime

OUTPUT_FILE = "builder_portfolios.json"

# Starter automated records
# Later this will scrape builder websites directly
new_records = [
    {
        "builder": "D.R. Horton",
        "community": "Avalon",
        "county": "Gaston",
        "city": "Gastonia",
        "status": "Selling",
        "product_type": "Single Family",
        "price_from": 444990,
        "lots": "",
        "source": "https://www.drhorton.com",
        "last_scanned": datetime.now().strftime("%Y-%m-%d")
    }
]

try:
    with open(OUTPUT_FILE, "r") as file:
        existing = json.load(file)
except FileNotFoundError:
    existing = []

# prevent duplicates by builder + community
existing_keys = {
    (item.get("builder"), item.get("community"))
    for item in existing
}

for record in new_records:
    key = (record.get("builder"), record.get("community"))

    if key not in existing_keys:
        existing.append(record)

with open(OUTPUT_FILE, "w") as file:
    json.dump(existing, file, indent=2)

print("Builder portfolio scan complete.")
print("Total communities:", len(existing))