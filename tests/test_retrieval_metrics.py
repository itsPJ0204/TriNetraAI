"""Phase 15: Retrieval quality metrics unit and integration tests."""

import csv
import json
from pathlib import Path
import pytest

from semantic_search.metrics import (
    calculate_aggregate_metrics,
    calculate_hit_at_k,
    calculate_precision_at_k,
    calculate_query_metrics,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
    evaluate_ensemble_retrieval_metrics,
    evaluate_retrieval_metrics,
    generate_retrieval_metrics_report,
    save_metrics_results,
)
from semantic_search.search import search
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def test_calculate_hit_at_k_deterministic() -> None:
    """Verify Hit@K metric logic across ranks and edge cases."""
    retrieved = ["tile_1.tif", "tile_2.tif", "tile_3.tif", "tile_4.tif"]
    relevant = {"tile_2.tif"}

    assert calculate_hit_at_k(retrieved, relevant, k=1) == 0
    assert calculate_hit_at_k(retrieved, relevant, k=2) == 1
    assert calculate_hit_at_k(retrieved, relevant, k=3) == 1
    assert calculate_hit_at_k(retrieved, relevant, k=4) == 1

    # No relevant items
    assert calculate_hit_at_k(retrieved, {"tile_99.tif"}, k=4) == 0

    # Edge cases
    assert calculate_hit_at_k(retrieved, relevant, k=0) == 0
    assert calculate_hit_at_k(retrieved, relevant, k=-1) == 0
    assert calculate_hit_at_k([], relevant, k=3) == 0
    assert calculate_hit_at_k(retrieved, [], k=3) == 0


def test_calculate_precision_at_k_deterministic() -> None:
    """Verify Precision@K computation and rounding."""
    retrieved = ["tile_1.tif", "tile_2.tif", "tile_3.tif", "tile_4.tif"]
    relevant = {"tile_1.tif", "tile_3.tif"}

    assert calculate_precision_at_k(retrieved, relevant, k=1) == 1.0  # 1/1
    assert calculate_precision_at_k(retrieved, relevant, k=2) == 0.5  # 1/2
    assert calculate_precision_at_k(retrieved, relevant, k=3) == pytest.approx(0.666667, rel=1e-5)  # 2/3
    assert calculate_precision_at_k(retrieved, relevant, k=4) == 0.5  # 2/4

    # Zero relevant in top K
    assert calculate_precision_at_k(retrieved, {"tile_4.tif"}, k=1) == 0.0

    # Edge cases
    assert calculate_precision_at_k(retrieved, relevant, k=0) == 0.0
    assert calculate_precision_at_k([], relevant, k=2) == 0.0


def test_calculate_recall_at_k_deterministic() -> None:
    """Verify Recall@K computation and rounding."""
    retrieved = ["tile_1.tif", "tile_2.tif", "tile_3.tif", "tile_4.tif"]
    relevant = {"tile_1.tif", "tile_3.tif", "tile_4.tif"}  # 3 total relevant

    assert calculate_recall_at_k(retrieved, relevant, k=1) == pytest.approx(0.333333, rel=1e-5)  # 1/3
    assert calculate_recall_at_k(retrieved, relevant, k=2) == pytest.approx(0.333333, rel=1e-5)  # 1/3
    assert calculate_recall_at_k(retrieved, relevant, k=3) == pytest.approx(0.666667, rel=1e-5)  # 2/3
    assert calculate_recall_at_k(retrieved, relevant, k=4) == 1.0  # 3/3

    # Edge cases
    assert calculate_recall_at_k(retrieved, [], k=2) == 0.0
    assert calculate_recall_at_k([], relevant, k=2) == 0.0
    assert calculate_recall_at_k(retrieved, relevant, k=0) == 0.0


def test_calculate_reciprocal_rank_deterministic() -> None:
    """Verify reciprocal rank computation across all rank positions."""
    retrieved = ["tile_1.tif", "tile_2.tif", "tile_3.tif", "tile_4.tif"]

    assert calculate_reciprocal_rank(retrieved, {"tile_1.tif"}) == 1.0  # 1/1
    assert calculate_reciprocal_rank(retrieved, {"tile_2.tif"}) == 0.5  # 1/2
    assert calculate_reciprocal_rank(retrieved, {"tile_3.tif"}) == pytest.approx(0.333333, rel=1e-5)  # 1/3
    assert calculate_reciprocal_rank(retrieved, {"tile_4.tif"}) == 0.25  # 1/4

    # When multiple relevant items exist, first rank is used
    assert calculate_reciprocal_rank(retrieved, {"tile_2.tif", "tile_4.tif"}) == 0.5

    # No match
    assert calculate_reciprocal_rank(retrieved, {"tile_99.tif"}) == 0.0
    assert calculate_reciprocal_rank([], {"tile_1.tif"}) == 0.0
    assert calculate_reciprocal_rank(retrieved, []) == 0.0


def test_calculate_query_and_aggregate_metrics() -> None:
    """Verify query metrics bundle and aggregate summary calculation."""
    retrieved = ["tile_1.tif", "tile_2.tif", "tile_3.tif", "tile_4.tif"]
    relevant = ["tile_1.tif"]
    m = calculate_query_metrics(retrieved, relevant, ks=(1, 3, 4))

    assert m["hit_at_1"] == 1.0
    assert m["hit_at_3"] == 1.0
    assert m["hit_at_4"] == 1.0
    assert m["precision_at_1"] == 1.0
    assert m["recall_at_1"] == 1.0
    assert m["reciprocal_rank"] == 1.0

    # Aggregate test
    mock_records = [
        {"metrics": {"hit_at_1": 1.0, "precision_at_1": 1.0, "recall_at_1": 1.0, "hit_at_3": 1.0, "precision_at_3": 0.333333, "recall_at_3": 1.0, "hit_at_4": 1.0, "precision_at_4": 0.25, "recall_at_4": 1.0, "reciprocal_rank": 1.0}},
        {"metrics": {"hit_at_1": 0.0, "precision_at_1": 0.0, "recall_at_1": 0.0, "hit_at_3": 1.0, "precision_at_3": 0.333333, "recall_at_3": 1.0, "hit_at_4": 1.0, "precision_at_4": 0.25, "recall_at_4": 1.0, "reciprocal_rank": 0.5}},
    ]
    agg = calculate_aggregate_metrics(mock_records, ks=(1, 3, 4))
    assert agg["total_queries"] == 2.0
    assert agg["mean_hit_at_1"] == 0.5
    assert agg["mean_precision_at_1"] == 0.5
    assert agg["mrr"] == 0.75


def test_evaluate_retrieval_metrics_integration() -> None:
    """Verify integration evaluation of search against real ground truth."""
    sample_queries = ("river", "water")
    results = evaluate_retrieval_metrics(queries=sample_queries, top_k=4)

    assert results["evaluation_type"] == "single_query_search"
    assert results["total_queries"] == 2
    assert "overall_aggregate" in results
    assert "query_results" in results
    assert len(results["query_results"]) == 2

    river_res = next(r for r in results["query_results"] if r["query"] == "river")
    assert river_res["retrieved_tiles"][0] == "tile_1.tif"
    assert river_res["relevant_tiles"] == ["tile_1.tif"]
    assert river_res["metrics"]["hit_at_1"] == 1.0
    assert river_res["metrics"]["precision_at_1"] == 1.0
    assert river_res["metrics"]["recall_at_1"] == 1.0
    assert river_res["metrics"]["reciprocal_rank"] == 1.0


def test_evaluate_ensemble_retrieval_metrics_integration() -> None:
    """Verify integration evaluation of prompt ensemble comparison."""
    sample_queries = ("river",)
    results = evaluate_ensemble_retrieval_metrics(queries=sample_queries, top_k=4)

    assert results["evaluation_type"] == "single_vs_ensemble_comparison"
    assert results["total_queries"] == 1
    assert "single_aggregate" in results
    assert "ensemble_aggregate" in results
    assert "delta_aggregate" in results

    comp_rec = results["query_comparisons"][0]
    assert comp_rec["query"] == "river"
    assert "single_metrics" in comp_rec
    assert "ensemble_metrics" in comp_rec
    assert "delta_metrics" in comp_rec


def test_save_metrics_results(tmp_path: Path) -> None:
    """Verify artifact persistence writes valid JSON and CSV files."""
    sample_queries = ("river",)
    metrics_data = evaluate_retrieval_metrics(queries=sample_queries, top_k=4)

    json_path, csv_path = save_metrics_results(
        metrics_data, output_dir=tmp_path, filename_prefix="test_metrics"
    )

    assert json_path.exists()
    assert csv_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["total_queries"] == 1

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["query"] == "river"
    assert rows[0]["hit_at_1"] == "1.0"


def test_generate_retrieval_metrics_report(tmp_path: Path) -> None:
    """Verify formatted text report generation and limitations documentation."""
    sample_queries = ("river", "buildings")
    single_metrics = evaluate_retrieval_metrics(queries=sample_queries, top_k=4)
    ens_metrics = evaluate_ensemble_retrieval_metrics(queries=sample_queries, top_k=4)

    report_file = tmp_path / "test_report.txt"
    report_text = generate_retrieval_metrics_report(
        single_metrics, ens_metrics, output_path=report_file
    )

    assert report_file.exists()
    assert "SEMANTIC AI RETRIEVAL QUALITY EVALUATION REPORT" in report_text
    assert "AGGREGATE RETRIEVAL METRICS" in report_text
    assert "SINGLE QUERY VS PROMPT ENSEMBLE COMPARISON" in report_text
    assert "INTERPRETATION & METHODOLOGICAL LIMITATIONS" in report_text


def test_qdrant_and_search_immutability() -> None:
    """Verify collection points and vector properties remain strictly unmodified."""
    client = get_qdrant_client()
    count = client.count(COLLECTION_NAME, exact=True).count
    info = client.get_collection(COLLECTION_NAME)

    assert count == 30
    assert info.config.params.vectors.size == 512

    # Verify search still operates cleanly
    results = search("river", top_k=2)
    assert len(results) == 2
    assert results[0].tile_name.endswith(".tif")
