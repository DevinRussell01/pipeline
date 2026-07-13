import json
import math

print("Conduit — Infrastructure Opportunity Correlator")
print("-----------------------------------------------")


SCORE_VERSION = "2.0"
PROJECT_RADIUS_MILES = 3
LAND_RADIUS_MILES = 3


def load_json(path):
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def distance_miles(lat1, lon1, lat2, lon2):
    if (
        lat1 in (None, "")
        or lon1 in (None, "")
        or lat2 in (None, "")
        or lon2 in (None, "")
    ):
        return None

    radius = 3958.8

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    arc = 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )

    return radius * arc


def project_key(project):
    """
    Prevent duplicate phases or repeated rows from inflating proximity counts.
    """

    parcel_id = str(project.get("parcel_id") or "").strip()
    description = str(project.get("description") or "").strip().upper()

    if parcel_id and description:
        return f"{parcel_id}:{description}"

    source_id = project.get("source_record_id")
    if source_id:
        return str(source_id)

    return (
        f"{project.get('case_number')}:"
        f"{project.get('lat')}:"
        f"{project.get('lon')}"
    )


def project_display_name(project):
    return (
        project.get("description")
        or project.get("zoning_change")
        or project.get("case_number")
        or "Unnamed Project"
    )


def project_units(project):
    return int(project.get("single_family_lots") or 0) + int(
        project.get("multifamily_units") or 0
    )


def score_project_cluster(projects):
    """
    Project proximity component: 0–8 points.
    """

    if not projects:
        return 0, []

    reasons = []
    count = len(projects)
    closest = min(project["distance_miles"] for project in projects)
    largest_units = max(project.get("units", 0) for project in projects)

    if count >= 10:
        score = 5
        reasons.append(f"{count} distinct projects within 3 miles")
    elif count >= 5:
        score = 4
        reasons.append(f"{count} distinct projects within 3 miles")
    elif count >= 2:
        score = 3
        reasons.append(f"{count} distinct projects within 3 miles")
    else:
        score = 2
        reasons.append("One project within 3 miles")

    if closest <= 1:
        score += 2
        reasons.append(
            f"Closest project is {closest:.2f} miles away"
        )
    elif closest <= 2:
        score += 1
        reasons.append(
            f"Closest project is {closest:.2f} miles away"
        )

    if largest_units >= 250:
        score += 1
        reasons.append(
            f"Largest nearby project contains {largest_units} units"
        )

    return min(score, 8), reasons


def score_land_cluster(parcels):
    """
    Land component: 0–7 points.
    """

    if not parcels:
        return 0, []

    reasons = []
    high_watch = [
        parcel
        for parcel in parcels
        if int(parcel.get("watch_score") or 0) >= 8
    ]

    if len(parcels) >= 5:
        score = 3
    elif len(parcels) >= 2:
        score = 2
    else:
        score = 1

    reasons.append(
        f"{len(parcels)} tracked parcel(s) within 3 miles"
    )

    if len(high_watch) >= 3:
        score += 4
        reasons.append(
            f"{len(high_watch)} nearby parcels have watch scores of 8 or 9"
        )
    elif high_watch:
        score += 2
        reasons.append(
            f"{len(high_watch)} nearby parcel(s) have high watch scores"
        )

    return min(score, 7), reasons


locates = load_json("locate_tickets.json")
projects = load_json("projects.json")
land = load_json("land_intelligence.json")

correlations = []

for locate in locates:
    locate_lat = locate.get("lat")
    locate_lon = locate.get("lon")
    locate_county = locate.get("county")

    nearby_project_map = {}
    nearby_land = []

    for project in projects:
        if project.get("county") != locate_county:
            continue

        distance = distance_miles(
            locate_lat,
            locate_lon,
            project.get("lat"),
            project.get("lon"),
        )

        if distance is None or distance > PROJECT_RADIUS_MILES:
            continue

        key = project_key(project)

        candidate = {
            "name": project_display_name(project),
            "case_number": project.get("case_number") or "",
            "county": project.get("county"),
            "distance_miles": round(distance, 2),
            "status": project.get("status") or "",
            "address": project.get("address") or "",
            "coordinates": project.get("coordinates") or "",
            "units": project_units(project),
            "priority_score": project.get("priority_score"),
            "intelligence_type": project.get("intelligence_type"),
            "source_url": project.get("source_url") or "",
        }

        existing = nearby_project_map.get(key)

        if (
            existing is None
            or candidate["distance_miles"]
            < existing["distance_miles"]
        ):
            nearby_project_map[key] = candidate

    nearby_projects = sorted(
        nearby_project_map.values(),
        key=lambda item: item["distance_miles"],
    )

    for parcel in land:
        if parcel.get("county") != locate_county:
            continue

        distance = distance_miles(
            locate_lat,
            locate_lon,
            parcel.get("lat"),
            parcel.get("lon"),
        )

        if distance is None or distance > LAND_RADIUS_MILES:
            continue

        nearby_land.append({
            "owner": parcel.get("owner") or "Unknown",
            "acres": parcel.get("acres"),
            "watch_score": parcel.get("watch_score"),
            "distance_miles": round(distance, 2),
            "pid": parcel.get("pid"),
            "coordinates": (
                f"{float(parcel.get('lat')):.8f}, "
                f"{float(parcel.get('lon')):.8f}"
            ),
        })

    nearby_land.sort(
        key=lambda item: item["distance_miles"]
    )

    source_score = int(locate.get("risk_score") or 0)

    project_score, project_reasons = score_project_cluster(
        nearby_projects
    )

    land_score, land_reasons = score_land_cluster(
        nearby_land
    )

    high_watch_land = [
        parcel
        for parcel in nearby_land
        if int(parcel.get("watch_score") or 0) >= 8
    ]

    opportunity_score = (
        source_score
        + project_score
        + land_score
    )

    explanation = [
        f"Source signal contributes {source_score} point(s)",
        *project_reasons,
        *land_reasons,
    ]

    correlations.append({
        "ticket_id": locate.get("ticket_id"),
        "county": locate.get("county"),
        "city": locate.get("city"),
        "street": locate.get("street"),
        "lat": locate_lat,
        "lon": locate_lon,
        "coordinates": (
            f"{float(locate_lat):.8f}, "
            f"{float(locate_lon):.8f}"
            if locate_lat is not None and locate_lon is not None
            else ""
        ),
        "work_type": locate.get("work_type"),
        "category": locate.get("category"),
        "risk_score": locate.get("risk_score"),
        "opportunity_score": opportunity_score,
        "score_version": SCORE_VERSION,
        "score_components": {
            "source_signal": source_score,
            "project_proximity": project_score,
            "land_concentration": land_score,
        },
        "score_explanation": explanation,
        "nearby_project_count": len(nearby_projects),
        "nearby_land_count": len(nearby_land),
        "nearby_high_watch_land_count": len(high_watch_land),
        "nearby_projects": nearby_projects[:10],
        "nearby_land": nearby_land[:10],
        "signal": locate.get("signal"),
        "summary": (
            f"{locate_county} signal near "
            f"{len(nearby_projects)} distinct project(s) and "
            f"{len(nearby_land)} tracked parcel(s)."
        ),
    })


with open(
    "locate_correlations.json",
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        correlations,
        file,
        indent=4,
        ensure_ascii=False,
    )


print(f"Infrastructure signals analyzed: {len(locates)}")
print(f"Correlations saved: {len(correlations)}")
print(f"Score version: {SCORE_VERSION}")
print("Saved locate_correlations.json")