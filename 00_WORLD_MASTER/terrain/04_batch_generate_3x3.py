#!/usr/bin/env python3
import json
import math
import os
import sys
import time
import bpy

# ============================================================
# PATH SETUP & DYNAMIC IMPORTS
# ============================================================

def find_project_root():
    candidate = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else os.getcwd()
    while candidate and candidate != os.path.dirname(candidate):
        if os.path.exists(os.path.join(candidate, "00_WORLD_MASTER")):
            return candidate
        candidate = os.path.dirname(candidate)
    return "/home/aks1727/programming/gamedev/Shadows-of-the-Fallen"

PROJECT_ROOT = find_project_root()
TERRAIN_SCRIPT_DIR = os.path.join(PROJECT_ROOT, "00_WORLD_MASTER", "terrain")
WORLD_MASTER_PATH = os.path.join(PROJECT_ROOT, "00_WORLD_MASTER", "coordinates", "world_master.json")
ELEVATION_MASTER_PATH = os.path.join(PROJECT_ROOT, "00_WORLD_MASTER", "elevation", "elevation_master.json")

if TERRAIN_SCRIPT_DIR not in sys.path:
    sys.path.insert(0, TERRAIN_SCRIPT_DIR)

# Flush module caches to guarantee changes in elevation_function register
sys.modules.pop("elevation_function", None)
sys.modules.pop("cell_generator", None)
sys.modules.pop("03_terrain_generate_cell", None)

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cell_generator", 
        os.path.join(TERRAIN_SCRIPT_DIR, "03_terrain_generate_cell.py")
    )
    generator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator_module)
except Exception as exc:
    raise ImportError(f"Failed to load generator module: {exc}")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

WORLD_MASTER = load_json(WORLD_MASTER_PATH)
ELEVATION_MASTER = load_json(ELEVATION_MASTER_PATH)
CELL_SIZE = float(ELEVATION_MASTER["sampling"]["prototype_cell_size_m"])


# ============================================================
# BOUNDS CALCULATOR
# ============================================================

def get_region_cell_bounds(region_id):
    regions = WORLD_MASTER.get("regions", {})
    if region_id not in regions:
        valid = ", ".join(regions.keys())
        raise ValueError(f"Unknown region '{region_id}'. Valid regions: {valid}")
    
    bounds = regions[region_id]["bounds"]
    min_cx = math.floor(float(bounds["min"][0]) / CELL_SIZE)
    max_cx = math.floor(float(bounds["max"][0]) / CELL_SIZE)
    min_cy = math.floor(float(bounds["min"][1]) / CELL_SIZE)
    max_cy = math.floor(float(bounds["max"][1]) / CELL_SIZE)
    
    return min_cx, max_cx, min_cy, max_cy


def clear_terrain_collection():
    terrain_coll = bpy.data.collections.get("TERRAIN")
    if not terrain_coll:
        return
    
    for obj in list(terrain_coll.objects):
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh:
            bpy.data.meshes.remove(mesh)


# ============================================================
# BATCH GENERATION EXECUTION
# ============================================================
def run_batch(
    min_cx,
    max_cx,
    min_cy,
    max_cy,
    clear_existing=False
):

    expected_cells = [
        (cx, cy)
        for cy in range(min_cy, max_cy + 1)
        for cx in range(min_cx, max_cx + 1)
    ]

    total_cells = len(expected_cells)

    print()
    print("=" * 70)
    print(
        f"[SOTF] Starting Generation: "
        f"{total_cells} Cells"
    )

    print(
        f"       Grid Bounds: "
        f"X [{min_cx:+03d} to {max_cx:+03d}], "
        f"Y [{min_cy:+03d} to {max_cy:+03d}]"
    )

    print("=" * 70)

    if clear_existing:

        print(
            "[SOTF] Clearing previous terrain objects..."
        )

        clear_terrain_collection()

    generated = []
    failed = []

    start_time = time.time()

    # --------------------------------------------------------
    # Blender progress bar
    # --------------------------------------------------------

    wm = bpy.context.window_manager

    wm.progress_begin(
        0.0,
        float(total_cells)
    )

    try:

        for index, (cx, cy) in enumerate(
            expected_cells,
            start=1
        ):

            cell_id = (
                f"CELL_{cx:+03d}_{cy:+03d}"
            )

            cell_start = time.time()

            try:

                generator_module.generate_terrain_cell(
                    cx,
                    cy
                )

                elapsed = (
                    time.time()
                    -
                    cell_start
                )

                generated.append(
                    (cx, cy)
                )

                print(
                    f"[{index:03d}/{total_cells:03d}] "
                    f"{cell_id} "
                    f"OK "
                    f"({elapsed:.2f}s)"
                )

            except Exception as err:

                failed.append(
                    (
                        cx,
                        cy,
                        str(err)
                    )
                )

                print()
                print(
                    f"[ERROR] {cell_id} FAILED"
                )

                print(
                    f"        {err}"
                )

                print()

            # ------------------------------------------------
            # REAL-TIME BLENDER PROGRESS
            # ------------------------------------------------

            wm.progress_update(
                float(index)
            )

            # Force Blender UI to redraw between cells.
            for window in bpy.context.window_manager.windows:

                screen = window.screen

                if screen:

                    for area in screen.areas:

                        area.tag_redraw()

    finally:

        wm.progress_end()

    total_time = (
        time.time()
        -
        start_time
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)

    print(
        f"[STATUS] Batch Complete "
        f"in {total_time:.2f}s"
    )

    print(
        f"  Success: "
        f"{len(generated)}/{total_cells}"
    )

    print(
        f"  Failed : "
        f"{len(failed)}/{total_cells}"
    )

    # --------------------------------------------------------
    # Missing-cell verification
    # --------------------------------------------------------

    generated_set = set(generated)

    missing = [
        (cx, cy)
        for cx, cy in expected_cells
        if (cx, cy) not in generated_set
    ]

    if missing:

        print()
        print(
            "[ERROR] MISSING CELLS:"
        )

        for cx, cy in missing:

            print(
                f"    CELL_{cx:+03d}_{cy:+03d}"
            )

    # --------------------------------------------------------
    # Error details
    # --------------------------------------------------------

    if failed:

        print()
        print(
            "[ERROR DETAILS]"
        )

        for cx, cy, err in failed:

            print(
                f"    CELL_{cx:+03d}_{cy:+03d}: "
                f"{err}"
            )

    print("=" * 70)
    print()

    return (
        len(failed) == 0
        and
        len(missing) == 0
    )


## ============================================================
# INTERACTIVE REGION SELECTION
# ============================================================

def list_regions():
    regions = list(WORLD_MASTER.get("regions", {}).keys())
    print("\n" + "=" * 60)
    print("  SHADOWS OF THE FALLEN - AVAILABLE REGIONS")
    print("=" * 60)
    print("  [0] Prototype 3x3 Cluster (Interchange: -1 to +1)")
    for i, reg_id in enumerate(regions, 1):
        min_cx, max_cx, min_cy, max_cy = get_region_cell_bounds(reg_id)
        count = (max_cx - min_cx + 1) * (max_cy - min_cy + 1)
        print(f"  [{i}] {reg_id.ljust(22)} ({count} cells: X[{min_cx}..{max_cx}], Y[{min_cy}..{max_cy}])")
    print("=" * 60)
    print("To bake, call: bake(<number>)   e.g. bake(1) or bake(0)\n")


def bake(choice=0, clear_existing=False):
    regions = list(WORLD_MASTER.get("regions", {}).keys())
    if choice == 0:
        run_batch(-1, 1, -1, 1, clear_existing=clear_existing)
        return

    if 1 <= choice <= len(regions):
        selected = regions[choice - 1]
        min_cx, max_cx, min_cy, max_cy = get_region_cell_bounds(selected)
        run_batch(min_cx, max_cx, min_cy, max_cy, clear_existing=clear_existing)
    else:
        print(f"[ERROR] Choice {choice} out of range (0 to {len(regions)}).")


if __name__ == "__main__":
    list_regions()