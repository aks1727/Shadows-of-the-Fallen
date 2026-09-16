import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

WORLD_MASTER_PATH = (
    PROJECT_ROOT
    / "00_WORLD_MASTER"
    / "coordinates"
    / "world_master.json"
)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def overlap(a_min, a_max, b_min, b_max):
    x_overlap = a_min[0] < b_max[0] and b_min[0] < a_max[0]
    y_overlap = a_min[1] < b_max[1] and b_min[1] < a_max[1]
    return x_overlap and y_overlap


def touch_or_near(a_min, a_max, b_min, b_max, tolerance=1):
    x_gap = max(0, max(b_min[0] - a_max[0], a_min[0] - b_max[0]))
    y_gap = max(0, max(b_min[1] - a_max[1], a_min[1] - b_max[1]))

    return x_gap <= tolerance and y_gap <= tolerance


def main():
    print("=" * 72)
    print("SHADOWS OF THE FALLEN")
    print("WORLD MASTER REGION LAYOUT DIAGNOSTIC")
    print("=" * 72)

    world = load_json(WORLD_MASTER_PATH)
    regions = world["regions"]

    print("\nREGION CENTERS")
    print("-" * 72)

    region_data = []

    for region_id, region in regions.items():
        bounds = region["bounds"]

        min_x, min_y = bounds["min"]
        max_x, max_y = bounds["max"]

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        region_data.append(
            {
                "id": region_id,
                "min": [min_x, min_y],
                "max": [max_x, max_y],
                "center": [center_x, center_y],
            }
        )

        print(
            f"{region_id:24s}"
            f" center=({center_x:8.1f}, {center_y:8.1f})"
            f" bounds=({min_x},{min_y}) → ({max_x},{max_y})"
        )

    print("\nREGION RELATIONSHIPS")
    print("-" * 72)

    for i in range(len(region_data)):
        a = region_data[i]

        for j in range(i + 1, len(region_data)):
            b = region_data[j]

            if overlap(
                a["min"],
                a["max"],
                b["min"],
                b["max"],
            ):
                relationship = "OVERLAP"

            elif touch_or_near(
                a["min"],
                a["max"],
                b["min"],
                b["max"],
                tolerance=1,
            ):
                relationship = "TOUCHING / SHARED EDGE"

            else:
                relationship = None

            if relationship:
                print(
                    f"{a['id']:24s} ↔ "
                    f"{b['id']:24s} : {relationship}"
                )

    print("\nWORLD EXTENT")
    print("-" * 72)

    min_x = min(r["min"][0] for r in region_data)
    min_y = min(r["min"][1] for r in region_data)
    max_x = max(r["max"][0] for r in region_data)
    max_y = max(r["max"][1] for r in region_data)

    print(f"X: {min_x} → {max_x}")
    print(f"Y: {min_y} → {max_y}")

    print("\nKALDAR CANDIDATE REGION")
    print("-" * 72)

    print(
        "western_timber is currently the only existing "
        "World Master region flagged as a possible Kaldar candidate."
    )

    print(
        "\nIMPORTANT:"
        "\nThis script does NOT modify world_master.json."
        "\nIt only reports spatial relationships."
    )

    print("\n" + "=" * 72)
    print("STATUS: DIAGNOSTIC COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()
