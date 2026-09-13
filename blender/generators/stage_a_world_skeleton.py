import bpy
import json
import os
import math


# ============================================================
# SOTF — STAGE A WORLD SKELETON GENERATOR
# ============================================================
#
# Source of truth:
# 00_WORLD_MASTER/coordinates/world_master.json
#
# Stage A ONLY:
# - Coordinate system
# - Region bounds
# - Hydrology guides
# - Infrastructure guides
# - Story / lore POIs
# - World grid
# - Labels
#
# NO terrain generation.
# NO final assets.
# NO materials.
# NO Unity export.
#
# ============================================================


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

PROJECT_ROOT = "/home/aks1727/programming/gamedev/Shadows-of-the-Fallen"

JSON_PATH = os.path.join(
    PROJECT_ROOT,
    "00_WORLD_MASTER",
    "coordinates",
    "world_master.json"
)

ROOT_COLLECTION_NAME = "00_WORLD_MASTER"

GRID_SPACING = 1000.0          # 1 km
GRID_EXTENT = 16000.0          # ±16 km

REGION_LINE_WIDTH = 0.03
RIVER_BEVEL = 25.0
ROAD_BEVEL = 15.0

POI_SIZE = 150.0
LABEL_SIZE = 120.0

LAKE_SEGMENTS = 96

GENERATED_TAG = "SOTF_STAGE_A"


# ------------------------------------------------------------
# COLLECTION HELPERS
# ------------------------------------------------------------

def get_or_create_collection(name, parent=None):

    if name in bpy.data.collections:
        collection = bpy.data.collections[name]
    else:
        collection = bpy.data.collections.new(name)

        if parent:
            parent.children.link(collection)
        else:
            bpy.context.scene.collection.children.link(collection)

    return collection


def get_stage_a_collections():

    root = get_or_create_collection(ROOT_COLLECTION_NAME)

    collections = {
        "root": root,
        "regions": get_or_create_collection(
            "01_REGION_BOUNDS",
            root
        ),
        "hydrology": get_or_create_collection(
            "02_HYDROLOGY",
            root
        ),
        "infrastructure": get_or_create_collection(
            "03_INFRASTRUCTURE",
            root
        ),
        "story": get_or_create_collection(
            "04_STORY_NODES",
            root
        ),
        "grid": get_or_create_collection(
            "05_WORLD_GRID",
            root
        ),
        "labels": get_or_create_collection(
            "06_LABELS",
            root
        ),
    }

    return collections


# ------------------------------------------------------------
# CLEAN GENERATED STAGE A DATA
# ------------------------------------------------------------

def clean_stage_a():

    print("[SOTF] Cleaning previous Stage A generation...")

    objects_to_remove = []

    for obj in bpy.data.objects:

        if obj.get("sotf_generated") == GENERATED_TAG:
            objects_to_remove.append(obj)

    for obj in objects_to_remove:

        bpy.data.objects.remove(
            obj,
            do_unlink=True
        )

    # Remove generated collections except root.
    for collection_name in [
        "01_REGION_BOUNDS",
        "02_HYDROLOGY",
        "03_INFRASTRUCTURE",
        "04_STORY_NODES",
        "05_WORLD_GRID",
        "06_LABELS",
    ]:

        collection = bpy.data.collections.get(collection_name)

        if collection:

            bpy.data.collections.remove(
                collection
            )

    print(
        f"[SOTF] Removed {len(objects_to_remove)} generated objects."
    )


# ------------------------------------------------------------
# SCENE SETUP
# ------------------------------------------------------------

def setup_scene():

    scene = bpy.context.scene

    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    # Useful world-scale viewport clipping.
    for area in bpy.context.screen.areas:

        if area.type == "VIEW_3D":

            for space in area.spaces:

                if space.type == "VIEW_3D":

                    space.clip_start = 0.1
                    space.clip_end = 100000.0

    # World background.
    scene.world.color = (0.015, 0.015, 0.015)

    print("[SOTF] Scene configured for metric units.")


# ------------------------------------------------------------
# OBJECT METADATA
# ------------------------------------------------------------

def tag_object(obj, category, source_key=None):

    obj["sotf_generated"] = GENERATED_TAG
    obj["sotf_category"] = category

    if source_key:
        obj["sotf_source_key"] = source_key


# ------------------------------------------------------------
# REGION BOUNDS
# ------------------------------------------------------------

def create_bounding_box(
    name,
    min_xy,
    max_xy,
    z_min,
    z_max,
    collection,
    source_key
):

    x0, y0 = min_xy
    x1, y1 = max_xy

    verts = [

        (x0, y0, z_min),
        (x1, y0, z_min),
        (x1, y1, z_min),
        (x0, y1, z_min),

        (x0, y0, z_max),
        (x1, y0, z_max),
        (x1, y1, z_max),
        (x0, y1, z_max),
    ]

    edges = [

        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),

        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),

        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]

    mesh = bpy.data.meshes.new(
        f"{name}_MESH"
    )

    mesh.from_pydata(
        verts,
        edges,
        []
    )

    mesh.update()

    obj = bpy.data.objects.new(
        name,
        mesh
    )

    obj.display_type = "WIRE"

    collection.objects.link(obj)

    tag_object(
        obj,
        "REGION_BOUND",
        source_key
    )

    obj["bounds_min"] = min_xy
    obj["bounds_max"] = max_xy
    obj["elevation_min"] = z_min
    obj["elevation_max"] = z_max

    return obj


# ------------------------------------------------------------
# REGION CENTER MARKER
# ------------------------------------------------------------

def create_region_center(
    name,
    min_xy,
    max_xy,
    z,
    collection,
    source_key
):

    x = (min_xy[0] + max_xy[0]) * 0.5
    y = (min_xy[1] + max_xy[1]) * 0.5

    empty = bpy.data.objects.new(
        name,
        None
    )

    empty.empty_display_type = "CUBE"
    empty.empty_display_size = 75.0

    empty.location = (
        x,
        y,
        z
    )

    collection.objects.link(empty)

    tag_object(
        empty,
        "REGION_CENTER",
        source_key
    )

    return empty


# ------------------------------------------------------------
# CURVE CREATION
# ------------------------------------------------------------

def create_3d_spline(
    name,
    points,
    collection,
    bevel_depth,
    category,
    source_key
):

    if len(points) < 2:
        print(
            f"[WARNING] {name} has fewer than 2 points."
        )
        return None

    curve_data = bpy.data.curves.new(
        name,
        type="CURVE"
    )

    curve_data.dimensions = "3D"

    curve_data.bevel_depth = bevel_depth
    curve_data.bevel_resolution = 3

    spline = curve_data.splines.new(
        "BEZIER"
    )

    spline.bezier_points.add(
        len(points) - 1
    )

    for i, point in enumerate(points):

        bp = spline.bezier_points[i]

        bp.co = point

        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"

    obj = bpy.data.objects.new(
        name,
        curve_data
    )

    collection.objects.link(obj)

    tag_object(
        obj,
        category,
        source_key
    )

    return obj


# ------------------------------------------------------------
# LAKE
# ------------------------------------------------------------

def create_lake(
    name,
    lake_data,
    collection
):

    center = lake_data["center"]
    radius = lake_data["radius"]
    water_z = lake_data["water_elevation"]

    curve_data = bpy.data.curves.new(
        f"{name}_OUTLINE",
        type="CURVE"
    )

    curve_data.dimensions = "3D"

    curve_data.bevel_depth = 3.0
    curve_data.bevel_resolution = 2

    spline = curve_data.splines.new(
        "POLY"
    )

    spline.points.add(
        LAKE_SEGMENTS - 1
    )

    for i in range(LAKE_SEGMENTS):

        angle = (
            2.0 *
            math.pi *
            i /
            LAKE_SEGMENTS
        )

        x = center[0] + math.cos(angle) * radius
        y = center[1] + math.sin(angle) * radius

        spline.points[i].co = (
            x,
            y,
            water_z,
            1.0
        )

    spline.use_cyclic_u = True

    outline = bpy.data.objects.new(
        name,
        curve_data
    )

    collection.objects.link(
        outline
    )

    tag_object(
        outline,
        "LAKE",
        "lake_valis"
    )

    outline["water_elevation"] = water_z
    outline["radius"] = radius

    # Create a simple surface disk.
    mesh = bpy.data.meshes.new(
        f"{name}_SURFACE_MESH"
    )

    verts = [
        (
            center[0],
            center[1],
            water_z
        )
    ]

    faces = []

    for i in range(LAKE_SEGMENTS):

        angle = (
            2.0 *
            math.pi *
            i /
            LAKE_SEGMENTS
        )

        verts.append(
            (
                center[0] +
                math.cos(angle) * radius,

                center[1] +
                math.sin(angle) * radius,

                water_z
            )
        )

    for i in range(LAKE_SEGMENTS):

        a = i + 1
        b = ((i + 1) % LAKE_SEGMENTS) + 1

        faces.append(
            (0, a, b)
        )

    mesh.from_pydata(
        verts,
        [],
        faces
    )

    mesh.update()

    surface = bpy.data.objects.new(
        f"{name}_SURFACE",
        mesh
    )

    collection.objects.link(
        surface
    )

    tag_object(
        surface,
        "LAKE_SURFACE",
        "lake_valis"
    )

    return outline


# ------------------------------------------------------------
# POI MARKER
# ------------------------------------------------------------

def create_poi(
    name,
    location,
    collection,
    source_key
):

    empty = bpy.data.objects.new(
        name,
        None
    )

    empty.empty_display_type = "SPHERE"
    empty.empty_display_size = POI_SIZE

    empty.location = location

    collection.objects.link(
        empty
    )

    tag_object(
        empty,
        "STORY_POI",
        source_key
    )

    return empty


# ------------------------------------------------------------
# LABELS
# ------------------------------------------------------------

def create_label(
    text,
    location,
    collection,
    source_key
):

    curve_data = bpy.data.curves.new(
        f"LABEL_{source_key}",
        type="FONT"
    )

    curve_data.body = text

    curve_data.align_x = "CENTER"
    curve_data.align_y = "CENTER"

    curve_data.size = LABEL_SIZE
    curve_data.extrude = 0.0

    # Make labels face upward.
    curve_data.space_character = 1.0

    obj = bpy.data.objects.new(
        f"LABEL_{source_key}",
        curve_data
    )

    obj.location = location

    # Horizontal text lying in XY plane.
    obj.rotation_euler = (
        0.0,
        0.0,
        0.0
    )

    collection.objects.link(
        obj
    )

    tag_object(
        obj,
        "LABEL",
        source_key
    )

    return obj


# ------------------------------------------------------------
# WORLD GRID
# ------------------------------------------------------------

def create_world_grid(
    collection
):

    print("[SOTF] Creating world grid...")

    verts = []
    edges = []

    extent = GRID_EXTENT
    spacing = GRID_SPACING

    positions = []

    value = -extent

    while value <= extent:

        positions.append(value)

        value += spacing

    # X lines.
    for x in positions:

        start = len(verts)

        verts.append(
            (x, -extent, 0)
        )

        verts.append(
            (x, extent, 0)
        )

        edges.append(
            (start, start + 1)
        )

    # Y lines.
    for y in positions:

        start = len(verts)

        verts.append(
            (-extent, y, 0)
        )

        verts.append(
            (extent, y, 0)
        )

        edges.append(
            (start, start + 1)
        )

    mesh = bpy.data.meshes.new(
        "WORLD_GRID_MESH"
    )

    mesh.from_pydata(
        verts,
        edges,
        []
    )

    mesh.update()

    obj = bpy.data.objects.new(
        "WORLD_GRID_1KM",
        mesh
    )

    obj.display_type = "WIRE"

    collection.objects.link(
        obj
    )

    tag_object(
        obj,
        "WORLD_GRID"
    )

    # X axis.
    axis_x_data = bpy.data.curves.new(
        "WORLD_AXIS_X",
        type="CURVE"
    )

    axis_x_data.dimensions = "3D"
    axis_x_data.bevel_depth = 5.0

    spline = axis_x_data.splines.new(
        "POLY"
    )

    spline.points.add(1)

    spline.points[0].co = (
        -extent,
        0,
        1,
        1
    )

    spline.points[1].co = (
        extent,
        0,
        1,
        1
    )

    axis_x = bpy.data.objects.new(
        "WORLD_AXIS_X",
        axis_x_data
    )

    collection.objects.link(
        axis_x
    )

    tag_object(
        axis_x,
        "WORLD_AXIS",
        "X"
    )

    # Y axis.
    axis_y_data = bpy.data.curves.new(
        "WORLD_AXIS_Y",
        type="CURVE"
    )

    axis_y_data.dimensions = "3D"
    axis_y_data.bevel_depth = 5.0

    spline = axis_y_data.splines.new(
        "POLY"
    )

    spline.points.add(1)

    spline.points[0].co = (
        0,
        -extent,
        1,
        1
    )

    spline.points[1].co = (
        0,
        extent,
        1,
        1
    )

    axis_y = bpy.data.objects.new(
        "WORLD_AXIS_Y",
        axis_y_data
    )

    collection.objects.link(
        axis_y
    )

    tag_object(
        axis_y,
        "WORLD_AXIS",
        "Y"
    )


# ------------------------------------------------------------
# ORIGIN
# ------------------------------------------------------------

def create_origin_marker(
    collection
):

    empty = bpy.data.objects.new(
        "WORLD_ORIGIN_0_0_0",
        None
    )

    empty.empty_display_type = "ARROWS"
    empty.empty_display_size = 300.0
    empty.location = (
        0.0,
        0.0,
        0.0
    )

    collection.objects.link(
        empty
    )

    tag_object(
        empty,
        "WORLD_ORIGIN"
    )


# ------------------------------------------------------------
# VIEWPORT
# ------------------------------------------------------------

def frame_world():

    for area in bpy.context.screen.areas:

        if area.type == "VIEW_3D":

            region_3d = area.spaces.active.region_3d

            region_3d.view_distance = 30000

            region_3d.view_location = (
                0.0,
                -1500.0,
                0.0
            )

            region_3d.view_rotation = (
                0.0,
                0.0,
                0.0,
                1.0
            )


# ------------------------------------------------------------
# VALIDATE JSON
# ------------------------------------------------------------

def validate_world_data(data):

    required_sections = [
        "system",
        "regions",
        "hydrology",
        "infrastructure",
        "story_lore_points",
    ]

    for section in required_sections:

        if section not in data:

            raise ValueError(
                f"Missing required JSON section: {section}"
            )

    system = data["system"]

    if system.get("units") != "meters":
        print(
            "[WARNING] World units are not meters."
        )

    if system.get("up_axis") != "Z":
        print(
            "[WARNING] World up axis is not Z."
        )

    print(
        f"[SOTF] Regions: "
        f"{len(data['regions'])}"
    )

    print(
        f"[SOTF] Story nodes: "
        f"{len(data['story_lore_points'])}"
    )


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def run():

    print("")
    print("=" * 60)
    print("SOTF — STAGE A WORLD SKELETON")
    print("=" * 60)

    # --------------------------------------------------------
    # Check JSON
    # --------------------------------------------------------

    if not os.path.isfile(JSON_PATH):

        print(
            f"[ERROR] World JSON not found:\n"
            f"{JSON_PATH}"
        )

        return

    print(
        f"[SOTF] Loading:\n{JSON_PATH}"
    )

    try:

        with open(
            JSON_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except json.JSONDecodeError as error:

        print(
            f"[ERROR] Invalid JSON:\n{error}"
        )

        return

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    try:

        validate_world_data(
            data
        )

    except ValueError as error:

        print(
            f"[ERROR] {error}"
        )

        return

    # --------------------------------------------------------
    # Clean previous generation
    # --------------------------------------------------------

    clean_stage_a()

    # --------------------------------------------------------
    # Scene
    # --------------------------------------------------------

    setup_scene()

    collections = get_stage_a_collections()

    # --------------------------------------------------------
    # World grid
    # --------------------------------------------------------

    create_world_grid(
        collections["grid"]
    )

    create_origin_marker(
        collections["grid"]
    )

    # --------------------------------------------------------
    # Regions
    # --------------------------------------------------------

    print(
        "[SOTF] Generating regional bounds..."
    )

    for key, region in data["regions"].items():

        bounds = region["bounds"]
        elevation = region["elevation"]

        min_xy = bounds["min"]
        max_xy = bounds["max"]

        z_min = elevation["min"]
        z_max = elevation["max"]

        create_bounding_box(
            f"BOUNDS_{key.upper()}",
            min_xy,
            max_xy,
            z_min,
            z_max,
            collections["regions"],
            key
        )

        center_z = (
            z_min +
            z_max
        ) * 0.5

        create_region_center(
            f"CENTER_{key.upper()}",
            min_xy,
            max_xy,
            center_z,
            collections["regions"],
            key
        )

        center_x = (
            min_xy[0] +
            max_xy[0]
        ) * 0.5

        center_y = (
            min_xy[1] +
            max_xy[1]
        ) * 0.5

        create_label(
            region["name"],
            (
                center_x,
                center_y,
                z_max + 100.0
            ),
            collections["labels"],
            f"REGION_{key}"
        )

    # --------------------------------------------------------
    # Hydrology
    # --------------------------------------------------------

    print(
        "[SOTF] Generating hydrology..."
    )

    for key, value in data["hydrology"].items():

        if key == "lake_valis":

            create_lake(
                "LAKE_VALIS",
                value,
                collections["hydrology"]
            )

            c = value["center"]

            create_label(
                "LAKE VALIS",
                (
                    c[0],
                    c[1],
                    c[2] + 50.0
                ),
                collections["labels"],
                "LAKE_VALIS"
            )

        else:

            create_3d_spline(
                f"RIVER_{key.upper()}",
                value,
                collections["hydrology"],
                RIVER_BEVEL,
                "RIVER",
                key
            )

    # --------------------------------------------------------
    # Infrastructure
    # --------------------------------------------------------

    print(
        "[SOTF] Generating infrastructure..."
    )

    for key, points in data["infrastructure"].items():

        create_3d_spline(
            f"ROAD_{key.upper()}",
            points,
            collections["infrastructure"],
            ROAD_BEVEL,
            "ROAD",
            key
        )

    # --------------------------------------------------------
    # Story / Lore nodes
    # --------------------------------------------------------

    print(
        "[SOTF] Generating story nodes..."
    )

    for key, coords in data[
        "story_lore_points"
    ].items():

        create_poi(
            f"POI_{key.upper()}",
            coords,
            collections["story"],
            key
        )

        label_z = coords[2] + POI_SIZE + 100.0

        create_label(
            key.replace("_", " ").upper(),
            (
                coords[0],
                coords[1],
                label_z
            ),
            collections["labels"],
            f"POI_{key}"
        )

    # --------------------------------------------------------
    # Metadata on root
    # --------------------------------------------------------

    root = collections["root"]

    root["sotf_generated"] = GENERATED_TAG
    root["world_source"] = JSON_PATH
    root["world_units"] = data[
        "system"
    ]["units"]

    root["up_axis"] = data[
        "system"
    ]["up_axis"]

    root["north_axis"] = data[
        "system"
    ]["north_axis"]

    root["east_axis"] = data[
        "system"
    ]["east_axis"]

    # --------------------------------------------------------
    # Finish
    # --------------------------------------------------------

    frame_world()

    print("")
    print("=" * 60)
    print(
        "[SUCCESS] SOTF Stage A generated."
    )
    print("=" * 60)
    print(
        "Source:",
        JSON_PATH
    )
    print(
        "Regions:",
        len(data["regions"])
    )
    print(
        "Hydrology:",
        len(data["hydrology"])
    )
    print(
        "Infrastructure:",
        len(data["infrastructure"])
    )
    print(
        "Story nodes:",
        len(data["story_lore_points"])
    )
    print("=" * 60)


# ------------------------------------------------------------
# EXECUTE
# ------------------------------------------------------------

if __name__ == "__main__":
    run()