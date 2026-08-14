import json
from datetime import datetime, timezone

import requests


API_URL = "https://central-api.diglogix.com/ticket/near-ticket"
OUTPUT_FILE = "locate_tickets.json"
HISTORY_FILE = "locate_tickets_history.json"


# =========================================================
# REGIONAL NC811 COLLECTION POINTS
# =========================================================
#
# Each point queries the NC811 public near-ticket endpoint.
# Overlap is intentional. Duplicate ticket revisions are
# removed after collection.
#
# ArcGIS/API coordinate order:
# [longitude, latitude]
#

QUERY_POINTS = [
    {
        "name": "Charlotte",
        "point": "[-80.8431,35.2271]"
    },
    {
        "name": "Gastonia",
        "point": "[-81.1873,35.2621]"
    },
    {
        "name": "Shelby",
        "point": "[-81.5356,35.2924]"
    },
    {
        "name": "Hickory",
        "point": "[-81.3412,35.7345]"
    },
    {
        "name": "Morganton",
        "point": "[-81.6848,35.7454]"
    },
    {
        "name": "Statesville",
        "point": "[-80.8873,35.7826]"
    },
    {
        "name": "Concord",
        "point": "[-80.5795,35.4088]"
    },
    {
        "name": "Monroe",
        "point": "[-80.5495,34.9854]"
    },
    {
        "name": "Asheville",
        "point": "[-82.5515,35.5951]"
    },
    {
        "name": "Hendersonville",
        "point": "[-82.4609,35.3187]"
    },
    {
        "name": "Waynesville",
        "point": "[-82.9887,35.4887]"
    },
    {
        "name": "Boone",
        "point": "[-81.6746,36.2168]"
    }
]


HEADERS = {
    "Accept": "application/json",
    "Origin": "https://diglogix.com",
    "Referer": "https://diglogix.com/",
    "User-Agent": "Mozilla/5.0"
}


def priority_score(priority):
    """
    Operational urgency score for a live 811 locate request.

    This score reflects ticket priority, not development opportunity.
    Opportunity potential is evaluated separately by Conduit's
    correlation engine.
    """

    priority = str(priority or "").upper()

    if priority == "EMER":
        return 10

    if priority == "RUSH":
        return 8

    if priority == "SHRT":
        return 6

    return 2


def normalize_ticket(ticket, query_region):
    """
    Convert a raw NC811 record into Conduit's normalized
    live 811 intelligence schema.
    """

    ticket_id = str(ticket.get("ticket") or "")
    revision = str(ticket.get("revision") or "")

    county = str(ticket.get("county") or "").strip().title()
    city = str(ticket.get("place") or "").strip().title()
    street = str(ticket.get("street") or "").strip().title()
    state = str(ticket.get("state") or "NC").strip().upper()

    cross_streets = [
        ticket.get("cross_street1"),
        ticket.get("cross_street2")
    ]

    cross_streets = [
        str(value).strip().title()
        for value in cross_streets
        if value
    ]

    ticket_type = str(
        ticket.get("type") or "UNKNOWN"
    ).strip().upper()

    priority = str(
        ticket.get("priority") or "NORM"
    ).strip().upper()

    caller = str(
        ticket.get("caller_name") or "Unknown"
    ).strip()

    return {
        # ---------------------------------------------
        # Canonical Conduit source metadata
        # ---------------------------------------------
        "source_system": "NC811",
        "source_type": "public_811_live",
        "source_record_id": f"{ticket_id}-{revision}",
        "source_region": query_region,
        "ingested_at": datetime.now(timezone.utc).isoformat(),

        # ---------------------------------------------
        # Geographic normalization
        # ---------------------------------------------
        "state": state,
        "county": county,
        "city": city,
        "street": street,
        "lat": ticket.get("latitude"),
        "lon": ticket.get("longitude"),

        # ---------------------------------------------
        # NC811-specific fields
        # ---------------------------------------------
        "ticket_id": ticket_id,
        "revision": revision,
        "cross_streets": cross_streets,
        "work_type": "811 Locate Request",
        "category": "Utility",
        "excavator": caller,
        "company": caller,
        "status": "Active 811 Locate",
        "ticket_type": ticket_type,
        "priority": priority,
        "created_date": ticket.get("created_at"),
        "work_date": ticket.get("work_at"),
        "expires_date": ticket.get("expires_at"),
        "risk_score": priority_score(priority),

        # ---------------------------------------------
        # Human-readable intelligence fields
        # ---------------------------------------------
        "source": "NC811 Public Near Ticket",
        "signal": (
            f"Live NC811 {ticket_type} locate request in "
            f"{city}, {county} County"
        )
    }


print("CONDUIT — REGIONAL LIVE NC811 SCANNER")
print("--------------------------------------")

all_raw_tickets = []

successful_points = 0
failed_points = 0

# =========================================================
# COLLECT REGIONAL NC811 RECORDS
# =========================================================

for query in QUERY_POINTS:

    name = query["name"]
    point = query["point"]

    print()
    print(f"Scanning {name}...")

    params = {
        "center": "NCOCC",
        "point": point
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=HEADERS,
            timeout=30
        )

        print("  HTTP:", response.status_code)

        response.raise_for_status()

        payload = response.json()
        records = payload.get("data", [])

        print("  Raw records:", len(records))

        successful_points += 1

        for ticket in records:
            all_raw_tickets.append(
                {
                    "ticket": ticket,
                    "query_region": name
                }
            )

    except Exception as error:
        failed_points += 1
        print(f"  ERROR: {error}")

# =========================================================
# NORMALIZE + DEDUPLICATE REVISIONS
# =========================================================

history_records = []
seen_revisions = set()
duplicate_revisions_removed = 0

for item in all_raw_tickets:

    ticket = item["ticket"]
    query_region = item["query_region"]

    ticket_id = str(ticket.get("ticket") or "")
    revision = str(ticket.get("revision") or "")

    if not ticket_id:
        continue

    revision_key = (
        ticket_id,
        revision
    )

    if revision_key in seen_revisions:
        duplicate_revisions_removed += 1
        continue

    seen_revisions.add(revision_key)

    record = normalize_ticket(
        ticket,
        query_region
    )

    if record["lat"] is None or record["lon"] is None:
        continue

    history_records.append(record)

# =========================================================
# SELECT CURRENT STATE PER TICKET
# =========================================================

latest_by_ticket = {}

for record in history_records:

    ticket_id = record.get("ticket_id")

    if not ticket_id:
        continue

    current = latest_by_ticket.get(ticket_id)

    if current is None:
        latest_by_ticket[ticket_id] = record
        continue

    try:
        current_revision = int(current.get("revision") or 0)
    except (TypeError, ValueError):
        current_revision = 0

    try:
        candidate_revision = int(record.get("revision") or 0)
    except (TypeError, ValueError):
        candidate_revision = 0

    if candidate_revision > current_revision:
        latest_by_ticket[ticket_id] = record

    elif candidate_revision == current_revision:

        current_created = str(
            current.get("created_date") or ""
        )

        candidate_created = str(
            record.get("created_date") or ""
        )

        if candidate_created > current_created:
            latest_by_ticket[ticket_id] = record


current_records = list(
    latest_by_ticket.values()
)

# =========================================================
# BUILD ACTIVE OPERATIONAL DATASET
# =========================================================

now = datetime.now(timezone.utc)

cancelled_records = []
expired_records = []
active_records = []

for record in current_records:

    ticket_type = str(
        record.get("ticket_type") or ""
    ).upper()

    if ticket_type == "CNCL":
        cancelled_records.append(record)
        continue

    expires_value = record.get("expires_date")

    if expires_value:
        try:
            expires_at = datetime.fromisoformat(
                str(expires_value).replace("Z", "+00:00")
            )

            if expires_at < now:
                expired_records.append(record)
                continue

        except (TypeError, ValueError):
            pass

    active_records.append(record)

normalized = []
seen = set()
duplicates_removed = 0

for item in all_raw_tickets:

    ticket = item["ticket"]
    query_region = item["query_region"]

    ticket_id = str(ticket.get("ticket") or "")
    revision = str(ticket.get("revision") or "")

    if not ticket_id:
        continue

    key = (
        ticket_id,
        revision
    )

    if key in seen:
        duplicates_removed += 1
        continue

    seen.add(key)

    record = normalize_ticket(
        ticket,
        query_region
    )

    if record["lat"] is None or record["lon"] is None:
        continue

    normalized.append(record)


# =========================================================
# SORT OUTPUT
# =========================================================

history_records.sort(
    key=lambda record: (
        record.get("ticket_id") or "",
        int(record.get("revision") or 0)
    )
)

active_records.sort(
    key=lambda record: (
        record.get("county") or "",
        record.get("city") or "",
        record.get("street") or "",
        record.get("ticket_id") or ""
    )
)

# =========================================================
# SAVE HISTORY
# =========================================================

with open(HISTORY_FILE, "w", encoding="utf-8") as file:
    json.dump(
        history_records,
        file,
        indent=2,
        ensure_ascii=False
    )


# =========================================================
# SAVE ACTIVE OPERATIONAL DATASET
# =========================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        active_records,
        file,
        indent=2,
        ensure_ascii=False
    )


# =========================================================
# SCAN SUMMARY
# =========================================================

counties = sorted({
    record.get("county")
    for record in active_records
    if record.get("county")
})

cities = sorted({
    record.get("city")
    for record in active_records
    if record.get("city")
})

print()
print("--------------------------------------")
print("REGIONAL NC811 SCAN COMPLETE")
print("--------------------------------------")

print("Query points:", len(QUERY_POINTS))
print("Successful points:", successful_points)
print("Failed points:", failed_points)

print("Raw records retrieved:", len(all_raw_tickets))
print(
    "Duplicate ticket revisions removed:",
    duplicate_revisions_removed
)
print(
    "Unique ticket revisions:",
    len(history_records)
)
print(
    "Unique ticket IDs:",
    len(current_records)
)
print(
    "Cancelled current-state tickets:",
    len(cancelled_records)
)
print(
    "Expired current-state tickets:",
    len(expired_records)
)
print(
    "Active operational tickets:",
    len(active_records)
)

print("Counties represented:", len(counties))
print("Cities represented:", len(cities))

print()
print("COUNTIES")
print("--------")

for county in counties:
    count = sum(
        record.get("county") == county
        for record in active_records
    )

    print(f"{county}: {count}")

print()
print("Saved history:", HISTORY_FILE)
print("Saved active:", OUTPUT_FILE)


if active_records:

    print()
    print("FIRST NORMALIZED RECORD")
    print("-----------------------")

    print(
        json.dumps(
            active_records[0],
            indent=2,
            ensure_ascii=False
        )
    )