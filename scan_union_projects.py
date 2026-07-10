import json
from datetime import datetime
from pathlib import Path

from adapters.union_legistar import scan_union_legistar


OUTPUT_FILE = Path("projects.json")
TODAY = datetime.now().strftime("%Y-%m-%d")

print("Conduit — Union County Legistar Adapter")
print("---------------------------------------")


def load_existing_projects():
    if not OUTPUT_FILE.exists():
        return []

    with OUTPUT_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize(value):
    return str(value or "").strip().upper()


def is_managed_union_record(record):
    """
    Identifies Union records controlled by this Legistar adapter.

    This includes:
    - current normalized Legistar records
    - older hardcoded Union records that pointed to Legistar
    """

    if record.get("county") != "Union":
        return False

    source_system = record.get("source_system") or ""
    source_url = record.get("source_url") or ""

    return (
        source_system == "Union County Legistar"
        or "unioncountync.legistar.com" in source_url.lower()
    )


def record_key(record):
    """
    Use a planning case number when available so the same rezoning
    appearing before multiple boards becomes one project.

    For records without a formal CZ, RZ, or SUP case, use the
    Legistar source record ID.
    """

    case_number = normalize(record.get("case_number"))

    if case_number.startswith(("CZ-", "RZ-", "SUP-")):
        return f"CASE:{case_number}"

    source_record_id = normalize(record.get("source_record_id"))

    if source_record_id:
        return f"SOURCE:{source_record_id}"

    matter_id = normalize(record.get("matter_id"))

    if matter_id:
        return f"MATTER:{matter_id}"

    return (
        f"FALLBACK:{normalize(record.get('county'))}:"
        f"{case_number}:"
        f"{normalize(record.get('zoning_change'))}"
    )


def meaningful_snapshot(record):
    """
    Fields used to decide whether an existing project materially changed.
    """

    fields = [
        "case_number",
        "zoning_change",
        "description",
        "status",
        "meeting_date",
        "meeting_body",
        "source_url",
        "matter_file",
        "intelligence_type",
        "priority_score",
    ]

    return {
        field: record.get(field)
        for field in fields
    }


existing_projects = load_existing_projects()

try:
    fetched_records = scan_union_legistar()
except Exception as error:
    print(f"Union Legistar scan failed: {error}")
    raise


# Events are returned newest first. Keep the first occurrence of each
# normalized project so an older meeting does not overwrite a newer one.
deduplicated_live = {}

for record in fetched_records:
    key = record_key(record)

    if key not in deduplicated_live:
        deduplicated_live[key] = record

live_records = list(deduplicated_live.values())


# Separate records managed by this adapter from the rest of projects.json.
existing_managed = [
    record
    for record in existing_projects
    if is_managed_union_record(record)
]

preserved_projects = [
    record
    for record in existing_projects
    if not is_managed_union_record(record)
]


existing_by_key = {}

for record in existing_managed:
    existing_by_key[record_key(record)] = record


refreshed_union = []

added = 0
updated = 0
unchanged = 0

for record in live_records:
    key = record_key(record)
    existing = existing_by_key.get(key)

    if existing is None:
        normalized_record = {
            **record,
            "first_seen": TODAY,
            "last_seen": TODAY,
            "last_scanned": TODAY,
            "record_status": "Active",
        }

        refreshed_union.append(normalized_record)
        added += 1
        continue

    first_seen = (
        existing.get("first_seen")
        or existing.get("last_scanned")
        or TODAY
    )

    merged = {
        **existing,
        **record,
        "first_seen": first_seen,
        "last_seen": TODAY,
        "last_scanned": TODAY,
        "record_status": "Active",
    }

    if meaningful_snapshot(existing) != meaningful_snapshot(merged):
        updated += 1
    else:
        unchanged += 1

    refreshed_union.append(merged)


live_keys = {
    record_key(record)
    for record in live_records
}

retired_records = [
    record
    for record in existing_managed
    if record_key(record) not in live_keys
]

retired = len(retired_records)


# Managed Union records are rebuilt from the current qualified API results.
# All unrelated county/project records remain untouched.
final_projects = preserved_projects + refreshed_union


with OUTPUT_FILE.open("w", encoding="utf-8") as file:
    json.dump(
        final_projects,
        file,
        indent=2,
        ensure_ascii=False,
    )


print(f"Legistar matters fetched and matched: {len(fetched_records)}")
print(f"Normalized live Union projects: {len(live_records)}")
print(f"New Union projects added: {added}")
print(f"Existing Union projects updated: {updated}")
print(f"Existing Union projects unchanged: {unchanged}")
print(f"Stale or filtered Union records retired: {retired}")
print(f"Total project records: {len(final_projects)}")
print("Union Legistar scan complete.")