"""Phase 11 & 12: Evaluation and baseline framework tests."""

import csv
import json
from pathlib import Path
import pytest

from semantic_search.evaluation import (
    BASELINE_QUERIES,
    COMPLEX_QUERIES,
    evaluate_queries,
    format_evaluation_report,
    save_evaluation_results,
)
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def test_baseline_queries_defined() -> None:
    """Verify baseline query set covers expected satellite semantic search domains."""
    expected_queries = {
        "river",
        "water",
        "road",
        "buildings",
        "urban area",
        "vegetation",
        "green area",
    }
    assert isinstance(BASELINE_QUERIES, (tuple, list))
    assert expected_queries.issubset(set(BASELINE_QUERIES))


def test_complex_queries_defined() -> None:
    """Verify complex multi-concept query set is defined and covers expected queries."""
    expected_complex = {
        "urban areas near water",
        "buildings near a river",
        "roads through green areas",
        "water surrounded by vegetation",
        "urban area with roads",
        "buildings and roads",
        "green area near water",
        "dense urban area",
    }
    assert isinstance(COMPLEX_QUERIES, (tuple, list))
    assert expected_complex.issubset(set(COMPLEX_QUERIES))
    # Ensure baseline and complex are distinct sets
    assert set(BASELINE_QUERIES).isdisjoint(set(COMPLEX_QUERIES))


def test_evaluate_queries_structure() -> None:
    """Verify evaluation returns well-formed records with all expected metadata fields."""
    sample_queries = ("river", "vegetation")
    eval_data = evaluate_queries(queries=sample_queries, top_k=4)

    assert len(eval_data) == 2
    for item in eval_data:
        assert item["query"] in sample_queries
        assert item["top_k"] == 4
        assert item["num_results"] == 4
        assert len(item["results"]) == 4

        for rank, r in enumerate(item["results"], start=1):
            assert r["rank"] == rank
            assert isinstance(r["tile_name"], str) and r["tile_name"].endswith(".tif")
            assert isinstance(r["score"], float)
            assert isinstance(r["image_path"], str)
            assert isinstance(r["crs"], str) and len(r["crs"]) > 0
            assert isinstance(r["bounds"], dict)
            assert all(k in r["bounds"] for k in ("left", "bottom", "right", "top"))
            assert isinstance(r["width"], int) and r["width"] > 0
            assert isinstance(r["height"], int) and r["height"] > 0
            assert isinstance(r["date"], str)


def test_evaluation_ranks_ordered_by_score() -> None:
    """Verify rankings within each query are monotonically ordered by descending score."""
    eval_data = evaluate_queries(queries=("river",), top_k=4)
    results = eval_data[0]["results"]
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_save_evaluation_results(tmp_path: Path) -> None:
    """Verify JSON and CSV artifacts are generated accurately."""
    sample_queries = ("water",)
    eval_data = evaluate_queries(queries=sample_queries, top_k=2)

    json_path, csv_path = save_evaluation_results(eval_data, output_dir=tmp_path)

    assert json_path.exists()
    assert csv_path.exists()

    # Verify JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
    assert len(loaded_json) == 1
    assert loaded_json[0]["query"] == "water"
    assert len(loaded_json[0]["results"]) == 2

    # Verify CSV content
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["query"] == "water"
    assert "score" in rows[0]
    assert "tile_name" in rows[0]


def test_format_evaluation_report() -> None:
    """Verify human-readable report formatting produces descriptive table text."""
    eval_data = evaluate_queries(queries=("road",), top_k=2)
    report_text = format_evaluation_report(
        eval_data, title="SEMANTIC AI BASELINE EVALUATION REPORT"
    )
    assert "SEMANTIC AI BASELINE EVALUATION REPORT" in report_text
    assert "road" in report_text
    assert "Tile Name" in report_text


def test_evaluate_complex_queries_structure() -> None:
    """Verify evaluating complex queries produces valid ranked SearchResult records."""
    sample_complex = ("urban areas near water", "dense urban area")
    eval_data = evaluate_queries(queries=sample_complex, top_k=4)

    assert len(eval_data) == 2
    for item in eval_data:
        assert item["query"] in sample_complex
        assert item["top_k"] == 4
        assert len(item["results"]) == 4

        # Validate monotonic score order
        scores = [r["score"] for r in item["results"]]
        assert scores == sorted(scores, reverse=True)


def test_save_complex_evaluation_results(tmp_path: Path) -> None:
    """Verify complex query evaluation results are saved under complex_query_results filename."""
    sample_queries = ("buildings near a river",)
    eval_data = evaluate_queries(queries=sample_queries, top_k=2)

    json_path, csv_path = save_evaluation_results(
        eval_data,
        output_dir=tmp_path,
        filename_prefix="complex_query_results",
    )

    assert json_path.name == "complex_query_results.json"
    assert csv_path.name == "complex_query_results.csv"
    assert json_path.exists()
    assert csv_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded[0]["query"] == "buildings near a river"


def test_evaluation_does_not_modify_qdrant() -> None:
    """Verify that running evaluation is strictly read-only and does not alter collection state."""
    client = get_qdrant_client()
    count_before = client.count(COLLECTION_NAME, exact=True).count
    info_before = client.get_collection(COLLECTION_NAME)

    # Run evaluation
    evaluate_queries(queries=("buildings",), top_k=4)

    count_after = client.count(COLLECTION_NAME, exact=True).count
    info_after = client.get_collection(COLLECTION_NAME)

    assert count_before == count_after == 4
    assert info_before.config.params.vectors.size == info_after.config.params.vectors.size == 512

