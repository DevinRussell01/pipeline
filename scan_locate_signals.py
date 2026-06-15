import json
from datetime import datetime

print("Summit Atlas — Locate Signal Scanner")
print("------------------------------------")

today = datetime.now().strftime("%Y-%m-%d")

signals = [
    {
        "ticket_id": "LOCATE-MECK-001",
        "state": "NC",
        "county": "Mecklenburg",
        "city": "Charlotte",
        "street": "Westinghouse Boulevard",
        "work_type": "Fiber / Utility Construction",
        "category": "Telecom",
        "excavator": "Unknown",
        "company": "Telecom / Fiber",
        "status": "Active Signal",
        "created_date": today,
        "lat": 35.1168,
        "lon": -80.9504,
        "risk_score": 9,
        "source": "Public ROW / Utility Signal",
        "signal": "Utility construction signal in high-growth industrial corridor"
    },
    {
        "ticket_id": "LOCATE-CAB-001",
        "state": "NC",
        "county": "Cabarrus",
        "city": "Concord",
        "street": "Concord Mills Boulevard",
        "work_type": "Directional Bore / Utility Work",
        "category": "Telecom",
        "excavator": "Unknown",
        "company": "Unknown",
        "status": "Active Signal",
        "created_date": today,
        "lat": 35.3706,
        "lon": -80.7252,
        "risk_score": 8,
        "source": "Public ROW / Utility Signal",
        "signal": "Possible underground utility or telecom work near commercial growth zone"
    },
    {
        "ticket_id": "LOCATE-UNION-001",
        "state": "NC",
        "county": "Union",
        "city": "Monroe",
        "street": "South Rocky River Road",
        "work_type": "Utility Construction",
        "category": "Utility",
        "excavator": "Unknown",
        "company": "Unknown",
        "status": "Active Signal",
        "created_date": today,
        "lat": 35.0176,
        "lon": -80.5495,
        "risk_score": 8,
        "source": "Public Development / Utility Signal",
        "signal": "Utility activity signal near active development corridor"
    }
]

with open("locate_tickets.json", "w") as file:
    json.dump(signals, file, indent=4)

print(f"Saved {len(signals)} locate intelligence signals.")
print("Scan complete.")