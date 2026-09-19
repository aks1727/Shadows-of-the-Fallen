import bpy
import json
import os
import math


# ============================================================
# SOTF — MASTER GLOBAL COORDINATE GRID
# ============================================================
#
# Purpose:
#   Build the authoritative GLOBAL 1 km × 1 km world grid.
#
# Sources:
#   00_WORLD_MASTER/coordinates/world_master.json
#
# Outputs:
#   00_WORLD_MASTER/coordinates/cell_grid.json
#   Blender visualization of the same exact cells
#
# Coordinate contract:
#   X = East
#   Y = North
#   Z = Up
#
# Cell convention:
#   CELL_X_Y
#
# Example:
#   CELL_+00_+00
#   CELL_+01_+00
#   CELL_-01_+00
#   CELL_+00_+01
#   CELL_+00_-01
#
# Each cell is exactly 1000 m × 1000 m unless the
# world extent itself ends inside a cell.
#
# IMPORTANT:
#   This script does NOT generate terrain.
#
# ============================================================


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

CELL_SIZE = 1000.0

GRID_Z = 2.0
BOUNDARY_Z = 5.0

GRID_LINE_WIDTH = 0.75
BOUNDARY_LINE_WIDTH = 3.0

GRID_COLLECTION_NAME = "SOTF_MASTER_GRID"
GRID_LINES_COLLECTION_NAME = "GRID_LINES"
CELL_COLLECTION_NAME = "SOTF_GRID_CELLS"
LABEL_COLLECTION_NAME = "SOTF_GRID_LABELS"
BOUNDARY_COLLECTION_NAME = "SOTF_REGION_BOUNDS"


# ------------------------------------------------------------
# COLORS
# ------------------------------------------------------------

GRID_COLOR = (0.15, 0.35, 0.8, 1.0)
BOUNDARY_COLOR = (1.0, 0.15, 0.05, 1.0)
ORIGIN_COLOR = (0.1, 1.0, 0.2, 1.0)


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

BLEND_PATH = bpy.data.filepath

if not BLEND_PATH:
    raise RuntimeError(
        "The Blender file has not been saved. "
        "Save SOTF_STAGE_A_MASTER.blend first."
    )

SCENE_DIR = os.path.dirname(
    os.path.abspath(BLEND_PATH)
)

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        SCENE_DIR,
        "../.."
    )
)

WORLD_MASTER_PATH = os.path.join(
    PROJECT_ROOT,
    "00_WORLD_MASTER",
    "coordinates",
    "world_master.json"
)

CELL_GRID_PATH = os.path.join(
    PROJECT_ROOT,
    "00_WORLD_MASTER",
    "coordinates",
    "cell_grid.json"
)


# ============================================================
# HELPERS
# ============================================================

def load_json(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"JSON file not found:\n{path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"[OK] Wrote: {path}")


def get_or_create_collection(name, parent=None):

    collection = bpy.data.collections.get(name)

    if collection is None:
        collection = bpy.data.collections.new(name)

        if parent:
            parent.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)

    else:
        # Ensure the collection is linked to the requested parent.
        if parent:
            if collection.name not in parent.children:
                try:
                    parent.children.link(collection)
                except RuntimeError:
                    pass
        else:
            if collection.name not in bpy.context.scene.collection.children:
                try:
                    bpy.context.scene.collection.children.link(collection)
                except RuntimeError:
                    pass

    return collection


def clear_collection(collection):

    objects = list(collection.objects)

    for obj in objects:
        bpy.data.objects.remove(
            obj,
            do_unlink=True
        )

    print(
        f"[CLEAR] {collection.name}: "
        f"{len(objects)} objects removed"
    )


def make_material(name, color, emission_strength=0.0):

    mat = bpy.data.materials.get(name)

    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color = color
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    if bsdf:

        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color

        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = color

        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength

    return mat


def create_line(
    name,
    start,
    end,
    material,
    width,
    collection
):

    curve_data = bpy.data.curves.new(
        name=name,
        type="CURVE"
    )

    curve_data.dimensions = "3D"
    curve_data.bevel_depth = width
    curve_data.bevel_resolution = 2

    spline = curve_data.splines.new("POLY")
    spline.points.add(1)

    spline.points[0].co = (
        start[0],
        start[1],
        start[2],
        1.0
    )

    spline.points[1].co = (
        end[0],
        end[1],
        end[2],
        1.0
    )

    obj = bpy.data.objects.new(
        name,
        curve_data
    )

    collection.objects.link(obj)

    obj.data.materials.append(material)

    return obj


def create_text(
    name,
    text,
    location,
    size,
    material,
    collection,
    align_x="CENTER",
    align_y="CENTER"
):

    curve = bpy.data.curves.new(
        name=name,
        type="FONT"
    )

    curve.body = text
    curve.align_x = align_x
    curve.align_y = align_y
    curve.size = size
    curve.extrude = 0.0

    obj = bpy.data.objects.new(
        name,
        curve
    )

    collection.objects.link(obj)

    obj.location = location

    obj.data.materials.append(material)

    return obj


def create_empty(
    name,
    location,
    display_type="PLAIN_AXES",
    size=20.0,
    collection=None
):

    obj = bpy.data.objects.new(
        name,
        None
    )

    obj.empty_display_type = display_type
    obj.empty_display_size = size
    obj.location = location

    if collection:
        collection.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)

    return obj


# ============================================================
# BOUNDS
# ============================================================

def parse_bounds(region):

    bounds = region.get("bounds")

    if not bounds:
        return None

    # ----------------------------------------
    # min/max arrays
    # ----------------------------------------

    if "min" in bounds and "max" in bounds:

        min_v = bounds["min"]
        max_v = bounds["max"]

        return (
            float(min_v[0]),
            float(max_v[0]),
            float(min_v[1]),
            float(max_v[1])
        )

    # ----------------------------------------
    # Explicit values
    # ----------------------------------------

    if all(
        k in bounds
        for k in [
            "min_x",
            "max_x",
            "min_y",
            "max_y"
        ]
    ):

        return (
            float(bounds["min_x"]),
            float(bounds["max_x"]),
            float(bounds["min_y"]),
            float(bounds["max_y"])
        )

    # ----------------------------------------
    # Southwest / Northeast
    # ----------------------------------------

    if (
        "southwest" in bounds
        and "northeast" in bounds
    ):

        sw = bounds["southwest"]
        ne = bounds["northeast"]

        return (
            float(sw[0]),
            float(ne[0]),
            float(sw[1]),
            float(ne[1])
        )

    return None


# ============================================================
# GLOBAL GRID INDEX
# ============================================================

def world_to_cell_index(value):
    """
    Convert world coordinate to global 1 km cell index.

    Examples:

        0       -> 0
        999.9   -> 0
        1000    -> 1
        -0.1    -> -1
        -1000   -> -1
        -1000.1 -> -2
    """

    return math.floor(
        value / CELL_SIZE
    )


def cell_id(cell_x, cell_y):

    return (
        f"CELL_{cell_x:+03d}_{cell_y:+03d}"
    )


def cell_bounds(cell_x, cell_y):

    min_x = cell_x * CELL_SIZE
    max_x = min_x + CELL_SIZE

    min_y = cell_y * CELL_SIZE
    max_y = min_y + CELL_SIZE

    return (
        min_x,
        max_x,
        min_y,
        max_y
    )


# ============================================================
# REGION INTERSECTION
# ============================================================

def cell_intersects_region(
    cell_min_x,
    cell_max_x,
    cell_min_y,
    cell_max_y,
    region_min_x,
    region_max_x,
    region_min_y,
    region_max_y
):

    return not (
        cell_max_x <= region_min_x
        or
        cell_min_x >= region_max_x
        or
        cell_max_y <= region_min_y
        or
        cell_min_y >= region_max_y
    )


# ============================================================
# BUILD GLOBAL CELL DATA
# ============================================================

def build_global_cells(data):

    regions = data.get(
        "regions",
        {}
    )

    if not regions:

        raise RuntimeError(
            "No 'regions' object found "
            "in world_master.json"
        )

    region_bounds = {}

    global_min_x = float("inf")
    global_max_x = float("-inf")
    global_min_y = float("inf")
    global_max_y = float("-inf")

    # --------------------------------------------------------
    # Parse all region bounds
    # --------------------------------------------------------

    for region_id, region in regions.items():

        parsed = parse_bounds(region)

        if parsed is None:

            print(
                f"[WARNING] Skipping region "
                f"without usable bounds: {region_id}"
            )

            continue

        min_x, max_x, min_y, max_y = parsed

        if max_x <= min_x or max_y <= min_y:

            print(
                f"[WARNING] Invalid bounds for "
                f"{region_id}: {parsed}"
            )

            continue

        region_bounds[region_id] = {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y
        }

        global_min_x = min(
            global_min_x,
            min_x
        )

        global_max_x = max(
            global_max_x,
            max_x
        )

        global_min_y = min(
            global_min_y,
            min_y
        )

        global_max_y = max(
            global_max_y,
            max_y
        )

    if not region_bounds:

        raise RuntimeError(
            "No valid region bounds found."
        )

    # --------------------------------------------------------
    # Convert world extents to global cell indices
    # --------------------------------------------------------

    min_cell_x = world_to_cell_index(
        global_min_x
    )

    max_cell_x = world_to_cell_index(
        global_max_x - 0.000001
    )

    min_cell_y = world_to_cell_index(
        global_min_y
    )

    max_cell_y = world_to_cell_index(
        global_max_y - 0.000001
    )

    print()
    print("=" * 70)
    print("GLOBAL GRID EXTENTS")
    print("=" * 70)

    print(
        f"World X : "
        f"{global_min_x} → {global_max_x}"
    )

    print(
        f"World Y : "
        f"{global_min_y} → {global_max_y}"
    )

    print(
        f"Cell X : "
        f"{min_cell_x} → {max_cell_x}"
    )

    print(
        f"Cell Y : "
        f"{min_cell_y} → {max_cell_y}"
    )

    print(
        f"Cell dimensions : "
        f"{CELL_SIZE} × {CELL_SIZE} m"
    )

    total_x = (
        max_cell_x -
        min_cell_x +
        1
    )

    total_y = (
        max_cell_y -
        min_cell_y +
        1
    )

    total_cells = total_x * total_y

    print(
        f"Grid dimensions : "
        f"{total_x} × {total_y}"
    )

    print(
        f"Total global cells : "
        f"{total_cells}"
    )

    # --------------------------------------------------------
    # Generate cells
    # --------------------------------------------------------

    cells = {}

    for cell_y in range(
        min_cell_y,
        max_cell_y + 1
    ):

        for cell_x in range(
            min_cell_x,
            max_cell_x + 1
        ):

            (
                min_x,
                max_x,
                min_y,
                max_y
            ) = cell_bounds(
                cell_x,
                cell_y
            )

            cx = (
                min_x + max_x
            ) / 2.0

            cy = (
                min_y + max_y
            ) / 2.0

            regions_here = []

            for region_id, rb in region_bounds.items():

                if cell_intersects_region(
                    min_x,
                    max_x,
                    min_y,
                    max_y,
                    rb["min_x"],
                    rb["max_x"],
                    rb["min_y"],
                    rb["max_y"]
                ):

                    regions_here.append(
                        region_id
                    )

            cid = cell_id(
                cell_x,
                cell_y
            )

            cells[cid] = {
                "id": cid,

                "grid": {
                    "x": cell_x,
                    "y": cell_y
                },

                "bounds": {
                    "min": [
                        min_x,
                        min_y
                    ],
                    "max": [
                        max_x,
                        max_y
                    ]
                },

                "center": [
                    cx,
                    cy
                ],

                "size_m": [
                    CELL_SIZE,
                    CELL_SIZE
                ],

                "regions": sorted(
                    regions_here
                )
            }

    return {
        "project": data.get(
            "project",
            "Shadows of the Fallen"
        ),

        "version": "1.0.0",

        "coordinate_system": {
            "units": "meters",
            "up_axis": "Z",
            "north_axis": "+Y",
            "east_axis": "+X",
            "origin": [
                0.0,
                0.0,
                0.0
            ]
        },

        "grid": {
            "cell_size_m": CELL_SIZE,

            "min_cell": [
                min_cell_x,
                min_cell_y
            ],

            "max_cell": [
                max_cell_x,
                max_cell_y
            ],

            "dimensions": [
                total_x,
                total_y
            ],

            "total_cells": total_cells
        },

        "source": {
            "world_master": os.path.relpath(
                WORLD_MASTER_PATH,
                PROJECT_ROOT
            )
        },

        "cells": cells
    }


# ============================================================
# BLENDER VISUALIZATION
# ============================================================

def generate_region_boundaries(
    region_bounds,
    boundary_collection,
    label_collection,
    boundary_material
):

    for region_id, rb in region_bounds.items():

        min_x = rb["min_x"]
        max_x = rb["max_x"]
        min_y = rb["min_y"]
        max_y = rb["max_y"]

        # West
        create_line(
            f"{region_id}_BOUNDARY_W",
            (min_x, min_y, BOUNDARY_Z),
            (min_x, max_y, BOUNDARY_Z),
            boundary_material,
            BOUNDARY_LINE_WIDTH,
            boundary_collection
        )

        # East
        create_line(
            f"{region_id}_BOUNDARY_E",
            (max_x, min_y, BOUNDARY_Z),
            (max_x, max_y, BOUNDARY_Z),
            boundary_material,
            BOUNDARY_LINE_WIDTH,
            boundary_collection
        )

        # South
        create_line(
            f"{region_id}_BOUNDARY_S",
            (min_x, min_y, BOUNDARY_Z),
            (max_x, min_y, BOUNDARY_Z),
            boundary_material,
            BOUNDARY_LINE_WIDTH,
            boundary_collection
        )

        # North
        create_line(
            f"{region_id}_BOUNDARY_N",
            (min_x, max_y, BOUNDARY_Z),
            (max_x, max_y, BOUNDARY_Z),
            boundary_material,
            BOUNDARY_LINE_WIDTH,
            boundary_collection
        )

        # Label
        center_x = (
            min_x + max_x
        ) / 2.0

        center_y = (
            min_y + max_y
        ) / 2.0

        create_text(
            f"{region_id}_LABEL",
            region_id.upper(),
            (
                center_x,
                center_y,
                BOUNDARY_Z + 10
            ),
            35.0,
            boundary_material,
            label_collection
        )


def generate_global_grid_visuals(
    grid_data,
    grid_collection,
    cell_collection,
    label_collection,
    grid_material
):

    cells = grid_data["cells"]

    min_cell_x = grid_data["grid"]["min_cell"][0]
    max_cell_x = grid_data["grid"]["max_cell"][0]

    min_cell_y = grid_data["grid"]["min_cell"][1]
    max_cell_y = grid_data["grid"]["max_cell"][1]

    # --------------------------------------------------------
    # Vertical grid lines
    # --------------------------------------------------------

    for x_index in range(
        min_cell_x,
        max_cell_x + 2
    ):

        x = x_index * CELL_SIZE

        create_line(
            f"GLOBAL_GRID_X_{x_index:+04d}",
            (
                x,
                min_cell_y * CELL_SIZE,
                GRID_Z
            ),
            (
                x,
                (max_cell_y + 1) * CELL_SIZE,
                GRID_Z
            ),
            grid_material,
            GRID_LINE_WIDTH,
            grid_collection
        )

    # --------------------------------------------------------
    # Horizontal grid lines
    # --------------------------------------------------------

    for y_index in range(
        min_cell_y,
        max_cell_y + 2
    ):

        y = y_index * CELL_SIZE

        create_line(
            f"GLOBAL_GRID_Y_{y_index:+04d}",
            (
                min_cell_x * CELL_SIZE,
                y,
                GRID_Z
            ),
            (
                (max_cell_x + 1) * CELL_SIZE,
                y,
                GRID_Z
            ),
            grid_material,
            GRID_LINE_WIDTH,
            grid_collection
        )

    # --------------------------------------------------------
    # Cell markers + labels
    # --------------------------------------------------------

    for cid, cell in cells.items():

        grid_x = cell["grid"]["x"]
        grid_y = cell["grid"]["y"]

        min_x = cell["bounds"]["min"][0]
        min_y = cell["bounds"]["min"][1]

        max_x = cell["bounds"]["max"][0]
        max_y = cell["bounds"]["max"][1]

        cx = cell["center"][0]
        cy = cell["center"][1]

        # Empty at cell center
        empty = create_empty(
            cid,
            (
                cx,
                cy,
                GRID_Z
            ),
            display_type="CUBE",
            size=10.0,
            collection=cell_collection
        )

        # Blender custom properties
        empty["cell_id"] = cid
        empty["cell_x"] = grid_x
        empty["cell_y"] = grid_y

        empty["min_x"] = min_x
        empty["max_x"] = max_x
        empty["min_y"] = min_y
        empty["max_y"] = max_y

        empty["center_x"] = cx
        empty["center_y"] = cy

        empty["width"] = CELL_SIZE
        empty["height"] = CELL_SIZE

        empty["full_1km"] = True

        empty["regions"] = ",".join(
            cell["regions"]
        )

        # Label
        create_text(
            f"{cid}_LABEL",
            cid,
            (
                cx,
                cy,
                GRID_Z + 3
            ),
            12.0,
            grid_material,
            label_collection
        )


# ============================================================
# WORLD ORIGIN
# ============================================================

def generate_world_origin(
    boundary_collection,
    label_collection,
    origin_material
):

    create_line(
        "WORLD_ORIGIN_X",
        (-100.0, 0.0, GRID_Z),
        (100.0, 0.0, GRID_Z),
        origin_material,
        2.0,
        boundary_collection
    )

    create_line(
        "WORLD_ORIGIN_Y",
        (0.0, -100.0, GRID_Z),
        (0.0, 100.0, GRID_Z),
        origin_material,
        2.0,
        boundary_collection
    )

    create_text(
        "WORLD_ORIGIN_LABEL",
        "WORLD ORIGIN (0,0)",
        (
            0.0,
            0.0,
            GRID_Z + 8
        ),
        18.0,
        origin_material,
        label_collection
    )

    create_empty(
        "WORLD_ORIGIN",
        (
            0.0,
            0.0,
            GRID_Z
        ),
        display_type="ARROWS",
        size=50.0,
        collection=boundary_collection
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("SOTF — MASTER GLOBAL COORDINATE GRID")
    print("=" * 70)
    print()

    print(
        f"Project root:\n  {PROJECT_ROOT}"
    )

    print()
    print(
        f"world_master.json:\n  "
        f"{WORLD_MASTER_PATH}"
    )

    print()
    print(
        f"cell_grid.json:\n  "
        f"{CELL_GRID_PATH}"
    )

    # --------------------------------------------------------
    # Load world master
    # --------------------------------------------------------

    data = load_json(
        WORLD_MASTER_PATH
    )

    print()
    print(
        "[OK] world_master.json loaded"
    )

    # --------------------------------------------------------
    # Build global cell data
    # --------------------------------------------------------

    grid_data = build_global_cells(
        data
    )

    print()
    print(
        f"[OK] Generated "
        f"{len(grid_data['cells'])} "
        f"global cells"
    )

    # --------------------------------------------------------
    # Write cell_grid.json
    # --------------------------------------------------------

    save_json(
        CELL_GRID_PATH,
        grid_data
    )

    # --------------------------------------------------------
    # Collections
    # --------------------------------------------------------

    master_collection = get_or_create_collection(
        GRID_COLLECTION_NAME
    )

    grid_collection = get_or_create_collection(
        GRID_LINES_COLLECTION_NAME,
        master_collection
    )

    cell_collection = get_or_create_collection(
        CELL_COLLECTION_NAME,
        master_collection
    )

    label_collection = get_or_create_collection(
        LABEL_COLLECTION_NAME,
        master_collection
    )

    boundary_collection = get_or_create_collection(
        BOUNDARY_COLLECTION_NAME,
        master_collection
    )

    # --------------------------------------------------------
    # Clear OLD grid visualization
    # --------------------------------------------------------

    clear_collection(
        grid_collection
    )

    clear_collection(
        cell_collection
    )

    clear_collection(
        label_collection
    )

    clear_collection(
        boundary_collection
    )

    # --------------------------------------------------------
    # Materials
    # --------------------------------------------------------

    grid_material = make_material(
        "SOTF_GRID_MAT",
        GRID_COLOR,
        emission_strength=1.0
    )

    boundary_material = make_material(
        "SOTF_BOUNDARY_MAT",
        BOUNDARY_COLOR,
        emission_strength=1.5
    )

    origin_material = make_material(
        "SOTF_ORIGIN_MAT",
        ORIGIN_COLOR,
        emission_strength=2.0
    )

    # --------------------------------------------------------
    # World origin
    # --------------------------------------------------------

    generate_world_origin(
        boundary_collection,
        label_collection,
        origin_material
    )

    # --------------------------------------------------------
    # Region bounds
    # --------------------------------------------------------

    region_bounds = {}

    for region_id, region in data.get(
        "regions",
        {}
    ).items():

        parsed = parse_bounds(region)

        if parsed is None:
            continue

        min_x, max_x, min_y, max_y = parsed

        region_bounds[region_id] = {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y
        }

    generate_region_boundaries(
        region_bounds,
        boundary_collection,
        label_collection,
        boundary_material
    )

    # --------------------------------------------------------
    # Global grid
    # --------------------------------------------------------

    generate_global_grid_visuals(
        grid_data,
        grid_collection,
        cell_collection,
        label_collection,
        grid_material
    )

    # --------------------------------------------------------
    # Scene metadata
    # --------------------------------------------------------

    scene = bpy.context.scene

    scene["SOTF_GRID_VERSION"] = "2.0.0"

    scene["SOTF_GRID_CELL_SIZE"] = CELL_SIZE

    scene["SOTF_GRID_SOURCE"] = (
        WORLD_MASTER_PATH
    )

    scene["SOTF_GRID_MANIFEST"] = (
        CELL_GRID_PATH
    )

    scene["SOTF_GRID_AXIS_X"] = "EAST"
    scene["SOTF_GRID_AXIS_Y"] = "NORTH"
    scene["SOTF_GRID_AXIS_Z"] = "UP"

    scene["SOTF_GRID_ORIGIN_X"] = 0.0
    scene["SOTF_GRID_ORIGIN_Y"] = 0.0
    scene["SOTF_GRID_ORIGIN_Z"] = 0.0

    scene["SOTF_GRID_TOTAL_CELLS"] = (
        len(grid_data["cells"])
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("GLOBAL GRID GENERATION COMPLETE")
    print("=" * 70)

    print()

    print(
        f"Cell size       : "
        f"{CELL_SIZE} m"
    )

    print(
        f"Total cells     : "
        f"{len(grid_data['cells'])}"
    )

    print(
        f"Cell X range    : "
        f"{grid_data['grid']['min_cell'][0]} "
        f"→ "
        f"{grid_data['grid']['max_cell'][0]}"
    )

    print(
        f"Cell Y range    : "
        f"{grid_data['grid']['min_cell'][1]} "
        f"→ "
        f"{grid_data['grid']['max_cell'][1]}"
    )

    print()

    print(
        f"Manifest        : "
        f"{CELL_GRID_PATH}"
    )

    print()

    print("Collections:")
    print(
        f"  {GRID_COLLECTION_NAME}"
    )
    print(
        f"  ├── {GRID_LINES_COLLECTION_NAME}"
    )
    print(
        f"  ├── {CELL_COLLECTION_NAME}"
    )
    print(
        f"  ├── {LABEL_COLLECTION_NAME}"
    )
    print(
        f"  └── {BOUNDARY_COLLECTION_NAME}"
    )

    print()

    print("Coordinate contract:")
    print("  X = East")
    print("  Y = North")
    print("  Z = Up")
    print("  Origin = (0, 0, 0)")

    print()

    print("No terrain was generated.")
    print("No world coordinates were modified.")

    print("=" * 70)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()