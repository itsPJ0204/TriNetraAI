"""Performance benchmark for Semantic AI satellite search components and end-to-end latency."""

import time
import sys
from pathlib import Path
from typing import Any

from semantic_search.model import load_remoteclip
from semantic_search.search import search, text_to_embedding, normalize_query
from semantic_search.vector_store import get_qdrant_client, COLLECTION_NAME


BENCHMARK_QUERIES = [
    "river",
    "water",
    "buildings",
    "urban area",
    "buildings near a river",
    "roads through green areas",
]


def run_component_benchmarks() -> dict[str, Any]:
    """Profile isolated components: model load, tokenization, inference, Qdrant query."""
    print("=" * 78)
    print("       PART 1: COMPONENT-LEVEL LATENCY BREAKDOWN (MICRO-BENCHMARK)")
    print("=" * 78)

    # 1. Model Cold Load Time
    t0 = time.perf_counter()
    model, tokenizer, _ = load_remoteclip(device="cpu")
    t_model_load = time.perf_counter() - t0
    print(f"1. RemoteCLIP Model Cold Load Time : {t_model_load * 1000:.2f} ms ({t_model_load:.4f} s)")

    # 2. Text Tokenization Time
    sample_query = "buildings near a river"
    tok_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        _ = tokenizer([sample_query])
        tok_times.append(time.perf_counter() - t0)
    avg_tok_ms = (sum(tok_times) / len(tok_times)) * 1000
    print(f"2. Tokenization Latency (Avg 50)   : {avg_tok_ms:.4f} ms")

    # 3. Text Embedding Generation Time
    emb_times = []
    for q in BENCHMARK_QUERIES:
        t0 = time.perf_counter()
        vec = text_to_embedding(q)
        emb_times.append(time.perf_counter() - t0)
    avg_emb_ms = (sum(emb_times) / len(emb_times)) * 1000
    print(f"3. text_to_embedding() Latency     : {avg_emb_ms:.2f} ms (Avg over {len(BENCHMARK_QUERIES)} queries)")

    # 4. Qdrant Client Creation & Vector Query Time
    client = get_qdrant_client()
    query_vector = vec.tolist()
    qdrant_times = []
    for _ in range(20):
        t0 = time.perf_counter()
        _ = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=4,
            with_payload=True,
            with_vectors=False,
        )
        qdrant_times.append(time.perf_counter() - t0)
    avg_qdrant_ms = (sum(qdrant_times) / len(qdrant_times)) * 1000
    print(f"4. Qdrant Query Latency (Avg 20)   : {avg_qdrant_ms:.2f} ms")

    return {
        "model_load_ms": t_model_load * 1000,
        "tokenization_ms": avg_tok_ms,
        "embedding_gen_ms": avg_emb_ms,
        "qdrant_query_ms": avg_qdrant_ms,
    }


def run_search_benchmarks(repetitions: int = 5) -> dict[str, Any]:
    """Profile full end-to-end search() cold-start and warm latency."""
    print("\n" + "=" * 78)
    print("       PART 2: END-TO-END search() LATENCY BENCHMARK")
    print("=" * 78)

    # Cold start search (first query executed)
    cold_query = BENCHMARK_QUERIES[0]
    t0 = time.perf_counter()
    _ = search(cold_query, top_k=4)
    cold_search_time = time.perf_counter() - t0
    print(f"Cold-Start Search Time ('{cold_query}') : {cold_search_time * 1000:.2f} ms ({cold_search_time:.4f} s)")

    # Warm searches across all benchmark queries
    warm_latencies = []
    print(f"\nRunning warm searches ({repetitions} repetitions x {len(BENCHMARK_QUERIES)} queries = {repetitions * len(BENCHMARK_QUERIES)} searches)...")

    for rep in range(repetitions):
        for q in BENCHMARK_QUERIES:
            t0 = time.perf_counter()
            res = search(q, top_k=4)
            dur_ms = (time.perf_counter() - t0) * 1000
            warm_latencies.append(dur_ms)

    avg_warm = sum(warm_latencies) / len(warm_latencies)
    min_warm = min(warm_latencies)
    max_warm = max(warm_latencies)

    print(f"Warm Search Average Latency : {avg_warm:.2f} ms")
    print(f"Warm Search Min Latency     : {min_warm:.2f} ms")
    print(f"Warm Search Max Latency     : {max_warm:.2f} ms")
    print(f"Total Warm Queries Tested   : {len(warm_latencies)}")
    print("=" * 78)

    return {
        "cold_start_search_ms": cold_search_time * 1000,
        "warm_search_avg_ms": avg_warm,
        "warm_search_min_ms": min_warm,
        "warm_search_max_ms": max_warm,
        "total_queries_tested": len(warm_latencies),
    }


def main() -> int:
    try:
        comp_results = run_component_benchmarks()
        search_results = run_search_benchmarks(repetitions=3)
    except Exception as exc:
        print(f"[ERROR] Benchmark failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
