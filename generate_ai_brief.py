import json
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

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
locate_tickets = load_json("locate_tickets.json", [])
topaz_activity = load_json("topaz_activity.json", [])
topaz_clusters = load_json("topaz_clusters.json", [])
brunswick_gis = load_json("brunswick_gis.json", [])

topaz_singles = [
    item for item in topaz_activity
    if item.get("activity_type") == "Single"
]

topaz_events = list(topaz_clusters) + topaz_singles

topaz_priority_events = [
    item for item in topaz_events
    if float(item.get("opportunity_score") or 0) >= 8
]

topaz_elevated_events = [
    item for item in topaz_events
    if 6 <= float(item.get("opportunity_score") or 0) < 8
]

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
        "locate_tickets": len(locate_tickets),
        "topaz_activity": len(topaz_activity),
        "topaz_clusters": len(topaz_clusters),
        "topaz_singles": len(topaz_singles),
        "topaz_events": len(topaz_events),
        "topaz_priority_events": len(topaz_priority_events),
        "topaz_elevated_events": len(topaz_elevated_events),
        "brunswick_gis_parcels": len(brunswick_gis),
        "counties": counties
    },
    "highest_watch_score_parcels": top_items(land, "watch_score", 8),
    "highest_topaz_events": top_items(topaz_events, "opportunity_score", 10),
    "topaz_priority_events": top_items(topaz_priority_events, "opportunity_score", 8),
    "topaz_elevated_events": top_items(topaz_elevated_events, "opportunity_score", 8),
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
- treat TOPAZ Intelligence Events as the primary infrastructure-analysis layer.
- a TOPAZ Intelligence Event is either a consolidated infrastructure cluster or a qualifying Single activity record.
- distinguish TOPAZ Intelligence Events from the underlying active 811 locate records.
- TOPAZ Opportunity Score prioritizes investigation; it is not a forecast or prediction.
- 811 activity indicates excavation/locate activity and does not by itself establish company identity, build intent, or causation.
- never describe 811 activity as proof that a development, telecom build, utility project, or infrastructure project is planned, imminent, or underway.
- never infer a specific operator, utility, technology, or project type from 811 activity unless that identity is explicitly supported by the source data.
- when discussing TOPAZ Opportunity Scores, use only TOPAZ event scores. Do not describe legacy locate correlation scores as TOPAZ Opportunity Scores.
- describe convergence as a reason for investigation, monitoring, coordination, or validation rather than as evidence that a future project will occur.
- use locate patterns and correlations as supporting intelligence rather than as the primary TOPAZ representation.
- mention counties, GIS, builder activity, TOPAZ infrastructure activity, locate patterns, and land/watchlist signals when supported by the data.

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

    if content.startswith("```json"):
        content = content.replace("```json", "", 1).strip()

    if content.startswith("```"):
        content = content.replace("```", "", 1).strip()

    if content.endswith("```"):
        content = content[:-3].strip()

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