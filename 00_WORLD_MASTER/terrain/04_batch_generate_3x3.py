#!/usr/bin/env python3
import os
import sys
import time
import bpy

# ============================================================
# CONFIGURATION
# ============================================================

RANGE_X = (-1, 1)  # X: -1, 0, +1
RANGE_Y = (-1, 1)  # Y: -1, 0, +1

# ============================================================
# PATH SETUP & IMPORT
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

if TERRAIN_SCRIPT_DIR not in sys.path:
    sys.path.insert(0, TERRAIN_SCRIPT_DIR)

# Clear module cache so changes in elevation_function always register
sys.modules.pop("elevation_function", None)
sys.modules.pop("03_generate_terrain_cell", None)

try:
    import importlib
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cell_generator", 
        os.path.join(TERRAIN_SCRIPT_DIR, "03_terrain_generate_cell.py")
    )
    generator_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator_module)
except Exception as exc:
    raise ImportError(f"Failed to load generator module: {exc}")


# ============================================================
# BATCH EXECUTION
# ============================================================

def run_batch():
    total_cells = (RANGE_X[1] - RANGE_X[0] + 1) * (RANGE_Y[1] - RANGE_Y[0] + 1)
    print("\n" + "=" * 60)
    print(f"[SOTF] Starting Batch Generation: {total_cells} Cells (3x3)")
    print("=" * 60)

    start_time = time.time()
    generated_count = 0
    failed_cells = []

    for cy in range(RANGE_Y[0], RANGE_Y[1] + 1):
        for cx in range(RANGE_X[0], RANGE_X[1] + 1):
            cell_id = f"CELL_{cx:+03d}_{cy:+03d}"
            cell_start = time.time()
            try:
                generator_module.generate_terrain_cell(cx, cy)
                elapsed = time.time() - cell_start
                generated_count += 1
                print(f"  --> [{generated_count}/{total_cells}] {cell_id} OK ({elapsed:.2f}s)")
            except Exception as err:
                print(f"  [ERROR] {cell_id} FAILED: {err}")
                failed_cells.append((cell_id, str(err)))

    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"[STATUS] 3x3 Batch Complete in {total_time:.2f}s")
    print(f"  Success: {generated_count}/{total_cells}")
    if failed_cells:
        print(f"  Failures: {len(failed_cells)}")
        for cid, err in failed_cells:
            print(f"    - {cid}: {err}")
    print("=" * 60)


if __name__ == "__main__":
    run_batch()