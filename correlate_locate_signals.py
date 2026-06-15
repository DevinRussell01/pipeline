import json
import math

print("Summit Atlas — Locate Signal Correlator")
print("--------------------------------------")


def load_json(path):
    try:
        with open(path) as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def distance_miles(lat1, lon1, lat2, lon2):
    if not lat1 or not lon1 or not lat2 or not lon2:
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
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return r * c


locates = load_json("locate_tickets.json")
projects = load_json("projects.json")
land = load_json("land_intelligence.json")

correlations = []

for locate in locates:
    locate_lat = locate.get("lat")
    locate_lon = locate.get("lon")
    locate_county = locate.get("county")

    nearby_projects = []
    nearby_land = []

    for project in projects:
        if project.get("county") != locate_county:
            continue

        dist = distance_miles(
            locate_lat,
            locate_lon,
            project.get("lat"),
            project.get("lon")
        )

        if dist is not None and dist <= 3:
            nearby_projects.append({
                "name": project.get("project_name") or project.get("name") or project.get("case_number") or "Unnamed Project",
                "county": project.get("county"),
                "distance_miles": round(dist, 2),
                "status": project.get("status") or project.get("project_status") or "",
                "address": project.get("address") or ""
            })

    for parcel in land:
        if parcel.get("county") != locate_county:
            continue

        dist = distance_miles(
            locate_lat,
            locate_lon,
            parcel.get("lat"),
            parcel.get("lon")
        )

        if dist is not None and dist <= 3:
            nearby_land.append({
                "owner": parcel.get("owner") or "Unknown",
                "acres": parcel.get("acres"),
                "watch_score": parcel.get("watch_score"),
                "distance_miles": round(dist, 2),
                "pid": parcel.get("pid")
            })

    opportunity_score = int(locate.get("risk_score") or 0)

    if nearby_projects:
        opportunity_score += 4

    if nearby_land:
        opportunity_score += 3

    high_watch_land = [
        parcel for parcel in nearby_land
        if int(parcel.get("watch_score") or 0) >= 8
    ]

    if high_watch_land:
        opportunity_score += 3

    correlations.append({
        "ticket_id": locate.get("ticket_id"),
        "county": locate.get("county"),
        "city": locate.get("city"),
        "street": locate.get("street"),
        "work_type": locate.get("work_type"),
        "category": locate.get("category"),
        "risk_score": locate.get("risk_score"),
        "opportunity_score": opportunity_score,
        "nearby_project_count": len(nearby_projects),
        "nearby_land_count": len(nearby_land),
        "nearby_high_watch_land_count": len(high_watch_land),
        "nearby_projects": nearby_projects[:5],
        "nearby_land": nearby_land[:5],
        "signal": locate.get("signal"),
        "summary": (
            f"{locate.get('county')} locate signal near "
            f"{len(nearby_projects)} project(s) and "
            f"{len(nearby_land)} tracked parcel(s)."
        )
    })

with open("locate_correlations.json", "w") as file:
    json.dump(correlations, file, indent=4)

print(f"Locate signals analyzed: {len(locates)}")
print(f"Correlations saved: {len(correlations)}")
print("Saved locate_correlations.json")