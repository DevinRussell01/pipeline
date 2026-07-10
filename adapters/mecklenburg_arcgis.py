from datetime import datetime

import requests


BASE_URL = (
    "https://gis.charlottenc.gov/arcgis/rest/services/"
    "PLN/Subdivisions/MapServer/0/query"
)

PAGE_SIZE = 2000


def arcgis_date(value):
    if value in (None, ""):
        return ""

    try:
        return datetime.fromtimestamp(
            int(value) / 1000
        ).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""
    
def latest_activity_date(record):
    dates = [
        record.get("submission_date") or "",
        record.get("status_date") or "",
        record.get("source_updated_at") or "",
    ]

    return max(dates)


def clean(value):
    if value is None:
        return ""

    return value

def normalize_status(value):
    text = str(value or "").strip()

    corrections = {
        "apporved": "Approved",
        "aproved": "Approved",
        "approved": "Approved",
        "in progress": "In Progress",
        "revisions": "Revisions",
        "withdrawn": "Withdrawn",
        "closed": "Closed",
        "complete": "Complete",
        "replaced": "Replaced",
    }

    return corrections.get(text.lower(), text or "Unknown")

def classify_project(attributes):
    single_family_lots = attributes.get("SFLots") or 0
    multifamily_units = attributes.get("MFUnits") or 0
    plan_type = str(attributes.get("PlanType") or "").lower()
    unit_type = str(attributes.get("UnitType") or "").lower()

    if multifamily_units >= 100:
        return "Residential Development", 10

    if single_family_lots >= 100:
        return "Residential Development", 10

    if multifamily_units >= 40 or single_family_lots >= 40:
        return "Residential Development", 9

    if multifamily_units > 0 or single_family_lots > 0:
        return "Residential Development", 8

    if "commercial" in plan_type or "commercial" in unit_type:
        return "Commercial Development", 8

    return "Residential Development", 7


def get_page(offset):
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "orderByFields": "OBJECTID ASC",
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=45,
        headers={
            "User-Agent": "Conduit Regional Intelligence Platform"
        },
    )

    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(
            f"Mecklenburg ArcGIS error: {data['error']}"
        )

    return data


def scan_mecklenburg_arcgis():
    features = []
    offset = 0

    while True:
        data = get_page(offset)
        page = data.get("features", [])

        features.extend(page)

        exceeded = data.get(
            "exceededTransferLimit",
            False,
        )

        if not page:
            break

        if len(page) < PAGE_SIZE and not exceeded:
            break

        offset += len(page)

    records = []

    for feature in features:
        attributes = feature.get("attributes", {})

        object_id = attributes.get("OBJECTID")
        global_id = attributes.get("GlobalID")
        alternate_id = attributes.get("AltID") or ""

        source_record_id = (
            f"MECK-GLOBAL-{global_id}"
            if global_id
            else f"MECK-OBJECT-{object_id}"
        )

        category, score = classify_project(attributes)

        project_name = attributes.get("ProjName") or ""
        status = normalize_status(attributes.get("AppStatus"))
        single_family_lots = attributes.get("SFLots") or 0
        multifamily_units = attributes.get("MFUnits") or 0
        rezoning_petition = attributes.get("RezonPetit") or ""

        description_parts = []

        if project_name:
            description_parts.append(
                f"Subdivision: {project_name}"
            )

        if single_family_lots:
            description_parts.append(
                f"Single-family lots: {single_family_lots}"
            )

        if multifamily_units:
            description_parts.append(
                f"Multifamily units: {multifamily_units}"
            )

        if status:
            description_parts.append(
                f"Status: {status}"
            )

        if rezoning_petition:
            description_parts.append(
                f"Rezoning petition: {rezoning_petition}"
            )

        record = {
            "county": "Mecklenburg",
            "case_number": alternate_id,
            "address": clean(attributes.get("Address")),
            "acreage": clean(attributes.get("AcreSF")),
            "owner": "",
            "applicant": clean(attributes.get("Developer")),
            "zoning_change": " | ".join(description_parts),
            "description": project_name,
            "status": status,
            "parcel_id": clean(attributes.get("ParcelID")),
            "plan_type": clean(attributes.get("PlanType")),
            "zoning": clean(attributes.get("Zoning")),
            "rezoning_petition": rezoning_petition,
            "single_family_lots": single_family_lots,
            "multifamily_acres": clean(attributes.get("AcreMF")),
            "multifamily_units": multifamily_units,
            "unit_type": clean(attributes.get("UnitType")),
            "submission_date": arcgis_date(
                attributes.get("SubmitDate")
            ),
            "status_date": arcgis_date(
                attributes.get("StatusDate")
            ),
            "source_updated_at": arcgis_date(
                attributes.get("last_edi_1")
            ),
            "object_id": object_id,
            "global_id": global_id,
            "source_system": "Charlotte-Mecklenburg ArcGIS",
            "source_record_id": source_record_id,
            "source_url": (
                attributes.get("Hyperlink")
                or "https://gis.charlottenc.gov/"
            ),
            "intelligence_type": category,
            "priority_score": score,
        }
        record["latest_activity_date"] = latest_activity_date(record)

        records.append(record)

    return records
