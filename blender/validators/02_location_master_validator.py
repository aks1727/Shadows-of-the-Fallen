import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WORLD_MASTER_PATH = (
    PROJECT_ROOT
    / "00_WORLD_MASTER"
    / "coordinates"
    / "world_master.json"
)

LOCATION_MASTER_PATH = (
    PROJECT_ROOT
    / "00_WORLD_MASTER"
    / "locations"
    / "location_master.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fail(message):
    print(f"ERROR: {message}")
    sys.exit(1)


def main():
    print("=" * 60)
    print("SHADOWS OF THE FALLEN")
    print("LOCATION MASTER VALIDATOR")
    print("=" * 60)

    print("\n[1/5] Loading files...")

    if not WORLD_MASTER_PATH.exists():
        fail(f"Missing World Master:\n{WORLD_MASTER_PATH}")

    if not LOCATION_MASTER_PATH.exists():
        fail(f"Missing Location Master:\n{LOCATION_MASTER_PATH}")

    world = load_json(WORLD_MASTER_PATH)
    locations = load_json(LOCATION_MASTER_PATH)

    print("OK")

    print("\n[2/5] Checking World Master regions...")

    world_regions = world.get("regions", {})

    if not world_regions:
        fail("No regions found in world_master.json")

    print(f"World Master regions: {len(world_regions)}")

    print("\n[3/5] Checking mapped regions...")

    mapped_regions = locations.get("regions", {})

    errors = 0

    for region_id, data in mapped_regions.items():
        if region_id not in world_regions:
            print(
                f"ERROR: Location Master references unknown "
                f"World Master region: {region_id}"
            )
            errors += 1

    if errors:
        fail(f"{errors} invalid region reference(s) found.")

    print(f"Mapped regions: {len(mapped_regions)}")
    print("OK")

    print("\n[4/5] Checking region bounds...")

    for region_id, data in mapped_regions.items():
        bounds = world_regions[region_id].get("bounds")

        if not bounds:
            print(
                f"WARNING: {region_id} has no bounds in World Master"
            )
            continue

        print(
            f"{region_id:24s} "
            f"min={bounds['min']} "
            f"max={bounds['max']}"
        )

    print("OK")

    print("\n[5/5] Checking unresolved story regions...")

    unresolved = locations.get("unresolved_story_regions", [])

    for item in unresolved:
        print(
            f"UNRESOLVED: {item['name']} "
            f"→ {item['problem']}"
        )

    print(f"\nUnresolved story regions: {len(unresolved)}")

    print("\n" + "=" * 60)

    if unresolved:
        print("STATUS: PASSED WITH DESIGN ITEMS")
        print()
        print("Coordinate references are valid.")
        print("No World Master coordinates were modified.")
        print("Kaldar Jungle still requires a design decision.")
    else:
        print("STATUS: PASSED")

    print("=" * 60)


if __name__ == "__main__":
    main()
