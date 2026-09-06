"""Ground-truth dataset handling and validation for Semantic AI evaluation."""

import json
from pathlib import Path
from typing import Any

from semantic_search.evaluation import BASELINE_QUERIES, COMPLEX_QUERIES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "evaluation" / "ground_truth.json"
DEFAULT_TILES_DIR = PROJECT_ROOT / "data" / "tiles"

VALID_TILE_NAMES: tuple[str, ...] = (
    "tile_1.tif",
    "tile_2.tif",
    "tile_3.tif",
    "tile_4.tif",
)

EXPECTED_BENCHMARK_QUERIES: tuple[str, ...] = BASELINE_QUERIES + COMPLEX_QUERIES


def load_ground_truth(
    path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Load the ground-truth annotations JSON file.

    Args:
        path: Path to ground_truth.json. Defaults to data/evaluation/ground_truth.json.

    Returns:
        Dictionary containing parsed ground truth dataset.

    Raises:
        FileNotFoundError: If the ground truth file does not exist.
        ValueError: If JSON is malformed.
    """
    target_path = Path(path) if path is not None else DEFAULT_GROUND_TRUTH_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Ground truth file not found at: {target_path}")

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in ground truth file ({target_path}): {exc}") from exc

    return data


def validate_ground_truth(
    data: dict[str, Any] | None = None,
    path: Path | str | None = None,
    tiles_dir: Path | str | None = None,
) -> list[str]:
    """
    Validate the ground-truth dataset integrity and consistency.

    Validation checks:
    - Dataset is a JSON dictionary with 'queries'.
    - Every referenced tile physically exists on disk.
    - Tile names are strictly within valid names ('tile_1.tif' .. 'tile_4.tif').
    - Every expected benchmark query is present.
    - Each query record has a non-empty list of 'relevant_tiles' without duplicates.
    - Each query record has 'notes' and 'uncertainty' fields.
    - No malformed records exist.

    Args:
        data: In-memory parsed ground truth dictionary (if None, loaded from path).
        path: Ground-truth file path if data is not supplied.
        tiles_dir: Directory containing tile GeoTIFF files for existence check.

    Returns:
        A list of validation error strings. If empty, validation passed.
    """
    errors: list[str] = []

    if data is None:
        try:
            data = load_ground_truth(path)
        except Exception as exc:
            return [f"Failed to load ground truth: {exc}"]

    if not isinstance(data, dict):
        return ["Ground truth root must be a JSON object (dict)."]

    if "queries" not in data or not isinstance(data["queries"], dict):
        errors.append("Missing or invalid 'queries' object in ground truth root.")
        return errors

    queries_dict = data["queries"]
    target_tiles_dir = Path(tiles_dir) if tiles_dir is not None else DEFAULT_TILES_DIR

    # Check that all expected benchmark queries are present
    for query in EXPECTED_BENCHMARK_QUERIES:
        if query not in queries_dict:
            errors.append(f"Missing expected benchmark query: '{query}'")

    # Validate each query record
    for q_name, q_record in queries_dict.items():
        if not isinstance(q_record, dict):
            errors.append(f"Record for query '{q_name}' must be a dictionary.")
            continue

        if "relevant_tiles" not in q_record:
            errors.append(f"Query '{q_name}' is missing 'relevant_tiles' field.")
            continue

        relevant_tiles = q_record["relevant_tiles"]
        if not isinstance(relevant_tiles, list):
            errors.append(f"'relevant_tiles' for query '{q_name}' must be a list.")
            continue

        if len(relevant_tiles) == 0:
            errors.append(f"'relevant_tiles' for query '{q_name}' is empty.")

        # Check for duplicates
        if len(relevant_tiles) != len(set(relevant_tiles)):
            errors.append(f"Duplicate tile names found in 'relevant_tiles' for query '{q_name}'.")

        # Check tile validity and physical existence
        for tile in relevant_tiles:
            if not isinstance(tile, str):
                errors.append(f"Invalid tile type for query '{q_name}': {tile}")
                continue

            if tile not in VALID_TILE_NAMES:
                errors.append(
                    f"Query '{q_name}' references invalid tile '{tile}'. Allowed: {VALID_TILE_NAMES}"
                )

            tile_file = target_tiles_dir / tile
            if not tile_file.exists():
                errors.append(f"Query '{q_name}' references non-existent tile file: {tile_file}")

        # Check metadata fields in record
        if "notes" not in q_record or not isinstance(q_record["notes"], str) or not q_record["notes"].strip():
            errors.append(f"Query '{q_name}' is missing a descriptive 'notes' string.")

        if "uncertainty" not in q_record or not isinstance(q_record["uncertainty"], str):
            errors.append(f"Query '{q_name}' is missing an 'uncertainty' field.")

    return errors


def get_relevant_tiles(
    query: str,
    ground_truth_data: dict[str, Any] | None = None,
) -> list[str]:
    """
    Retrieve the list of relevant tile filenames for a given query.

    Args:
        query: Query string to look up.
        ground_truth_data: Loaded ground truth data. If None, loaded from disk.

    Returns:
        List of relevant tile filename strings.

    Raises:
        KeyError: If query is not found in ground truth dataset.
    """
    if ground_truth_data is None:
        ground_truth_data = load_ground_truth()

    queries = ground_truth_data.get("queries", {})
    if query not in queries:
        raise KeyError(f"Query '{query}' not found in ground truth dataset.")

    return list(queries[query].get("relevant_tiles", []))
