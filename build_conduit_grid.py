import json
import math
import urllib.request
from pathlib import Path

TERRITORY_FILE = Path("conduit_territories.json")
GEOMETRY_CACHE = Path("conduit_county_boundaries.geojson")

# Census cartographic boundary GeoJSON.
# State/county selection is performed locally from the downloaded file.
CENSUS_GEOJSON_URL = (
    "https://raw.githubusercontent.com/plotly/datasets/master/"
    "geojson-counties-fips.json"
)

LAKE_WYLIE_REFERENCE = {
    "name": "Lake Wylie Regression",
    "lat": 35.1980556,
    "lon": -81.0651667,
    "region": "WESTERN_NC",
}

EARTH_RADIUS_MILES = 3958.7613


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def download_geometry():
    if GEOMETRY_CACHE.exists():
        print("County geometry cache: FOUND")
        return

    print("County geometry cache: NOT FOUND")
    print("Downloading county geometry...")

    req = urllib.request.Request(
        CENSUS_GEOJSON_URL,
        headers={
            "User-Agent": "Conduit-TOPAZ/1.0"
        },
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read()

    GEOMETRY_CACHE.write_bytes(data)

    print(
        "County geometry downloaded:",
        f"{len(data):,} bytes"
    )


def county_fips(feature):
    feature_id = str(feature.get("id", "")).zfill(5)

    if len(feature_id) == 5:
        return feature_id

    props = feature.get("properties", {})

    state = str(
        props.get("STATE")
        or props.get("STATEFP")
        or ""
    ).zfill(2)

    county = str(
        props.get("COUNTY")
        or props.get("COUNTYFP")
        or ""
    ).zfill(3)

    if state.strip("0") or county.strip("0"):
        return state + county

    return ""


def county_name(feature):
    props = feature.get("properties", {})

    return (
        props.get("NAME")
        or props.get("name")
        or ""
    ).strip()


def feature_state_fips(feature):
    fips = county_fips(feature)

    if len(fips) == 5:
        return fips[:2]

    return ""


def normalize_name(value):
    return (
        value.lower()
        .replace(" county", "")
        .replace(".", "")
        .strip()
    )


def ring_contains_point(lon, lat, ring):
    inside = False
    j = len(ring) - 1

    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]

        intersects = (
            ((yi > lat) != (yj > lat))
            and (
                lon
                < (
                    (xj - xi)
                    * (lat - yi)
                    / ((yj - yi) or 1e-15)
                    + xi
                )
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def polygon_contains_point(lon, lat, polygon):
    if not polygon:
        return False

    # First ring = exterior.
    if not ring_contains_point(
        lon,
        lat,
        polygon[0],
    ):
        return False

    # Remaining rings = holes.
    for hole in polygon[1:]:
        if ring_contains_point(
            lon,
            lat,
            hole,
        ):
            return False

    return True


def geometry_contains_point(lon, lat, geometry):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "Polygon":
        return polygon_contains_point(
            lon,
            lat,
            coordinates,
        )

    if geometry_type == "MultiPolygon":
        return any(
            polygon_contains_point(
                lon,
                lat,
                polygon,
            )
            for polygon in coordinates
        )

    return False


def geometry_bounds(geometry):
    xs = []
    ys = []

    def walk(obj):
        if (
            isinstance(obj, list)
            and len(obj) >= 2
            and isinstance(obj[0], (int, float))
            and isinstance(obj[1], (int, float))
        ):
            xs.append(float(obj[0]))
            ys.append(float(obj[1]))
            return

        if isinstance(obj, list):
            for child in obj:
                walk(child)

    walk(geometry.get("coordinates", []))

    if not xs:
        raise ValueError("Geometry contains no coordinates.")

    return min(xs), min(ys), max(xs), max(ys)


def haversine_miles(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2) ** 2
    )

    return 2 * EARTH_RADIUS_MILES * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )


def build_region_grid(
    region_key,
    config,
    features,
):
    requested_counties = {
        normalize_name(name): name
        for name in config["counties"]
    }

    state_fips = config["state_fips"]

    selected = []

    for feature in features:
        if feature_state_fips(feature) != state_fips:
            continue

        name = county_name(feature)

        if normalize_name(name) in requested_counties:
            selected.append(feature)

    found_names = {
        normalize_name(county_name(feature))
        for feature in selected
    }

    missing = [
        original
        for normalized, original
        in requested_counties.items()
        if normalized not in found_names
    ]

    if missing:
        raise RuntimeError(
            f"{region_key}: missing county geometry: "
            + ", ".join(missing)
        )

    spacing = float(
        config["grid_spacing_miles"]
    )

    partition_count = int(
        config["partition_count"]
    )

    lat_step = spacing / 69.0

    points = []
    point_counter = 0

    for feature in selected:
        geometry = feature["geometry"]

        min_lon, min_lat, max_lon, max_lat = (
            geometry_bounds(geometry)
        )

        lat = min_lat

        while lat <= max_lat + 1e-9:
            miles_per_lon_degree = (
                69.172
                * math.cos(math.radians(lat))
            )

            lon_step = (
                spacing
                / miles_per_lon_degree
            )

            lon = min_lon

            while lon <= max_lon + 1e-9:
                if geometry_contains_point(
                    lon,
                    lat,
                    geometry,
                ):
                    # Stable geographically interleaved
                    # partition assignment.
                    #
                    # Quantized coordinates distribute each
                    # partition across the territory instead
                    # of walking county-by-county.
                    lat_key = round(
                        lat * 1000000
                    )
                    lon_key = round(
                        abs(lon) * 1000000
                    )

                    partition = (
                        (
                            lat_key * 73856093
                        )
                        ^ (
                            lon_key * 19349663
                        )
                    ) % partition_count

                    points.append({
                        "lat": round(lat, 6),
                        "lon": round(lon, 6),
                        "partition": partition,
                        "county": county_name(feature),
                    })

                    point_counter += 1

                lon += lon_step

            lat += lat_step

    partition_counts = {
        i: 0
        for i in range(partition_count)
    }

    for point in points:
        partition_counts[
            point["partition"]
        ] += 1

    return {
        "region": region_key,
        "name": config["name"],
        "state": config["state"],
        "counties": len(selected),
        "spacing_miles": spacing,
        "partition_count": partition_count,
        "points": points,
        "partition_counts": partition_counts,
        "infrastructure_source":
            config.get(
                "topaz_infrastructure_source"
            ),
    }


def main():
    print("CONDUIT TERRITORY GRID VALIDATOR")
    print("================================")
    print("Live NC811 requests made: 0")
    print()

    territories = load_json(
        TERRITORY_FILE
    )

    download_geometry()

    geometry_data = load_json(
        GEOMETRY_CACHE
    )

    features = geometry_data.get(
        "features",
        []
    )

    if not features:
        raise RuntimeError(
            "County geometry contains no features."
        )

    results = {}

    for region_key, config in (
        territories["regions"].items()
    ):
        result = build_region_grid(
            region_key,
            config,
            features,
        )

        results[region_key] = result

        print(region_key)
        print("-" * len(region_key))

        print(
            "Counties:",
            result["counties"]
        )

        print(
            "Grid spacing:",
            result["spacing_miles"],
            "miles"
        )

        print(
            "Polygon-clipped points:",
            len(result["points"])
        )

        counts = list(
            result[
                "partition_counts"
            ].values()
        )

        print(
            "Partition size:",
            min(counts),
            "to",
            max(counts),
            "points"
        )

        source = result[
            "infrastructure_source"
        ]

        print(
            "Infrastructure source:",
            source
            if source
            else "NOT CONFIGURED"
        )

        print()

    # --------------------------------------------------------
    # Lake Wylie regression
    # --------------------------------------------------------

    western = results[
        LAKE_WYLIE_REFERENCE["region"]
    ]

    nearest = min(
        western["points"],
        key=lambda point: haversine_miles(
            LAKE_WYLIE_REFERENCE["lat"],
            LAKE_WYLIE_REFERENCE["lon"],
            point["lat"],
            point["lon"],
        ),
    )

    distance = haversine_miles(
        LAKE_WYLIE_REFERENCE["lat"],
        LAKE_WYLIE_REFERENCE["lon"],
        nearest["lat"],
        nearest["lon"],
    )

    print("LAKE WYLIE REGRESSION")
    print("---------------------")

    print(
        "Nearest grid point:",
        nearest["lat"],
        nearest["lon"]
    )

    print(
        "County:",
        nearest["county"]
    )

    print(
        "Distance:",
        round(distance, 4),
        "miles"
    )

    print(
        "Coverage:",
        "PASS"
        if distance < 1.0
        else "FAIL"
    )

    print()

    if distance >= 1.0:
        raise RuntimeError(
            "Lake Wylie regression failed."
        )

    print(
        "PASS: territory geometry "
        "and grid generation validated."
    )


if __name__ == "__main__":
    main()
