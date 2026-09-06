"""Query expansion and prompt ensemble experiment for Semantic AI search."""

import csv
import json
from pathlib import Path
from typing import Any

from semantic_search.evaluation import (
    BASELINE_QUERIES,
    COMPLEX_QUERIES,
    DEFAULT_EVALUATION_DIR,
)
from semantic_search.schemas import SearchResult
from semantic_search.search import search

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Fixed, deterministic domain expansion dictionary
QUERY_EXPANSIONS: dict[str, tuple[str, ...]] = {
    # Phase 11 Baseline queries
    "river": (
        "river",
        "stream or waterway",
        "river flowing through landscape",
        "water river channel",
    ),
    "water": (
        "water",
        "body of water",
        "water surface",
        "lake river or sea",
    ),
    "road": (
        "road",
        "highway or street",
        "paved road network",
        "transportation route",
    ),
    "buildings": (
        "buildings",
        "urban structures",
        "residential and commercial buildings",
        "built-up structures",
    ),
    "urban area": (
        "urban area",
        "city or town",
        "built-up urban settlement",
        "densely populated area",
    ),
    "vegetation": (
        "vegetation",
        "green plant cover",
        "trees and foliage",
        "natural vegetation",
    ),
    "green area": (
        "green area",
        "park or grassland",
        "green landscape with vegetation",
        "foliage and open green space",
    ),
    # Phase 12 Multi-concept complex queries
    "urban areas near water": (
        "urban areas near water",
        "city waterfront",
        "urban buildings along water body",
        "settlement adjacent to water",
    ),
    "buildings near a river": (
        "buildings near a river",
        "urban buildings beside water",
        "built-up area near water",
        "structures close to a river",
    ),
    "roads through green areas": (
        "roads through green areas",
        "highway crossing vegetation",
        "road passing through green landscape",
        "paved route in countryside",
    ),
    "water surrounded by vegetation": (
        "water surrounded by vegetation",
        "pond or lake with trees",
        "water body encircled by greenery",
        "river surrounded by forest",
    ),
    "urban area with roads": (
        "urban area with roads",
        "city street grid",
        "urban settlement with transportation network",
        "built-up town with roads",
    ),
    "buildings and roads": (
        "buildings and roads",
        "built-up structures and streets",
        "urban infrastructure with buildings and roads",
        "city buildings with paved roads",
    ),
    "green area near water": (
        "green area near water",
        "greenery along riverbank",
        "park adjacent to water",
        "vegetation close to water body",
    ),
    "dense urban area": (
        "dense urban area",
        "tightly packed buildings",
        "highly built-up urban core",
        "dense city infrastructure",
    ),
}

ALL_BENCHMARK_QUERIES: tuple[str, ...] = BASELINE_QUERIES + COMPLEX_QUERIES


def get_expansions_for_query(
    query: str,
    expansions_dict: dict[str, tuple[str, ...]] | None = None,
) -> tuple[str, ...]:
    """Retrieve fixed expansions for a query, defaulting to (query,) if not mapped."""
    mapping = expansions_dict if expansions_dict is not None else QUERY_EXPANSIONS
    return mapping.get(query.strip(), (query.strip(),))


def compare_query_ensemble(
    query: str,
    expansions: tuple[str, ...] | list[str] | None = None,
    top_k: int = 4,
) -> dict[str, Any]:
    """
    Execute both single-query search and expanded prompt-ensemble search, returning detailed comparison.

    Args:
        query: Original natural-language query string.
        expansions: List of expanded query formulations (defaults to QUERY_EXPANSIONS entry).
        top_k: Number of ranked results to return (default 4).

    Returns:
        Dictionary containing single-query and ensemble rankings, scores, and comparison metadata.
    """
    # 1. Single query baseline
    single_results: list[SearchResult] = search(query=query, top_k=top_k)
    single_formatted = [
        {
            "rank": rank,
            "tile_name": r.tile_name,
            "score": float(r.score),
            "image_path": r.image_path,
            "crs": r.crs,
            "bounds": r.bounds,
            "width": r.width,
            "height": r.height,
            "date": r.date,
        }
        for rank, r in enumerate(single_results, start=1)
    ]

    # 2. Expanded prompt ensemble retrieval
    formulations = list(expansions) if expansions is not None else list(get_expansions_for_query(query))
    if query not in formulations:
        formulations.insert(0, query)

    # Accumulate scores and metadata per tile across all formulations
    tile_scores: dict[str, list[float]] = {}
    tile_meta: dict[str, SearchResult] = {}

    for prompt in formulations:
        prompt_results = search(query=prompt, top_k=top_k)
        for r in prompt_results:
            if r.tile_name not in tile_scores:
                tile_scores[r.tile_name] = []
                tile_meta[r.tile_name] = r
            tile_scores[r.tile_name].append(float(r.score))

    # Mean score averaging
    num_formulations = len(formulations)
    ensemble_scored_tiles: list[dict[str, Any]] = []

    for tile_name, scores in tile_scores.items():
        # If tile was missing in some top_k, average over total formulations
        mean_score = sum(scores) / num_formulations
        meta = tile_meta[tile_name]
        ensemble_scored_tiles.append(
            {
                "tile_name": tile_name,
                "score": float(mean_score),
                "image_path": meta.image_path,
                "crs": meta.crs,
                "bounds": meta.bounds,
                "width": meta.width,
                "height": meta.height,
                "date": meta.date,
                "raw_scores": scores,
            }
        )

    # Sort descending by ensemble score
    ensemble_scored_tiles.sort(key=lambda x: x["score"], reverse=True)
    ensemble_results = ensemble_scored_tiles[:top_k]

    for rank, item in enumerate(ensemble_results, start=1):
        item["rank"] = rank

    # Comparison metrics
    single_top = single_formatted[0]["tile_name"] if single_formatted else ""
    ensemble_top = ensemble_results[0]["tile_name"] if ensemble_results else ""
    top_rank_changed = single_top != ensemble_top

    single_top_score = single_formatted[0]["score"] if single_formatted else 0.0
    ensemble_top_score = ensemble_results[0]["score"] if ensemble_results else 0.0
    top_score_diff = round(ensemble_top_score - single_top_score, 6)

    return {
        "query": query,
        "expansions": formulations,
        "num_expansions": len(formulations),
        "top_k": top_k,
        "single_query_results": single_formatted,
        "ensemble_results": ensemble_results,
        "single_top_tile": single_top,
        "ensemble_top_tile": ensemble_top,
        "top_rank_changed": top_rank_changed,
        "top_score_diff": top_score_diff,
    }


def evaluate_query_ensemble(
    queries: tuple[str, ...] | list[str] | None = None,
    expansions_dict: dict[str, tuple[str, ...]] | None = None,
    top_k: int = 4,
) -> list[dict[str, Any]]:
    """
    Run the query ensemble comparison across a sequence of benchmark queries.
    """
    if queries is None:
        queries = ALL_BENCHMARK_QUERIES

    results: list[dict[str, Any]] = []
    for q in queries:
        exp = get_expansions_for_query(q, expansions_dict=expansions_dict)
        comp = compare_query_ensemble(query=q, expansions=exp, top_k=top_k)
        results.append(comp)

    return results


def calculate_ensemble_statistics(ensemble_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate descriptive comparison statistics for the ensemble experiment."""
    total = len(ensemble_data)
    changed = sum(1 for d in ensemble_data if d["top_rank_changed"])
    unchanged = total - changed
    score_diffs = [d["top_score_diff"] for d in ensemble_data]
    avg_diff = sum(score_diffs) / total if total > 0 else 0.0

    return {
        "total_queries": total,
        "top_rank_changed_count": changed,
        "top_rank_unchanged_count": unchanged,
        "percent_changed": round((changed / total) * 100, 2) if total > 0 else 0.0,
        "percent_unchanged": round((unchanged / total) * 100, 2) if total > 0 else 0.0,
        "avg_top_score_diff": round(avg_diff, 6),
    }


def save_ensemble_results(
    ensemble_data: list[dict[str, Any]],
    output_dir: Path | str = DEFAULT_EVALUATION_DIR,
    filename_prefix: str = "query_ensemble_results",
) -> tuple[Path, Path]:
    """
    Save ensemble comparison results to JSON and CSV artifacts.
    """
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    json_path = target_dir / f"{filename_prefix}.json"
    csv_path = target_dir / f"{filename_prefix}.csv"

    stats = calculate_ensemble_statistics(ensemble_data)
    json_payload = {
        "benchmark_summary": stats,
        "results": ensemble_data,
    }

    # Write JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2)

    # Write CSV
    fieldnames = [
        "query",
        "rank",
        "single_tile",
        "single_score",
        "ensemble_tile",
        "ensemble_score",
        "top_rank_changed",
        "single_top_tile",
        "ensemble_top_tile",
        "top_score_diff",
        "num_expansions",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in ensemble_data:
            q = item["query"]
            s_results = {r["rank"]: r for r in item["single_query_results"]}
            e_results = {r["rank"]: r for r in item["ensemble_results"]}
            max_ranks = max(len(s_results), len(e_results))

            for rank in range(1, max_ranks + 1):
                s_r = s_results.get(rank, {})
                e_r = e_results.get(rank, {})
                writer.writerow(
                    {
                        "query": q,
                        "rank": rank,
                        "single_tile": s_r.get("tile_name", ""),
                        "single_score": s_r.get("score", ""),
                        "ensemble_tile": e_r.get("tile_name", ""),
                        "ensemble_score": e_r.get("score", ""),
                        "top_rank_changed": item["top_rank_changed"],
                        "single_top_tile": item["single_top_tile"],
                        "ensemble_top_tile": item["ensemble_top_tile"],
                        "top_score_diff": item["top_score_diff"],
                        "num_expansions": item["num_expansions"],
                    }
                )

    return json_path, csv_path


def format_ensemble_report(ensemble_data: list[dict[str, Any]]) -> str:
    """Produce human-readable text comparison table."""
    stats = calculate_ensemble_statistics(ensemble_data)
    lines: list[str] = [
        "=" * 78,
        "      SEMANTIC AI QUERY EXPANSION / PROMPT ENSEMBLE EXPERIMENT REPORT",
        "=" * 78,
    ]

    for item in ensemble_data:
        q = item["query"]
        changed_flag = "[CHANGED]" if item["top_rank_changed"] else "[SAME]"
        lines.append(f"\nQuery: '{q}' (Expansions: {item['num_expansions']}) -> Top Rank: {changed_flag}")
        lines.append(f"  Expansions: {item['expansions']}")
        lines.append("-" * 78)
        lines.append(
            f"{'Rank':<6} {'Single-Query Tile':<18} {'Single Score':<14} {'Ensemble Tile':<18} {'Ensemble Score':<14}"
        )
        lines.append("-" * 78)

        s_dict = {r["rank"]: r for r in item["single_query_results"]}
        e_dict = {r["rank"]: r for r in item["ensemble_results"]}
        for rank in range(1, item["top_k"] + 1):
            s_tile = s_dict.get(rank, {}).get("tile_name", "-")
            s_score = f"{s_dict.get(rank, {}).get('score', 0.0):.6f}" if rank in s_dict else "-"
            e_tile = e_dict.get(rank, {}).get("tile_name", "-")
            e_score = f"{e_dict.get(rank, {}).get('score', 0.0):.6f}" if rank in e_dict else "-"
            lines.append(f"{rank:<6} {s_tile:<18} {s_score:<14} {e_tile:<18} {e_score:<14}")

    lines.append("\n" + "=" * 78)
    lines.append("                         EXPERIMENT SUMMARY")
    lines.append("=" * 78)
    lines.append(f"Total Queries Evaluated       : {stats['total_queries']}")
    lines.append(f"Top-Ranked Tile Changed       : {stats['top_rank_changed_count']} ({stats['percent_changed']}%)")
    lines.append(f"Top-Ranked Tile Unchanged     : {stats['top_rank_unchanged_count']} ({stats['percent_unchanged']}%)")
    lines.append(f"Average Top Score Difference  : {stats['avg_top_score_diff']:+.6f}")
    lines.append("=" * 78)

    return "\n".join(lines)
