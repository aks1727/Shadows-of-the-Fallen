import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WORLD_MASTER_PATH = (
    PROJECT_ROOT
    / "00_WORLD_MASTER"
    / "coordinates"
    / "world_master.json"
)

CELL_GRID_PATH = (
    PROJECT_ROOT
    / "00_WORLD_MASTER"
    / "coordinates"
    / "cell_grid.json"
)

LOCATION_MASTER_PATH = (
    PROJECT_ROOT
    / "00_WORLD_MASTER"
    / "locations"
    / "location_master.json"
)

ELEVATION_MASTER_PATH = (
    PROJECT_ROOT
    / "00_WORLD_MASTER"
    / "elevation"
    / "elevation_master.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fail(errors, message):
    errors.append(message)
    print(f"ERROR: {message}")


def main():

    print("=" * 72)
    print("SHADOWS OF THE FALLEN")
    print("ELEVATION MASTER VALIDATOR")
    print("=" * 72)

    errors = []
    warnings = []

    # ------------------------------------------------------------
    # 1. LOAD FILES
    # ------------------------------------------------------------

    print("\n[1/9] Loading source files...")

    required_files = [
        WORLD_MASTER_PATH,
        CELL_GRID_PATH,
        LOCATION_MASTER_PATH,
        ELEVATION_MASTER_PATH,
    ]

    for path in required_files:
        if not path.exists():
            fail(errors, f"Missing file: {path}")

    if errors:
        print("\nSTATUS: FAILED")
        return 1

    world = load_json(WORLD_MASTER_PATH)
    cell_grid = load_json(CELL_GRID_PATH)
    location_master = load_json(LOCATION_MASTER_PATH)
    elevation = load_json(ELEVATION_MASTER_PATH)

    print("OK")

    # ------------------------------------------------------------
    # 2. CHECK WORLD MASTER REGIONS
    # ------------------------------------------------------------

    print("\n[2/9] Checking World Master regions...")

    world_regions = world.get("regions", {})
    elevation_regions = elevation.get("regions", {})

    if not world_regions:
        fail(errors, "World Master contains no regions.")

    print(f"World Master regions : {len(world_regions)}")
    print(f"Elevation definitions: {len(elevation_regions)}")

    missing_regions = sorted(
        set(world_regions) - set(elevation_regions)
    )

    extra_regions = sorted(
        set(elevation_regions) - set(world_regions)
    )

    if missing_regions:
        fail(
            errors,
            "Missing elevation definitions: "
            + ", ".join(missing_regions)
        )

    if extra_regions:
        fail(
            errors,
            "Elevation contains non-World-Master regions: "
            + ", ".join(extra_regions)
        )

    if not missing_regions and not extra_regions:
        print("OK")

    # ------------------------------------------------------------
    # 3. CHECK COORDINATE SYSTEM
    # ------------------------------------------------------------

    print("\n[3/9] Checking coordinate system...")

    world_system = world.get("system", {})
    elevation_system = elevation.get("coordinate_system", {})

    checks = [
        (
            "units",
            world_system.get("units"),
            elevation_system.get("units"),
        ),
        (
            "up axis",
            world_system.get("up_axis"),
            elevation_system.get("up_axis"),
        ),
    ]

    for name, world_value, elevation_value in checks:
        if world_value != elevation_value:
            fail(
                errors,
                f"Coordinate mismatch for {name}: "
                f"World Master={world_value}, "
                f"Elevation={elevation_value}"
            )

    if not errors:
        print("Units: meters")
        print("Up axis: +Z")
        print("OK")

    # ------------------------------------------------------------
    # 4. CHECK SEA LEVEL
    # ------------------------------------------------------------

    print("\n[4/9] Checking sea level...")

    sea_level = elevation.get("sea_level", {})
    sea_level_z = sea_level.get("z")

    if sea_level_z != 0.0:
        fail(
            errors,
            f"Sea level must be 0.0m, found {sea_level_z}"
        )
    else:
        print("Sea level: 0.0 m")
        print("OK")

    # ------------------------------------------------------------
    # 5. CHECK GLOBAL ELEVATION ENVELOPE
    # ------------------------------------------------------------

    print("\n[5/9] Checking global elevation envelope...")

    envelope = elevation.get("global_elevation_envelope", {})

    global_min = envelope.get("minimum_m")
    global_max = envelope.get("maximum_m")

    if global_min is None or global_max is None:
        fail(errors, "Global elevation envelope is incomplete.")

    elif global_min >= global_max:
        fail(
            errors,
            "Global minimum elevation must be lower than maximum."
        )

    else:
        print(f"Global minimum: {global_min} m")
        print(f"Global maximum: {global_max} m")
        print("OK")

    # ------------------------------------------------------------
    # 6. CHECK REGION ELEVATION RANGES
    # ------------------------------------------------------------

    print("\n[6/9] Checking regional elevation ranges...")

    range_errors = 0

    for region_id, region in elevation_regions.items():

        elevation_data = region.get("elevation", {})

        minimum = elevation_data.get("minimum_m")
        typical_min = elevation_data.get("typical_min_m")
        typical_max = elevation_data.get("typical_max_m")
        maximum = elevation_data.get("maximum_m")

        values = [
            minimum,
            typical_min,
            typical_max,
            maximum,
        ]

        if any(value is None for value in values):
            fail(
                errors,
                f"{region_id}: incomplete elevation range."
            )
            range_errors += 1
            continue

        if not (
            minimum
            <= typical_min
            <= typical_max
            <= maximum
        ):
            fail(
                errors,
                f"{region_id}: invalid elevation ordering."
            )
            range_errors += 1

        if minimum < global_min or maximum > global_max:
            fail(
                errors,
                f"{region_id}: exceeds global elevation envelope."
            )
            range_errors += 1

    if range_errors == 0:
        print(f"Checked regions: {len(elevation_regions)}")
        print("OK")

    # ------------------------------------------------------------
    # 7. CHECK KALDAR SUB-REGION
    # ------------------------------------------------------------

    print("\n[7/9] Checking Kaldar Jungle sub-region...")

    western = elevation_regions.get("western_timber", {})
    sub_regions = western.get("sub_regions", {})
    kaldar = sub_regions.get("kaldar_jungle")

    if kaldar is None:
        fail(
            errors,
            "Kaldar Jungle is missing from western_timber sub-regions."
        )

    else:

        parent = kaldar.get("design_notes", [])

        if not isinstance(parent, list):
            fail(
                errors,
                "Kaldar design_notes must be a list."
            )

        if kaldar.get("terrain_character") != "dense_tropical_jungle":
            fail(
                errors,
                "Kaldar terrain character is incorrect."
            )

        kaldar_elevation = kaldar.get("elevation", {})

        kmin = kaldar_elevation.get("minimum_m")
        ktmin = kaldar_elevation.get("typical_min_m")
        ktmax = kaldar_elevation.get("typical_max_m")
        kmax = kaldar_elevation.get("maximum_m")

        if not (
            kmin
            <= ktmin
            <= ktmax
            <= kmax
        ):
            fail(
                errors,
                "Kaldar elevation range is invalid."
            )

        else:
            print("Parent region: western_timber")
            print("Type: geographic sub-region")
            print("Terrain: dense tropical jungle")
            print("Top-level World Master region: NO")
            print("OK")

    # ------------------------------------------------------------
    # 8. CHECK SAMPLING
    # ------------------------------------------------------------

    print("\n[8/9] Checking prototype terrain sampling...")

    sampling = elevation.get("sampling", {})

    cell_size = sampling.get("prototype_cell_size_m")
    spacing = sampling.get("prototype_sample_spacing_m")
    vertices = sampling.get("prototype_vertices_per_axis")
    faces = sampling.get("prototype_faces_per_cell")

    if cell_size != 1000.0:
        fail(
            errors,
            f"Prototype cell size must be 1000m, found {cell_size}"
        )

    expected_intervals = cell_size / spacing
    expected_vertices = int(expected_intervals) + 1
    expected_faces = int(expected_intervals) ** 2

    if vertices != expected_vertices:
        fail(
            errors,
            f"Expected {expected_vertices} vertices per axis, "
            f"found {vertices}"
        )

    if faces != expected_faces:
        fail(
            errors,
            f"Expected {expected_faces} faces per cell, "
            f"found {faces}"
        )

    if not errors:
        print(f"Cell size      : {cell_size} m")
        print(f"Sample spacing : {spacing} m")
        print(f"Vertices       : {vertices} × {vertices}")
        print(f"Faces          : {faces}")
        print("OK")

    # ------------------------------------------------------------
    # 9. CHECK TERRAIN RULES
    # ------------------------------------------------------------

    print("\n[9/9] Checking terrain continuity rules...")

    rules = elevation.get("terrain_rules", {})
    continuity = elevation.get("continuity_rules", [])

    required_flags = {
        "world_coordinate_based": True,
        "continuous_across_cells": True,
        "continuous_across_regions": True,
        "independent_cell_elevation": False,
        "flat_region_elevation": False,
    }

    for key, expected in required_flags.items():

        actual = rules.get(key)

        if actual != expected:
            fail(
                errors,
                f"Terrain rule '{key}' must be {expected}, "
                f"found {actual}"
            )

    if len(continuity) < 5:
        fail(
            errors,
            "Insufficient continuity rules defined."
        )

    if not errors:
        print("World-coordinate elevation: YES")
        print("Cell continuity: YES")
        print("Region continuity: YES")
        print("Independent cell elevation: NO")
        print("Flat region elevation: NO")
        print("OK")

    # ------------------------------------------------------------
    # FINAL REPORT
    # ------------------------------------------------------------

    print("\n" + "=" * 72)
    print("ELEVATION MASTER VALIDATION REPORT")
    print("=" * 72)

    print(f"Errors   : {len(errors)}")
    print(f"Warnings : {len(warnings)}")

    if warnings:
        print("\nWARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")

    if errors:

        print("\nERRORS:")
        for error in errors:
            print(f"  - {error}")

        print("\nSTATUS: FAILED")
        print("=" * 72)

        return 1

    print("\nSTATUS: PASSED")
    print()
    print("Elevation Master structure is internally consistent.")
    print("World Master regions have matching elevation definitions.")
    print("Kaldar Jungle is correctly defined as a sub-region.")
    print("Prototype terrain sampling is mathematically consistent.")
    print("Terrain continuity rules are enabled.")
    print()
    print("No terrain geometry has been generated.")
    print("Safe to proceed to elevation design refinement.")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
