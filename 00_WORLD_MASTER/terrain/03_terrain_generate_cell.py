#!/usr/bin/env python3
import os
import sys
import math
import json
import bpy

# ============================================================
# CONFIGURATION
# ============================================================

TARGET_CELL_X = 1
TARGET_CELL_Y = 0

SPACING_M = 10.0
EXPECTED_CELL_SIZE_M = 1000.0
TOLERANCE_M = 1e-4  # 0.1 mm tolerance, safe for 32-bit Blender float quantization

ROOT_COLLECTION_NAME = "TERRAIN"

# ============================================================
# PATH RESOLUTION & IMPORTS
# ============================================================

def find_project_root():
    candidate = os.path.dirname(os.path.abspath(bpy.data.filepath)) if bpy.data.filepath else os.getcwd()
    while candidate and candidate != os.path.dirname(candidate):
        if os.path.exists(os.path.join(candidate, "00_WORLD_MASTER")):
            return candidate
        candidate = os.path.dirname(candidate)
    return "/home/aks1727/programming/gamedev/Shadows-of-the-Fallen"

PROJECT_ROOT = find_project_root()

COORDINATES_DIR = os.path.join(PROJECT_ROOT, "00_WORLD_MASTER", "coordinates")
CELL_GRID_PATH = os.path.join(COORDINATES_DIR, "cell_grid.json")
ELEVATION_DIR = os.path.join(PROJECT_ROOT, "00_WORLD_MASTER", "elevation")

if ELEVATION_DIR not in sys.path:
    sys.path.insert(0, ELEVATION_DIR)

try:
    from elevation_function import elevation_at
except ImportError as exc:
    raise ImportError(f"Failed to import elevation_at from {ELEVATION_DIR}: {exc}")


# ============================================================
# COLLECTION MANAGEMENT
# ============================================================

def get_or_create_collection(name, parent=None):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        if parent:
            parent.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)
    return collection


def clean_cell_collection(parent_coll, cell_name):
    target = bpy.data.collections.get(cell_name)
    if target and target.name in parent_coll.children:
        for obj in list(target.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(target)


# ============================================================
# CELL RESOLUTION
# ============================================================

def load_cell_metadata(cell_id):
    if not os.path.isfile(CELL_GRID_PATH):
        raise FileNotFoundError(f"cell_grid.json missing at: {CELL_GRID_PATH}")

    with open(CELL_GRID_PATH, "r", encoding="utf-8") as f:
        grid_data = json.load(f)

    cells = grid_data.get("cells", {})
    if cell_id not in cells:
        raise KeyError(f"Cell ID '{cell_id}' not found in cell_grid.json")

    return cells[cell_id]


# ============================================================
# GENERATION & VALIDATION
# ============================================================

def generate_terrain_cell(cell_x, cell_y):
    cell_id = f"CELL_{cell_x:+03d}_{cell_y:+03d}"
    print(f"\n[SOTF] Initializing Terrain Generation for {cell_id}...")

    # 1. Resolve & Pre-validate Manifest
    meta = load_cell_metadata(cell_id)
    min_x, min_y = meta["bounds"]["min"]
    max_x, max_y = meta["bounds"]["max"]

    dx = max_x - min_x
    dy = max_y - min_y

    assert math.isclose(dx, EXPECTED_CELL_SIZE_M, abs_tol=TOLERANCE_M), f"Cell width mismatch: {dx}m"
    assert math.isclose(dy, EXPECTED_CELL_SIZE_M, abs_tol=TOLERANCE_M), f"Cell height mismatch: {dy}m"

    intervals = int(round(EXPECTED_CELL_SIZE_M / SPACING_M))
    num_verts_per_axis = intervals + 1
    expected_vertex_count = num_verts_per_axis * num_verts_per_axis
    expected_face_count = intervals * intervals

    print(f"  Bounds: X [{min_x}, {max_x}] | Y [{min_y}, {max_y}]")
    print(f"  Target Vertices: {num_verts_per_axis} x {num_verts_per_axis} = {expected_vertex_count}")
    print(f"  Target Quads:    {intervals} x {intervals} = {expected_face_count}")

    # 2. Sample Mathematical Elevation directly into World Space
    verts = []
    min_z = float("inf")
    max_z = float("-inf")

    for iy in range(num_verts_per_axis):
        world_y = min_y + (iy * SPACING_M)
        for ix in range(num_verts_per_axis):
            world_x = min_x + (ix * SPACING_M)

            z = elevation_at(world_x, world_y)

            # Sanity checks
            if math.isnan(z) or math.isinf(z):
                raise ValueError(f"Invalid elevation {z} evaluated at ({world_x}, {world_y})")

            min_z = min(min_z, z)
            max_z = max(max_z, z)

            # World coordinates: direct placement, no local transform offsets
            verts.append((world_x, world_y, z))

    # 3. Construct Quad Face Topology (CCW winding)
    faces = []
    for iy in range(intervals):
        row_offset = iy * num_verts_per_axis
        next_row_offset = (iy + 1) * num_verts_per_axis
        for ix in range(intervals):
            v0 = row_offset + ix
            v1 = row_offset + (ix + 1)
            v2 = next_row_offset + (ix + 1)
            v3 = next_row_offset + ix
            faces.append((v0, v1, v2, v3))

    # 4. Blender Mesh Construction
    terrain_root = get_or_create_collection(ROOT_COLLECTION_NAME)
    clean_cell_collection(terrain_root, cell_id)
    cell_coll = get_or_create_collection(cell_id, terrain_root)

    mesh_name = f"TERRAIN_{cell_id}"
    mesh = bpy.data.meshes.new(name=f"{mesh_name}_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(mesh_name, mesh)
    cell_coll.objects.link(obj)

    # Lock object transforms to origin so vertices remain true world coordinates
    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)

    # 5. Automated Post-Mesh Validation
    print("\n[VALIDATION]")
    actual_vert_count = len(obj.data.vertices)
    actual_face_count = len(obj.data.polygons)

    assert actual_vert_count == expected_vertex_count, f"Vert count mismatch: {actual_vert_count}"
    assert actual_face_count == expected_face_count, f"Face count mismatch: {actual_face_count}"
    print(f"  ✓ Geometry topology confirmed: {actual_vert_count} verts, {actual_face_count} quads")

    # Corner validation
    c_sw = obj.data.vertices[0].co
    c_se = obj.data.vertices[intervals].co
    c_nw = obj.data.vertices[-num_verts_per_axis].co
    c_ne = obj.data.vertices[-1].co

    assert math.isclose(c_sw.x, min_x, abs_tol=TOLERANCE_M) and math.isclose(c_sw.y, min_y, abs_tol=TOLERANCE_M)
    assert math.isclose(c_se.x, max_x, abs_tol=TOLERANCE_M) and math.isclose(c_se.y, min_y, abs_tol=TOLERANCE_M)
    assert math.isclose(c_nw.x, min_x, abs_tol=TOLERANCE_M) and math.isclose(c_nw.y, max_y, abs_tol=TOLERANCE_M)
    assert math.isclose(c_ne.x, max_x, abs_tol=TOLERANCE_M) and math.isclose(c_ne.y, max_y, abs_tol=TOLERANCE_M)
    print("  ✓ Four corners align with world grid extents")

    # Boundary mathematical equivalence verification
    max_boundary_diff = 0.0
    for idx, v in enumerate(obj.data.vertices):
        # Identify perimeter vertices
        is_x_boundary = math.isclose(v.co.x, min_x, abs_tol=TOLERANCE_M) or math.isclose(v.co.x, max_x, abs_tol=TOLERANCE_M)
        is_y_boundary = math.isclose(v.co.y, min_y, abs_tol=TOLERANCE_M) or math.isclose(v.co.y, max_y, abs_tol=TOLERANCE_M)

        if is_x_boundary or is_y_boundary:
            independent_z = elevation_at(v.co.x, v.co.y)
            diff = abs(v.co.z - independent_z)
            if diff > max_boundary_diff:
                max_boundary_diff = diff

    assert max_boundary_diff <= 1e-4, f"Boundary drift detected: {max_boundary_diff}m"
    print(f"  ✓ Boundary integrity: Verified (Max ΔZ = {max_boundary_diff:.10f} m)")
    print(f"  ✓ Elevation span: Min Z = {min_z:.2f} m | Max Z = {max_z:.2f} m")

    print(f"\n[STATUS] {cell_id} successfully generated and linked to {ROOT_COLLECTION_NAME}/{cell_id}")


if __name__ == "__main__":
    generate_terrain_cell(TARGET_CELL_X, TARGET_CELL_Y)