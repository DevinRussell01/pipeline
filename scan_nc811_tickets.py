import json
from datetime import datetime

print("Summit Atlas — NC811 Ticket Scanner")
print("-----------------------------------")

# Temporary structured seed data.
# Later this will be replaced with real NC811 / Positive Response / Exactix data.
tickets = [
    {
        "ticket_id": "NC811-UNION-001",
        "state": "NC",
        "county": "Union",
        "city": "Monroe",
        "street": "South Rocky River Road",
        "work_type": "Utility Construction",
        "category": "Utility",
        "excavator": "Unknown",
        "company": "Unknown",
        "status": "Active",
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "lat": 35.0176,
        "lon": -80.5495,
        "risk_score": 8,
        "source": "NC811",
        "signal": "Locate activity near active Union County development corridor"
    },
    {
        "ticket_id": "NC811-MECK-001",
        "state": "NC",
        "county": "Mecklenburg",
        "city": "Charlotte",
        "street": "Westinghouse Boulevard",
        "work_type": "Fiber Installation",
        "category": "Telecom",
        "excavator": "Unknown",
        "company": "Fiber / Telecom",
        "status": "Active",
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "lat": 35.1168,
        "lon": -80.9504,
        "risk_score": 9,
        "source": "NC811",
        "signal": "Telecom locate activity in high-growth industrial corridor"
    },
    {
        "ticket_id": "NC811-CAB-001",
        "state": "NC",
        "county": "Cabarrus",
        "city": "Concord",
        "street": "Concord Mills Boulevard",
        "work_type": "Directional Bore",
        "category": "Telecom",
        "excavator": "Unknown",
        "company": "Unknown",
        "status": "Active",
        "created_date": datetime.now().strftime("%Y-%m-%d"),
        "lat": 35.3706,
        "lon": -80.7252,
        "risk_score": 8,
        "source": "NC811",
        "signal": "Possible telecom construction activity near commercial growth zone"
    }
]

with open("locate_tickets.json", "w") as file:
    json.dump(tickets, file, indent=4)

print(f"Saved {len(tickets)} NC811 locate tickets.")
print("Scan complete.")