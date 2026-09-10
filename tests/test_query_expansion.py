"""Phase 13: Query expansion and prompt ensemble experiment verification."""

import csv
import json
from pathlib import Path
import pytest

from semantic_search.evaluation import BASELINE_QUERIES, COMPLEX_QUERIES
from semantic_search.query_expansion import (
    ALL_BENCHMARK_QUERIES,
    QUERY_EXPANSIONS,
    calculate_ensemble_statistics,
    compare_query_ensemble,
    evaluate_query_ensemble,
    format_ensemble_report,
    get_expansions_for_query,
    save_ensemble_results,
)
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def test_query_expansions_completeness() -> None:
    """Verify that all 15 benchmark queries have defined, deterministic expansions."""
    all_queries = BASELINE_QUERIES + COMPLEX_QUERIES
    assert len(all_queries) == 15

    for q in all_queries:
        assert q in QUERY_EXPANSIONS
        expansions = QUERY_EXPANSIONS[q]
        assert isinstance(expansions, tuple)
        assert len(expansions) >= 2
        # Original query must be present in its expansion set
        assert q in expansions
        assert all(isinstance(e, str) and len(e.strip()) > 0 for e in expansions)


def test_get_expansions_fallback() -> None:
    """Verify unmapped queries default cleanly to a single-item tuple of the query itself."""
    unmapped = "custom uncharted terrain"
    exp = get_expansions_for_query(unmapped)
    assert exp == (unmapped,)


def test_compare_query_ensemble_structure() -> None:
    """Verify compare_query_ensemble produces expected structure and clean metadata."""
    query = "buildings near a river"
    comp = compare_query_ensemble(query=query, top_k=4)

    assert comp["query"] == query
    assert isinstance(comp["expansions"], list)
    assert comp["num_expansions"] == len(comp["expansions"])
    assert comp["top_k"] == 4

    # Single results
    assert len(comp["single_query_results"]) == 4
    for r in comp["single_query_results"]:
        assert "tile_name" in r
        assert "score" in r
        assert "crs" in r
        assert "bounds" in r
        assert "width" in r
        assert "height" in r
        assert "date" in r
        assert not hasattr(r, "payload")
        assert not hasattr(r, "vector")

    # Ensemble results
    assert len(comp["ensemble_results"]) == 4
    for r in comp["ensemble_results"]:
        assert "tile_name" in r
        assert "score" in r
        assert "raw_scores" in r
        assert 1 <= len(r["raw_scores"]) <= comp["num_expansions"]

    # Scores must be sorted descending
    single_scores = [r["score"] for r in comp["single_query_results"]]
    assert single_scores == sorted(single_scores, reverse=True)

    ensemble_scores = [r["score"] for r in comp["ensemble_results"]]
    assert ensemble_scores == sorted(ensemble_scores, reverse=True)

    assert isinstance(comp["top_rank_changed"], bool)
    assert isinstance(comp["top_score_diff"], float)


def test_ensemble_deterministic_repeatability() -> None:
    """Verify running ensemble comparison multiple times produces identical rankings."""
    q = "river"
    run_1 = compare_query_ensemble(q, top_k=4)
    run_2 = compare_query_ensemble(q, top_k=4)

    tiles_1 = [r["tile_name"] for r in run_1["ensemble_results"]]
    tiles_2 = [r["tile_name"] for r in run_2["ensemble_results"]]
    assert tiles_1 == tiles_2

    scores_1 = [r["score"] for r in run_1["ensemble_results"]]
    scores_2 = [r["score"] for r in run_2["ensemble_results"]]
    assert pytest.approx(scores_1, rel=1e-5) == scores_2


def test_calculate_ensemble_statistics() -> None:
    """Verify aggregate summary statistics computation."""
    sample_data = [
        {
            "query": "q1",
            "top_rank_changed": True,
            "top_score_diff": 0.05,
        },
        {
            "query": "q2",
            "top_rank_changed": False,
            "top_score_diff": -0.01,
        },
    ]
    stats = calculate_ensemble_statistics(sample_data)
    assert stats["total_queries"] == 2
    assert stats["top_rank_changed_count"] == 1
    assert stats["top_rank_unchanged_count"] == 1
    assert stats["percent_changed"] == 50.0
    assert stats["percent_unchanged"] == 50.0
    assert stats["avg_top_score_diff"] == 0.02


def test_save_ensemble_results(tmp_path: Path) -> None:
    """Verify ensemble artifacts write to query_ensemble_results.json and .csv."""
    sample_queries = ("water",)
    data = evaluate_query_ensemble(queries=sample_queries, top_k=2)

    json_path, csv_path = save_ensemble_results(
        data, output_dir=tmp_path, filename_prefix="query_ensemble_results"
    )

    assert json_path.name == "query_ensemble_results.json"
    assert csv_path.name == "query_ensemble_results.csv"
    assert json_path.exists()
    assert csv_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert "benchmark_summary" in loaded
    assert "results" in loaded
    assert loaded["results"][0]["query"] == "water"

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert "single_tile" in rows[0]
    assert "ensemble_tile" in rows[0]
    assert "top_score_diff" in rows[0]


def test_format_ensemble_report() -> None:
    """Verify human-readable table output."""
    sample_queries = ("urban area",)
    data = evaluate_query_ensemble(queries=sample_queries, top_k=2)
    report = format_ensemble_report(data)
    assert "PROMPT ENSEMBLE EXPERIMENT REPORT" in report
    assert "urban area" in report
    assert "Single-Query Tile" in report
    assert "Ensemble Tile" in report
    assert "EXPERIMENT SUMMARY" in report


def test_qdrant_and_existing_artifacts_preserved(tmp_path: Path) -> None:
    """Verify Qdrant collection is unchanged and previous artifacts are untouched."""
    client = get_qdrant_client()
    count_before = client.count(COLLECTION_NAME, exact=True).count
    info_before = client.get_collection(COLLECTION_NAME)

    # Run ensemble
    evaluate_query_ensemble(queries=("river", "road"), top_k=4)

    count_after = client.count(COLLECTION_NAME, exact=True).count
    info_after = client.get_collection(COLLECTION_NAME)

    assert count_before == count_after == 90
    assert info_before.config.params.vectors.size == info_after.config.params.vectors.size == 512
