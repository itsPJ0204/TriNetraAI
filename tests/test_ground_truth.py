"""Phase 14: Ground-truth dataset validation and integrity tests."""

import json
from pathlib import Path
import pytest

from semantic_search.evaluation import BASELINE_QUERIES, COMPLEX_QUERIES
from semantic_search.ground_truth import (
    DEFAULT_GROUND_TRUTH_PATH,
    EXPECTED_BENCHMARK_QUERIES,
    VALID_TILE_NAMES,
    get_relevant_tiles,
    load_ground_truth,
    validate_ground_truth,
)
from semantic_search.search import search
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def test_ground_truth_file_loads() -> None:
    """Verify ground_truth.json loads successfully as valid JSON with core metadata."""
    assert DEFAULT_GROUND_TRUTH_PATH.exists()

    data = load_ground_truth()
    assert isinstance(data, dict)
    assert "version" in data
    assert "created_at" in data
    assert "dataset_tiles" in data
    assert "queries" in data
    assert isinstance(data["queries"], dict)
    assert len(data["dataset_tiles"]) == 4


def test_all_expected_benchmark_concepts_exist() -> None:
    """Verify all 15 benchmark queries (7 baseline + 8 complex) are defined in ground truth."""
    data = load_ground_truth()
    queries = data["queries"]

    for q in BASELINE_QUERIES:
        assert q in queries, f"Baseline query '{q}' missing from ground truth"

    for q in COMPLEX_QUERIES:
        assert q in queries, f"Complex query '{q}' missing from ground truth"

    assert len(queries) >= 15


def test_all_referenced_tiles_exist() -> None:
    """Verify all referenced tiles in ground truth exist on disk and are strictly within valid names."""
    data = load_ground_truth()
    queries = data["queries"]

    for q_name, q_rec in queries.items():
        assert "relevant_tiles" in q_rec, f"Query '{q_name}' missing relevant_tiles"
        tiles = q_rec["relevant_tiles"]
        assert isinstance(tiles, list), f"relevant_tiles for '{q_name}' is not a list"
        assert len(tiles) > 0, f"relevant_tiles for '{q_name}' is empty"

        for tile in tiles:
            assert tile in VALID_TILE_NAMES, f"Query '{q_name}' references invalid tile '{tile}'"
            tile_path = Path("data/tiles") / tile
            assert tile_path.exists(), f"Tile file {tile_path} does not exist on disk"


def test_no_duplicate_tiles_per_query() -> None:
    """Verify no query record contains duplicate tile entries."""
    data = load_ground_truth()
    queries = data["queries"]

    for q_name, q_rec in queries.items():
        tiles = q_rec["relevant_tiles"]
        assert len(tiles) == len(set(tiles)), f"Duplicate tile names in query '{q_name}'"


def test_query_metadata_notes_and_uncertainty() -> None:
    """Verify every query has descriptive visual rationale notes and an uncertainty field."""
    data = load_ground_truth()
    queries = data["queries"]

    for q_name, q_rec in queries.items():
        assert "notes" in q_rec, f"Query '{q_name}' missing notes"
        assert isinstance(q_rec["notes"], str) and len(q_rec["notes"].strip()) > 0
        assert "uncertainty" in q_rec, f"Query '{q_name}' missing uncertainty"
        assert isinstance(q_rec["uncertainty"], str)


def test_validate_ground_truth_success() -> None:
    """Verify validate_ground_truth() passes with 0 errors on actual dataset."""
    errors = validate_ground_truth()
    assert errors == [], f"Ground truth validation failed with errors: {errors}"


def test_validate_ground_truth_detects_errors(tmp_path: Path) -> None:
    """Verify validation utility correctly identifies anomalies."""
    # Test missing queries section
    bad_data_1 = {"version": "1.0.0"}
    errors_1 = validate_ground_truth(bad_data_1)
    assert any("Missing or invalid 'queries'" in e for e in errors_1)

    # Test invalid tile reference
    bad_data_2 = {
        "queries": {
            **{q: {"relevant_tiles": ["tile_1.tif"], "notes": "n", "uncertainty": "u"} for q in EXPECTED_BENCHMARK_QUERIES},
            "river": {"relevant_tiles": ["non_existent_tile.tif"], "notes": "n", "uncertainty": "u"},
        }
    }
    errors_2 = validate_ground_truth(bad_data_2)
    assert any("invalid tile 'non_existent_tile.tif'" in e for e in errors_2)

    # Test duplicate tiles
    bad_data_3 = {
        "queries": {
            **{q: {"relevant_tiles": ["tile_1.tif"], "notes": "n", "uncertainty": "u"} for q in EXPECTED_BENCHMARK_QUERIES},
            "water": {"relevant_tiles": ["tile_1.tif", "tile_1.tif"], "notes": "n", "uncertainty": "u"},
        }
    }
    errors_3 = validate_ground_truth(bad_data_3)
    assert any("Duplicate tile names" in e for e in errors_3)


def test_get_relevant_tiles_helper() -> None:
    """Verify helper function retrieves expected ground truth lists."""
    river_tiles = get_relevant_tiles("river")
    assert river_tiles == ["tile_1.tif"]

    water_tiles = get_relevant_tiles("water")
    assert "tile_1.tif" in water_tiles
    assert "tile_4.tif" in water_tiles

    with pytest.raises(KeyError):
        get_relevant_tiles("unregistered_random_concept")


def test_qdrant_and_search_unchanged() -> None:
    """Verify vector collection and production search() remain completely unchanged."""
    client = get_qdrant_client()
    count = client.count(COLLECTION_NAME, exact=True).count
    info = client.get_collection(COLLECTION_NAME)

    assert count == 4
    assert info.config.params.vectors.size == 512

    # Verify search still operates as normal
    results = search("river", top_k=2)
    assert len(results) == 2
    assert results[0].tile_name == "tile_1.tif"
