import json
from datetime import datetime
from pathlib import Path

from adapters.mecklenburg_arcgis import scan_mecklenburg_arcgis


PROJECTS_FILE = Path("projects.json")
ARCHIVE_FILE = Path("mecklenburg_projects_archive.json")

TODAY = datetime.now().strftime("%Y-%m-%d")
ACTIVE_CUTOFF = "2024-01-01"

print("Conduit — Mecklenburg ArcGIS Adapter")
print("------------------------------------")


def load_json(path, fallback):
    if not path.exists():
        return fallback

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def is_managed_mecklenburg_record(record):
    if record.get("county") != "Mecklenburg":
        return False

    source_system = record.get("source_system") or ""
    source_url = record.get("source_url") or ""

    return (
        source_system == "Charlotte-Mecklenburg ArcGIS"
        or "gis.charlottenc.gov" in source_url.lower()
        or "aca3.accela.com/charlotte" in source_url.lower()
        or "aca-prod.accela.com/charlotte" in source_url.lower()
    )


def record_key(record):
    source_id = record.get("source_record_id")

    if source_id:
        return f"SOURCE:{source_id}"

    global_id = record.get("global_id")

    if global_id:
        return f"GLOBAL:{global_id}"

    object_id = record.get("object_id")

    if object_id not in (None, ""):
        return f"OBJECT:{object_id}"

    case_number = str(
        record.get("case_number") or ""
    ).strip().upper()

    address = str(
        record.get("address") or ""
    ).strip().upper()

    return f"FALLBACK:{case_number}:{address}"


def is_operational_project(record):
    status = record.get("status") or "Unknown"
    latest_activity = record.get("latest_activity_date") or ""

    excluded_statuses = {
        "Closed",
        "Withdrawn",
        "Replaced",
    }

    if status in excluded_statuses:
        return False

    if latest_activity >= ACTIVE_CUTOFF:
        return True

    return False


def meaningful_snapshot(record):
    fields = [
        "lat",
        "lon",
        "coordinates",
        "coordinate_source",
        "coordinate_confidence",
        "case_number",
        "address",
        "acreage",
        "applicant",
        "zoning_change",
        "status",
        "parcel_id",
        "plan_type",
        "zoning",
        "single_family_lots",
        "multifamily_units",
        "submission_date",
        "status_date",
        "source_updated_at",
        "latest_activity_date",
        "intelligence_type",
        "priority_score",
    ]

    return {
        field: record.get(field)
        for field in fields
    }


existing_projects = load_json(PROJECTS_FILE, [])
existing_archive = load_json(ARCHIVE_FILE, [])

try:
    live_records = scan_mecklenburg_arcgis()
except Exception as error:
    print(f"Mecklenburg ArcGIS scan failed: {error}")
    raise


existing_archive_by_key = {
    record_key(record): record
    for record in existing_archive
}

refreshed_archive = []

added = 0
updated = 0
unchanged = 0

for record in live_records:
    key = record_key(record)
    existing = existing_archive_by_key.get(key)

    if existing is None:
        merged = {
            **record,
            "first_seen": TODAY,
            "last_seen": TODAY,
            "last_scanned": TODAY,
            "record_status": "Active",
        }

        added += 1

    else:
        merged = {
            **existing,
            **record,
            "first_seen": (
                existing.get("first_seen")
                or existing.get("last_scanned")
                or TODAY
            ),
            "last_seen": TODAY,
            "last_scanned": TODAY,
            "record_status": "Active",
        }

        if meaningful_snapshot(existing) != meaningful_snapshot(merged):
            updated += 1
        else:
            unchanged += 1

    refreshed_archive.append(merged)


live_keys = {
    record_key(record)
    for record in live_records
}

retired = sum(
    1
    for record in existing_archive
    if record_key(record) not in live_keys
)


active_mecklenburg = [
    record
    for record in refreshed_archive
    if is_operational_project(record)
]


preserved_projects = [
    record
    for record in existing_projects
    if not is_managed_mecklenburg_record(record)
]

final_projects = preserved_projects + active_mecklenburg


with ARCHIVE_FILE.open("w", encoding="utf-8") as file:
    json.dump(
        refreshed_archive,
        file,
        indent=2,
        ensure_ascii=False,
    )


with PROJECTS_FILE.open("w", encoding="utf-8") as file:
    json.dump(
        final_projects,
        file,
        indent=2,
        ensure_ascii=False,
    )


print(f"Complete Mecklenburg archive: {len(refreshed_archive)}")
print(f"Operational Mecklenburg projects: {len(active_mecklenburg)}")
print(f"New archive records added: {added}")
print(f"Existing archive records updated: {updated}")
print(f"Existing archive records unchanged: {unchanged}")
print(f"Stale archive records retired: {retired}")
print(f"Total operational project records: {len(final_projects)}")
print("Mecklenburg ArcGIS scan complete.")