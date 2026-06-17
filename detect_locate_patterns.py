import json
from datetime import datetime

print("Summit Atlas — Locate Pattern Detector")
print("--------------------------------------")

with open("locate_correlations.json") as f:
    correlations = json.load(f)

patterns = []

for item in correlations:
    score = int(item.get("opportunity_score") or 0)
    county = item.get("county")
    street = item.get("street")
    work_type = str(item.get("work_type") or "").lower()
    nearby_land = int(item.get("nearby_land_count") or 0)
    high_watch = int(item.get("nearby_high_watch_land_count") or 0)

    pattern_type = "General Utility Activity"
    confidence = score
    opportunity = "Medium"
    reason = item.get("summary") or ""

    if high_watch >= 3 and ("fiber" in work_type or "utility" in work_type):
        pattern_type = "Development / Infrastructure Cluster"
        opportunity = "High"
        reason = "Locate signal overlaps with multiple high-watch parcels, suggesting possible site development or infrastructure preparation."

    elif "bore" in work_type or "fiber" in work_type:
        pattern_type = "Telecom Expansion Signal"
        opportunity = "High" if score >= 10 else "Medium"
        reason = "Telecom or boring activity may indicate fiber expansion, competitive entry, or new network construction."

    elif nearby_land >= 2:
        pattern_type = "Land Development Proximity Signal"
        opportunity = "High" if score >= 10 else "Medium"
        reason = "Locate signal is near multiple tracked land parcels, increasing development relevance."

    if score >= 14:
        confidence_label = "Very High"
    elif score >= 10:
        confidence_label = "High"
    elif score >= 7:
        confidence_label = "Moderate"
    else:
        confidence_label = "Low"

    patterns.append({
        "pattern_id": f"PATTERN-{county}-{len(patterns)+1:03d}",
        "county": county,
        "street": street,
        "pattern_type": pattern_type,
        "confidence_score": score,
        "confidence_label": confidence_label,
        "opportunity": opportunity,
        "nearby_land_count": nearby_land,
        "nearby_high_watch_land_count": high_watch,
        "nearby_project_count": item.get("nearby_project_count"),
        "reason": reason,
        "source_ticket": item.get("ticket_id"),
        "created_date": datetime.now().strftime("%Y-%m-%d")
    })

with open("locate_patterns.json", "w") as f:
    json.dump(patterns, f, indent=4)

print(f"Patterns detected: {len(patterns)}")
print("Saved locate_patterns.json")