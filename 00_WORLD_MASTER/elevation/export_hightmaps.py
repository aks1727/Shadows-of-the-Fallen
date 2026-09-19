#!/usr/bin/env python3
"""
Standalone Unity Heightmap Exporter for Shadows of the Fallen
Bypasses Blender entirely and samples elevation_function.py directly.
"""

import os
import sys
import json
import math
import struct
import numpy as np

# ============================================================
# PATH SETUP & AUTONOMOUS DISCOVERY
# ============================================================

def find_project_root():
    candidate = os.getcwd()
    while candidate and candidate != os.path.dirname(candidate):
        if os.path.exists(os.path.join(candidate, "00_WORLD_MASTER")):
            return candidate
        candidate = os.path.dirname(candidate)
    return "/home/aks1727/programming/gamedev/Shadows-of-the-Fallen"

PROJECT_ROOT = find_project_root()
ELEVATION_DIR = os.path.join(PROJECT_ROOT, "00_WORLD_MASTER", "elevation")
COORDINATES_DIR = os.path.join(PROJECT_ROOT, "00_WORLD_MASTER", "coordinates")

if ELEVATION_DIR not in sys.path:
    sys.path.insert(0, ELEVATION_DIR)

# Directly import master configs and authoritative elevation logic
import elevation_function as ef

WORLD_MASTER_PATH = os.path.join(COORDINATES_DIR, "world_master.json")
with open(WORLD_MASTER_PATH, "r", encoding="utf-8") as f:
    WORLD_MASTER = json.load(f)

# Master terrain parameters
CELL_SIZE = float(ef.CELL_SIZE)
GLOBAL_MIN = float(ef.GLOBAL_MIN)
GLOBAL_MAX = float(ef.GLOBAL_MAX)
HEIGHT_SPAN = GLOBAL_MAX - GLOBAL_MIN

# Unity Heightmap Resolution (must be 2^n + 1)
RESOLUTION = 513

# Target Unity directory
UNITY_ASSETS_DIR = os.path.join(PROJECT_ROOT, "unity/ShadowsOfTheFallen", "Assets")
UNITY_EXPORT_BASE = os.path.join(UNITY_ASSETS_DIR, "TerrainData", "RawHeightmaps")

# ============================================================
# BOUNDS CALCULATION
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

# ============================================================
# EXPORT LOGIC
# ============================================================

def export_region(region_id, min_cx, max_cx, min_cy, max_cy):
    out_dir = os.path.join(UNITY_EXPORT_BASE, region_id)
    os.makedirs(out_dir, exist_ok=True)

    cells = [
        (cx, cy)
        for cy in range(min_cy, max_cy + 1)
        for cx in range(min_cx, max_cx + 1)
    ]
    total = len(cells)

    print()
    print("=" * 70)
    print(f"[SOTF] Exporting Region '{region_id}' to Unity ({total} cells)")
    print(f"       Grid Bounds : X[{min_cx:+03d}..{max_cx:+03d}]  Y[{min_cy:+03d}..{max_cy:+03d}]")
    print(f"       Envelope    : {GLOBAL_MIN:.2f}m to {GLOBAL_MAX:.2f}m (Span: {HEIGHT_SPAN:.2f}m)")
    print(f"       Resolution  : {RESOLUTION}x{RESOLUTION} per 1km² tile")
    print("-" * 70)
    print("Cells queued for generation:")
    formatted_cell_list = [f"CELL_{cx:+03d}_{cy:+03d}" for cx, cy in cells]
    for i in range(0, len(formatted_cell_list), 4):
        print("   " + "   ".join(formatted_cell_list[i:i+4]))
    print("=" * 70)

    # Write region metadata for Unity C# Importer
    meta = {
        "region_id": region_id,
        "min_cx": min_cx,
        "max_cx": max_cx,
        "min_cy": min_cy,
        "max_cy": max_cy,
        "global_min_z": GLOBAL_MIN,
        "global_max_z": GLOBAL_MAX,
        "height_span": HEIGHT_SPAN,
        "resolution": RESOLUTION,
        "cell_size": CELL_SIZE
    }
    with open(os.path.join(out_dir, "region_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    for idx, (cx, cy) in enumerate(cells, 1):
        cell_tag = f"CELL_{cx:+03d}_{cy:+03d}"
        min_x = cx * CELL_SIZE
        min_y = cy * CELL_SIZE

        xs = np.linspace(min_x, min_x + CELL_SIZE, RESOLUTION)
        ys = np.linspace(min_y, min_y + CELL_SIZE, RESOLUTION)

        raw_bytes = bytearray()
        for wy in ys:
            for wx in xs:
                z = ef.elevation_at(wx, wy)
                norm = (z - GLOBAL_MIN) / HEIGHT_SPAN
                norm = max(0.0, min(1.0, norm))
                val_u16 = int(norm * 65535.0)
                raw_bytes.extend(struct.pack("<H", val_u16))

        filename = f"Terrain_RAW_{cx:+03d}_{cy:+03d}.raw"
        with open(os.path.join(out_dir, filename), "wb") as f:
            f.write(raw_bytes)

        print(f"[{idx:03d}/{total:03d}] {cell_tag} -> Generated ({filename})")

    print(f"\n[STATUS] Region '{region_id}' export complete.")
    print(f"         Output directory: {out_dir}\n")

# ============================================================
# CLI INTERACTIVE MENU
# ============================================================

def main():
    regions = list(WORLD_MASTER.get("regions", {}).keys())

    print("\n" + "=" * 65)
    print("  SHADOWS OF THE FALLEN - TERMINAL UNITY EXPORTER")
    print("=" * 65)
    print("  [0] Prototype 3x3 Cluster (Interchange: -1 to +1)")
    for i, reg_id in enumerate(regions, 1):
        min_cx, max_cx, min_cy, max_cy = get_region_cell_bounds(reg_id)
        count = (max_cx - min_cx + 1) * (max_cy - min_cy + 1)
        print(f"  [{i}] {reg_id.ljust(22)} ({count} cells: X[{min_cx}..{max_cx}], Y[{min_cy}..{max_cy}])")
    print(f"  [10] {"generate complete area"}" )
        
    print("=" * 65)

    try:
        raw_choice = input(f"Enter choice [0-{len(regions)}]: ").strip()
        choice = int(raw_choice)
    except (ValueError, KeyboardInterrupt):
        print("\nExiting.")
        return

    if choice == 0:
        export_region("prototype_cluster", -1, 1, -1, 1)
    elif 1 <= choice <= len(regions):
        selected = regions[choice - 1]
        min_cx, max_cx, min_cy, max_cy = get_region_cell_bounds(selected)
        export_region(selected, min_cx, max_cx, min_cy, max_cy)
    elif choice ==10:
        for i in regions:
            min_cx, max_cx, min_cy, max_cy = get_region_cell_bounds(i)
            export_region(i, min_cx, max_cx, min_cy, max_cy)

    else:
        print(f"[ERROR] Choice {choice} out of range (0 to {len(regions)}).")

if __name__ == "__main__":
    main()