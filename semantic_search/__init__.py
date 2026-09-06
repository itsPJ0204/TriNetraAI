"""Semantic AI module for satellite image semantic search."""

from semantic_search.evaluation import BASELINE_QUERIES, COMPLEX_QUERIES, evaluate_queries
from semantic_search.ground_truth import (
    get_relevant_tiles,
    load_ground_truth,
    validate_ground_truth,
)
from semantic_search.metrics import (
    calculate_hit_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_reciprocal_rank,
    evaluate_ensemble_retrieval_metrics,
    evaluate_retrieval_metrics,
)
from semantic_search.query_expansion import (
    ALL_BENCHMARK_QUERIES,
    QUERY_EXPANSIONS,
    compare_query_ensemble,
    evaluate_query_ensemble,
)
from semantic_search.model import clear_model_cache, load_remoteclip
from semantic_search.schemas import SearchResult
from semantic_search.search import (
    clear_query_cache,
    get_query_cache_size,
    normalize_query,
    search,
)
from semantic_search.vector_store import clear_client_cache, get_qdrant_client

__all__ = [
    "search",
    "normalize_query",
    "SearchResult",
    "BASELINE_QUERIES",
    "COMPLEX_QUERIES",
    "ALL_BENCHMARK_QUERIES",
    "QUERY_EXPANSIONS",
    "evaluate_queries",
    "compare_query_ensemble",
    "evaluate_query_ensemble",
    "load_ground_truth",
    "validate_ground_truth",
    "get_relevant_tiles",
    "calculate_hit_at_k",
    "calculate_precision_at_k",
    "calculate_recall_at_k",
    "calculate_reciprocal_rank",
    "evaluate_retrieval_metrics",
    "evaluate_ensemble_retrieval_metrics",
    "clear_model_cache",
    "clear_client_cache",
    "clear_query_cache",
    "get_query_cache_size",
    "load_remoteclip",
    "get_qdrant_client",
]
