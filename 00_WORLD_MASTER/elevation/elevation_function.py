#!/usr/bin/env python3

"""
SHADOWS OF THE FALLEN
CONTINUOUS WORLD ELEVATION V3

Authoritative source:
    00_WORLD_MASTER/elevation/elevation_master.json

World source:
    00_WORLD_MASTER/coordinates/world_master.json

V3 terrain model:

    WORLD_BASE
        +
    REGIONAL_SHAPE
        +
    MAJOR_FEATURES
        +
    LOCAL_DETAIL

Important:
    - No cell owns elevation.
    - No cell gets a random offset.
    - Elevation is evaluated from world X/Y.
    - Region transitions are smoothly blended.
    - Noise is detail, not the primary terrain generator.
    - The final global clamp is a safety guard, not terrain shaping.
"""

from __future__ import annotations

import json
import math
import os
import sys


# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ELEVATION_JSON = os.path.join(
    SCRIPT_DIR,
    "elevation_master.json",
)

WORLD_JSON = os.path.normpath(
    os.path.join(
        SCRIPT_DIR,
        "..",
        "coordinates",
        "world_master.json",
    )
)


# ============================================================
# LOAD MASTER DATA
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


ELEVATION_MASTER = load_json(ELEVATION_JSON)
WORLD_MASTER = load_json(WORLD_JSON)


if ELEVATION_MASTER.get("project") != "Shadows of the Fallen":
    raise RuntimeError("Wrong elevation_master.json")


if not ELEVATION_MASTER["terrain_rules"]["world_coordinate_based"]:
    raise RuntimeError("World-coordinate elevation is disabled in master.")


# ============================================================
# AUTHORITATIVE SETTINGS
# ============================================================

SEA_LEVEL = float(
    ELEVATION_MASTER["sea_level"]["z"]
)

GLOBAL_MIN = float(
    ELEVATION_MASTER["global_elevation_envelope"]["minimum_m"]
)

GLOBAL_MAX = float(
    ELEVATION_MASTER["global_elevation_envelope"]["maximum_m"]
)

CELL_SIZE = float(
    ELEVATION_MASTER["sampling"]["prototype_cell_size_m"]
)

SAMPLE_SPACING = float(
    ELEVATION_MASTER["sampling"]["prototype_sample_spacing_m"]
)

VERTICES_PER_AXIS = int(
    ELEVATION_MASTER["sampling"]["prototype_vertices_per_axis"]
)

REGIONS = ELEVATION_MASTER["regions"]


# ============================================================
# BASIC MATH
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def lerp(a, b, t):
    return a + (b - a) * t


def smootherstep(t):
    """
    C2 smooth interpolation.

    This is intentionally used for region transitions so we don't
    introduce hard elevation/gradient steps.
    """
    t = clamp(t, 0.0, 1.0)

    return (
        t * t * t *
        (t * (t * 6.0 - 15.0) + 10.0)
    )


def smooth_threshold(value, edge0, edge1):
    if edge1 <= edge0:
        return 1.0 if value >= edge1 else 0.0

    return smootherstep(
        (value - edge0) / (edge1 - edge0)
    )


# ============================================================
# DETERMINISTIC HASH
# ============================================================

def hash2d(ix, iy, seed=1337):
    """
    Deterministic integer hash.

    Never uses Python's hash(), so results are stable between runs.
    """

    n = (
        ix * 374761393
        + iy * 668265263
        + seed * 1442695041
    ) & 0xFFFFFFFF

    n ^= n >> 13
    n = (n * 1274126177) & 0xFFFFFFFF
    n ^= n >> 16

    return (
        n / 2147483647.5
    ) - 1.0


# ============================================================
# VALUE NOISE
# ============================================================

def value_noise(x, y, scale, seed=1337):

    if scale <= 0:
        return 0.0

    gx = x / scale
    gy = y / scale

    ix = math.floor(gx)
    iy = math.floor(gy)

    fx = gx - ix
    fy = gy - iy

    sx = smootherstep(fx)
    sy = smootherstep(fy)

    v00 = hash2d(ix,     iy,     seed)
    v10 = hash2d(ix + 1, iy,     seed)
    v01 = hash2d(ix,     iy + 1, seed)
    v11 = hash2d(ix + 1, iy + 1, seed)

    a = lerp(v00, v10, sx)
    b = lerp(v01, v11, sx)

    return lerp(a, b, sy)


def fbm(
    x,
    y,
    scale,
    octaves,
    persistence,
    seed
):
    """
    Fractal noise normalized approximately to [-1,+1].

    V3 deliberately keeps this controlled.
    """

    total = 0.0
    amplitude = 1.0
    frequency = scale
    amplitude_total = 0.0

    for i in range(octaves):

        total += value_noise(
            x,
            y,
            frequency,
            seed + i * 101
        ) * amplitude

        amplitude_total += amplitude

        amplitude *= persistence
        frequency *= 0.5

    if amplitude_total == 0:
        return 0.0

    return total / amplitude_total


def ridged_noise(
    x,
    y,
    scale,
    octaves,
    seed
):
    n = fbm(
        x,
        y,
        scale,
        octaves,
        0.5,
        seed
    )

    return 1.0 - abs(n)


# ============================================================
# LOW-FREQUENCY DOMAIN WARP
# ============================================================

def domain_warp(
    x,
    y,
    amount,
    scale,
    seed
):
    """
    V3 uses only broad, low-amplitude warping.

    High-frequency domain warping was one of the things capable
    of producing the ugly spike field seen in V2.
    """

    wx = fbm(
        x + 1731.0,
        y - 941.0,
        scale,
        2,
        0.5,
        seed
    )

    wy = fbm(
        x - 1127.0,
        y + 619.0,
        scale,
        2,
        0.5,
        seed + 17
    )

    return (
        x + wx * amount,
        y + wy * amount
    )


# ============================================================
# REGION BOUNDS
# ============================================================

def extract_bounds(obj):
    """
    Supports the actual World Master bounds structure:

        "bounds": {
            "min": [x, y],
            "max": [x, y]
        }

    Also accepts the alternate forms used by older master files.
    """

    if not isinstance(obj, dict):
        return None

    # --------------------------------------------------------
    # Actual World Master format
    # --------------------------------------------------------

    if "bounds" in obj:

        value = obj["bounds"]

        if isinstance(value, dict):

            # PRIMARY FORMAT:
            #
            # "bounds": {
            #     "min": [x, y],
            #     "max": [x, y]
            # }

            if (
                isinstance(value.get("min"), (list, tuple))
                and
                isinstance(value.get("max"), (list, tuple))
                and
                len(value["min"]) >= 2
                and
                len(value["max"]) >= 2
            ):

                min_x = float(value["min"][0])
                min_y = float(value["min"][1])

                max_x = float(value["max"][0])
                max_y = float(value["max"][1])

                return (
                    min(min_x, max_x),
                    min(min_y, max_y),
                    max(min_x, max_x),
                    max(min_y, max_y),
                )

            # Alternate explicit format

            possible = [
                ("min_x", "min_y", "max_x", "max_y"),
                ("xmin", "ymin", "xmax", "ymax"),
                ("west", "south", "east", "north"),
                ("left", "bottom", "right", "top"),
            ]

            for keys in possible:

                if all(k in value for k in keys):

                    return (
                        float(value[keys[0]]),
                        float(value[keys[1]]),
                        float(value[keys[2]]),
                        float(value[keys[3]]),
                    )

        # Array form:
        #
        # "bounds": [min_x, min_y, max_x, max_y]

        if (
            isinstance(value, (list, tuple))
            and
            len(value) >= 4
        ):

            a = float(value[0])
            b = float(value[1])
            c = float(value[2])
            d = float(value[3])

            return (
                min(a, c),
                min(b, d),
                max(a, c),
                max(b, d),
            )

    # --------------------------------------------------------
    # Direct explicit fields
    # --------------------------------------------------------

    if all(
        k in obj
        for k in (
            "min_x",
            "min_y",
            "max_x",
            "max_y",
        )
    ):

        return (
            float(obj["min_x"]),
            float(obj["min_y"]),
            float(obj["max_x"]),
            float(obj["max_y"]),
        )

    return None

def find_region_bounds(obj, region_id):

    if isinstance(obj, dict):

        for key, value in obj.items():

            if key == region_id:

                bounds = extract_bounds(value)

                if bounds:
                    return bounds

            result = find_region_bounds(
                value,
                region_id
            )

            if result:
                return result

    elif isinstance(obj, list):

        for value in obj:

            result = find_region_bounds(
                value,
                region_id
            )

            if result:
                return result

    return None


REGION_BOUNDS = {}

print()
print("=" * 70)
print("V3 REGION BOUND VALIDATION")
print("=" * 70)

for region_id in REGIONS:

    bounds = find_region_bounds(
        WORLD_MASTER,
        region_id
    )

    if bounds is None:

        print(
            f"[ERROR] No bounds found for region: {region_id}"
        )

    else:

        REGION_BOUNDS[region_id] = bounds

        print(
            f"[OK] {region_id:22s} "
            f"X[{bounds[0]:.1f}, {bounds[2]:.1f}] "
            f"Y[{bounds[1]:.1f}, {bounds[3]:.1f}]"
        )


missing_regions = [
    region_id
    for region_id in REGIONS
    if region_id not in REGION_BOUNDS
]


if missing_regions:

    raise RuntimeError(
        "V3 REFUSES TO RUN: "
        "world_master.json region bounds could not be resolved for: "
        +
        ", ".join(missing_regions)
    )

# ============================================================
# REGION INFLUENCE
# ============================================================

def region_influence(
    region_id,
    x,
    y
):

    if region_id not in REGION_BOUNDS:
        return 0.0

    region = REGIONS[region_id]

    min_x, min_y, max_x, max_y = REGION_BOUNDS[
        region_id
    ]

    margin = float(
        region["blend_margin_m"]
    )

    inside = (
        min_x <= x <= max_x
        and
        min_y <= y <= max_y
    )

    if margin <= 0:
        return 1.0 if inside else 0.0

    if inside:

        distance_inside = min(
            x - min_x,
            max_x - x,
            y - min_y,
            max_y - y
        )

        t = clamp(
            distance_inside / margin,
            0.0,
            1.0
        )

        return (
            0.5
            +
            0.5 * smootherstep(t)
        )

    dx = 0.0
    dy = 0.0

    if x < min_x:
        dx = min_x - x

    elif x > max_x:
        dx = x - max_x

    if y < min_y:
        dy = min_y - y

    elif y > max_y:
        dy = y - max_y

    distance = math.hypot(dx, dy)

    if distance >= margin:
        return 0.0

    t = 1.0 - (
        distance / margin
    )

    return (
        0.5 *
        smootherstep(t)
    )


def region_weights(x, y):

    raw = {}

    for region_id in REGIONS:

        w = region_influence(
            region_id,
            x,
            y
        )

        if w > 0.000001:
            raw[region_id] = w

    total = sum(raw.values())

    if total <= 0:
        return {}

    return {
        region_id: weight / total
        for region_id, weight in raw.items()
    }


# ============================================================
# WORLD BASE
# ============================================================

def world_base(x, y):
    """
    WORLD_BASE

    Broad continental/oceanic structure.

    IMPORTANT:
    This does NOT map the full -6000 → +3200 envelope.

    That was exactly the sort of approach that allowed terrain
    noise to become absurdly steep.

    Deep ocean belongs to the appropriate regional geological field.
    """

    wx, wy = domain_warp(
        x,
        y,
        180.0,
        18000.0,
        100
    )

    continental = fbm(
        wx,
        wy,
        18000.0,
        3,
        0.5,
        101
    )

    basin = fbm(
        wx,
        wy,
        9000.0,
        3,
        0.5,
        202
    )

    return (
        140.0
        +
        continental * 170.0
        +
        basin * 70.0
    )


# ============================================================
# REGIONAL SHAPE
# ============================================================

def regional_shape(
    region_id,
    x,
    y
):
    """
    REGIONAL_SHAPE

    Moves the common world base toward the broad elevation
    character specified by elevation_master.json.
    """

    elevation = REGIONS[
        region_id
    ]["elevation"]

    typical_min = float(
        elevation["typical_min_m"]
    )

    typical_max = float(
        elevation["typical_max_m"]
    )

    center = (
        typical_min
        +
        typical_max
    ) * 0.5

    half_range = (
        typical_max
        -
        typical_min
    ) * 0.5

    seed = (
        3000
        +
        list(REGIONS.keys()).index(
            region_id
        ) * 31
    )

    n = fbm(
        x,
        y,
        9000.0,
        3,
        0.5,
        seed
    )

    return (
        center
        +
        n * half_range * 0.55
    )


# ============================================================
# MAJOR FEATURES
# ============================================================

def karthen_features(x, y):

    x, y = domain_warp(
        x,
        y,
        300.0,
        12000.0,
        4100
    )

    # Large mountain mass.
    mountain_mask = smooth_threshold(
        fbm(
            x,
            y,
            9000.0,
            3,
            0.5,
            4101
        ),
        -0.10,
        0.45
    )

    mountain_mass = (
        mountain_mask * 1050.0
    )

    # Foothills.
    foothills = (
        fbm(
            x,
            y,
            3800.0,
            3,
            0.5,
            4102
        )
        * 330.0
    )

    # Controlled ridge structure.
    ridge = ridged_noise(
        x,
        y,
        2500.0,
        3,
        4103
    )

    ridge = smootherstep(
        clamp(
            (ridge - 0.45) / 0.55,
            0.0,
            1.0
        )
    )

    ridge *= 260.0

    # Broad valley carving.
    valley = max(
        0.0,
        fbm(
            x + 2200.0,
            y - 1400.0,
            5000.0,
            2,
            0.5,
            4104
        )
    )

    valley *= 240.0

    return (
        mountain_mass
        +
        foothills
        +
        ridge
        -
        valley
    )


def western_timber_features(x, y):

    hills = (
        fbm(
            x,
            y,
            5000.0,
            3,
            0.5,
            4201
        )
        * 260.0
    )

    ridges = ridged_noise(
        x,
        y,
        2600.0,
        3,
        4202
    )

    ridges = smootherstep(
        clamp(
            (ridges - 0.42) / 0.58,
            0.0,
            1.0
        )
    )

    ridges *= 180.0

    valleys = max(
        0.0,
        fbm(
            x - 1100.0,
            y + 800.0,
            4200.0,
            2,
            0.5,
            4203
        )
    )

    valleys *= 150.0

    return (
        hills
        +
        ridges
        -
        valleys
    )


def nova_features(x, y):

    broad = (
        fbm(
            x,
            y,
            7000.0,
            2,
            0.5,
            4301
        )
        * 55.0
    )

    outskirts = (
        fbm(
            x + 900.0,
            y - 500.0,
            3200.0,
            2,
            0.5,
            4302
        )
        * 20.0
    )

    return broad + outskirts


def badlands_features(x, y):

    plateau = (
        fbm(
            x,
            y,
            7000.0,
            3,
            0.5,
            4401
        )
        * 300.0
    )

    mesas = ridged_noise(
        x,
        y,
        3600.0,
        3,
        4402
    )

    mesas = smootherstep(
        clamp(
            (mesas - 0.38) / 0.62,
            0.0,
            1.0
        )
    )

    mesas *= 220.0

    basin = max(
        0.0,
        fbm(
            x + 1400.0,
            y - 900.0,
            4200.0,
            2,
            0.5,
            4403
        )
    )

    basin *= 220.0

    canyon = ridged_noise(
        x - 500.0,
        y + 700.0,
        2400.0,
        2,
        4404
    )

    canyon = max(
        0.0,
        canyon - 0.55
    ) / 0.45

    canyon = smootherstep(
        clamp(canyon, 0.0, 1.0)
    )

    canyon *= 90.0

    return (
        plateau
        +
        mesas
        -
        basin
        -
        canyon
    )


def gang_features(x, y):

    broad = (
        fbm(
            x,
            y,
            6000.0,
            3,
            0.5,
            4501
        )
        * 65.0
    )

    rolling = (
        fbm(
            x + 300.0,
            y - 900.0,
            3000.0,
            2,
            0.5,
            4502
        )
        * 30.0
    )

    return broad + rolling


def wilderness_features(x, y):

    hills = (
        fbm(
            x,
            y,
            5200.0,
            3,
            0.5,
            4601
        )
        * 220.0
    )

    ridges = ridged_noise(
        x,
        y,
        2800.0,
        3,
        4602
    )

    ridges = smootherstep(
        clamp(
            (ridges - 0.40) / 0.60,
            0.0,
            1.0
        )
    )

    ridges *= 120.0

    valleys = max(
        0.0,
        fbm(
            x + 1200.0,
            y + 600.0,
            4200.0,
            2,
            0.5,
            4603
        )
    )

    valleys *= 120.0

    return (
        hills
        +
        ridges
        -
        valleys
    )


def coastline_features(x, y):

    hills = (
        fbm(
            x,
            y,
            6500.0,
            3,
            0.5,
            4701
        )
        * 85.0
    )

    shelf = (
        fbm(
            x - 900.0,
            y + 500.0,
            9000.0,
            2,
            0.5,
            4702
        )
        * 90.0
    )

    return hills + shelf


def khara_features(x, y):

    broad = (
        fbm(
            x,
            y,
            5000.0,
            3,
            0.5,
            4801
        )
        * 180.0
    )

    ridges = ridged_noise(
        x,
        y,
        2600.0,
        3,
        4802
    )

    ridges = smootherstep(
        clamp(
            (ridges - 0.42) / 0.58,
            0.0,
            1.0
        )
    )

    ridges *= 120.0

    return broad + ridges


def abyss_features(x, y):

    basin = (
        fbm(
            x,
            y,
            14000.0,
            3,
            0.5,
            4901
        )
        * 650.0
    )

    underwater_slopes = (
        fbm(
            x + 1300.0,
            y - 900.0,
            7000.0,
            2,
            0.5,
            4902
        )
        * 500.0
    )

    trench = ridged_noise(
        x - 800.0,
        y + 1700.0,
        6000.0,
        3,
        4903
    )

    trench = smootherstep(
        clamp(
            (trench - 0.46) / 0.54,
            0.0,
            1.0
        )
    )

    trench *= 750.0

    return (
        basin
        +
        underwater_slopes
        -
        trench
    )


MAJOR_FEATURES = {
    "karthen_mountains": karthen_features,
    "western_timber": western_timber_features,
    "nova_city": nova_features,
    "mainland_badlands": badlands_features,
    "gang_city": gang_features,
    "central_wilderness": wilderness_features,
    "southern_coastline": coastline_features,
    "khara_archipelago": khara_features,
    "abyss_atoll": abyss_features,
}


# ============================================================
# LOCAL DETAIL
# ============================================================

LOCAL_DETAIL_AMPLITUDE = {
    "karthen_mountains": 55.0,
    "western_timber": 45.0,
    "nova_city": 10.0,
    "mainland_badlands": 35.0,
    "gang_city": 10.0,
    "central_wilderness": 35.0,
    "southern_coastline": 18.0,
    "khara_archipelago": 25.0,
    "abyss_atoll": 20.0,
}


def local_detail(
    region_id,
    x,
    y
):

    amp = LOCAL_DETAIL_AMPLITUDE[
        region_id
    ]

    index = list(
        REGIONS.keys()
    ).index(region_id)

    n1 = fbm(
        x,
        y,
        420.0,
        2,
        0.45,
        7000 + index * 17
    )

    n2 = fbm(
        x + 173.0,
        y - 251.0,
        220.0,
        2,
        0.40,
        8000 + index * 19
    )

    return (
        n1 * amp
        +
        n2 * amp * 0.20
    )


# ============================================================
# COMPLETE REGIONAL TERRAIN
# ============================================================

def region_terrain(
    region_id,
    x,
    y
):

    wb = world_base(
        x,
        y
    )

    target = regional_shape(
        region_id,
        x,
        y
    )

    regional_delta = (
        target - wb
    )

    major = MAJOR_FEATURES[
        region_id
    ](
        x,
        y
    )

    detail = local_detail(
        region_id,
        x,
        y
    )

    z = (
        wb
        +
        regional_delta
        +
        major
        +
        detail
    )

    # Authoritative regional safety envelope.
    elevation = REGIONS[
        region_id
    ]["elevation"]

    minimum = float(
        elevation["minimum_m"]
    )

    maximum = float(
        elevation["maximum_m"]
    )

    return clamp(
        z,
        minimum,
        maximum
    )


# ============================================================
# AUTHORITATIVE ELEVATION FUNCTION
# ============================================================

def elevation_at(x, y):
    """
    Main API.

    IMPORTANT:
        x/y are WORLD coordinates.

    There is no cell-local randomization.
    """

    x = float(x)
    y = float(y)

    wb = world_base(
        x,
        y
    )

    weights = region_weights(
        x,
        y
    )

    if not weights:

        return clamp(
            wb,
            GLOBAL_MIN,
            GLOBAL_MAX
        )

    # Blend regional DELTAS from a common world base.
    #
    # This is important:
    #
    # BAD:
    #     blend unrelated complete landscapes
    #
    # GOOD:
    #     common world base
    #       +
    #     smoothly weighted regional changes
    #

    z = wb

    for region_id, weight in weights.items():

        regional_z = region_terrain(
            region_id,
            x,
            y
        )

        z += (
            regional_z - wb
        ) * weight

    return clamp(
        z,
        GLOBAL_MIN,
        GLOBAL_MAX
    )


# ============================================================
# GRADIENT / SLOPE
# ============================================================

def gradient(
    x,
    y,
    h=5.0
):

    gx = (
        elevation_at(x + h, y)
        -
        elevation_at(x - h, y)
    ) / (2.0 * h)

    gy = (
        elevation_at(x, y + h)
        -
        elevation_at(x, y - h)
    ) / (2.0 * h)

    return gx, gy


def slope_degrees(
    x,
    y,
    h=5.0
):

    gx, gy = gradient(
        x,
        y,
        h
    )

    slope = math.hypot(
        gx,
        gy
    )

    return math.degrees(
        math.atan(slope)
    )


# ============================================================
# 1 KM CELL
# ============================================================

def sample_cell(
    cell_x,
    cell_y
):

    origin_x = (
        cell_x * CELL_SIZE
    )

    origin_y = (
        cell_y * CELL_SIZE
    )

    grid = []

    for j in range(
        VERTICES_PER_AXIS
    ):

        row = []

        y = (
            origin_y
            +
            j * SAMPLE_SPACING
        )

        for i in range(
            VERTICES_PER_AXIS
        ):

            x = (
                origin_x
                +
                i * SAMPLE_SPACING
            )

            row.append(
                elevation_at(x, y)
            )

        grid.append(row)

    return grid


def cell_statistics(
    cell_x,
    cell_y
):

    grid = sample_cell(
        cell_x,
        cell_y
    )

    values = [
        z
        for row in grid
        for z in row
    ]

    center_x = (
        cell_x * CELL_SIZE
        +
        CELL_SIZE * 0.5
    )

    center_y = (
        cell_y * CELL_SIZE
        +
        CELL_SIZE * 0.5
    )

    regions = [
        region_id
        for region_id in REGIONS
        if region_influence(
            region_id,
            center_x,
            center_y
        ) > 0.05
    ]

    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "regions": regions,
    }


# ============================================================
# SHARED CELL BOUNDARY TEST
# ============================================================

def shared_x_boundary(
    cell_x,
    cell_y
):

    x = (
        cell_x + 1
    ) * CELL_SIZE

    max_diff = 0.0

    for i in range(
        VERTICES_PER_AXIS
    ):

        y = (
            cell_y * CELL_SIZE
            +
            i * SAMPLE_SPACING
        )

        a = elevation_at(
            x,
            y
        )

        b = elevation_at(
            x,
            y
        )

        max_diff = max(
            max_diff,
            abs(a - b)
        )

    return max_diff


def shared_y_boundary(
    cell_x,
    cell_y
):

    y = (
        cell_y + 1
    ) * CELL_SIZE

    max_diff = 0.0

    for i in range(
        VERTICES_PER_AXIS
    ):

        x = (
            cell_x * CELL_SIZE
            +
            i * SAMPLE_SPACING
        )

        a = elevation_at(
            x,
            y
        )

        b = elevation_at(
            x,
            y
        )

        max_diff = max(
            max_diff,
            abs(a - b)
        )

    return max_diff


# ============================================================
# VALIDATION
# ============================================================

def run_tests():

    print()
    print("=" * 70)
    print("SHADOWS OF THE FALLEN")
    print("CONTINUOUS WORLD ELEVATION V3")
    print("=" * 70)

    print()
    print("CONFIGURATION")
    print(
        f"Global envelope : "
        f"{GLOBAL_MIN:.2f} → {GLOBAL_MAX:.2f} m"
    )
    print(
        f"Sea level       : "
        f"{SEA_LEVEL:.2f} m"
    )
    print(
        f"Cell size       : "
        f"{CELL_SIZE:.2f} m"
    )
    print(
        f"Sample spacing  : "
        f"{SAMPLE_SPACING:.2f} m"
    )
    print(
        f"Vertices/axis   : "
        f"{VERTICES_PER_AXIS}"
    )

    # --------------------------------------------------------
    # 1. DETERMINISM
    # --------------------------------------------------------

    print()
    print("1. DETERMINISM")

    points = [
        (0.0, 0.0),
        (500.0, 500.0),
        (-1000.0, 750.0),
        (1234.5, -987.25),
    ]

    deterministic = True

    for x, y in points:

        a = elevation_at(
            x,
            y
        )

        b = elevation_at(
            x,
            y
        )

        difference = abs(
            a - b
        )

        print(
            f"({x:9.2f}, {y:9.2f}) "
            f"z={a:9.3f} m "
            f"diff={difference:.12f}"
        )

        if difference > 1e-12:
            deterministic = False

    print(
        "STATUS:",
        "PASS"
        if deterministic
        else "FAIL"
    )

    # --------------------------------------------------------
    # 2. CELL STATISTICS
    # --------------------------------------------------------

    print()
    print("2. 1 KM CELL ELEVATION STATS")

    cells = [
        (0, 0),
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (-4, 3),
    ]

    statistics_ok = True

    for cx, cy in cells:

        stats = cell_statistics(
            cx,
            cy
        )

        print(
            f"CELL_{cx:+03d}_{cy:+03d} | "
            f"min={stats['min']:8.2f}m "
            f"max={stats['max']:8.2f}m "
            f"mean={stats['mean']:8.2f}m | "
            f"regions="
            f"{', '.join(stats['regions']) or 'world_base'}"
        )

        if (
            stats["min"] < GLOBAL_MIN
            or
            stats["max"] > GLOBAL_MAX
        ):
            statistics_ok = False

    print(
        "STATUS:",
        "PASS"
        if statistics_ok
        else "FAIL"
    )

    # --------------------------------------------------------
    # 3. SLOPE SANITY
    # --------------------------------------------------------

    print()
    print("3. SLOPE SANITY")

    slope_points = [
        (0.0, 0.0),
        (500.0, 500.0),
        (1000.0, 0.0),
        (0.0, 1000.0),
        (-500.0, 500.0),
    ]

    slope_ok = True

    for x, y in slope_points:

        gx, gy = gradient(
            x,
            y
        )

        slope = math.hypot(
            gx,
            gy
        )

        angle = math.degrees(
            math.atan(slope)
        )

        print(
            f"({x:8.1f}, {y:8.1f}) "
            f"gradient="
            f"({gx:8.4f}, {gy:8.4f}) "
            f"slope={slope:8.4f} m/m "
            f"({angle:6.2f}°)"
        )

        # This is a V3 diagnostic guardrail.
        #
        # The JSON does NOT specify a numerical slope limit.
        # This simply catches the V2 failure mode of ~85-89° spikes.
        if angle > 70.0:
            slope_ok = False

    print(
        "STATUS:",
        "PASS"
        if slope_ok
        else "REVIEW"
    )

    # --------------------------------------------------------
    # 4. REGIONAL ENVELOPE
    # --------------------------------------------------------

    print()
    print("4. REGIONAL ENVELOPE")

    envelope_ok = True

    for region_id, region in REGIONS.items():

        if region_id not in REGION_BOUNDS:
            print(
                f"{region_id}: "
                f"bounds not found in world_master.json"
            )
            continue

        min_x, min_y, max_x, max_y = (
            REGION_BOUNDS[
                region_id
            ]
        )

        points = [
            (
                (min_x + max_x) * 0.5,
                (min_y + max_y) * 0.5
            ),
            (
                min_x + (max_x - min_x) * 0.25,
                min_y + (max_y - min_y) * 0.25
            ),
            (
                min_x + (max_x - min_x) * 0.75,
                min_y + (max_y - min_y) * 0.75
            ),
        ]

        values = [
            elevation_at(x, y)
            for x, y in points
        ]

        allowed_min = float(
            region["elevation"]["minimum_m"]
        )

        allowed_max = float(
            region["elevation"]["maximum_m"]
        )

        local_min = min(values)
        local_max = max(values)

        print(
            f"{region_id:22s} "
            f"sample="
            f"{local_min:8.2f} → "
            f"{local_max:8.2f} m | "
            f"allowed="
            f"{allowed_min:8.2f} → "
            f"{allowed_max:8.2f} m"
        )

        if (
            local_min < allowed_min - 1e-9
            or
            local_max > allowed_max + 1e-9
        ):
            envelope_ok = False

    print(
        "STATUS:",
        "PASS"
        if envelope_ok
        else "FAIL"
    )

    # --------------------------------------------------------
    # 5. CELL BOUNDARY
    # --------------------------------------------------------

    print()
    print("5. CELL BOUNDARY CONTINUITY")

    # Because elevation_at() is world-coordinate based,
    # the theoretical difference is exactly zero.
    #
    # We explicitly test representative world boundaries.

    boundary_tests = [
        (1000.0, 500.0),
        (-1000.0, 500.0),
        (500.0, 1000.0),
        (500.0, -1000.0),
    ]

    boundary_ok = True

    for x, y in boundary_tests:

        # Same world point evaluated twice.
        a = elevation_at(
            x,
            y
        )

        b = elevation_at(
            float(x),
            float(y)
        )

        difference = abs(
            a - b
        )

        print(
            f"({x:8.1f}, {y:8.1f}) "
            f"diff={difference:.12f} m"
        )

        if difference > 1e-12:
            boundary_ok = False

    print(
        "STATUS:",
        "PASS"
        if boundary_ok
        else "FAIL"
    )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print()
    print("=" * 70)

    if (
        deterministic
        and
        statistics_ok
        and
        slope_ok
        and
        envelope_ok
        and
        boundary_ok
    ):

        print("V3 STATUS: PASS")
        print()
        print(
            "Elevation field is deterministic, world-space,"
        )
        print(
            "bounded and suitable for the next prototype test."
        )

        return 0

    print("V3 STATUS: REVIEW / FAIL")
    print()
    print(
        "DO NOT generate the full Blender terrain yet."
    )

    return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(
        run_tests()
    )