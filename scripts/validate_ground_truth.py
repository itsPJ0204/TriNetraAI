"""CLI tool to inspect and validate the human ground-truth dataset."""

import argparse
from pathlib import Path
import sys

from semantic_search.ground_truth import (
    DEFAULT_GROUND_TRUTH_PATH,
    load_ground_truth,
    validate_ground_truth,
)


def main() -> int:
    """Run ground-truth dataset validation and print summary report."""
    parser = argparse.ArgumentParser(
        description="Validate satellite semantic search ground-truth dataset."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_GROUND_TRUTH_PATH,
        help="Path to ground_truth.json (default: data/evaluation/ground_truth.json)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("           GROUND-TRUTH DATASET VALIDATION REPORT")
    print("=" * 80)
    print(f"Dataset path: {args.path.resolve()}")

    try:
        data = load_ground_truth(args.path)
    except Exception as exc:
        print(f"\n[ERROR] Could not load dataset: {exc}")
        return 1

    metadata_version = data.get("version", "unknown")
    metadata_date = data.get("created_at", "unknown")
    queries_dict = data.get("queries", {})

    print(f"Dataset Version : {metadata_version}")
    print(f"Created Date    : {metadata_date}")
    print(f"Total Queries   : {len(queries_dict)}")
    print("-" * 80)
    print(f"{'Query':<32} {'Relevant Tiles':<25} {'Uncertainty Note':<20}")
    print("-" * 80)

    for q_name, q_rec in queries_dict.items():
        rel_tiles = ", ".join(q_rec.get("relevant_tiles", []))
        uncert = q_rec.get("uncertainty", "None")
        # Truncate uncertainty for clean table display
        uncert_short = (uncert[:25] + "...") if len(uncert) > 28 else uncert
        print(f"{q_name:<32} {rel_tiles:<25} {uncert_short:<20}")

    print("=" * 80)

    errors = validate_ground_truth(data=data, path=args.path)
    if errors:
        print("\n[VALIDATION FAILED] The following integrity errors were found:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\n[VALIDATION SUCCESSFUL] Ground truth dataset is valid, consistent, and all tiles exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
