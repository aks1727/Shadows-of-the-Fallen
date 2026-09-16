#!/usr/bin/env python3

import json
import math
import os
import re
import sys


# ============================================================
# Shadows of the Fallen
# 03_cell_manifest_validator.py
#
# PURPOSE:
# Validate the global 1 km cell coordinate system.
#
# SOURCE OF TRUTH:
#   world_master.json -> world/region bounds
#   cell_grid.json    -> global cell manifest
#
# VALIDATES:
#   1. Manifest structure
#   2. Grid dimensions
#   3. Cell IDs
#   4. Cell coordinates
#   5. Cell bounds
#   6. Cell centers
#   7. 1 km cell size
#   8. Neighbor continuity
#   9. Region membership
#  10. Filesystem CELL_* directories
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
print(f"BASE_DIR: {BASE_DIR}")
COORDINATES_DIR = os.path.join(BASE_DIR, "00_WORLD_MASTER/coordinates")

WORLD_MASTER_PATH = os.path.join(
    COORDINATES_DIR,
    "world_master.json"
)

CELL_GRID_PATH = os.path.join(
    COORDINATES_DIR,
    "cell_grid.json"
)

CELLS_DIR = os.path.join(
    BASE_DIR,
    "00_WORLD_MASTER/cells"
)


CELL_SIZE = 1000.0

CELL_ID_PATTERN = re.compile(
    r"^CELL_([+-]\d+)_([+-]\d+)$"
)


# ------------------------------------------------------------
# VALIDATION STATE
# ------------------------------------------------------------

errors = []
warnings = []

checks_passed = 0


def error(message):
    errors.append(message)


def warning(message):
    warnings.append(message)


def check(condition, message):
    global checks_passed

    if condition:
        checks_passed += 1
    else:
        error(message)


def nearly_equal(a, b, tolerance=1e-6):
    return abs(float(a) - float(b)) <= tolerance


# ------------------------------------------------------------
# LOAD JSON
# ------------------------------------------------------------

print()
print("=" * 70)
print("SHADOWS OF THE FALLEN")
print("03_CELL_MANIFEST_VALIDATOR")
print("=" * 70)
print()

print("[1/10] Loading source files...")

if not os.path.isfile(WORLD_MASTER_PATH):
    error(f"Missing world_master.json: {WORLD_MASTER_PATH}")

if not os.path.isfile(CELL_GRID_PATH):
    error(f"Missing cell_grid.json: {CELL_GRID_PATH}")

if errors:
    print("FAIL")
    for e in errors:
        print("  ERROR:", e)
    sys.exit(1)


try:
    with open(WORLD_MASTER_PATH, "r", encoding="utf-8") as f:
        world_master = json.load(f)
except Exception as exc:
    error(f"Could not read world_master.json: {exc}")
    world_master = None


try:
    with open(CELL_GRID_PATH, "r", encoding="utf-8") as f:
        cell_grid = json.load(f)
except Exception as exc:
    error(f"Could not read cell_grid.json: {exc}")
    cell_grid = None


if errors:
    print("FAIL")
    for e in errors:
        print("  ERROR:", e)
    sys.exit(1)

print("  OK")


# ------------------------------------------------------------
# 1. BASIC STRUCTURE
# ------------------------------------------------------------

print()
print("[2/10] Checking manifest structure...")

check(
    isinstance(cell_grid, dict),
    "cell_grid.json root must be an object"
)

check(
    "grid" in cell_grid,
    "Missing 'grid' section"
)

check(
    "cells" in cell_grid,
    "Missing 'cells' section"
)

check(
    isinstance(cell_grid.get("cells"), dict),
    "'cells' must be an object"
)

check(
    cell_grid.get("grid", {}).get("cell_size_m") == CELL_SIZE,
    f"Cell size must be exactly {CELL_SIZE} m"
)

print("  OK")


# ------------------------------------------------------------
# 2. READ GRID METADATA
# ------------------------------------------------------------

print()
print("[3/10] Checking grid metadata...")

grid = cell_grid["grid"]

min_cell = grid.get("min_cell")
max_cell = grid.get("max_cell")
dimensions = grid.get("dimensions")
total_cells = grid.get("total_cells")

check(
    isinstance(min_cell, list) and len(min_cell) == 2,
    "grid.min_cell must be [x, y]"
)

check(
    isinstance(max_cell, list) and len(max_cell) == 2,
    "grid.max_cell must be [x, y]"
)

check(
    isinstance(dimensions, list) and len(dimensions) == 2,
    "grid.dimensions must be [width, height]"
)

check(
    isinstance(total_cells, int),
    "grid.total_cells must be an integer"
)

expected_width = max_cell[0] - min_cell[0] + 1
expected_height = max_cell[1] - min_cell[1] + 1
expected_total = expected_width * expected_height

check(
    dimensions == [expected_width, expected_height],
    f"Grid dimensions incorrect: expected "
    f"[{expected_width}, {expected_height}], got {dimensions}"
)

check(
    total_cells == expected_total,
    f"Grid total_cells incorrect: expected "
    f"{expected_total}, got {total_cells}"
)

print(f"  Grid range : X {min_cell[0]} → {max_cell[0]}")
print(f"               Y {min_cell[1]} → {max_cell[1]}")
print(f"  Dimensions : {dimensions[0]} × {dimensions[1]}")
print(f"  Total      : {total_cells}")
print("  OK")


# ------------------------------------------------------------
# 3. CELL COUNT
# ------------------------------------------------------------

print()
print("[4/10] Checking cell count...")

cells = cell_grid["cells"]

check(
    len(cells) == total_cells,
    f"Manifest contains {len(cells)} cells, "
    f"but grid declares {total_cells}"
)

print(f"  Manifest cells: {len(cells)}")
print("  OK")


# ------------------------------------------------------------
# 4. CELL IDS + COORDINATES
# ------------------------------------------------------------

print()
print("[5/10] Checking cell IDs and coordinates...")

expected_ids = set()
actual_ids = set()

for y in range(min_cell[1], max_cell[1] + 1):

    for x in range(min_cell[0], max_cell[0] + 1):

        expected_id = f"CELL_{x:+03d}_{y:+03d}"
        expected_ids.add(expected_id)


for cell_id, cell in cells.items():

    actual_ids.add(cell_id)

    match = CELL_ID_PATTERN.match(cell_id)

    check(
        match is not None,
        f"Malformed cell ID: {cell_id}"
    )

    if not match:
        continue

    id_x = int(match.group(1))
    id_y = int(match.group(2))

    grid_data = cell.get("grid")

    check(
        isinstance(grid_data, dict),
        f"{cell_id}: missing grid data"
    )

    if isinstance(grid_data, dict):

        check(
            grid_data.get("x") == id_x,
            f"{cell_id}: grid.x does not match ID"
        )

        check(
            grid_data.get("y") == id_y,
            f"{cell_id}: grid.y does not match ID"
        )

        check(
            min_cell[0] <= id_x <= max_cell[0],
            f"{cell_id}: X outside global grid"
        )

        check(
            min_cell[1] <= id_y <= max_cell[1],
            f"{cell_id}: Y outside global grid"
        )


missing_ids = expected_ids - actual_ids
unexpected_ids = actual_ids - expected_ids

for cell_id in sorted(missing_ids):
    error(f"Missing manifest cell: {cell_id}")

for cell_id in sorted(unexpected_ids):
    error(f"Unexpected manifest cell: {cell_id}")


print(f"  Expected IDs : {len(expected_ids)}")
print(f"  Actual IDs   : {len(actual_ids)}")
print(f"  Missing      : {len(missing_ids)}")
print(f"  Unexpected   : {len(unexpected_ids)}")
print("  OK")


# ------------------------------------------------------------
# 5. CELL BOUNDS
# ------------------------------------------------------------

print()
print("[6/10] Checking cell bounds...")

for cell_id, cell in cells.items():

    match = CELL_ID_PATTERN.match(cell_id)

    if not match:
        continue

    x = int(match.group(1))
    y = int(match.group(2))

    expected_min_x = x * CELL_SIZE
    expected_min_y = y * CELL_SIZE

    expected_max_x = expected_min_x + CELL_SIZE
    expected_max_y = expected_min_y + CELL_SIZE

    bounds = cell.get("bounds", {})

    actual_min = bounds.get("min")
    actual_max = bounds.get("max")

    check(
        isinstance(actual_min, list) and len(actual_min) == 2,
        f"{cell_id}: invalid bounds.min"
    )

    check(
        isinstance(actual_max, list) and len(actual_max) == 2,
        f"{cell_id}: invalid bounds.max"
    )

    if not actual_min or not actual_max:
        continue

    check(
        nearly_equal(actual_min[0], expected_min_x),
        f"{cell_id}: min X incorrect"
    )

    check(
        nearly_equal(actual_min[1], expected_min_y),
        f"{cell_id}: min Y incorrect"
    )

    check(
        nearly_equal(actual_max[0], expected_max_x),
        f"{cell_id}: max X incorrect"
    )

    check(
        nearly_equal(actual_max[1], expected_max_y),
        f"{cell_id}: max Y incorrect"
    )

    check(
        nearly_equal(actual_max[0] - actual_min[0], CELL_SIZE),
        f"{cell_id}: width is not 1000 m"
    )

    check(
        nearly_equal(actual_max[1] - actual_min[1], CELL_SIZE),
        f"{cell_id}: height is not 1000 m"
    )

print("  OK")


# ------------------------------------------------------------
# 6. CELL CENTERS
# ------------------------------------------------------------

print()
print("[7/10] Checking cell centers...")

for cell_id, cell in cells.items():

    bounds = cell.get("bounds", {})
    actual_min = bounds.get("min")
    actual_max = bounds.get("max")
    center = cell.get("center")

    if not actual_min or not actual_max:
        continue

    check(
        isinstance(center, list) and len(center) == 2,
        f"{cell_id}: invalid center"
    )

    if not isinstance(center, list) or len(center) != 2:
        continue

    expected_center_x = (
        actual_min[0] + actual_max[0]
    ) / 2.0

    expected_center_y = (
        actual_min[1] + actual_max[1]
    ) / 2.0

    check(
        nearly_equal(center[0], expected_center_x),
        f"{cell_id}: center X incorrect"
    )

    check(
        nearly_equal(center[1], expected_center_y),
        f"{cell_id}: center Y incorrect"
    )

print("  OK")


# ------------------------------------------------------------
# 7. NEIGHBOR CONTINUITY
# ------------------------------------------------------------

print()
print("[8/10] Checking neighboring cell continuity...")

neighbor_checks = 0

for cell_id, cell in cells.items():

    match = CELL_ID_PATTERN.match(cell_id)

    if not match:
        continue

    x = int(match.group(1))
    y = int(match.group(2))

    bounds = cell.get("bounds", {})

    if "max" not in bounds:
        continue

    max_xy = bounds["max"]

    # East neighbor
    east_id = f"CELL_{x + 1:+03d}_{y:+03d}"

    if east_id in cells:

        east_bounds = cells[east_id]["bounds"]

        check(
            nearly_equal(
                max_xy[0],
                east_bounds["min"][0]
            ),
            f"{cell_id} → {east_id}: X edge mismatch"
        )

        check(
            nearly_equal(
                bounds["min"][1],
                east_bounds["min"][1]
            ),
            f"{cell_id} → {east_id}: Y alignment mismatch"
        )

        neighbor_checks += 1

    # North neighbor
    north_id = f"CELL_{x:+03d}_{y + 1:+03d}"

    if north_id in cells:

        north_bounds = cells[north_id]["bounds"]

        check(
            nearly_equal(
                max_xy[1],
                north_bounds["min"][1]
            ),
            f"{cell_id} → {north_id}: Y edge mismatch"
        )

        check(
            nearly_equal(
                bounds["min"][0],
                north_bounds["min"][0]
            ),
            f"{cell_id} → {north_id}: X alignment mismatch"
        )

        neighbor_checks += 1


print(f"  Shared-edge checks: {neighbor_checks}")
print("  OK")


# ------------------------------------------------------------
# 8. REGION MEMBERSHIP
# ------------------------------------------------------------

print()
print("[9/10] Checking region membership...")

regions = world_master.get("regions", {})

for cell_id, cell in cells.items():

    bounds = cell.get("bounds", {})

    if "min" not in bounds or "max" not in bounds:
        continue

    cell_min_x = bounds["min"][0]
    cell_min_y = bounds["min"][1]
    cell_max_x = bounds["max"][0]
    cell_max_y = bounds["max"][1]

    expected_regions = []

    for region_id, region in regions.items():

        region_bounds = region.get("bounds")

        if not region_bounds:
            continue

        region_min_x = region_bounds["min"][0]
        region_min_y = region_bounds["min"][1]
        region_max_x = region_bounds["max"][0]
        region_max_y = region_bounds["max"][1]

        intersects = (
            cell_min_x < region_max_x
            and cell_max_x > region_min_x
            and cell_min_y < region_max_y
            and cell_max_y > region_min_y
        )

        if intersects:
            expected_regions.append(region_id)

    actual_regions = cell.get("regions", [])

    check(
        sorted(actual_regions) == sorted(expected_regions),
        f"{cell_id}: region membership mismatch. "
        f"Expected {expected_regions}, got {actual_regions}"
    )

print("  OK")


# ------------------------------------------------------------
# 9. FILESYSTEM CELLS
# ------------------------------------------------------------

print()
print("[10/10] Checking filesystem CELL_* directories...")

filesystem_ids = set()

if not os.path.isdir(CELLS_DIR):

    warning(
        f"Cells directory does not exist: {CELLS_DIR}"
    )

else:

    for name in os.listdir(CELLS_DIR):

        path = os.path.join(CELLS_DIR, name)

        if not os.path.isdir(path):
            continue

        if CELL_ID_PATTERN.match(name):
            filesystem_ids.add(name)


missing_dirs = expected_ids - filesystem_ids
extra_dirs = filesystem_ids - expected_ids

for cell_id in sorted(missing_dirs):
    error(f"Missing filesystem cell directory: {cell_id}")

for cell_id in sorted(extra_dirs):
    error(f"Filesystem cell has no manifest entry: {cell_id}")


print(f"  Manifest cells : {len(expected_ids)}")
print(f"  Disk cells     : {len(filesystem_ids)}")
print(f"  Missing dirs   : {len(missing_dirs)}")
print(f"  Extra dirs     : {len(extra_dirs)}")


# ------------------------------------------------------------
# FINAL REPORT
# ------------------------------------------------------------

print()
print("=" * 70)
print("VALIDATION REPORT")
print("=" * 70)

print()
print(f"Checks passed : {checks_passed}")
print(f"Errors        : {len(errors)}")
print(f"Warnings      : {len(warnings)}")

if warnings:
    print()
    print("WARNINGS:")

    for w in warnings:
        print("  WARNING:", w)

if errors:

    print()
    print("ERRORS:")

    for e in errors:
        print("  ERROR:", e)

    print()
    print("STATUS: FAILED")
    print("=" * 70)
    print()

    sys.exit(1)

print()
print("STATUS: PASSED")
print()
print("Global 1 km coordinate grid is internally consistent.")
print("Filesystem cell layout matches the manifest.")
print("Safe to proceed to terrain generation.")
print("=" * 70)
print()

sys.exit(0)