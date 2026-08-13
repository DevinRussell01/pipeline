import json
import requests

API_URL = "https://central-api.diglogix.com/ticket/near-ticket"
OUTPUT_FILE = "locate_tickets.json"

params = {
    "center": "NCOCC",
    "point": "[-81.26662061693096,35.291530037458266]"
}

headers = {
    "Accept": "application/json",
    "Origin": "https://diglogix.com",
    "Referer": "https://diglogix.com/",
    "User-Agent": "Mozilla/5.0"
}


def priority_score(priority):
    """
    Base intelligence value for a verified live 811 locate request.

    Ticket urgency is preserved separately in the priority field and
    does not directly imply a stronger development opportunity.
    """
    return 2


def normalize_ticket(ticket):
    county = str(ticket.get("county") or "").title()
    city = str(ticket.get("place") or "").title()
    street = str(ticket.get("street") or "").title()

    cross_streets = [
        ticket.get("cross_street1"),
        ticket.get("cross_street2")
    ]

    cross_streets = [
        str(value).title()
        for value in cross_streets
        if value
    ]

    ticket_type = str(ticket.get("type") or "UNKNOWN").upper()
    priority = str(ticket.get("priority") or "NORM").upper()

    return {
        "ticket_id": str(ticket.get("ticket") or ""),
        "revision": str(ticket.get("revision") or ""),
        "state": str(ticket.get("state") or "NC"),
        "county": county,
        "city": city,
        "street": street,
        "cross_streets": cross_streets,
        "work_type": "811 Locate Request",
        "category": "Utility",
        "excavator": str(ticket.get("caller_name") or "Unknown"),
        "company": str(ticket.get("caller_name") or "Unknown"),
        "status": "Active 811 Locate",
        "ticket_type": ticket_type,
        "priority": priority,
        "created_date": ticket.get("created_at"),
        "work_date": ticket.get("work_at"),
        "expires_date": ticket.get("expires_at"),
        "lat": ticket.get("latitude"),
        "lon": ticket.get("longitude"),
        "risk_score": priority_score(priority),
        "source": "NC811 Public Near Ticket",
        "source_type": "public_811_live",
        "signal": (
            f"Live NC811 {ticket_type} locate request in "
            f"{city}, {county} County"
        )
    }


print("CONDUIT — LIVE NC811 SCANNER")
print("----------------------------")

response = requests.get(
    API_URL,
    params=params,
    headers=headers,
    timeout=30
)

print("HTTP:", response.status_code)

response.raise_for_status()

payload = response.json()
raw_tickets = payload.get("data", [])

print("Raw records:", len(raw_tickets))

normalized = []
seen = set()

for ticket in raw_tickets:

    key = (
        str(ticket.get("ticket") or ""),
        str(ticket.get("revision") or "")
    )

    if not key[0]:
        continue

    if key in seen:
        continue

    seen.add(key)

    record = normalize_ticket(ticket)

    if record["lat"] is None or record["lon"] is None:
        continue

    normalized.append(record)


with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        normalized,
        file,
        indent=2,
        ensure_ascii=False
    )


print("Normalized records:", len(normalized))
print("Saved:", OUTPUT_FILE)

if normalized:
    first = normalized[0]

    print()
    print("FIRST NORMALIZED RECORD")
    print("-----------------------")
    print(json.dumps(first, indent=2))