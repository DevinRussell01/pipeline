import json
import os
from datetime import datetime, timezone
from pathlib import Path

LOCATES_FILE = Path("locate_tickets.json")
ACTIVITY_FILE = Path("topaz_activity.json")
CLUSTERS_FILE = Path("topaz_clusters.json")
REGISTRY_FILE = Path("topaz_event_registry.json")

OUTPUT_FILE = Path("conduit_web_data.json")


LOCATE_FIELDS = (
    "ticket_id",
    "revision",
    "county",
    "city",
    "street",
    "cross_streets",
    "lat",
    "lon",
    "ticket_type",
    "priority",
    "created_date",
    "work_date",
    "expires_date",
    "status",
    "work_type",
    "category",
    "excavator",
    "company",
    "risk_score",
    "signal",
    "source",
)

ACTIVITY_FIELDS = (
    "ticket_id",
    "activity_type",
    "cluster_id",
    "cluster_ticket_count",
    "county",
    "city",
    "lat",
    "lon",
    "nearby_project_count",
    "nearby_strategic_land_count",
    "nearest_project_distance",
    "nearest_strategic_land_distance",
    "opportunity_score",
    "opportunity_reason",
    "project_proximity_label",
    "strategic_land_proximity_label",
)

CLUSTER_FIELDS = (
    "cluster_id",
    "county",
    "cities",
    "streets",
    "center_lat",
    "center_lon",
    "ticket_count",
    "ticket_ids",
    "unique_excavators",
    "nearby_project_count",
    "nearby_strategic_land_count",
    "nearest_project_distance",
    "nearest_strategic_land_distance",
    "opportunity_score",
    "opportunity_reason",
    "project_proximity_label",
    "strategic_land_proximity_label",
)


def load_list(path):
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise SystemExit(
            f"ERROR: {path} must contain a JSON list."
        )

    return data


def compact_record(record, fields):
    return {
        field: record[field]
        for field in fields
        if field in record
        and record[field] is not None
    }


def atomic_write(path, data):
    temp = Path(str(path) + ".tmp")

    with temp.open("w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            separators=(",", ":")
        )
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp, path)


print("CONDUIT — WEB DATA BUILDER")
print("--------------------------")

locates = load_list(LOCATES_FILE)
activity = load_list(ACTIVITY_FILE)
clusters = load_list(CLUSTERS_FILE)
registry = load_list(REGISTRY_FILE)


compact_locates = [
    compact_record(
        record,
        LOCATE_FIELDS
    )
    for record in locates
]

activity_by_ticket = {
    str(record.get("ticket_id")): record
    for record in activity
    if record.get("ticket_id") is not None
}

compact_locates = []

for record in locates:
    compact = compact_record(
        record,
        LOCATE_FIELDS
    )

    ticket_id = record.get("ticket_id")

    activity_record = activity_by_ticket.get(
        str(ticket_id)
    )

    if activity_record:
        for field in ACTIVITY_FIELDS:
            if field == "ticket_id":
                continue

            value = activity_record.get(field)

            if value is not None:
                compact[field] = value

    compact_locates.append(compact)

compact_clusters = [
    compact_record(
        record,
        CLUSTER_FIELDS
    )
    for record in clusters
]


active_registry = [
    record
    for record in registry
    if record.get("active") is not False
]


payload = {
    "metadata": {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "schema_version": "1.0",
        "active_locates": len(locates),
        "activity_records": len(activity),
        "enriched_locates": len(compact_locates),
        "clusters": len(clusters),
        "registry_records": len(registry),
        "active_registry_records": len(
            active_registry
        ),
    },
    "locates": compact_locates,
    "clusters": compact_clusters,
}


atomic_write(
    OUTPUT_FILE,
    payload
)


original_bytes = sum(
    path.stat().st_size
    for path in (
        LOCATES_FILE,
        ACTIVITY_FILE,
        CLUSTERS_FILE,
    )
)

web_bytes = OUTPUT_FILE.stat().st_size

reduction = (
    100
    * (
        1
        - web_bytes / original_bytes
    )
    if original_bytes
    else 0
)


print("Active locates:", len(compact_locates))
print("Activity merged into locates:", len(activity))
print("Clusters:", len(compact_clusters))

print()
print(
    "Original frontend datasets:",
    f"{original_bytes / 1024 / 1024:.2f} MiB"
)

print(
    "Web payload:",
    f"{web_bytes / 1024 / 1024:.2f} MiB"
)

print(
    "Size reduction:",
    f"{reduction:.1f}%"
)

print()
print(
    "Saved:",
    OUTPUT_FILE
)
