import json
import os
import math
from datetime import datetime, timezone

ACTIVITY_FILE = "topaz_activity.json"
CLUSTERS_FILE = "topaz_clusters.json"
REGISTRY_FILE = "topaz_event_registry.json"

REGISTRY_VERSION = "1.0"


def load_json(path, default=None):
    if default is None:
        default = []

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def atomic_write_json(path, data):
    temp_path = f"{path}.tmp"

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_path, path)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def build_current_events(activity, clusters):
    events = []

    for cluster in clusters:
        ticket_ids = sorted(
            str(ticket_id)
            for ticket_id in cluster.get("ticket_ids", [])
            if ticket_id
        )

        events.append({
            "current_reference_id": cluster.get("cluster_id"),
            "event_type": "Cluster",
            "county": cluster.get("county"),
            "center_lat": cluster.get("center_lat"),
            "center_lon": cluster.get("center_lon"),
            "ticket_ids": ticket_ids,
            "ticket_count": len(ticket_ids),
            "opportunity_score": int(
                cluster.get("opportunity_score") or 0
            ),
            "nearby_project_count": int(
                cluster.get("nearby_project_count") or 0
            ),
            "nearby_strategic_land_count": int(
                cluster.get("nearby_strategic_land_count") or 0
            )
        })

    for row in activity:
        if row.get("activity_type") != "Single":
            continue

        ticket_id = str(row.get("ticket_id") or "")

        if not ticket_id:
            continue

        events.append({
            "current_reference_id": f"SINGLE:{ticket_id}",
            "event_type": "Single",
            "county": row.get("county"),
            "center_lat": row.get("lat"),
            "center_lon": row.get("lon"),
            "ticket_ids": [ticket_id],
            "ticket_count": 1,
            "opportunity_score": int(
                row.get("opportunity_score") or 0
            ),
            "nearby_project_count": int(
                row.get("nearby_project_count") or 0
            ),
            "nearby_strategic_land_count": int(
                row.get("nearby_strategic_land_count") or 0
            )
        })

    return events


def next_event_number(registry):
    highest = 0

    for event in registry:
        event_key = str(event.get("event_key") or "")

        if not event_key.startswith("TOPAZ-EVT-"):
            continue

        try:
            highest = max(
                highest,
                int(event_key.split("-")[-1])
            )
        except ValueError:
            continue

    return highest + 1


def distance_miles(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None

    r = 3958.8

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * r * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )


def match_by_exact_location(current_event, registry, claimed_keys):
    """
    Conservative fallback for complete ticket turnover.

    Events may inherit an existing identity only when they are in the
    same county and their centers are within 0.01 miles (~53 feet).
    """

    candidates = []

    for historical in registry:
        event_key = historical.get("event_key")

        if not event_key or event_key in claimed_keys:
            continue

        if historical.get("county") != current_event.get("county"):
            continue

        distance = distance_miles(
            current_event.get("center_lat"),
            current_event.get("center_lon"),
            historical.get("center_lat"),
            historical.get("center_lon")
        )

        if distance is None or distance > 0.01:
            continue

        candidates.append((
            distance,
            event_key,
            historical
        ))

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1]
        )
    )

    return candidates[0][2]


def match_by_ticket_overlap(current_event, registry, claimed_keys):
    current_ids = set(current_event["ticket_ids"])

    if not current_ids:
        return None

    candidates = []

    for historical in registry:
        event_key = historical.get("event_key")

        if not event_key or event_key in claimed_keys:
            continue

        if historical.get("county") != current_event.get("county"):
            continue

        historical_ids = set(
            str(ticket_id)
            for ticket_id in historical.get("ticket_ids", [])
            if ticket_id
        )

        shared = current_ids & historical_ids

        if not shared:
            continue

        union = current_ids | historical_ids
        overlap_ratio = (
            len(shared) / len(union)
            if union
            else 0
        )

        candidates.append((
            len(shared),
            overlap_ratio,
            event_key,
            historical
        ))

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            item[2]
        )
    )

    return candidates[0][3]


def main():
    activity = load_json(ACTIVITY_FILE)
    clusters = load_json(CLUSTERS_FILE)

    if not activity or not clusters:
        raise SystemExit(
            "ERROR: TOPAZ source datasets are empty. "
            "Registry was not modified."
        )

    current_events = build_current_events(
        activity,
        clusters
    )

    if not current_events:
        raise SystemExit(
            "ERROR: No current TOPAZ Intelligence Events. "
            "Registry was not modified."
        )

    registry = load_json(REGISTRY_FILE, [])

    if not isinstance(registry, list):
        raise SystemExit(
            "ERROR: Existing TOPAZ registry is not a list."
        )

    now = utc_now()
    claimed_keys = set()
    next_number = next_event_number(registry)

    updated_registry = []
    matched_count = 0
    new_count = 0

    for current in current_events:
        historical = match_by_ticket_overlap(
            current,
            registry,
            claimed_keys
        )

        if not historical:
            historical = match_by_exact_location(
                current,
                registry,
                claimed_keys
            )

        if historical:
            record = dict(historical)
            event_key = record["event_key"]

            matched_count += 1
        else:
            event_key = f"TOPAZ-EVT-{next_number:06d}"
            next_number += 1

            record = {
                "event_key": event_key,
                "first_seen": now,
                "review_state": "Unreviewed"
            }

            new_count += 1

        claimed_keys.add(event_key)

        previous_reference = record.get(
            "current_reference_id"
        )
        previous_type = record.get("event_type")
        previous_score = record.get(
            "opportunity_score"
        )
        previous_ticket_count = record.get(
            "ticket_count"
        )

        record.update(current)

        record["event_key"] = event_key
        record["last_seen"] = now
        record["active"] = True
        record["registry_version"] = REGISTRY_VERSION

        record["changed_since_previous"] = any([
            previous_reference is not None
            and previous_reference
            != current["current_reference_id"],

            previous_type is not None
            and previous_type
            != current["event_type"],

            previous_score is not None
            and previous_score
            != current["opportunity_score"],

            previous_ticket_count is not None
            and previous_ticket_count
            != current["ticket_count"]
        ])

        updated_registry.append(record)

    current_keys = {
        record["event_key"]
        for record in updated_registry
    }

    inactive_count = 0

    for historical in registry:
        event_key = historical.get("event_key")

        if not event_key:
            continue

        if event_key in current_keys:
            continue

        record = dict(historical)
        record["active"] = False
        record["registry_version"] = REGISTRY_VERSION

        updated_registry.append(record)
        inactive_count += 1

    updated_registry.sort(
        key=lambda row: row.get("event_key") or ""
    )

    atomic_write_json(
        REGISTRY_FILE,
        updated_registry
    )

    print("TOPAZ EVENT REGISTRY")
    print("--------------------")
    print("Current Intelligence Events:", len(current_events))
    print("Matched existing events:", matched_count)
    print("New persistent events:", new_count)
    print("Inactive retained events:", inactive_count)
    print("Registry records:", len(updated_registry))
    print("Saved:", REGISTRY_FILE)


if __name__ == "__main__":
    main()
