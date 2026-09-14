import bpy
import json
import os
import math
from mathutils import Vector


# ============================================================
# SOTF — MASTER COORDINATE GRID
# ============================================================
#
# Purpose:
#   Generate a visual 1 km coordinate grid directly from
#   00_WORLD_MASTER/coordinates/world_master.json
#
# This script DOES NOT generate terrain.
#
# It visualizes:
#   - World origin
#   - Region bounds
#   - 1 km cells
#   - Cell IDs
#   - Region labels
#
# Coordinate contract:
#   X = East
#   Y = North
#   Z = Up
#
# Units:
#   meters
#
# ============================================================


# ------------------------------------------------------------
# CONFIG
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

JSON_PATH = os.path.join(
    PROJECT_ROOT,
    "00_WORLD_MASTER",
    "coordinates",
    "world_master.json"
)

CELL_SIZE = 1000.0

GRID_Z = 2.0
BOUNDARY_Z = 5.0

GRID_LINE_WIDTH = 0.75
BOUNDARY_LINE_WIDTH = 3.0

GRID_COLLECTION_NAME = "SOTF_MASTER_GRID"
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
# HELPERS
# ------------------------------------------------------------

def load_json(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Master coordinate file not found:\n{path}"
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_or_create_collection(name, parent=None):
    collection = bpy.data.collections.get(name)

    if collection is None:
        collection = bpy.data.collections.new(name)

        if parent:
            parent.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)

    return collection


def clear_collection(collection):
    objects = list(collection.objects)

    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def make_material(name, color, emission_strength=0.0):
    mat = bpy.data.materials.get(name)

    if mat is None:
        mat = bpy.data.materials.new(name)

    mat.diffuse_color = color

    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")

    if bsdf:
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

    obj = bpy.data.objects.new(name, curve_data)

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

    obj = bpy.data.objects.new(name, curve)

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
    obj = bpy.data.objects.new(name, None)

    obj.empty_display_type = display_type
    obj.empty_display_size = size
    obj.location = location

    if collection:
        collection.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)

    return obj


# ------------------------------------------------------------
# BOUNDS PARSER
# ------------------------------------------------------------

def parse_bounds(region):
    """
    Supports the common forms:

        bounds:
            min: [x, y]
            max: [x, y]

    OR:

        bounds:
            min_x
            max_x
            min_y
            max_y

    OR:

        bounds:
            southwest: [x, y]
            northeast: [x, y]

    Returns:
        min_x, max_x, min_y, max_y
    """

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


# ------------------------------------------------------------
# GRID GENERATION
# ------------------------------------------------------------

def generate_region_grid(
    region_id,
    region,
    grid_collection,
    cell_collection,
    label_collection,
    boundary_collection,
    grid_material,
    boundary_material,
    origin_material
):
    parsed = parse_bounds(region)

    if parsed is None:
        print(
            f"[WARNING] No usable bounds for region: {region_id}"
        )
        return

    min_x, max_x, min_y, max_y = parsed

    if max_x <= min_x or max_y <= min_y:
        print(
            f"[ERROR] Invalid bounds for {region_id}: "
            f"{parsed}"
        )
        return

    width = max_x - min_x
    height = max_y - min_y

    cols = math.ceil(width / CELL_SIZE)
    rows = math.ceil(height / CELL_SIZE)

    print()
    print("=" * 60)
    print(f"REGION: {region_id}")
    print("=" * 60)

    print(f"Min X : {min_x}")
    print(f"Max X : {max_x}")
    print(f"Min Y : {min_y}")
    print(f"Max Y : {max_y}")

    print(f"Width : {width} m")
    print(f"Height: {height} m")

    print(f"Cells X: {cols}")
    print(f"Cells Y: {rows}")
    print(f"Total : {cols * rows}")

    # --------------------------------------------------------
    # Region boundary
    # --------------------------------------------------------

    create_line(
        f"{region_id}_BOUNDARY_W",
        (min_x, min_y, BOUNDARY_Z),
        (min_x, max_y, BOUNDARY_Z),
        boundary_material,
        BOUNDARY_LINE_WIDTH,
        boundary_collection
    )

    create_line(
        f"{region_id}_BOUNDARY_E",
        (max_x, min_y, BOUNDARY_Z),
        (max_x, max_y, BOUNDARY_Z),
        boundary_material,
        BOUNDARY_LINE_WIDTH,
        boundary_collection
    )

    create_line(
        f"{region_id}_BOUNDARY_S",
        (min_x, min_y, BOUNDARY_Z),
        (max_x, min_y, BOUNDARY_Z),
        boundary_material,
        BOUNDARY_LINE_WIDTH,
        boundary_collection
    )

    create_line(
        f"{region_id}_BOUNDARY_N",
        (min_x, max_y, BOUNDARY_Z),
        (max_x, max_y, BOUNDARY_Z),
        boundary_material,
        BOUNDARY_LINE_WIDTH,
        boundary_collection
    )

    # --------------------------------------------------------
    # Region label
    # --------------------------------------------------------

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    create_text(
        f"{region_id}_LABEL",
        region_id.upper(),
        (center_x, center_y, BOUNDARY_Z + 10),
        35.0,
        boundary_material,
        label_collection
    )

    # --------------------------------------------------------
    # Grid lines
    # --------------------------------------------------------

    # Vertical / X lines
    for col in range(cols + 1):

        x = min_x + col * CELL_SIZE

        # Clamp to region
        x = min(x, max_x)

        create_line(
            f"{region_id}_GRID_X_{col:04d}",
            (x, min_y, GRID_Z),
            (x, max_y, GRID_Z),
            grid_material,
            GRID_LINE_WIDTH,
            grid_collection
        )

    # Horizontal / Y lines
    for row in range(rows + 1):

        y = min_y + row * CELL_SIZE

        y = min(y, max_y)

        create_line(
            f"{region_id}_GRID_Y_{row:04d}",
            (min_x, y, GRID_Z),
            (max_x, y, GRID_Z),
            grid_material,
            GRID_LINE_WIDTH,
            grid_collection
        )

    # --------------------------------------------------------
    # Cells
    # --------------------------------------------------------

    for row in range(rows):

        cell_min_y = min_y + row * CELL_SIZE
        cell_max_y = min(
            cell_min_y + CELL_SIZE,
            max_y
        )

        for col in range(cols):

            cell_min_x = min_x + col * CELL_SIZE
            cell_max_x = min(
                cell_min_x + CELL_SIZE,
                max_x
            )

            cell_width = cell_max_x - cell_min_x
            cell_height = cell_max_y - cell_min_y

            cell_id = (
                f"{region_id.upper()}_"
                f"X{col:03d}_"
                f"Y{row:03d}"
            )

            # ----------------------------------------------
            # Cell center
            # ----------------------------------------------

            cx = (
                cell_min_x + cell_max_x
            ) / 2.0

            cy = (
                cell_min_y + cell_max_y
            ) / 2.0

            # ----------------------------------------------
            # Cell empty
            # ----------------------------------------------

            cell_empty = create_empty(
                cell_id,
                (cx, cy, GRID_Z),
                display_type="CUBE",
                size=10.0,
                collection=cell_collection
            )

            cell_empty["region_id"] = region_id
            cell_empty["cell_x"] = col
            cell_empty["cell_y"] = row

            cell_empty["min_x"] = cell_min_x
            cell_empty["max_x"] = cell_max_x
            cell_empty["min_y"] = cell_min_y
            cell_empty["max_y"] = cell_max_y

            cell_empty["width"] = cell_width
            cell_empty["height"] = cell_height

            cell_empty["full_1km"] = (
                abs(cell_width - CELL_SIZE) < 0.001
                and
                abs(cell_height - CELL_SIZE) < 0.001
            )

            # ----------------------------------------------
            # Cell label
            # ----------------------------------------------

            create_text(
                f"{cell_id}_LABEL",
                cell_id,
                (
                    cx,
                    cy,
                    GRID_Z + 3
                ),
                12.0,
                grid_material,
                label_collection
            )

    # --------------------------------------------------------
    # Region origin marker
    # --------------------------------------------------------

    create_empty(
        f"{region_id}_ORIGIN",
        (min_x, min_y, BOUNDARY_Z),
        display_type="ARROWS",
        size=25.0,
        collection=boundary_collection
    )

    print(
        f"[OK] Generated {cols * rows} cells for {region_id}"
    )


# ------------------------------------------------------------
# WORLD ORIGIN
# ------------------------------------------------------------

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
        (0.0, 0.0, GRID_Z + 8),
        18.0,
        origin_material,
        label_collection
    )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print()
    print("=" * 70)
    print("SOTF — MASTER COORDINATE GRID")
    print("=" * 70)
    print()

    print(f"Project root:")
    print(f"  {PROJECT_ROOT}")

    print()
    print(f"Master coordinate file:")
    print(f"  {JSON_PATH}")

    # --------------------------------------------------------
    # Load master
    # --------------------------------------------------------

    data = load_json(JSON_PATH)

    print()
    print("[OK] world_master.json loaded")

    # --------------------------------------------------------
    # Collections
    # --------------------------------------------------------

    master_collection = get_or_create_collection(
        GRID_COLLECTION_NAME
    )

    grid_collection = get_or_create_collection(
        "GRID_LINES",
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
    # Clear previous generated grid
    # --------------------------------------------------------

    clear_collection(grid_collection)
    clear_collection(cell_collection)
    clear_collection(label_collection)
    clear_collection(boundary_collection)

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
    # Regions
    # --------------------------------------------------------

    regions = data.get("regions", {})

    if not regions:
        raise RuntimeError(
            "No 'regions' object found in world_master.json"
        )

    print()
    print(f"[INFO] Regions found: {len(regions)}")

    for region_id, region in regions.items():

        generate_region_grid(
            region_id,
            region,
            grid_collection,
            cell_collection,
            label_collection,
            boundary_collection,
            grid_material,
            boundary_material,
            origin_material
        )

    # --------------------------------------------------------
    # Scene metadata
    # --------------------------------------------------------

    scene = bpy.context.scene

    scene["SOTF_GRID_VERSION"] = "1.0.0"
    scene["SOTF_GRID_CELL_SIZE"] = CELL_SIZE
    scene["SOTF_GRID_SOURCE"] = JSON_PATH
    scene["SOTF_GRID_AXIS_X"] = "EAST"
    scene["SOTF_GRID_AXIS_Y"] = "NORTH"
    scene["SOTF_GRID_AXIS_Z"] = "UP"

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("GRID GENERATION COMPLETE")
    print("=" * 70)
    print()
    print(f"Cell size : {CELL_SIZE} m")
    print(f"Source    : {JSON_PATH}")
    print()
    print("Collections:")
    print(f"  {GRID_COLLECTION_NAME}")
    print(f"  ├── GRID_LINES")
    print(f"  ├── {CELL_COLLECTION_NAME}")
    print(f"  ├── {LABEL_COLLECTION_NAME}")
    print(f"  └── {BOUNDARY_COLLECTION_NAME}")
    print()
    print("No terrain was generated.")
    print("No world coordinates were modified.")
    print()
    print("=" * 70)


# ------------------------------------------------------------
# RUN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()