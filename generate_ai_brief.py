import json
import os
from datetime import datetime
from openai import OpenAI

OUTPUT_FILE = "executive_brief.json"

def load_json(filename, fallback):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return fallback

def top_items(items, key, limit=10):
    return sorted(
        items,
        key=lambda x: float(x.get(key) or 0),
        reverse=True
    )[:limit]

projects = load_json("projects.json", [])
land = load_json("land_intelligence.json", [])
builders = load_json("builder_portfolios.json", [])
patterns = load_json("locate_patterns.json", [])
correlations = load_json("locate_correlations.json", [])
brunswick_gis = load_json("brunswick_gis.json", [])

counties = sorted(set(
    [p.get("county") for p in projects if p.get("county")] +
    [p.get("county") for p in land if p.get("county")] +
    [p.get("county") for p in brunswick_gis if p.get("county")]
))

intelligence_package = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "counts": {
        "projects": len(projects),
        "land_parcels": len(land),
        "builder_communities": len(builders),
        "locate_patterns": len(patterns),
        "locate_correlations": len(correlations),
        "brunswick_gis_parcels": len(brunswick_gis),
        "counties": counties
    },
    "highest_watch_score_parcels": top_items(land, "watch_score", 8),
    "highest_opportunity_correlations": top_items(correlations, "opportunity_score", 6),
    "locate_patterns": patterns[:8],
    "recent_projects": projects[-12:],
    "builder_samples": builders[:10]
}

prompt = f"""
You are Conduit AI, an executive land development, GIS, builder, and telecom infrastructure intelligence analyst.

Use the structured Conduit intelligence package below to produce a concise executive briefing.

Do not invent facts. If evidence is limited, say so carefully.

Return valid JSON only with exactly these keys:
summary
key_findings
top_opportunities
telecom_insights
counties_to_watch
recommended_actions

Rules:
- summary must be one polished executive paragraph.
- each list must contain 3 to 5 concise strings.
- focus on actionable intelligence.
- mention counties, GIS, builder activity, locate patterns, and land/watchlist signals when supported by the data.

CONDUIT INTELLIGENCE PACKAGE:
{json.dumps(intelligence_package, indent=2)}
"""

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

try:
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    content = response.output_text.strip()

    try:
        brief = json.loads(content)
    except Exception:
        brief = {
            "summary": content,
            "key_findings": [],
            "top_opportunities": [],
            "telecom_insights": [],
            "counties_to_watch": [],
            "recommended_actions": []
        }

except Exception as error:
    brief = {
        "summary": "AI executive brief could not be generated during this scan.",
        "key_findings": [str(error)],
        "top_opportunities": [],
        "telecom_insights": [],
        "counties_to_watch": [],
        "recommended_actions": []
    }

brief["generated_at"] = intelligence_package["generated_at"]
brief["source_counts"] = intelligence_package["counts"]

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(brief, file, indent=2)

print("Executive AI brief generated.")
print("Saved:", OUTPUT_FILE)