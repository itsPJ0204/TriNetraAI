"""Phase 10: Public Semantic AI search integration contract verification."""

import pytest

from semantic_search import SearchResult, search
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def test_public_import_contract() -> None:
    """Verify search and SearchResult are exported at package root."""
    assert callable(search)
    assert SearchResult is not None


def test_public_search_basic() -> None:
    """Verify basic semantic search returns ranked SearchResult items."""
    results = search("river")
    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        assert isinstance(r, SearchResult)
        assert isinstance(r.tile_name, str)
        assert isinstance(r.image_path, str)
        assert isinstance(r.score, float)
        assert isinstance(r.crs, str)
        assert isinstance(r.bounds, dict)
        assert isinstance(r.width, int)
        assert isinstance(r.height, int)
        assert isinstance(r.date, str)


def test_public_search_top_k() -> None:
    """Verify top_k parameter bounds the result length accurately."""
    res_1 = search("river", top_k=1)
    assert len(res_1) == 1

    res_2 = search("river", top_k=2)
    assert len(res_2) == 2

    # Preserves cosine similarity ordering
    assert res_2[0].score >= res_2[1].score


def test_public_search_bbox() -> None:
    """Verify geographic bbox parameter filters results through public interface."""
    bbox_tile_1 = {
        "left": 77.158,
        "bottom": 28.645,
        "right": 77.178,
        "top": 28.662,
    }
    results = search("river", bbox=bbox_tile_1, top_k=5)
    assert len(results) >= 1
    assert all(r.tile_name == "sentinel2_tile_1.tif" for r in results)


def test_public_search_invalid_query() -> None:
    """Verify empty or non-string queries raise clear ValueError."""
    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        search("")

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        search("   ")

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        search(None)  # type: ignore

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        search(123)  # type: ignore


def test_public_search_invalid_top_k() -> None:
    """Verify non-positive or non-integer top_k values raise clear ValueError."""
    with pytest.raises(ValueError, match="top_k must be a positive integer."):
        search("river", top_k=0)

    with pytest.raises(ValueError, match="top_k must be a positive integer."):
        search("river", top_k=-5)

    with pytest.raises(ValueError, match="top_k must be a positive integer."):
        search("river", top_k=True)  # type: ignore

    with pytest.raises(ValueError, match="top_k must be a positive integer."):
        search("river", top_k="3")  # type: ignore


def test_public_search_no_qdrant_leakage() -> None:
    """Verify no Qdrant internal classes or attributes leak to callers."""
    results = search("green forest", top_k=3)
    for r in results:
        assert isinstance(r, SearchResult)
        # Ensure it's not a Qdrant ScoredPoint / PointStruct
        assert type(r).__name__ == "SearchResult"
        assert not hasattr(r, "payload")
        assert not hasattr(r, "vector")
        assert not hasattr(r, "shard_key")

        # Ensure dictionary serialization is pure python primitives
        d = r.to_dict()
        assert isinstance(d, dict)
        assert type(d["score"]) is float
        assert type(d["bounds"]) is dict
        assert all(type(v) is float for v in d["bounds"].values())


def test_role3_search_contract() -> None:
    """Verify Role 3 query 'buildings near a river' and all 8 required metadata attributes."""
    results = search("buildings near a river", top_k=5)
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 5

    for r in results:
        assert isinstance(r, SearchResult)
        # Check all 8 required Role 3 attributes
        assert isinstance(r.tile_name, str) and len(r.tile_name) > 0
        assert isinstance(r.image_path, str) and len(r.image_path) > 0
        assert isinstance(r.score, float)
        assert isinstance(r.crs, str) and len(r.crs) > 0
        assert isinstance(r.bounds, dict)
        for key in ("left", "bottom", "right", "top"):
            assert key in r.bounds
            assert isinstance(r.bounds[key], float)
        assert r.bounds["left"] < r.bounds["right"]
        assert r.bounds["bottom"] < r.bounds["top"]
        assert isinstance(r.width, int) and r.width > 0
        assert isinstance(r.height, int) and r.height > 0
        assert isinstance(r.date, str) and len(r.date) > 0

