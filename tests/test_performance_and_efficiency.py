"""Phase 17: Performance, model caching, resource efficiency, and regression tests."""

import numpy as np
import pytest

from semantic_search import (
    SearchResult,
    clear_client_cache,
    clear_model_cache,
    clear_query_cache,
    get_qdrant_client,
    get_query_cache_size,
    load_remoteclip,
    normalize_query,
    search,
)
from semantic_search.search import text_to_embedding
from semantic_search.vector_store import COLLECTION_NAME


def test_model_reuse_and_identity() -> None:
    """Verify load_remoteclip returns the same cached instance across multiple invocations."""
    m1, tok1, prep1 = load_remoteclip(device="cpu")
    m2, tok2, prep2 = load_remoteclip(device="cpu")

    assert m1 is m2
    assert tok1 is tok2
    assert prep1 is prep2

    # Verify reload=True generates a fresh instance
    m3, tok3, prep3 = load_remoteclip(device="cpu", reload=True)
    assert m3 is not m1


def test_client_reuse_and_caching() -> None:
    """Verify get_qdrant_client reuses connection pool across repeated invocations."""
    c1 = get_qdrant_client()
    c2 = get_qdrant_client()
    assert c1 is c2

    # Verify clear_client_cache resets pool
    clear_client_cache()
    c3 = get_qdrant_client()
    assert c3 is not None


def test_query_embedding_cache_behavior() -> None:
    """Verify in-memory query embedding cache hit, miss, and clear behavior."""
    clear_query_cache()
    assert get_query_cache_size() == 0

    # First computation (cache miss)
    emb1 = text_to_embedding("buildings near a river", use_cache=True)
    assert get_query_cache_size() == 1
    assert emb1.shape == (512,)
    assert emb1.dtype == np.float32

    # Second retrieval (cache hit, normalized whitespace variant)
    emb2 = text_to_embedding("  buildings   near   a   river  ", use_cache=True)
    assert get_query_cache_size() == 1
    assert np.allclose(emb1, emb2)

    # Mutating returned copy does not affect cache
    emb1[0] = 999.0
    emb3 = text_to_embedding("buildings near a river", use_cache=True)
    assert emb3[0] != 999.0

    clear_query_cache()
    assert get_query_cache_size() == 0


def test_repeated_searches_return_consistent_search_results() -> None:
    """Verify repeated search invocations maintain exact consistency without side effects."""
    query = "urban area with roads"

    run_1 = search(query, top_k=4)
    run_2 = search(query, top_k=4)

    assert len(run_1) == len(run_2) == 4
    for r1, r2 in zip(run_1, run_2):
        assert isinstance(r1, SearchResult)
        assert isinstance(r2, SearchResult)
        assert r1.tile_name == r2.tile_name
        assert pytest.approx(r1.score, rel=1e-5) == r2.score
        assert r1.bounds == r2.bounds
        assert r1.crs == r2.crs


def test_embedding_normalization_and_dimension_invariant() -> None:
    """Verify text embeddings strictly adhere to 512-dim float32 unit-length vector constraints."""
    test_queries = ["river", "green vegetation", "dense urban city", "waterway"]
    for q in test_queries:
        vec = text_to_embedding(q)
        assert vec.shape == (512,)
        assert vec.dtype == np.float32
        norm = float(np.linalg.norm(vec))
        assert pytest.approx(norm, rel=1e-4) == 1.0


def test_bbox_filtering_remains_active_with_caching() -> None:
    """Verify dynamic bounding-box filtering continues to execute correctly when embeddings are cached."""
    bbox_tile_1 = {
        "left": 77.158,
        "bottom": 28.645,
        "right": 77.178,
        "top": 28.662,
    }
    # First search without bbox
    all_results = search("river", top_k=4)
    assert len(all_results) == 4

    # Second search with bbox (reuses cached embedding, executes filtered Qdrant query)
    filtered_results = search("river", bbox=bbox_tile_1, top_k=4)
    assert len(filtered_results) == 1
    assert filtered_results[0].tile_name == "sentinel2_tile_1.tif"


def test_qdrant_integrity_and_immutability() -> None:
    """Verify Qdrant collection point count and dimension remain strictly preserved."""
    client = get_qdrant_client()
    count = client.count(COLLECTION_NAME, exact=True).count
    info = client.get_collection(COLLECTION_NAME)

    assert count == 30
    assert info.config.params.vectors.size == 512
    assert str(info.config.params.vectors.distance).lower().endswith("cosine")
