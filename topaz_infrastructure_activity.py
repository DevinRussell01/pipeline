import json
import math
from collections import defaultdict
from datetime import datetime, timezone

INPUT_FILE = "locate_tickets.json"
PROJECTS_FILE = "projects.json"
LAND_FILE = "land_intelligence.json"

OUTPUT_FILE = "topaz_activity.json"
CLUSTERS_FILE = "topaz_clusters.json"

CLUSTER_RADIUS_MILES = 0.10
MIN_CLUSTER_SIZE = 3

PROJECT_RADIUS_MILES = 1.5
LAND_RADIUS_MILES = 1.5


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


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

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return r * c


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_ticket_components(tickets):
    """
    Build compact geographic ticket groups.

    Tickets may join a candidate group only when they remain within
    CLUSTER_RADIUS_MILES of the evolving cluster centroid.

    This prevents chain-link clustering where individually adjacent
    tickets merge into a large corridor-scale blob.
    """

    unassigned = set(range(len(tickets)))
    components = []

    while unassigned:

        seed_index = min(unassigned)
        seed = tickets[seed_index]

        seed_lat = seed.get("lat")
        seed_lon = seed.get("lon")
        seed_county = seed.get("county")

        if seed_lat is None or seed_lon is None:
            components.append([seed_index])
            unassigned.remove(seed_index)
            continue

        component = [seed_index]
        unassigned.remove(seed_index)

        centroid_lat = float(seed_lat)
        centroid_lon = float(seed_lon)

        changed = True

        while changed:
            changed = False

            candidates = []

            for index in list(unassigned):

                ticket = tickets[index]

                if ticket.get("county") != seed_county:
                    continue

                lat = ticket.get("lat")
                lon = ticket.get("lon")

                if lat is None or lon is None:
                    continue

                distance = distance_miles(
                    centroid_lat,
                    centroid_lon,
                    lat,
                    lon
                )

                if (
                    distance is not None
                    and distance <= CLUSTER_RADIUS_MILES
                ):
                    candidates.append(index)

            if not candidates:
                break

            candidates.sort(
                key=lambda index: distance_miles(
                    centroid_lat,
                    centroid_lon,
                    tickets[index].get("lat"),
                    tickets[index].get("lon")
                ) or 999
            )

            for index in candidates:

                if index not in unassigned:
                    continue

                ticket = tickets[index]

                proposed = component + [index]

                proposed_lat = sum(
                    float(tickets[i].get("lat"))
                    for i in proposed
                ) / len(proposed)

                proposed_lon = sum(
                    float(tickets[i].get("lon"))
                    for i in proposed
                ) / len(proposed)

                valid = all(
                    (
                        distance_miles(
                            proposed_lat,
                            proposed_lon,
                            tickets[i].get("lat"),
                            tickets[i].get("lon")
                        )
                        or 0
                    ) <= CLUSTER_RADIUS_MILES
                    for i in proposed
                )

                if not valid:
                    continue

                component.append(index)
                unassigned.remove(index)

                centroid_lat = proposed_lat
                centroid_lon = proposed_lon

                changed = True

        components.append(component)

    return components


def proximity_strength(distance):
    """
    Convert distance into a 0-5 contextual evidence strength.

    5 = direct convergence
    4 = very strong proximity
    3 = strong proximity
    2 = contextual proximity
    1 = weak supporting context
    0 = outside intelligence radius
    """

    if distance is None:
        return 0

    if distance <= 0.10:
        return 5
    if distance <= 0.25:
        return 4
    if distance <= 0.50:
        return 3
    if distance <= 1.00:
        return 2
    if distance <= 1.50:
        return 1

    return 0


def proximity_label(distance):
    if distance is None:
        return "None"

    if distance <= 0.10:
        return "Direct"
    if distance <= 0.25:
        return "Very Strong"
    if distance <= 0.50:
        return "Strong"
    if distance <= 1.00:
        return "Contextual"
    if distance <= 1.50:
        return "Weak"

    return "None"


def summarize_context(lat, lon, county, projects, land):
    nearby_projects = []
    nearby_land = []

    # =====================================================
    # DEVELOPMENT CONTEXT
    # =====================================================

    for project in projects:
        if project.get("county") != county:
            continue

        distance = distance_miles(
            lat,
            lon,
            project.get("lat"),
            project.get("lon")
        )

        if distance is None or distance > PROJECT_RADIUS_MILES:
            continue

        nearby_projects.append({
            "case_number": project.get("case_number"),
            "address": project.get("address"),
            "description": project.get("description"),
            "distance_miles": round(distance, 3),
            "proximity_strength": proximity_strength(distance),
            "proximity_label": proximity_label(distance),
            "source_url": project.get("source_url")
        })

    # =====================================================
    # STRATEGIC LAND CONTEXT
    # =====================================================

    for parcel in land:
        if parcel.get("county") != county:
            continue

        acres = safe_float(parcel.get("acres"))
        watch_score = int(parcel.get("watch_score") or 0)

        if acres < 5:
            continue

        if watch_score < 6:
            continue

        distance = distance_miles(
            lat,
            lon,
            parcel.get("lat"),
            parcel.get("lon")
        )

        if distance is None or distance > LAND_RADIUS_MILES:
            continue

        strategic_owner = bool(
            parcel.get("strategic_owner_flag")
        )

        nearby_land.append({
            "pid": parcel.get("pid"),
            "owner": parcel.get("owner"),
            "owner_type": parcel.get("owner_type"),
            "acres": acres,
            "watch_score": watch_score,
            "llc_flag": bool(parcel.get("llc_flag")),
            "strategic_owner_flag": strategic_owner,
            "distance_miles": round(distance, 3),
            "proximity_strength": proximity_strength(distance),
            "proximity_label": proximity_label(distance)
        })

    nearby_projects.sort(
        key=lambda x: x["distance_miles"]
    )

    nearby_land.sort(
        key=lambda x: x["distance_miles"]
    )

    strategic_land = [
        parcel
        for parcel in nearby_land
        if parcel.get("strategic_owner_flag")
    ]

    literal_llc_land = [
        parcel
        for parcel in nearby_land
        if parcel.get("llc_flag")
    ]

    nearest_project_distance = (
        nearby_projects[0]["distance_miles"]
        if nearby_projects
        else None
    )

    nearest_land_distance = (
        nearby_land[0]["distance_miles"]
        if nearby_land
        else None
    )

    nearest_strategic_land_distance = (
        strategic_land[0]["distance_miles"]
        if strategic_land
        else None
    )

    project_strength = proximity_strength(
        nearest_project_distance
    )

    strategic_land_strength = proximity_strength(
        nearest_strategic_land_distance
    )

    project_direct_count = sum(
        p["distance_miles"] <= 0.25
        for p in nearby_projects
    )

    strategic_land_direct_count = sum(
        p["distance_miles"] <= 0.25
        for p in strategic_land
    )

    return {
        "nearby_projects": nearby_projects[:10],
        "nearby_land": nearby_land[:10],
        "nearby_strategic_land": strategic_land[:10],

        "nearby_project_count": len(nearby_projects),
        "nearby_land_count": len(nearby_land),
        "nearby_strategic_land_count": len(strategic_land),
        "nearby_llc_land_count": len(literal_llc_land),

        "nearest_project_distance": nearest_project_distance,
        "nearest_land_distance": nearest_land_distance,
        "nearest_strategic_land_distance": nearest_strategic_land_distance,

        "project_proximity_strength": project_strength,
        "strategic_land_proximity_strength": strategic_land_strength,

        "project_proximity_label": proximity_label(
            nearest_project_distance
        ),
        "strategic_land_proximity_label": proximity_label(
            nearest_strategic_land_distance
        ),

        "projects_within_quarter_mile": project_direct_count,
        "strategic_land_within_quarter_mile": strategic_land_direct_count
    }


def score_opportunity(activity_type, cluster_size, context):
    """
    TOPAZ Infrastructure Activity Opportunity Score: 1-10.

    Ticket urgency / Risk Score is intentionally excluded.

    Activity establishes the baseline.
    Geographic convergence with development and strategic ownership
    determines whether the signal becomes operationally important.
    """

    project_strength = int(
        context.get("project_proximity_strength") or 0
    )

    land_strength = int(
        context.get("strategic_land_proximity_strength") or 0
    )

    has_projects = project_strength > 0
    has_strategic_land = land_strength > 0

    # =====================================================
    # SINGLE TICKET
    # =====================================================

    if activity_type == "Single":

        if not has_projects and not has_strategic_land:
            return 1, (
                "Single infrastructure ticket with no supporting "
                "development or strategic land convergence"
            )

        if has_projects and has_strategic_land:
            combined = project_strength + land_strength

            if combined >= 8:
                return 7, (
                    "Single ticket with strong development and "
                    "strategic land convergence"
                )

            if combined >= 5:
                return 6, (
                    "Single ticket with development and strategic "
                    "land context"
                )

            return 4, (
                "Single ticket with weak multi-source context"
            )

        strongest = max(project_strength, land_strength)

        if strongest >= 5:
            return 6, (
                "Single ticket directly adjacent to a high-value "
                "development or strategic land signal"
            )

        if strongest >= 4:
            return 5, (
                "Single ticket with very strong supporting context"
            )

        if strongest >= 3:
            return 4, (
                "Single ticket with strong supporting context"
            )

        if strongest >= 2:
            return 3, (
                "Single ticket with contextual supporting evidence"
            )

        return 2, (
            "Single ticket with weak supporting evidence"
        )

    # =====================================================
    # CLUSTER BASELINE
    # =====================================================

    if cluster_size >= 10:
        base = 5
    elif cluster_size >= 5:
        base = 4
    else:
        base = 3

    # Cluster volume alone cannot exceed 5.
    if not has_projects and not has_strategic_land:
        return base, (
            "811 activity cluster without supporting development "
            "or strategic land convergence"
        )

    # =====================================================
    # CLUSTER + BOTH CONTEXT TYPES
    # =====================================================

    if has_projects and has_strategic_land:

        combined = project_strength + land_strength

        if (
            project_strength >= 4
            and land_strength >= 4
        ):
            return 10, (
                "Infrastructure cluster with very strong development "
                "and strategic ownership convergence"
            )

        if combined >= 6:
            return 9, (
                "Infrastructure cluster with strong development and "
                "strategic land convergence"
            )

        return 8, (
            "Infrastructure cluster supported by both development "
            "and strategic land context"
        )

    # =====================================================
    # CLUSTER + ONE STRONG CONTEXT TYPE
    # =====================================================

    strongest = max(project_strength, land_strength)

    if strongest >= 5:
        return 8, (
            "Infrastructure cluster directly adjacent to a high-value "
            "development or strategic land signal"
        )

    if strongest >= 4:
        return 7, (
            "Infrastructure cluster with very strong supporting context"
        )

    if strongest >= 3:
        return 6, (
            "Infrastructure cluster with strong supporting context"
        )

    # Weak/contextual evidence should not overpower cluster baseline.
    return min(base + 1, 6), (
        "Infrastructure cluster with limited supporting context"
    )


def main():
    tickets = load_json(INPUT_FILE)
    projects = load_json(PROJECTS_FILE)
    land = load_json(LAND_FILE)

    print("TOPAZ — INFRASTRUCTURE ACTIVITY INTELLIGENCE")
    print("------------------------------------------")
    print("Active tickets:", len(tickets))

    components = build_ticket_components(tickets)

    activity_records = []
    cluster_records = []

    cluster_number = 0

    for component in components:
        members = [tickets[i] for i in component]

        if len(members) >= MIN_CLUSTER_SIZE:
            cluster_number += 1
            activity_type = "Cluster"
            cluster_id = f"TOPAZ-IAI-{cluster_number:04d}"
        else:
            activity_type = "Single"
            cluster_id = None

        center_lat = sum(
            float(t.get("lat"))
            for t in members
        ) / len(members)

        center_lon = sum(
            float(t.get("lon"))
            for t in members
        ) / len(members)

        county = members[0].get("county")

        context = summarize_context(
            center_lat,
            center_lon,
            county,
            projects,
            land
        )

        opportunity_score, opportunity_reason = score_opportunity(
            activity_type,
            len(members),
            context
        )

        if activity_type == "Cluster":
            cluster_record = {
                "intelligence_engine": "TOPAZ",
                "intelligence_product": "Infrastructure Activity Intelligence",
                "engine_version": "1.0-beta",
                "cluster_id": cluster_id,
                "activity_type": "Cluster",
                "county": county,
                "cities": sorted(set(
                    t.get("city")
                    for t in members
                    if t.get("city")
                )),
                "streets": sorted(set(
                    t.get("street")
                    for t in members
                    if t.get("street")
                )),
                "center_lat": center_lat,
                "center_lon": center_lon,
                "ticket_count": len(members),
                "ticket_ids": [
                    t.get("ticket_id")
                    for t in members
                ],
                "unique_excavators": len(set(
                    t.get("excavator")
                    for t in members
                    if t.get("excavator")
                )),
                "max_risk_score": max(
                    int(t.get("risk_score") or 0)
                    for t in members
                ),
                "opportunity_score": opportunity_score,
                "opportunity_reason": opportunity_reason,
                **context
            }

            cluster_records.append(cluster_record)

        for ticket in members:
            record = dict(ticket)

            record["intelligence_engine"] = "TOPAZ"
            record["intelligence_product"] = "Infrastructure Activity Intelligence"
            record["engine_version"] = "1.0-beta"

            record["activity_type"] = activity_type
            record["cluster_id"] = cluster_id
            record["cluster_size"] = len(members)

            record["nearby_project_count"] = context[
                "nearby_project_count"
            ]

            record["nearby_land_count"] = context[
                "nearby_land_count"
            ]

            record["nearby_strategic_land_count"] = context[
                "nearby_strategic_land_count"
            ]

            record["nearby_llc_land_count"] = context[
                "nearby_llc_land_count"
            ]

            record["nearest_project_distance"] = context[
                "nearest_project_distance"
            ]

            record["nearest_strategic_land_distance"] = context[
                "nearest_strategic_land_distance"
            ]

            record["project_proximity_label"] = context[
                "project_proximity_label"
            ]

            record["strategic_land_proximity_label"] = context[
                "strategic_land_proximity_label"
            ]

            record["nearby_projects"] = context[
                "nearby_projects"
            ][:5]

            record["nearby_strategic_land"] = context[
                "nearby_strategic_land"
            ][:5]

            record["opportunity_score"] = opportunity_score
            record["opportunity_reason"] = opportunity_reason

            activity_records.append(record)

    activity_records.sort(
        key=lambda x: (
            -int(x.get("opportunity_score") or 0),
            x.get("county") or "",
            x.get("city") or "",
            x.get("street") or ""
        )
    )

    cluster_records.sort(
        key=lambda x: (
            -int(x.get("opportunity_score") or 0),
            -int(x.get("ticket_count") or 0)
        )
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            activity_records,
            f,
            indent=2,
            ensure_ascii=False
        )

    with open(CLUSTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            cluster_records,
            f,
            indent=2,
            ensure_ascii=False
        )

    singles = sum(
        1
        for row in activity_records
        if row["activity_type"] == "Single"
    )

    clustered_tickets = len(activity_records) - singles

    print()
    print("CLASSIFICATION COMPLETE")
    print("-----------------------")
    print("Singles:", singles)
    print("Clustered tickets:", clustered_tickets)
    print("Clusters:", len(cluster_records))
    print("Saved:", OUTPUT_FILE)
    print("Saved:", CLUSTERS_FILE)

    print()
    print("TOP CLUSTERS")
    print("------------")

    for cluster in cluster_records[:20]:
        print(
            cluster["cluster_id"],
            "|",
            cluster["county"],
            "| Tickets:",
            cluster["ticket_count"],
            "| Score:",
            cluster["opportunity_score"],
            "| Projects:",
            cluster["nearby_project_count"],
            "| Land:",
            cluster["nearby_land_count"],
            "| LLC Land:",
            cluster["nearby_llc_land_count"]
        )


if __name__ == "__main__":
    main()
