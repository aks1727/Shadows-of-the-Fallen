#!/usr/bin/env python3
"""
SHADOWS OF THE FALLEN
Continuous World Elevation Function v2

Goals
-----
1. Deterministic world-space sampling.
2. No cell-boundary special cases.
3. Broad geological landforms first, detail second.
4. Smooth regional transitions without hard terrain shelves.
5. JSON remains authoritative for region/global elevation envelopes.
6. No terrace quantization in the base elevation model.
7. Roads/hydrology are applied only after the continuous terrain field.
"""

import json
import math
import os


# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

WORLD_MASTER_PATH = os.path.join(
    SCRIPT_DIR, "..", "coordinates", "world_master.json"
)

ELEVATION_MASTER_PATH = os.path.join(
    SCRIPT_DIR, "elevation_master.json"
)


# ============================================================
# LOAD MASTER DATA
# ============================================================

def load_json(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Required JSON file not found:\n{path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


WORLD_MASTER = load_json(WORLD_MASTER_PATH)
ELEVATION_MASTER = load_json(ELEVATION_MASTER_PATH)

WORLD_REGIONS = WORLD_MASTER["regions"]
ELEVATION_REGIONS = ELEVATION_MASTER["regions"]

GLOBAL_MIN = float(
    ELEVATION_MASTER["global_elevation_envelope"]["minimum_m"]
)
GLOBAL_MAX = float(
    ELEVATION_MASTER["global_elevation_envelope"]["maximum_m"]
)
SEA_LEVEL = float(ELEVATION_MASTER["sea_level"]["z"])
CELL_SIZE = float(
    ELEVATION_MASTER["sampling"]["prototype_cell_size_m"]
)


# ============================================================
# BASIC MATH
# ============================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smootherstep(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def remap01(value, a, b):
    if abs(b - a) <= 1e-12:
        return 0.5
    return clamp((value - a) / (b - a), 0.0, 1.0)


def smooth_range(value, minimum, maximum):
    """Map value into [0,1] with smooth endpoint behavior."""
    return smootherstep(remap01(value, minimum, maximum))


# ============================================================
# DETERMINISTIC HASH / VALUE NOISE
# ============================================================

def hash2d(x, y, seed=1337):
    """
    Deterministic pseudo-random value in [-1, 1].
    Integer lattice coordinates only.
    """
    x = int(x)
    y = int(y)

    n = (
        x * 374761393
        + y * 668265263
        + int(seed) * 1442695041
    )
    n &= 0xFFFFFFFFFFFFFFFF

    n ^= n >> 13
    n = (n * 1274126177) & 0xFFFFFFFFFFFFFFFF
    n ^= n >> 16

    return ((n & 0x7FFFFFFF) / 1073741823.5) - 1.0


def value_noise(x, y, scale=1000.0, seed=1337):
    """Smooth deterministic 2D value noise in [-1, 1]."""
    if scale <= 0.0:
        return 0.0

    gx = x / scale
    gy = y / scale

    x0 = math.floor(gx)
    y0 = math.floor(gy)

    tx = gx - x0
    ty = gy - y0

    sx = smootherstep(tx)
    sy = smootherstep(ty)

    n00 = hash2d(x0, y0, seed)
    n10 = hash2d(x0 + 1, y0, seed)
    n01 = hash2d(x0, y0 + 1, seed)
    n11 = hash2d(x0 + 1, y0 + 1, seed)

    nx0 = lerp(n00, n10, sx)
    nx1 = lerp(n01, n11, sx)

    return lerp(nx0, nx1, sy)


def fractal_noise(
    x,
    y,
    base_scale=1000.0,
    octaves=4,
    persistence=0.5,
    seed=1337,
):
    """
    Normalized multi-octave noise in [0,1].

    Kept deliberately moderate. Fine detail is not allowed
    to dominate the macro landform.
    """
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    amplitude_sum = 0.0

    for octave in range(int(octaves)):
        scale = base_scale / frequency

        total += value_noise(
            x,
            y,
            scale=scale,
            seed=int(seed) + octave * 101,
        ) * amplitude

        amplitude_sum += amplitude
        amplitude *= persistence
        frequency *= 2.0

    if amplitude_sum <= 0.0:
        return 0.5

    return clamp(
        (total / amplitude_sum) * 0.5 + 0.5,
        0.0,
        1.0,
    )


def ridged_noise(
    x,
    y,
    base_scale=1200.0,
    octaves=4,
    lacunarity=2.0,
    gain=0.5,
    seed=0,
):
    """
    Ridged noise in [0,1].

    Used as a secondary ridge/erosion structure, never as the
    entire mountain system.
    """
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    amplitude_sum = 0.0

    for i in range(int(octaves)):
        n = value_noise(
            x,
            y,
            scale=base_scale / frequency,
            seed=int(seed) + i * 31,
        )

        ridge = 1.0 - abs(n)
        ridge = ridge * ridge

        value += ridge * amplitude
        amplitude_sum += amplitude

        frequency *= lacunarity
        amplitude *= gain

    if amplitude_sum <= 0.0:
        return 0.0

    return clamp(value / amplitude_sum, 0.0, 1.0)


def domain_warp(
    x,
    y,
    strength=180.0,
    scale=1400.0,
    seed=77,
):
    """
    Low-frequency coordinate distortion.

    This breaks the obvious grid/noise appearance without
    introducing discontinuities at cell boundaries.
    """
    dx = (
        fractal_noise(
            x,
            y,
            base_scale=scale,
            octaves=2,
            persistence=0.5,
            seed=seed,
        ) * 2.0 - 1.0
    ) * strength

    dy = (
        fractal_noise(
            x + 52.3,
            y + 18.7,
            base_scale=scale,
            octaves=2,
            persistence=0.5,
            seed=seed + 101,
        ) * 2.0 - 1.0
    ) * strength

    return x + dx, y + dy


# ============================================================
# WORLD REGION HELPERS
# ============================================================

def point_inside_region(x, y, region_data):
    bounds = region_data["bounds"]
    minimum = bounds["min"]
    maximum = bounds["max"]

    return (
        minimum[0] <= x <= maximum[0]
        and minimum[1] <= y <= maximum[1]
    )


def containing_regions(x, y):
    result = []

    for region_id, region_data in WORLD_REGIONS.items():
        if point_inside_region(x, y, region_data):
            result.append(region_id)

    return result


def get_region_blend_margin(region_id, default=500.0):
    reg_data = ELEVATION_REGIONS.get(region_id, {})
    return float(reg_data.get("blend_margin_m", default))


def region_influence(x, y, region_id, blend_margin=None):
    """
    C2-friendly regional influence.

    Inside a region:
        influence approaches 1 toward the interior.

    Outside:
        influence decays smoothly to 0.

    The field is world-space, so cell boundaries have no special
    behavior.
    """
    if blend_margin is None:
        blend_margin = get_region_blend_margin(region_id)

    blend_margin = max(float(blend_margin), 1.0)

    region = WORLD_REGIONS[region_id]
    bounds = region["bounds"]

    min_x = float(bounds["min"][0])
    max_x = float(bounds["max"][0])
    min_y = float(bounds["min"][1])
    max_y = float(bounds["max"][1])

    dx = max(min_x - x, 0.0, x - max_x)
    dy = max(min_y - y, 0.0, y - max_y)
    dist_outside = math.hypot(dx, dy)

    if dist_outside > 0.0:
        if dist_outside >= blend_margin:
            return 0.0

        return 0.5 * (
            1.0
            + smootherstep(1.0 - dist_outside / blend_margin)
        )

    dist_inside = min(
        x - min_x,
        max_x - x,
        y - min_y,
        max_y,
    )

    if dist_inside >= blend_margin:
        return 1.0

    # 0.5 at the actual region boundary, smoothly increasing inward.
    return 0.5 + 0.5 * smootherstep(
        dist_inside / blend_margin
    )


def active_region_weights(x, y):
    """
    Normalize all region influences.

    Only regions with meaningful influence are included.
    """
    raw = []

    for region_id in WORLD_REGIONS.keys():
        w = region_influence(x, y, region_id)
        if w > 0.001:
            raw.append((region_id, w))

    if not raw:
        return []

    total = sum(w for _, w in raw)

    if total <= 1e-12:
        return []

    return [
        (region_id, w / total)
        for region_id, w in raw
    ]


# ============================================================
# REGIONAL JSON ENVELOPES
# ============================================================

def region_elevation_limits(region_id):
    data = ELEVATION_REGIONS[region_id]["elevation"]

    return (
        float(data["minimum_m"]),
        float(data["maximum_m"]),
    )


# ============================================================
# LANDSCAPE PRIMITIVES
# ============================================================

def broad_terrain_field(x, y, seed):
    """
    4-10 km scale landform field.

    This is intentionally low frequency. It establishes
    believable terrain masses before local detail is introduced.
    """
    wx, wy = domain_warp(
        x,
        y,
        strength=260.0,
        scale=7000.0,
        seed=seed,
    )

    macro = fractal_noise(
        wx,
        wy,
        base_scale=9000.0,
        octaves=3,
        persistence=0.55,
        seed=seed + 1,
    )

    large = fractal_noise(
        wx,
        wy,
        base_scale=3500.0,
        octaves=3,
        persistence=0.55,
        seed=seed + 2,
    )

    return clamp(
        macro * 0.70 + large * 0.30,
        0.0,
        1.0,
    )


def rolling_hills_field(x, y, seed):
    wx, wy = domain_warp(
        x,
        y,
        strength=110.0,
        scale=1800.0,
        seed=seed,
    )

    broad = fractal_noise(
        wx,
        wy,
        base_scale=1800.0,
        octaves=3,
        persistence=0.55,
        seed=seed + 10,
    )

    hills = fractal_noise(
        wx,
        wy,
        base_scale=650.0,
        octaves=3,
        persistence=0.50,
        seed=seed + 20,
    )

    return clamp(
        broad * 0.68 + hills * 0.32,
        0.0,
        1.0,
    )


def erosion_field(x, y, seed):
    """
    Medium-scale breakup.

    Kept small enough that the terrain remains readable at
    10 m sampling.
    """
    detail = fractal_noise(
        x,
        y,
        base_scale=260.0,
        octaves=3,
        persistence=0.48,
        seed=seed,
    )

    gullies = ridged_noise(
        x,
        y,
        base_scale=420.0,
        octaves=3,
        lacunarity=2.0,
        gain=0.5,
        seed=seed + 100,
    )

    return clamp(
        detail * 0.60 + gullies * 0.40,
        0.0,
        1.0,
    )


def terrain_from_normalized(
    z_min,
    z_max,
    structural,
    variation=0.0,
):
    """
    Convert a normalized structural field to a regional elevation.

    Variation is intentionally a modest fraction of the regional
    span instead of another full-range lerp.
    """
    span = z_max - z_min

    base = lerp(z_min, z_max, clamp(structural, 0.0, 1.0))
    return base + variation * span


# ============================================================
# REGIONAL TERRAIN FUNCTIONS
# ============================================================

def karthen_mountains_elevation(x, y):
    z_min, z_max = region_elevation_limits("karthen_mountains")
    span = z_max - z_min

    wx, wy = domain_warp(
        x,
        y,
        strength=420.0,
        scale=5000.0,
        seed=105,
    )

    # Mountain mass: broad, slow-changing elevation.
    mass = fractal_noise(
        wx,
        wy,
        base_scale=6500.0,
        octaves=3,
        persistence=0.58,
        seed=110,
    )

    foothills = fractal_noise(
        wx,
        wy,
        base_scale=2600.0,
        octaves=3,
        persistence=0.52,
        seed=120,
    )

    # Ridge structure is secondary to mass.
    ridges = ridged_noise(
        wx,
        wy,
        base_scale=1500.0,
        octaves=4,
        lacunarity=2.0,
        gain=0.52,
        seed=210,
    )

    erosion = erosion_field(x, y, 310)

    # Compress extremes so we do not get "noise mountains".
    mass = smooth_range(mass, 0.18, 0.82)
    foothills = smooth_range(foothills, 0.20, 0.80)
    ridges = smooth_range(ridges, 0.28, 0.82)

    structural = (
        mass * 0.55
        + foothills * 0.23
        + ridges * 0.17
        + erosion * 0.05
    )

    # Ridge amplitude is limited.
    variation = (ridges - 0.5) * 0.10

    return clamp(
        terrain_from_normalized(
            z_min,
            z_max,
            structural,
            variation,
        ),
        z_min,
        z_max,
    )


def western_timber_elevation(x, y):
    z_min, z_max = region_elevation_limits("western_timber")

    broad = broad_terrain_field(x, y, 410)
    hills = rolling_hills_field(x, y, 510)
    detail = erosion_field(x, y, 610)

    structural = (
        broad * 0.55
        + hills * 0.37
        + detail * 0.08
    )

    variation = (detail - 0.5) * 0.045

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


def nova_city_elevation(x, y):
    z_min, z_max = region_elevation_limits("nova_city")

    broad = fractal_noise(
        x, y,
        base_scale=5000.0,
        octaves=3,
        persistence=0.55,
        seed=710,
    )

    local = rolling_hills_field(x, y, 810)

    structural = broad * 0.72 + local * 0.28
    variation = (local - 0.5) * 0.025

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


def mainland_badlands_elevation(x, y):
    z_min, z_max = region_elevation_limits("mainland_badlands")
    span = z_max - z_min

    wx, wy = domain_warp(
        x,
        y,
        strength=260.0,
        scale=2600.0,
        seed=44,
    )

    macro = fractal_noise(
        wx, wy,
        base_scale=4200.0,
        octaves=3,
        persistence=0.55,
        seed=201,
    )

    mesas = ridged_noise(
        wx, wy,
        base_scale=1100.0,
        octaves=3,
        lacunarity=2.0,
        gain=0.50,
        seed=202,
    )

    gullies = ridged_noise(
        x, y,
        base_scale=320.0,
        octaves=3,
        lacunarity=2.1,
        gain=0.48,
        seed=203,
    )

    # No floor()/terracing. Mesa character comes from broad
    # plateaus plus ridge/gully contrast.
    plateau = smooth_range(macro, 0.28, 0.76)
    mesa_shape = smooth_range(mesas, 0.35, 0.80)

    structural = (
        plateau * 0.58
        + mesa_shape * 0.30
        + (1.0 - gullies) * 0.12
    )

    # Gully incision is continuous, not stepped.
    incision = (gullies ** 2.2) * span * 0.045

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural
        ) - incision,
        z_min,
        z_max,
    )


def gang_city_elevation(x, y):
    z_min, z_max = region_elevation_limits("gang_city")

    broad = broad_terrain_field(x, y, 1210)
    local = rolling_hills_field(x, y, 1310)

    structural = broad * 0.68 + local * 0.32
    variation = (local - 0.5) * 0.025

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


def central_wilderness_elevation(x, y):
    z_min, z_max = region_elevation_limits("central_wilderness")

    broad = broad_terrain_field(x, y, 1410)
    hills = rolling_hills_field(x, y, 1510)
    detail = erosion_field(x, y, 1610)

    structural = (
        broad * 0.58
        + hills * 0.34
        + detail * 0.08
    )

    variation = (detail - 0.5) * 0.04

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


def southern_coastline_elevation(x, y):
    z_min, z_max = region_elevation_limits("southern_coastline")

    broad = fractal_noise(
        x, y,
        base_scale=6000.0,
        octaves=3,
        persistence=0.55,
        seed=1710,
    )

    coastal_hills = fractal_noise(
        x, y,
        base_scale=1600.0,
        octaves=3,
        persistence=0.50,
        seed=1810,
    )

    structural = broad * 0.74 + coastal_hills * 0.26
    variation = (coastal_hills - 0.5) * 0.035

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


def khara_archipelago_elevation(x, y):
    z_min, z_max = region_elevation_limits("khara_archipelago")

    broad = fractal_noise(
        x, y,
        base_scale=3600.0,
        octaves=3,
        persistence=0.55,
        seed=1910,
    )

    island_mass = fractal_noise(
        x, y,
        base_scale=1500.0,
        octaves=3,
        persistence=0.52,
        seed=2010,
    )

    relief = ridged_noise(
        x, y,
        base_scale=700.0,
        octaves=3,
        lacunarity=2.0,
        gain=0.5,
        seed=2110,
    )

    structural = (
        broad * 0.35
        + island_mass * 0.45
        + relief * 0.20
    )

    variation = (relief - 0.5) * 0.045

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


def abyss_atoll_elevation(x, y):
    z_min, z_max = region_elevation_limits("abyss_atoll")

    broad = fractal_noise(
        x, y,
        base_scale=5000.0,
        octaves=3,
        persistence=0.55,
        seed=2210,
    )

    atoll_relief = fractal_noise(
        x, y,
        base_scale=1800.0,
        octaves=3,
        persistence=0.50,
        seed=2310,
    )

    trench = ridged_noise(
        x, y,
        base_scale=900.0,
        octaves=3,
        lacunarity=2.0,
        gain=0.5,
        seed=2410,
    )

    structural = (
        broad * 0.50
        + atoll_relief * 0.35
        + trench * 0.15
    )

    variation = (trench - 0.5) * 0.035

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


REGION_FUNCTIONS = {
    "karthen_mountains": karthen_mountains_elevation,
    "western_timber": western_timber_elevation,
    "nova_city": nova_city_elevation,
    "mainland_badlands": mainland_badlands_elevation,
    "gang_city": gang_city_elevation,
    "central_wilderness": central_wilderness_elevation,
    "southern_coastline": southern_coastline_elevation,
    "khara_archipelago": khara_archipelago_elevation,
    "abyss_atoll": abyss_atoll_elevation,
}


# ============================================================
# GLOBAL BACKGROUND
# ============================================================

def global_background_elevation(x, y):
    """
    Open-world background.

    It should remain relatively calm because regional functions
    are responsible for strong geographic identities.
    """
    broad = fractal_noise(
        x, y,
        base_scale=10000.0,
        octaves=3,
        persistence=0.55,
        seed=3010,
    )

    hills = fractal_noise(
        x, y,
        base_scale=3500.0,
        octaves=3,
        persistence=0.50,
        seed=3110,
    )

    structural = broad * 0.78 + hills * 0.22

    # Background rises smoothly from GLOBAL_MIN toward SEA_LEVEL.
    return lerp(
        GLOBAL_MIN,
        SEA_LEVEL,
        clamp(structural, 0.0, 1.0),
    )


# ============================================================
# FEATURE CARVING
# ============================================================

def point_segment_distance_3d(px, py, seg_start, seg_end):
    x1, y1, z1 = seg_start
    x2, y2, z2 = seg_end

    dx = x2 - x1
    dy = y2 - y1

    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq <= 1e-6:
        d = math.hypot(px - x1, py - y1)
        return d, z1

    t = (
        (px - x1) * dx
        + (py - y1) * dy
    ) / seg_len_sq

    t = clamp(t, 0.0, 1.0)

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    proj_z = z1 + t * (z2 - z1)

    d = math.hypot(
        px - proj_x,
        py - proj_y,
    )

    return d, proj_z


def evaluate_polyline_carving(
    x,
    y,
    polyline,
    width_m=40.0,
    depth_offset_m=0.0,
):
    if len(polyline) < 2:
        return 0.0, 0.0

    min_dist = float("inf")
    best_target_z = 0.0

    for i in range(len(polyline) - 1):
        d, z = point_segment_distance_3d(
            x,
            y,
            polyline[i],
            polyline[i + 1],
        )

        if d < min_dist:
            min_dist = d
            best_target_z = z

    if min_dist >= width_m:
        return 0.0, best_target_z

    factor = 1.0 - min_dist / width_m
    weight = smootherstep(factor)

    return weight, best_target_z + depth_offset_m


def apply_feature_carving(x, y, base_z):
    final_z = base_z

    # Roads
    infrastructure = WORLD_MASTER.get("infrastructure", {})

    for _, points in infrastructure.items():
        if not isinstance(points, list) or len(points) < 2:
            continue

        w_valley, target_z = evaluate_polyline_carving(
            x,
            y,
            points,
            width_m=120.0,
            depth_offset_m=0.0,
        )

        if w_valley > 0.0:
            effective_target = max(
                target_z,
                base_z - 12.0,
            )

            final_z = lerp(
                final_z,
                effective_target,
                w_valley * 0.7,
            )

        w_bed, target_z_bed = evaluate_polyline_carving(
            x,
            y,
            points,
            width_m=25.0,
            depth_offset_m=-0.5,
        )

        if w_bed > 0.0:
            effective_target = max(
                target_z_bed - 0.5,
                base_z - 12.5,
            )

            final_z = lerp(
                final_z,
                effective_target,
                w_bed,
            )

    # Rivers / hydrology
    hydrology = WORLD_MASTER.get("hydrology", {})

    for _, river_data in hydrology.items():
        points = (
            river_data
            if isinstance(river_data, list)
            else river_data.get("path", [])
        )

        if len(points) < 2:
            continue

        w_bank, bank_z = evaluate_polyline_carving(
            x,
            y,
            points,
            width_m=70.0,
            depth_offset_m=0.0,
        )

        if w_bank > 0.0:
            target_cut = min(final_z, bank_z)

            final_z = lerp(
                final_z,
                target_cut,
                w_bank * 0.8,
            )

        w_bed, bed_z = evaluate_polyline_carving(
            x,
            y,
            points,
            width_m=22.0,
            depth_offset_m=-2.5,
        )

        if w_bed > 0.0:
            target_cut = min(
                final_z,
                bed_z - 2.5,
            )

            final_z = lerp(
                final_z,
                target_cut,
                w_bed,
            )

    return final_z


# ============================================================
# MAIN ELEVATION FUNCTION
# ============================================================

def elevation_at(x, y):
    """
    Single authoritative world-space terrain function.

    IMPORTANT:
    There is no cell lookup here.
    There is no cell boundary logic here.
    There is no mesh-dependent state here.
    """
    x = float(x)
    y = float(y)

    weights = active_region_weights(x, y)

    if not weights:
        z = global_background_elevation(x, y)
        return clamp(
            apply_feature_carving(x, y, z),
            GLOBAL_MIN,
            GLOBAL_MAX,
        )

    regional_z = 0.0

    for region_id, weight in weights:
        terrain_function = REGION_FUNCTIONS.get(region_id)

        if terrain_function is None:
            continue

        regional_z += (
            terrain_function(x, y) * weight
        )

    # IMPORTANT:
    # Do NOT clamp to a moving weighted regional envelope here.
    #
    # That old operation could create artificial plateaus/shelves.
    # The JSON envelope remains authoritative as a safety envelope,
    # while the actual terrain shape is controlled by the continuous
    # landform functions above.
    final_z = apply_feature_carving(
        x,
        y,
        regional_z,
    )

    return clamp(
        final_z,
        GLOBAL_MIN,
        GLOBAL_MAX,
    )


# ============================================================
# KALDAR JUNGLE PROTOTYPE
# ============================================================

def kaldar_jungle_elevation(x, y):
    z_min, z_max = region_elevation_limits("western_timber")

    broad = broad_terrain_field(x, y, 5010)
    hills = rolling_hills_field(x, y, 5110)
    detail = erosion_field(x, y, 5210)

    structural = (
        broad * 0.48
        + hills * 0.40
        + detail * 0.12
    )

    variation = (detail - 0.5) * 0.035

    return clamp(
        terrain_from_normalized(
            z_min, z_max, structural, variation
        ),
        z_min,
        z_max,
    )


def kaldar_elevation_at(x, y):
    return kaldar_jungle_elevation(
        float(x),
        float(y),
    )


# ============================================================
# CELL SAMPLING
# ============================================================

def sample_cell(cell_x, cell_y, spacing=10.0):
    cell_x = int(cell_x)
    cell_y = int(cell_y)
    spacing = float(spacing)

    if spacing <= 0.0:
        raise ValueError("spacing must be greater than zero")

    intervals = int(round(CELL_SIZE / spacing))

    if not math.isclose(
        intervals * spacing,
        CELL_SIZE,
        abs_tol=1e-6,
    ):
        raise ValueError(
            "Spacing must divide the configured cell size exactly."
        )

    samples = []

    world_min_x = cell_x * CELL_SIZE
    world_min_y = cell_y * CELL_SIZE

    for iy in range(intervals + 1):
        row = []

        world_y = world_min_y + iy * spacing

        for ix in range(intervals + 1):
            world_x = world_min_x + ix * spacing
            row.append(
                elevation_at(world_x, world_y)
            )

        samples.append(row)

    return samples


def cell_statistics(cell_x, cell_y, spacing=10.0):
    samples = sample_cell(
        cell_x,
        cell_y,
        spacing,
    )

    values = [
        value
        for row in samples
        for value in row
    ]

    minimum = min(values)
    maximum = max(values)
    mean = sum(values) / len(values)

    regions = containing_regions(
        cell_x * CELL_SIZE + CELL_SIZE / 2.0,
        cell_y * CELL_SIZE + CELL_SIZE / 2.0,
    )

    return {
        "cell": [int(cell_x), int(cell_y)],
        "samples": len(values),
        "min_m": minimum,
        "max_m": maximum,
        "mean_m": mean,
        "center_regions": regions,
    }


def compare_shared_boundary(
    cell_a_x,
    cell_a_y,
    cell_b_x,
    cell_b_y,
    spacing=10.0,
):
    ax = int(cell_a_x)
    ay = int(cell_a_y)
    bx = int(cell_b_x)
    by = int(cell_b_y)

    dx = bx - ax
    dy = by - ay

    if abs(dx) + abs(dy) != 1:
        raise ValueError(
            "Cells must share exactly one edge."
        )

    samples_a = sample_cell(ax, ay, spacing)
    samples_b = sample_cell(bx, by, spacing)

    differences = []

    if dx == 1:
        for row_a, row_b in zip(samples_a, samples_b):
            differences.append(
                abs(row_a[-1] - row_b[0])
            )

    elif dx == -1:
        for row_a, row_b in zip(samples_a, samples_b):
            differences.append(
                abs(row_a[0] - row_b[-1])
            )

    elif dy == 1:
        differences.extend(
            abs(a - b)
            for a, b in zip(
                samples_a[-1],
                samples_b[0],
            )
        )

    else:
        differences.extend(
            abs(a - b)
            for a, b in zip(
                samples_a[0],
                samples_b[-1],
            )
        )

    return max(differences)


# ============================================================
# CONTINUITY / SLOPE TESTS
# ============================================================

def finite_difference_gradient(x, y, step=1.0):
    """
    Approximate gradient in m/m.
    """
    dx = (
        elevation_at(x + step, y)
        - elevation_at(x - step, y)
    ) / (2.0 * step)

    dy = (
        elevation_at(x, y + step)
        - elevation_at(x, y - step)
    ) / (2.0 * step)

    return dx, dy


def gradient_magnitude(x, y, step=1.0):
    gx, gy = finite_difference_gradient(
        x, y, step
    )
    return math.hypot(gx, gy)


def compare_gradient_across_boundary(
    x,
    y,
    axis="x",
    offset=5.0,
    gradient_step=1.0,
):
    """
    Compare terrain gradient immediately on both sides of a
    coordinate line.

    This does NOT require the gradient to be identical. It is
    intended to expose pathological slope jumps.
    """
    if axis == "x":
        left = finite_difference_gradient(
            x - offset,
            y,
            gradient_step,
        )
        right = finite_difference_gradient(
            x + offset,
            y,
            gradient_step,
        )
    elif axis == "y":
        left = finite_difference_gradient(
            x,
            y - offset,
            gradient_step,
        )
        right = finite_difference_gradient(
            x,
            y + offset,
            gradient_step,
        )
    else:
        raise ValueError("axis must be 'x' or 'y'")

    return math.hypot(
        left[0] - right[0],
        left[1] - right[1],
    )


# ============================================================
# CLI TEST SUITE
# ============================================================

def run_tests():
    print("\nSHADOWS OF THE FALLEN")
    print("CONTINUOUS WORLD ELEVATION V2 VERIFICATION")
    print("=" * 62)

    print("\nWORLD CONFIGURATION")
    print(f"Global envelope : {GLOBAL_MIN:.2f} m → {GLOBAL_MAX:.2f} m")
    print(f"Sea level       : {SEA_LEVEL:.2f} m")
    print(f"Cell size       : {CELL_SIZE:.2f} m")

    # --------------------------------------------------------
    # Determinism
    # --------------------------------------------------------
    print("\n1. DETERMINISM")

    deterministic_points = [
        (0.0, 0.0),
        (500.0, 500.0),
        (-1000.0, 750.0),
        (1234.5, -987.25),
    ]

    deterministic_failures = 0

    for x, y in deterministic_points:
        a = elevation_at(x, y)
        b = elevation_at(x, y)

        diff = abs(a - b)

        print(
            f"({x:9.2f}, {y:9.2f}) "
            f"z={a:9.3f} m "
            f"diff={diff:.12f}"
        )

        if diff > 1e-12:
            deterministic_failures += 1

    print(
        "STATUS:",
        "PASS" if deterministic_failures == 0 else "FAIL"
    )

    # --------------------------------------------------------
    # Shared cell boundaries
    # --------------------------------------------------------
    print("\n2. SHARED CELL BOUNDARIES")

    boundary_tests = [
        ((0, 0), (1, 0)),
        ((0, 0), (0, 1)),
        ((-1, 0), (0, 0)),
        ((0, -1), (0, 0)),
    ]

    boundary_failures = 0

    for cell_a, cell_b in boundary_tests:
        diff = compare_shared_boundary(
            cell_a[0],
            cell_a[1],
            cell_b[0],
            cell_b[1],
            spacing=10.0,
        )

        print(
            f"CELL_{cell_a[0]:+03d}_{cell_a[1]:+03d} "
            f"↔ CELL_{cell_b[0]:+03d}_{cell_b[1]:+03d} "
            f": max diff = {diff:.12f} m"
        )

        if diff > 1e-9:
            boundary_failures += 1

    print(
        "STATUS:",
        "PASS" if boundary_failures == 0 else "FAIL"
    )

    # --------------------------------------------------------
    # 1 km cell statistics
    # --------------------------------------------------------
    print("\n3. 1 KM CELL ELEVATION STATS")

    cells_to_test = [
        (0, 0),
        (1, 0),
        (-1, 0),
        (0, 1),
        (0, -1),
        (-4, 3),
    ]

    envelope_failures = 0

    for cx, cy in cells_to_test:
        stats = cell_statistics(
            cx,
            cy,
            spacing=10.0,
        )

        print(
            f"CELL_{cx:+03d}_{cy:+03d} | "
            f"min={stats['min_m']:8.2f}m "
            f"max={stats['max_m']:8.2f}m "
            f"mean={stats['mean_m']:8.2f}m | "
            f"regions={', '.join(stats['center_regions']) or 'open_world'}"
        )

        if (
            stats["min_m"] < GLOBAL_MIN - 1e-9
            or stats["max_m"] > GLOBAL_MAX + 1e-9
        ):
            envelope_failures += 1

    print(
        "STATUS:",
        "PASS" if envelope_failures == 0 else "FAIL"
    )

    # --------------------------------------------------------
    # Gradient sanity
    # --------------------------------------------------------
    print("\n4. GRADIENT SANITY")

    gradient_points = [
        (0.0, 0.0),
        (500.0, 500.0),
        (1000.0, 0.0),
        (0.0, 1000.0),
        (-500.0, 500.0),
    ]

    gradient_failures = 0

    for x, y in gradient_points:
        slope = gradient_magnitude(
            x,
            y,
            step=1.0,
        )

        print(
            f"({x:8.1f}, {y:8.1f}) "
            f"slope={slope:.5f} m/m "
            f"({math.degrees(math.atan(slope)):.2f}°)"
        )

        # 2.0 m/m is ~63.4 degrees. This is a diagnostic ceiling,
        # not a geological rule.
        if slope > 2.0:
            gradient_failures += 1

    print(
        "STATUS:",
        "PASS" if gradient_failures == 0 else "REVIEW"
    )

    # --------------------------------------------------------
    # Cell-edge slope continuity
    # --------------------------------------------------------
    print("\n5. CELL-EDGE SLOPE CONTINUITY")

    edge_tests = [
        (1000.0, 500.0, "x"),
        (-1000.0, 500.0, "x"),
        (500.0, 1000.0, "y"),
        (500.0, -1000.0, "y"),
    ]

    for x, y, axis in edge_tests:
        jump = compare_gradient_across_boundary(
            x,
            y,
            axis=axis,
            offset=5.0,
            gradient_step=1.0,
        )

        print(
            f"{axis.upper()} boundary at "
            f"({x:.1f}, {y:.1f}) : "
            f"gradient delta={jump:.6f} m/m"
        )

    print("\n" + "=" * 62)

    all_core_pass = (
        deterministic_failures == 0
        and boundary_failures == 0
        and envelope_failures == 0
    )

    if all_core_pass:
        print("STATUS: CORE TESTS PASSED.")
        print(
            "The terrain field is deterministic, world-space, "
            "cell-watertight and globally bounded."
        )
    else:
        print("STATUS: CORE TESTS FAILED.")
        print("Do not generate Blender terrain yet.")


if __name__ == "__main__":
    run_tests()
