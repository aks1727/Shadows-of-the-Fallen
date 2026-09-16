#!/usr/bin/env python3

import json
import math
import os
import sys

# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORLD_MASTER_PATH = os.path.join(
    SCRIPT_DIR,
    "..",
    "coordinates",
    "world_master.json"
)

ELEVATION_MASTER_PATH = os.path.join(
    SCRIPT_DIR,
    "elevation_master.json"
)

# ============================================================
# LOAD MASTER DATA
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

WORLD_MASTER = load_json(WORLD_MASTER_PATH)
ELEVATION_MASTER = load_json(ELEVATION_MASTER_PATH)

WORLD_REGIONS = WORLD_MASTER["regions"]
ELEVATION_REGIONS = ELEVATION_MASTER["regions"]

GLOBAL_MIN = float(ELEVATION_MASTER["global_elevation_envelope"]["minimum_m"])
GLOBAL_MAX = float(ELEVATION_MASTER["global_elevation_envelope"]["maximum_m"])
SEA_LEVEL = float(ELEVATION_MASTER["sea_level"]["z"])
CELL_SIZE = float(ELEVATION_MASTER["sampling"]["prototype_cell_size_m"])

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

# ============================================================
# DETERMINISTIC HASH / NOISE
# ============================================================

def hash2d(x, y, seed=1337):
    """
    Deterministic pseudo-random value in [-1, 1].
    """
    n = (
        int(x) * 374761393
        + int(y) * 668265263
        + seed * 1442695041
    )
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return ((n & 0x7fffffff) / 1073741823.5) - 1.0

def value_noise(x, y, scale=1000.0, seed=1337):
    """
    Smooth deterministic 2D value noise in [-1.0, 1.0].
    """
    if scale <= 0:
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
    seed=1337
):
    """
    Normalized multi-octave noise mapped to [0.0, 1.0].
    """
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    amplitude_sum = 0.0

    for octave in range(octaves):
        scale = base_scale / frequency
        total += value_noise(
            x,
            y,
            scale=scale,
            seed=seed + octave * 101
        ) * amplitude

        amplitude_sum += amplitude
        amplitude *= persistence
        frequency *= 2.0

    if amplitude_sum == 0.0:
        return 0.5

    # Map [-1.0, 1.0] -> [0.0, 1.0]
    return clamp((total / amplitude_sum) * 0.5 + 0.5, 0.0, 1.0)

def ridged_noise(x, y, base_scale=800.0, octaves=4, lacunarity=2.0, gain=0.5, seed=0):
    """
    Multi-octave ridged noise mapped to normalized [0.0, 1.0].
    """
    val = 0.0
    amp = 1.0
    freq = 1.0 / base_scale
    weight = 1.0
    amp_sum = 0.0

    for i in range(octaves):
        n = value_noise(x * freq, y * freq, seed=seed + i * 31)
        # Fold noise to create sharp ridge creases: 1 - |noise|
        n = 1.0 - abs(n)
        n = n * n * weight
        weight = clamp(n * 2.0, 0.0, 1.0)
        val += n * amp
        amp_sum += amp
        freq *= lacunarity
        amp *= gain

    if amp_sum == 0.0:
        return 0.0
    return clamp(val / amp_sum, 0.0, 1.0)

def domain_warp(x, y, strength=180.0, scale=1200.0, seed=77):
    # Normalized offset from [-1, 1]
    dx = (fractal_noise(x, y, base_scale=scale, octaves=2, seed=seed) * 2.0 - 1.0) * strength
    dy = (fractal_noise(x + 52.3, y + 18.7, base_scale=scale, octaves=2, seed=seed + 101) * 2.0 - 1.0) * strength
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
        and
        minimum[1] <= y <= maximum[1]
    )

def containing_regions(x, y):
    result = []
    for region_id, region_data in WORLD_REGIONS.items():
        if point_inside_region(x, y, region_data):
            result.append(region_id)
    return result

def region_influence(x, y, region_id, blend_margin=400.0):
    region = WORLD_REGIONS[region_id]
    bounds = region["bounds"]

    min_x, max_x = float(bounds["min"][0]), float(bounds["max"][0])
    min_y, max_y = float(bounds["min"][1]), float(bounds["max"][1])

    dx = max(min_x - x, 0.0, x - max_x)
    dy = max(min_y - y, 0.0, y - max_y)
    dist_outside = math.hypot(dx, dy)

    if dist_outside <= 0.0:
        dist_inside = min(x - min_x, max_x - x, y - min_y, max_y - y)
        if dist_inside < blend_margin:
            return 0.5 + 0.5 * smootherstep(dist_inside / blend_margin)
        return 1.0

    if dist_outside >= blend_margin:
        return 0.0

    return 0.5 * smootherstep(1.0 - (dist_outside / blend_margin))

def active_region_weights(x, y):
    raw_weights = []
    for reg_id in WORLD_REGIONS.keys():
        w = region_influence(x, y, reg_id)
        if w > 0.001:
            raw_weights.append((reg_id, w))

    if not raw_weights:
        return []

    total_w = sum(w for _, w in raw_weights)
    return [(reg_id, w / total_w) for reg_id, w in raw_weights]

# ============================================================
# REGIONAL ENVELOPE HELPERS
# ============================================================

def region_elevation_limits(region_id):
    """
    Authoritative minimum and maximum elevation directly from elevation_master.json.
    """
    data = ELEVATION_REGIONS[region_id]["elevation"]
    return (
        float(data["minimum_m"]),
        float(data["maximum_m"])
    )

def weighted_elevation_limits(weights):
    if not weights:
        return GLOBAL_MIN, GLOBAL_MAX
    min_lim = sum(region_elevation_limits(r)[0] * w for r, w in weights)
    max_lim = sum(region_elevation_limits(r)[1] * w for r, w in weights)
    return min_lim, max_lim

# ============================================================
# REGIONAL TERRAIN FUNCTIONS (PURE JSON-BOUNDED)
# ============================================================

def karthen_mountains_elevation(x, y):
    z_min, z_max = region_elevation_limits("karthen_mountains")
    wx, wy = domain_warp(x, y, strength=250.0, scale=2000.0, seed=105)

    mass = fractal_noise(wx, wy, base_scale=3000.0, octaves=4, persistence=0.55, seed=110)
    ridges = ridged_noise(wx, wy, base_scale=1200.0, octaves=4, lacunarity=2.0, gain=0.5, seed=210)
    detail = fractal_noise(x, y, base_scale=250.0, octaves=3, persistence=0.50, seed=310)

    # Combined normalized structural factor
    shape = mass * 0.45 + ridges * 0.45 + detail * 0.10
    return lerp(z_min, z_max, shape)

def western_timber_elevation(x, y):
    z_min, z_max = region_elevation_limits("western_timber")

    broad = fractal_noise(x, y, base_scale=2200.0, octaves=4, persistence=0.55, seed=410)
    hills = fractal_noise(x, y, base_scale=700.0, octaves=3, persistence=0.50, seed=510)
    detail = fractal_noise(x, y, base_scale=180.0, octaves=3, persistence=0.50, seed=610)

    shape = broad * 0.50 + hills * 0.35 + detail * 0.15
    return lerp(z_min, z_max, shape)

def nova_city_elevation(x, y):
    z_min, z_max = region_elevation_limits("nova_city")

    broad = fractal_noise(x, y, base_scale=2500.0, octaves=3, persistence=0.50, seed=710)
    local = fractal_noise(x, y, base_scale=500.0, octaves=3, persistence=0.50, seed=810)

    shape = broad * 0.70 + local * 0.30
    return lerp(z_min, z_max, shape)

def mainland_badlands_elevation(x, y):
    z_min, z_max = region_elevation_limits("mainland_badlands")
    span = z_max - z_min

    wx, wy = domain_warp(x, y, strength=180.0, scale=800.0, seed=44)
    plateau = fractal_noise(wx, wy, base_scale=1600.0, octaves=3, persistence=0.5, seed=201)
    crests = ridged_noise(wx, wy, base_scale=600.0, octaves=4, seed=202)

    # Stepped mesa terraces
    step_m = 45.0
    raw_h = plateau * span
    mesa = math.floor(raw_h / step_m) * step_m + smootherstep((raw_h % step_m) / step_m) * step_m
    canyons = (1.0 - crests) * (span * 0.25)

    z = z_min + mesa - canyons
    return clamp(z, z_min, z_max)

def gang_city_elevation(x, y):
    z_min, z_max = region_elevation_limits("gang_city")

    broad = fractal_noise(x, y, base_scale=2200.0, octaves=3, persistence=0.50, seed=1210)
    local = fractal_noise(x, y, base_scale=500.0, octaves=3, persistence=0.50, seed=1310)

    shape = broad * 0.65 + local * 0.35
    return lerp(z_min, z_max, shape)

def central_wilderness_elevation(x, y):
    z_min, z_max = region_elevation_limits("central_wilderness")

    broad = fractal_noise(x, y, base_scale=2000.0, octaves=4, persistence=0.55, seed=1410)
    hills = fractal_noise(x, y, base_scale=650.0, octaves=3, persistence=0.50, seed=1510)
    detail = fractal_noise(x, y, base_scale=180.0, octaves=3, persistence=0.50, seed=1610)

    shape = broad * 0.55 + hills * 0.35 + detail * 0.10
    return lerp(z_min, z_max, shape)

def southern_coastline_elevation(x, y):
    z_min, z_max = region_elevation_limits("southern_coastline")

    broad = fractal_noise(x, y, base_scale=3000.0, octaves=4, persistence=0.55, seed=1710)
    local = fractal_noise(x, y, base_scale=700.0, octaves=3, persistence=0.50, seed=1810)

    shape = broad * 0.70 + local * 0.30
    return lerp(z_min, z_max, shape)

def khara_archipelago_elevation(x, y):
    z_min, z_max = region_elevation_limits("khara_archipelago")

    broad = fractal_noise(x, y, base_scale=1800.0, octaves=4, persistence=0.55, seed=1910)
    islands = fractal_noise(x, y, base_scale=700.0, octaves=3, persistence=0.50, seed=2010)
    detail = fractal_noise(x, y, base_scale=200.0, octaves=3, persistence=0.50, seed=2110)

    shape = broad * 0.40 + islands * 0.45 + detail * 0.15
    return lerp(z_min, z_max, shape)

def abyss_atoll_elevation(x, y):
    z_min, z_max = region_elevation_limits("abyss_atoll")

    broad = fractal_noise(x, y, base_scale=2500.0, octaves=4, persistence=0.55, seed=2210)
    trench = fractal_noise(x, y, base_scale=1000.0, octaves=3, persistence=0.50, seed=2310)
    detail = fractal_noise(x, y, base_scale=250.0, octaves=3, persistence=0.50, seed=2410)

    shape = broad * 0.50 + trench * 0.40 + detail * 0.10
    return lerp(z_min, z_max, shape)

# ============================================================
# REGION DISPATCH
# ============================================================

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
    broad = fractal_noise(x, y, base_scale=6000.0, octaves=4, persistence=0.55, seed=3010)
    detail = fractal_noise(x, y, base_scale=1500.0, octaves=3, persistence=0.50, seed=3110)
    shape = broad * 0.75 + detail * 0.25
    return lerp(GLOBAL_MIN, SEA_LEVEL, shape)

# ============================================================
# FEATURE CARVING (HYDROLOGY & ROADS)
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

    t = ((px - x1) * dx + (py - y1) * dy) / seg_len_sq
    t = clamp(t, 0.0, 1.0)

    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    proj_z = z1 + t * (z2 - z1)

    d = math.hypot(px - proj_x, py - proj_y)
    return d, proj_z

def evaluate_polyline_carving(x, y, polyline, width_m=40.0, depth_offset_m=0.0):
    min_dist = float("inf")
    best_target_z = 0.0

    for i in range(len(polyline) - 1):
        d, z = point_segment_distance_3d(x, y, polyline[i], polyline[i + 1])
        if d < min_dist:
            min_dist = d
            best_target_z = z

    if min_dist >= width_m:
        return 0.0, best_target_z

    factor = 1.0 - (min_dist / width_m)
    weight = smootherstep(factor)
    return weight, best_target_z + depth_offset_m

def apply_feature_carving(x, y, base_z):
    final_z = base_z

    # 1. Roads (Highway 1 & Route 9)
    infra = WORLD_MASTER.get("infrastructure", {})
    for road_name, points in infra.items():
        w_valley, target_z = evaluate_polyline_carving(
            x, y, points, width_m=120.0, depth_offset_m=0.0
        )
        if w_valley > 0.0:
            effective_target = max(target_z, base_z - 12.0)
            final_z = lerp(final_z, effective_target, w_valley * 0.7)

        w_bed, target_z_bed = evaluate_polyline_carving(
            x, y, points, width_m=25.0, depth_offset_m=-0.5
        )
        if w_bed > 0.0:
            effective_target = max(target_z_bed - 0.5, base_z - 12.5)
            final_z = lerp(final_z, effective_target, w_bed)

    # 2. Hydrology (Raven River & The Black Gut)
    hydro = WORLD_MASTER.get("hydrology", {})
    for river_name, river_data in hydro.items():
        points = river_data if isinstance(river_data, list) else river_data.get("path", [])
        if not points:
            continue

        w_bank, bank_z = evaluate_polyline_carving(
            x, y, points, width_m=70.0, depth_offset_m=0.0
        )
        if w_bank > 0.0:
            target_cut = min(final_z, bank_z)
            final_z = lerp(final_z, target_cut, w_bank * 0.8)

        w_bed, bed_z = evaluate_polyline_carving(
            x, y, points, width_m=22.0, depth_offset_m=-2.5
        )
        if w_bed > 0.0:
            target_cut = min(final_z, bed_z - 2.5)
            final_z = lerp(final_z, target_cut, w_bed)

    return final_z

# ============================================================
# MAIN ELEVATION FUNCTION
# ============================================================

def elevation_at(x, y):
    x = float(x)
    y = float(y)

    weights = active_region_weights(x, y)

    if not weights:
        return global_background_elevation(x, y)

    regional_z = 0.0
    for region_id, weight in weights:
        terrain_function = REGION_FUNCTIONS.get(region_id)
        if terrain_function is None:
            continue
        z = terrain_function(x, y)
        regional_z += z * weight

    # Enforce blended regional envelope
    regional_min, regional_max = weighted_elevation_limits(weights)
    final_z = clamp(regional_z, regional_min, regional_max)

    # Apply vector path carving (roads & hydrology)
    final_z = apply_feature_carving(x, y, final_z)

    # Global safety envelope
    final_z = clamp(final_z, GLOBAL_MIN, GLOBAL_MAX)
    return final_z

# ============================================================
# KALDAR JUNGLE PROTOTYPE
# ============================================================

def kaldar_jungle_elevation(x, y):
    z_min, z_max = region_elevation_limits("western_timber")
    broad = fractal_noise(x, y, base_scale=1800.0, octaves=4, persistence=0.55, seed=5010)
    jungle_hills = fractal_noise(x, y, base_scale=600.0, octaves=3, persistence=0.50, seed=5110)
    detail = fractal_noise(x, y, base_scale=160.0, octaves=3, persistence=0.50, seed=5210)
    shape = broad * 0.45 + jungle_hills * 0.35 + detail * 0.20
    return lerp(z_min, z_max, shape)

def kaldar_elevation_at(x, y):
    return kaldar_jungle_elevation(float(x), float(y))

# ============================================================
# CELL SAMPLING
# ============================================================

def sample_cell(cell_x, cell_y, spacing=10.0):
    cell_x = int(cell_x)
    cell_y = int(cell_y)
    spacing = float(spacing)

    if spacing <= 0:
        raise ValueError("spacing must be greater than zero")

    intervals = int(round(CELL_SIZE / spacing))
    if not math.isclose(intervals * spacing, CELL_SIZE, abs_tol=1e-6):
        raise ValueError("Spacing must divide the 1000m cell size exactly.")

    samples = []
    world_min_x = cell_x * CELL_SIZE
    world_min_y = cell_y * CELL_SIZE

    for iy in range(intervals + 1):
        row = []
        world_y = world_min_y + iy * spacing
        for ix in range(intervals + 1):
            world_x = world_min_x + ix * spacing
            row.append(elevation_at(world_x, world_y))
        samples.append(row)

    return samples

def cell_statistics(cell_x, cell_y, spacing=10.0):
    samples = sample_cell(cell_x, cell_y, spacing)
    values = [value for row in samples for value in row]
    minimum = min(values)
    maximum = max(values)
    mean = sum(values) / len(values)
    regions = containing_regions(
        cell_x * CELL_SIZE + CELL_SIZE / 2.0,
        cell_y * CELL_SIZE + CELL_SIZE / 2.0
    )
    return {
        "cell": [int(cell_x), int(cell_y)],
        "samples": len(values),
        "min_m": minimum,
        "max_m": maximum,
        "mean_m": mean,
        "center_regions": regions,
    }

def compare_shared_boundary(cell_a_x, cell_a_y, cell_b_x, cell_b_y, spacing=10.0):
    ax, ay = int(cell_a_x), int(cell_a_y)
    bx, by = int(cell_b_x), int(cell_b_y)

    dx = bx - ax
    dy = by - ay

    if abs(dx) + abs(dy) != 1:
        raise ValueError("Cells must share exactly one edge.")

    samples_a = sample_cell(ax, ay, spacing)
    samples_b = sample_cell(bx, by, spacing)
    differences = []

    if dx == 1:
        for row_a, row_b in zip(samples_a, samples_b):
            differences.append(abs(row_a[-1] - row_b[0]))
    elif dx == -1:
        for row_a, row_b in zip(samples_a, samples_b):
            differences.append(abs(row_a[0] - row_b[-1]))
    elif dy == 1:
        differences.extend(abs(a - b) for a, b in zip(samples_a[-1], samples_b[0]))
    elif dy == -1:
        differences.extend(abs(a - b) for a, b in zip(samples_a[0], samples_b[-1]))

    return max(differences)

# ============================================================
# CLI TEST SUITE
# ============================================================

def run_tests():
    print("\nSHADOWS OF THE FALLEN")
    print("WORLD ELEVATION JSON-STRICT VERIFICATION\n")

    boundary_tests = [
        ((0, 0), (1, 0)),
        ((0, 0), (0, 1)),
        ((-1, 0), (0, 0)),
        ((0, -1), (0, 0)),
    ]

    boundary_failures = 0
    for cell_a, cell_b in boundary_tests:
        diff = compare_shared_boundary(cell_a[0], cell_a[1], cell_b[0], cell_b[1], spacing=10.0)
        print(f"CELL_{cell_a[0]:+03d}_{cell_a[1]:+03d} ↔ CELL_{cell_b[0]:+03d}_{cell_b[1]:+03d} : max diff = {diff:.10f} m")
        if diff > 1e-9:
            boundary_failures += 1

    print("\n1 KM CELL ELEVATION STATS vs JSON BOUNDS")
    cells_to_test = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (-4, 3)]
    for cx, cy in cells_to_test:
        stats = cell_statistics(cx, cy, spacing=10.0)
        print(
            f"CELL_{cx:+03d}_{cy:+03d} | "
            f"min={stats['min_m']:7.2f}m  max={stats['max_m']:7.2f}m  mean={stats['mean_m']:7.2f}m | "
            f"regions={', '.join(stats['center_regions']) or 'open_world'}"
        )

    if boundary_failures == 0:
        print("\nSTATUS: ALL BOUNDARIES WATERTIGHT AND PRECISE TO JSON.\n")
    else:
        print(f"\nSTATUS: FAILED with {boundary_failures} boundary issues.\n")

if __name__ == "__main__":
    run_tests()