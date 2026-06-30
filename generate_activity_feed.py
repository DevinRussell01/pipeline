import json
from datetime import datetime

def load_json(filename, fallback):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return fallback

now = datetime.now().strftime("%H:%M")

projects = load_json("projects.json", [])
land = load_json("land_intelligence.json", [])
builders = load_json("builder_portfolios.json", [])
patterns = load_json("locate_patterns.json", [])
correlations = load_json("locate_correlations.json", [])
brunswick_gis = load_json("brunswick_gis.json", [])
brief = load_json("executive_brief.json", {})

top_county = "Regional"
try:
    counties = brief.get("counties_to_watch", [])
    if counties:
        top_county = counties[0].split("—")[0].split("-")[0].strip()
except Exception:
    pass

feed = [
    {
        "time": now,
        "type": "AI",
        "message": "Executive intelligence brief generated"
    },
    {
        "time": now,
        "type": "Projects",
        "message": f"{len(projects)} development project records indexed"
    },
    {
        "time": now,
        "type": "Land",
        "message": f"{len(land)} land intelligence parcels evaluated"
    },
    {
        "time": now,
        "type": "Builders",
        "message": f"{len(builders)} builder communities monitored"
    },
    {
        "time": now,
        "type": "Signals",
        "message": f"{len(patterns)} infrastructure patterns detected"
    },
    {
        "time": now,
        "type": "GIS",
        "message": f"{len(brunswick_gis)} Brunswick GIS parcels refreshed"
    },
    {
        "time": now,
        "type": "Opportunity",
        "message": f"{len(correlations)} locate correlations analyzed"
    },
    {
        "time": now,
        "type": "Watch",
        "message": f"{top_county} flagged as a county to watch"
    }
]

with open("activity_feed.json", "w", encoding="utf-8") as file:
    json.dump(feed, file, indent=2)

print("Activity feed generated.")
print("Saved: activity_feed.json")