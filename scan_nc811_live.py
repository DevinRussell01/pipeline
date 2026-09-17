import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests

from build_conduit_grid import (
    build_region_grid,
    load_json,
)


API_URL = "https://central-api.diglogix.com/ticket/near-ticket"
OUTPUT_FILE = "locate_tickets.json"
HISTORY_FILE = "locate_tickets_history.json"

STATE_FILE = "topaz_scan_state.json"
TERRITORY_FILE = "conduit_territories.json"
GEOMETRY_FILE = "conduit_county_boundaries.geojson"

REGION_KEY = "WESTERN_NC"
REQUEST_DELAY_SECONDS = 0.50


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

def load_scan_partition():
    """
    Build the deterministic polygon-clipped TOPAZ grid and
    return only the partition scheduled for this run.

    No NC811 requests occur in this function.
    """

    territory_data = load_json(
        Path(TERRITORY_FILE)
    )

    geometry_data = load_json(
        Path(GEOMETRY_FILE)
    )

    state_data = load_json(
        Path(STATE_FILE)
    )

    region_config = (
        territory_data
        .get("regions", {})
        .get(REGION_KEY)
    )

    if not region_config:
        raise RuntimeError(
            f"Missing territory configuration: "
            f"{REGION_KEY}"
        )

    region_state = (
        state_data
        .get("regions", {})
        .get(REGION_KEY)
    )

    if not region_state:
        raise RuntimeError(
            f"Missing scan state: {REGION_KEY}"
        )

    partition_count = int(
        region_config.get(
            "partition_count",
            0
        )
    )

    if partition_count <= 0:
        raise RuntimeError(
            "Invalid partition count."
        )

    state_partition_count = int(
        region_state.get(
            "partition_count",
            0
        )
    )

    if (
        state_partition_count
        != partition_count
    ):
        raise RuntimeError(
            "Territory/state partition-count "
            "mismatch."
        )

    partition = int(
        region_state.get(
            "next_partition",
            0
        )
    )

    if not (
        0 <= partition < partition_count
    ):
        raise RuntimeError(
            f"Invalid next partition: "
            f"{partition}"
        )

    grid = build_region_grid(
        REGION_KEY,
        region_config,
        geometry_data.get(
            "features",
            []
        ),
    )

    selected = [
        point
        for point in grid["points"]
        if int(
            point.get("partition", -1)
        ) == partition
    ]

    if not selected:
        raise RuntimeError(
            f"Partition {partition} "
            "contains no query points."
        )

    queries = []

    for index, point in enumerate(
        selected,
        start=1
    ):
        queries.append({
            "name": (
                f"{REGION_KEY}:"
                f"P{partition:02d}:"
                f"{point.get('county', 'Unknown')}:"
                f"{index:04d}"
            ),
            "county": point.get("county"),
            "lat": point["lat"],
            "lon": point["lon"],
            "point": (
                f"[{point['lon']},"
                f"{point['lat']}]"
            ),
        })

    return (
        queries,
        state_data,
        partition,
        partition_count,
    )


(
    QUERY_POINTS,
    SCAN_STATE,
    CURRENT_PARTITION,
    PARTITION_COUNT,
) = load_scan_partition()


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

        if REQUEST_DELAY_SECONDS > 0:
            time.sleep(
                REQUEST_DELAY_SECONDS
            )

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
# COLLECTION VALIDATION / FAIL-SAFE
# =========================================================
#
# Never replace a known-good NC811 dataset with an empty
# dataset caused by an upstream/API collection failure.
#
# A regional scan that retrieves zero raw records is treated
# as a failed collection, not as evidence that regional
# excavation activity has disappeared.
#

if (
    successful_points != len(QUERY_POINTS)
    or failed_points != 0
    or len(all_raw_tickets) == 0
):
    print()
    print("ERROR: NC811 collection produced no usable source records.")
    print("Existing locate intelligence files were NOT overwritten.")
    print(
        f"Successful query points: {successful_points}/"
        f"{len(QUERY_POINTS)}"
    )
    print(f"Failed query points: {failed_points}")
    print(f"Raw records retrieved: {len(all_raw_tickets)}")
    sys.exit(1)


# =========================================================
# NORMALIZE + DEDUPLICATE REVISIONS
# =========================================================

history_records = []
seen_revisions = set()
duplicate_revisions_removed = 0
existing_history_records = 0
new_history_records = 0

# ---------------------------------------------------------
# Load previously discovered ticket revisions.
#
# Rotating geographic partitions must never erase history
# merely because a ticket's area was not queried this run.
# ---------------------------------------------------------

if os.path.exists(HISTORY_FILE):
    try:
        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:
            existing_history = json.load(
                file
            )

        if not isinstance(
            existing_history,
            list
        ):
            raise ValueError(
                "Existing history is not a list."
            )

        for record in existing_history:
            if not isinstance(record, dict):
                continue

            ticket_id = str(
                record.get("ticket_id")
                or ""
            )

            revision = str(
                record.get("revision")
                or ""
            )

            if not ticket_id:
                continue

            revision_key = (
                ticket_id,
                revision
            )

            if revision_key in seen_revisions:
                continue

            seen_revisions.add(
                revision_key
            )

            history_records.append(
                record
            )

        existing_history_records = len(
            history_records
        )

    except (
        OSError,
        ValueError,
        json.JSONDecodeError
    ) as exc:
        print()
        print(
            "ERROR: existing NC811 history "
            "could not be loaded safely."
        )
        print(exc)
        print(
            "Existing production files were "
            "NOT overwritten."
        )
        sys.exit(1)

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
    new_history_records += 1

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
# DATASET VALIDATION / FAIL-SAFE
# =========================================================
#
# Successful HTTP responses do not automatically mean the
# resulting operational dataset is valid. If normalization
# or filtering produces no usable active records, preserve
# the existing production files and fail the scan.
#

if len(history_records) == 0 or len(active_records) == 0:
    print()
    print("ERROR: NC811 processing produced an unusable dataset.")
    print("Existing locate intelligence files were NOT overwritten.")
    print(f"Raw records retrieved: {len(all_raw_tickets)}")
    print(f"Normalized history records: {len(history_records)}")
    print(f"Active operational tickets: {len(active_records)}")
    sys.exit(1)


# =========================================================
# ATOMIC SAVE
# =========================================================
#
# Write each dataset to a temporary file first, then replace
# the production file only after serialization succeeds.
#

def atomic_json_write(filename, data):
    temp_file = f"{filename}.tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )
            file.flush()
            os.fsync(file.fileno())

        os.replace(temp_file, filename)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# =========================================================
# SAVE HISTORY
# =========================================================

atomic_json_write(
    HISTORY_FILE,
    history_records
)


# =========================================================
# SAVE ACTIVE OPERATIONAL DATASET
# =========================================================

atomic_json_write(
    OUTPUT_FILE,
    active_records
)


# =========================================================
# ADVANCE ROLLING PARTITION STATE
# =========================================================
#
# This occurs only after both production datasets have been
# written successfully. A failed collection never advances
# the geographic partition.
#

region_state = (
    SCAN_STATE["regions"][REGION_KEY]
)

next_partition = (
    CURRENT_PARTITION + 1
) % PARTITION_COUNT

region_state[
    "last_successful_partition"
] = CURRENT_PARTITION

region_state[
    "last_scan"
] = datetime.now(
    timezone.utc
).isoformat()

region_state[
    "next_partition"
] = next_partition

if next_partition == 0:
    region_state[
        "completed_cycles"
    ] = int(
        region_state.get(
            "completed_cycles",
            0
        )
    ) + 1

atomic_json_write(
    STATE_FILE,
    SCAN_STATE
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

print(
    "Region:",
    REGION_KEY
)
print(
    "Partition:",
    f"{CURRENT_PARTITION:02d}/"
    f"{PARTITION_COUNT - 1:02d}"
)
print("Query points:", len(QUERY_POINTS))
print("Successful points:", successful_points)
print("Failed points:", failed_points)

print("Raw records retrieved:", len(all_raw_tickets))
print(
    "Existing history loaded:",
    existing_history_records
)
print(
    "New ticket revisions added:",
    new_history_records
)
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
print("Saved state:", STATE_FILE)
print(
    "Next partition:",
    f"{next_partition:02d}"
)


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