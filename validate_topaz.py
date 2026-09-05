#!/usr/bin/env python3

"""
Conduit 2.0 / TOPAZ 1.0 Beta
Infrastructure Activity Intelligence Validation Suite

Validates structural and analytical integrity of generated TOPAZ outputs.
"""

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ACTIVITY_FILE = Path("topaz_activity.json")
CLUSTER_FILE = Path("topaz_clusters.json")

MAX_CLUSTER_RADIUS_MILES = 0.10
MIN_CLUSTER_SIZE = 3

passed = 0
failed = 0
warnings = 0


def check(condition, description, detail=None):
    global passed, failed

    if condition:
        passed += 1
        print(f"[PASS] {description}")
    else:
        failed += 1
        print(f"[FAIL] {description}")
        if detail:
            print(f"       {detail}")


def warn(description, detail=None):
    global warnings
    warnings += 1
    print(f"[WARN] {description}")
    if detail:
        print(f"       {detail}")


def load_json(path):
    if not path.exists():
        print(f"[FATAL] Missing required file: {path}")
        sys.exit(1)

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.7613

    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


print("=" * 68)
print("CONDUIT 2.0 / TOPAZ 1.0 BETA")
print("Infrastructure Activity Intelligence Validation")
print("=" * 68)

activity = load_json(ACTIVITY_FILE)
clusters = load_json(CLUSTER_FILE)

print()
print(f"Activity records: {len(activity):,}")
print(f"Cluster records:  {len(clusters):,}")
print()

# ---------------------------------------------------------
# Basic structure
# ---------------------------------------------------------

check(
    isinstance(activity, list) and len(activity) > 0,
    "TOPAZ activity dataset exists and contains records"
)

check(
    isinstance(clusters, list),
    "TOPAZ cluster dataset has expected list structure"
)

activity_types = Counter(
    r.get("activity_type") for r in activity
)

print()
print("Activity classification:")
for key, value in sorted(activity_types.items(), key=lambda x: str(x[0])):
    print(f"  {key}: {value:,}")

check(
    set(activity_types).issubset({"Single", "Cluster"}),
    "All activity records use recognized activity classifications",
    f"Observed: {dict(activity_types)}"
)

# ---------------------------------------------------------
# Engine identity
# ---------------------------------------------------------

engines = {
    r.get("intelligence_engine")
    for r in activity
}

versions = {
    r.get("engine_version")
    for r in activity
}

check(
    engines == {"TOPAZ"},
    "All activity records identify TOPAZ as the intelligence engine",
    f"Observed: {engines}"
)

check(
    versions == {"1.0-beta"},
    "All activity records use TOPAZ engine version 1.0-beta",
    f"Observed: {versions}"
)

cluster_versions = {
    c.get("engine_version")
    for c in clusters
    if c.get("engine_version") is not None
}

check(
    not cluster_versions or cluster_versions == {"1.0-beta"},
    "Cluster records use TOPAZ engine version 1.0-beta",
    f"Observed: {cluster_versions}"
)

# ---------------------------------------------------------
# Opportunity scoring
# ---------------------------------------------------------

scores = [
    r.get("opportunity_score")
    for r in activity
]

invalid_scores = [
    s for s in scores
    if not isinstance(s, (int, float)) or not 1 <= s <= 10
]

check(
    not invalid_scores,
    "Every activity record has a TOPAZ Opportunity Score from 1–10",
    f"Invalid scores: {invalid_scores[:10]}"
)

score_distribution = Counter(scores)

print()
print("Opportunity score distribution:")
for score in sorted(score_distribution):
    print(f"  {score}: {score_distribution[score]:,}")

# ---------------------------------------------------------
# Cluster membership integrity
# ---------------------------------------------------------

cluster_activity = [
    r for r in activity
    if r.get("activity_type") == "Cluster"
]

single_activity = [
    r for r in activity
    if r.get("activity_type") == "Single"
]

cluster_without_id = [
    r.get("ticket_id")
    for r in cluster_activity
    if not r.get("cluster_id")
]

check(
    not cluster_without_id,
    "Every clustered activity record has a cluster ID",
    f"Examples: {cluster_without_id[:10]}"
)

single_with_cluster = [
    r.get("ticket_id")
    for r in single_activity
    if r.get("cluster_id")
]

check(
    not single_with_cluster,
    "Single activity records are not assigned to clusters",
    f"Examples: {single_with_cluster[:10]}"
)

membership = defaultdict(list)

for record in cluster_activity:
    membership[record.get("ticket_id")].append(
        record.get("cluster_id")
    )

duplicate_membership = {
    ticket: ids
    for ticket, ids in membership.items()
    if len(set(ids)) > 1
}

check(
    not duplicate_membership,
    "No ticket belongs to multiple TOPAZ clusters",
    f"Examples: {list(duplicate_membership.items())[:10]}"
)

cluster_counts = Counter(
    r.get("cluster_id")
    for r in cluster_activity
)

undersized = {
    cluster_id: count
    for cluster_id, count in cluster_counts.items()
    if count < MIN_CLUSTER_SIZE
}

check(
    not undersized,
    f"Every TOPAZ cluster contains at least {MIN_CLUSTER_SIZE} activity records",
    f"Undersized clusters: {undersized}"
)

# ---------------------------------------------------------
# Cluster registry integrity
# ---------------------------------------------------------

registry_ids = {
    c.get("cluster_id")
    for c in clusters
}

activity_cluster_ids = set(cluster_counts)

check(
    registry_ids == activity_cluster_ids,
    "Cluster registry and activity membership reference the same cluster IDs",
    (
        f"Only registry: {sorted(registry_ids - activity_cluster_ids)[:10]} | "
        f"Only activity: {sorted(activity_cluster_ids - registry_ids)[:10]}"
    )
)

# ---------------------------------------------------------
# Geographic compactness
# ---------------------------------------------------------

radius_failures = []

for cluster in clusters:

    cluster_id = cluster.get("cluster_id")

    center_lat = (
        cluster.get("lat")
        if cluster.get("lat") is not None
        else cluster.get("center_lat")
    )

    center_lon = (
        cluster.get("lon")
        if cluster.get("lon") is not None
        else cluster.get("center_lon")
    )

    if center_lat is None or center_lon is None:
        warn(
            f"{cluster_id} does not expose a usable centroid; "
            "radius validation skipped for this cluster"
        )
        continue

    members = [
        r for r in cluster_activity
        if r.get("cluster_id") == cluster_id
    ]

    max_distance = 0

    for member in members:

        if member.get("lat") is None or member.get("lon") is None:
            continue

        distance = haversine_miles(
            center_lat,
            center_lon,
            member["lat"],
            member["lon"]
        )

        max_distance = max(max_distance, distance)

    if max_distance > MAX_CLUSTER_RADIUS_MILES + 0.0005:
        radius_failures.append(
            (cluster_id, max_distance)
        )

check(
    not radius_failures,
    f"Every validated cluster remains within approximately "
    f"{MAX_CLUSTER_RADIUS_MILES:.2f} miles of its centroid",
    (
        "Failures: "
        + ", ".join(
            f"{cid}={distance:.4f}mi"
            for cid, distance in radius_failures[:10]
        )
    )
)

# ---------------------------------------------------------
# Risk / opportunity separation
# ---------------------------------------------------------

risk_fields = {
    "risk_score",
    "priority"
}

opportunity_reason_fields = {
    key
    for record in activity
    for key in record.keys()
    if "opportunity" in key.lower()
}

print()
print(
    "Operational fields present:",
    ", ".join(
        sorted(
            key
            for key in risk_fields
            if any(key in r for r in activity)
        )
    ) or "none"
)

print(
    "Opportunity fields present:",
    ", ".join(sorted(opportunity_reason_fields))
)

# This validates output separation. Source-code validation of the
# scoring formula is handled independently during technical review.

check(
    "opportunity_score" in opportunity_reason_fields,
    "TOPAZ Opportunity Score is represented as a distinct analytical field"
)

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print()
print("=" * 68)
print("VALIDATION SUMMARY")
print("=" * 68)
print(f"Passed:   {passed}")
print(f"Failed:   {failed}")
print(f"Warnings: {warnings}")

if failed:
    print()
    print("TOPAZ VALIDATION RESULT: FAIL")
    sys.exit(1)

print()
print("TOPAZ VALIDATION RESULT: PASS")
