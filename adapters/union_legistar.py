import re
from datetime import datetime, timedelta

import requests


BASE_URL = "https://webapi.legistar.com/v1/unioncountync"

RELEVANT_BODIES = {
    "land use board",
    "board of commissioners",
}

KEYWORDS = [
    "rezoning",
    "zoning petition",
    "special use permit",
    "subdivision",
    "development ordinance",
    "site plan",
    "planned development",
    "industrial park",
    "economic development",
    "warehouse",
    "distribution",
    "utility",
    "construction agreement",
    "fiber",
    "broadband",
    "telecom",
    "data center",
    "cryptomining",
    "solar",
    "bess",
    "battery energy storage",
    "annexation",
]

INTELLIGENCE_RULES = [
    ("Broadband", 10, [
        "fiber",
        "broadband",
        "telecom",
    ]),

    ("Utility Infrastructure", 9, [
        "utility",
        "construction agreement",
        "easement",
        "water",
        "sewer",
    ]),

    ("Industrial Development", 9, [
    "industrial",
    "industrial park",
    "project canopy",
    "warehouse",
    "distribution center",
    "manufacturing",
    ]),

    ("Renewable Energy", 8, [
        "solar",
        "battery",
        "bess",
        "battery energy storage",
    ]),

    ("Commercial Development", 8, [
        "commercial",
        "site plan",
        "office",
        "retail",
    ]),

    ("Residential Development", 8, [
        "rezoning",
        "conditional rezoning",
        "subdivision",
        "planned development",
        "special use permit",
    ]),

    ("Land Use Policy", 6, [
        "development ordinance",
        "text amendment",
        "zoning ordinance",
    ]),

    ("Economic Development", 6, [
        "economic development",
        "incentive grant",
    ]),
]

def classify_project(title):
    text = (title or "").lower()

    for category, score, keywords in INTELLIGENCE_RULES:

        for keyword in keywords:

            if keyword in text:
                return category, score

    return "Review Required", 4

def get_json(url, params=None):
    response = requests.get(
        url,
        params=params,
        timeout=30,
        headers={"User-Agent": "Conduit Regional Intelligence Platform"},
    )
    response.raise_for_status()
    return response.json()


def canonical_case_number(title, matter_file, matter_id):
    """
    Converts titles such as:
      2026-CZ-007 -> CZ-2026-007
      CZ-2026-007 -> CZ-2026-007
      2026-SUP-01 -> SUP-2026-01
    """

    title_upper = (title or "").upper()

    patterns = [
        r"\b(\d{4})-(CZ|RZ|SUP)-(\d+)\b",
        r"\b(CZ|RZ|SUP)-(\d{4})-(\d+)\b",
    ]

    first_pattern = re.search(patterns[0], title_upper)
    if first_pattern:
        year, case_type, number = first_pattern.groups()
        return f"{case_type}-{year}-{number}"

    second_pattern = re.search(patterns[1], title_upper)
    if second_pattern:
        case_type, year, number = second_pattern.groups()
        return f"{case_type}-{year}-{number}"

    if matter_file:
        return f"UNION-{matter_file}"

    return f"UNION-MATTER-{matter_id}"


IGNORE = [
    "appointment",
    "appointments",
    "minutes",
    "consent agenda",
    "closed session",
    "recognition",
    "proclamation",
    "meals on wheels",
    "board member",
    "presentation",
    "budget amendment",
    "merger indemnification",
    "vacant position",
    "citizen comments",
    "public comments",
    "call to order",
    "adjournment",
    "approval of minutes"
    "commission merger",
    "economic development commission merger",
    "board of directors",
    "commission board",
    "indemnification agreement",
    "merger of union county and the monroe-union county economic development commission",
    "dissolution and liquidation of the monroe-union county economic development commission",
    "economic development commission board of directors",
]

def is_relevant(title):
    text = (title or "").lower()

    # Filter out obvious administrative items
    if any(ignore in text for ignore in IGNORE):
        return False

    # Keep only titles that match intelligence keywords
    return any(keyword.lower() in text for keyword in KEYWORDS)

def fetch_matter(matter_id):
    if not matter_id:
        return {}

    try:
        return get_json(f"{BASE_URL}/matters/{matter_id}")
    except Exception as error:
        print(f"Warning: unable to enrich MatterId {matter_id}: {error}")
        return {}


def scan_union_legistar(lookback_days=550):
    start_date = datetime.now() - timedelta(days=lookback_days)
    date_filter = start_date.strftime("%Y-%m-%dT00:00:00")

    events = get_json(
        f"{BASE_URL}/events",
        params={
            "$filter": f"EventDate ge datetime'{date_filter}'",
            "$orderby": "EventDate desc",
            "$top": 200,
        },
    )

    records = []
    seen_source_ids = set()

    for event in events:
        body_name = (event.get("EventBodyName") or "").strip()

        if body_name.lower() not in RELEVANT_BODIES:
            continue

        event_id = event.get("EventId")
        event_date = (event.get("EventDate") or "")[:10]

        try:
            items = get_json(
                f"{BASE_URL}/events/{event_id}/eventitems"
            )
        except Exception as error:
            print(f"Warning: unable to read EventId {event_id}: {error}")
            continue

        for item in items:
            title = (item.get("EventItemTitle") or "").strip()
            matter_id = item.get("EventItemMatterId")

            if not matter_id or not is_relevant(title):
                continue

            source_record_id = f"UNION-LEGISTAR-{matter_id}"

            # The same matter may appear before both the Land Use Board
            # and Board of Commissioners. Keep one normalized project.
            if source_record_id in seen_source_ids:
                continue

            seen_source_ids.add(source_record_id)

            matter = fetch_matter(matter_id)

            matter_file = (
                item.get("EventItemMatterFile")
                or matter.get("MatterFile")
                or ""
            )

            case_number = canonical_case_number(
                title,
                matter_file,
                matter_id,
            )

            description = (
                matter.get("MatterTitle")
                or matter.get("MatterName")
                or title
            )

            status = (
                matter.get("MatterStatusName")
                or event.get("EventAgendaStatusName")
                or "Published Agenda"
            )

            source_url = (
                matter.get("MatterInSiteURL")
                or event.get("EventInSiteURL")
                or event.get("EventAgendaFile")
                or "https://unioncountync.legistar.com/"
            )

            category, score = classify_project(title)

            record = {
                "county": "Union",
                "case_number": case_number,
                "address": "",
                "acreage": "",
                "owner": "",
                "applicant": "",
                "zoning_change": title,
                "description": description,
                "status": status,
                "meeting_date": event_date,
                "meeting_body": body_name,
                "matter_file": matter_file,
                "matter_id": matter_id,
                "event_id": event_id,
                "source_system": "Union County Legistar",
                "source_record_id": source_record_id,
                "source_url": source_url,
                "intelligence_type": category,
                "priority_score": score,
            }

            records.append(record)

    return records
