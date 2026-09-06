"""Evaluation framework for Semantic AI search baseline and quality benchmarking."""

import csv
import json
from pathlib import Path
from typing import Any

from semantic_search.schemas import SearchResult
from semantic_search.search import search

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"

BASELINE_QUERIES: tuple[str, ...] = (
    "river",
    "water",
    "road",
    "buildings",
    "urban area",
    "vegetation",
    "green area",
)

COMPLEX_QUERIES: tuple[str, ...] = (
    "urban areas near water",
    "buildings near a river",
    "roads through green areas",
    "water surrounded by vegetation",
    "urban area with roads",
    "buildings and roads",
    "green area near water",
    "dense urban area",
)


def evaluate_queries(
    queries: tuple[str, ...] | list[str] | None = None,
    top_k: int = 4,
) -> list[dict[str, Any]]:
    """
    Evaluate a fixed set of natural-language queries against the semantic search index.

    Args:
        queries: Sequence of query strings to test. Defaults to BASELINE_QUERIES.
        top_k: Number of top results to retrieve per query (default 4).

    Returns:
        A list of evaluation dictionaries, each containing query text and its ranked results.
    """
    if queries is None:
        queries = BASELINE_QUERIES

    evaluation_report: list[dict[str, Any]] = []

    for query in queries:
        search_results: list[SearchResult] = search(query=query, top_k=top_k)

        query_record: dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "num_results": len(search_results),
            "results": [],
        }

        for rank, result in enumerate(search_results, start=1):
            query_record["results"].append(
                {
                    "rank": rank,
                    "tile_name": result.tile_name,
                    "score": result.score,
                    "image_path": result.image_path,
                    "crs": result.crs,
                    "bounds": result.bounds,
                    "width": result.width,
                    "height": result.height,
                    "date": result.date,
                }
            )

        evaluation_report.append(query_record)

    return evaluation_report


def save_evaluation_results(
    evaluation_data: list[dict[str, Any]],
    output_dir: Path | str = DEFAULT_EVALUATION_DIR,
    filename_prefix: str = "baseline_results",
) -> tuple[Path, Path]:
    """
    Save evaluation results to both JSON and CSV files.

    Args:
        evaluation_data: Output from `evaluate_queries`.
        output_dir: Target directory path for storing evaluation result files.
        filename_prefix: File name prefix for output artifacts (e.g. 'baseline_results', 'complex_query_results').

    Returns:
        Tuple of (json_path, csv_path).
    """
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / f"{filename_prefix}.json"
    csv_path = target_dir / f"{filename_prefix}.csv"

    # Write JSON report
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_data, f, indent=2)

    # Write CSV report (flattened per rank)
    fieldnames = [
        "query",
        "rank",
        "tile_name",
        "score",
        "image_path",
        "crs",
        "bounds_left",
        "bounds_bottom",
        "bounds_right",
        "bounds_top",
        "width",
        "height",
        "date",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in evaluation_data:
            query_text = item["query"]
            for r in item["results"]:
                bounds = r.get("bounds", {})
                writer.writerow(
                    {
                        "query": query_text,
                        "rank": r["rank"],
                        "tile_name": r["tile_name"],
                        "score": r["score"],
                        "image_path": r["image_path"],
                        "crs": r["crs"],
                        "bounds_left": bounds.get("left", ""),
                        "bounds_bottom": bounds.get("bottom", ""),
                        "bounds_right": bounds.get("right", ""),
                        "bounds_top": bounds.get("top", ""),
                        "width": r["width"],
                        "height": r["height"],
                        "date": r["date"],
                    }
                )

    return json_path, csv_path


def format_evaluation_report(
    evaluation_data: list[dict[str, Any]],
    title: str = "SEMANTIC AI EVALUATION REPORT",
) -> str:
    """Format evaluation data into a human-readable text report."""
    lines: list[str] = [
        "=" * 70,
        f"             {title}",
        "=" * 70,
    ]

    for item in evaluation_data:
        query = item["query"]
        lines.append(f"\nQuery: '{query}' (Results: {item['num_results']})")
        lines.append("-" * 70)
        lines.append(
            f"{'Rank':<6} {'Tile Name':<15} {'Score':<10} {'Dimensions':<12} {'Date':<12}"
        )
        lines.append("-" * 70)
        for r in item["results"]:
            dims = f"{r['width']}x{r['height']}"
            lines.append(
                f"{r['rank']:<6} {r['tile_name']:<15} {r['score']:<10.6f} {dims:<12} {r['date']:<12}"
            )

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)

