"""Phase 6 and Phase 8 verification for text-to-satellite-tile semantic search with geographic filtering."""

import numbers
from unittest.mock import patch

import pytest
from qdrant_client import models

from semantic_search.schemas import SearchResult
from semantic_search.search import build_geographic_filter, search, validate_bbox
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def test_search_result_schema_instantiation() -> None:
    """Test that SearchResult schema instantiates properly with all expected attributes and to_dict."""
    sample = SearchResult(
        tile_name="tile_1.tif",
        image_path="data/tiles/tile_1.tif",
        score=0.85,
        crs="EPSG:4326",
        bounds={"left": 88.34, "bottom": 22.57, "right": 88.36, "top": 22.58},
        width=233,
        height=191,
        date="2025-03-29",
    )
    assert sample.tile_name == "tile_1.tif"
    assert sample.image_path == "data/tiles/tile_1.tif"
    assert sample.score == 0.85
    assert sample.crs == "EPSG:4326"
    assert sample.width == 233
    assert sample.height == 191
    assert sample.date == "2025-03-29"
    assert sample["tile_name"] == "tile_1.tif"
    assert "score" in sample

    d = sample.to_dict()
    assert isinstance(d, dict)
    assert d["tile_name"] == "tile_1.tif"
    assert d["bounds"]["left"] == 88.34


def test_semantic_search_unfiltered() -> None:
    """Test A: Confirm semantic search without a geographic filter returns typed SearchResult matches."""
    client = get_qdrant_client()
    assert client.collection_exists(COLLECTION_NAME)

    results = search("river", top_k=4)

    assert isinstance(results, list)
    assert len(results) == 4
    for result in results:
        assert isinstance(result, SearchResult)
        assert isinstance(result.tile_name, str) and result.tile_name.endswith(".tif")
        assert isinstance(result.image_path, str) and result.image_path.startswith("data/tiles/")
        assert isinstance(result.score, float)
        assert isinstance(result.crs, str) and len(result.crs) > 0
        assert isinstance(result.width, int) and result.width > 0
        assert isinstance(result.height, int) and result.height > 0
        assert isinstance(result.date, str) and result.date == "2025-03-29"

        # Check bounds structure
        assert isinstance(result.bounds, dict)
        assert all(k in result.bounds for k in ("left", "bottom", "right", "top"))
        assert result.bounds["left"] < result.bounds["right"]
        assert result.bounds["bottom"] < result.bounds["top"]

        # Backwards compatibility access
        assert "tile_name" in result
        assert result["score"] == result.score


def test_no_raw_qdrant_objects_exposed() -> None:
    """Confirm search results return clean domain objects rather than Qdrant PointStructs."""
    results = search("forest", top_k=2)
    for result in results:
        assert not hasattr(result, "payload")
        assert not hasattr(result, "vector")
        assert isinstance(result, SearchResult)


def test_geographic_filter_tile_1() -> None:
    """Test B: A bounding box covering only tile_1 returns only tile_1.tif as a SearchResult."""
    bbox_tile_1 = {
        "left": 88.345,
        "bottom": 22.572,
        "right": 88.360,
        "top": 22.585,
    }
    results = search("river", bbox=bbox_tile_1)

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].tile_name == "tile_1.tif"
    assert results[0].crs == "EPSG:4326"
    assert results[0].date == "2025-03-29"


def test_geographic_filter_tile_4() -> None:
    """Test C: A bounding box covering only tile_4 returns only tile_4.tif as a SearchResult."""
    bbox_tile_4 = {
        "left": 88.370,
        "bottom": 22.556,
        "right": 88.385,
        "top": 22.569,
    }
    results = search("river", bbox=bbox_tile_4)

    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].tile_name == "tile_4.tif"


def test_geographic_filter_complete_source_area() -> None:
    """Test D: A bounding box covering the entire source area returns all 4 tiles."""
    bbox_full = {
        "left": 88.34,
        "bottom": 22.55,
        "right": 88.39,
        "top": 22.59,
    }
    results = search("river", top_k=5, bbox=bbox_full)

    assert isinstance(results, list)
    assert len(results) == 4
    result_names = {r.tile_name for r in results}
    assert result_names == {"tile_1.tif", "tile_2.tif", "tile_3.tif", "tile_4.tif"}


def test_geographic_filter_outside_area() -> None:
    """Test E: A bounding box completely outside the source area returns zero results."""
    bbox_outside = {
        "left": 10.0,
        "bottom": 10.0,
        "right": 11.0,
        "top": 11.0,
    }
    results = search("river", bbox=bbox_outside)

    assert isinstance(results, list)
    assert len(results) == 0


def test_invalid_bbox_left_gte_right() -> None:
    """Test F: Invalid bbox where left >= right fails with ValueError."""
    invalid_bbox = {
        "left": 88.40,
        "bottom": 22.55,
        "right": 88.30,
        "top": 22.59,
    }
    with pytest.raises(ValueError, match="must be strictly less than 'right'"):
        search("river", bbox=invalid_bbox)


def test_invalid_bbox_bottom_gte_top() -> None:
    """Test G: Invalid bbox where bottom >= top fails with ValueError."""
    invalid_bbox = {
        "left": 88.30,
        "bottom": 22.60,
        "right": 88.40,
        "top": 22.50,
    }
    with pytest.raises(ValueError, match="must be strictly less than 'top'"):
        search("river", bbox=invalid_bbox)


def test_qdrant_payload_filter_construction() -> None:
    """Test H: Verify that build_geographic_filter creates proper Qdrant payload conditions."""
    bbox = {
        "left": 88.34,
        "bottom": 22.55,
        "right": 88.38,
        "top": 22.58,
    }
    q_filter = build_geographic_filter(bbox)

    assert isinstance(q_filter, models.Filter)
    assert len(q_filter.must) == 4

    keys = {cond.key for cond in q_filter.must}
    assert keys == {"bounds.left", "bounds.right", "bounds.bottom", "bounds.top"}

    for cond in q_filter.must:
        if cond.key == "bounds.left":
            assert cond.range.lte == 88.38
        elif cond.key == "bounds.right":
            assert cond.range.gte == 88.34
        elif cond.key == "bounds.bottom":
            assert cond.range.lte == 22.58
        elif cond.key == "bounds.top":
            assert cond.range.gte == 22.55


if __name__ == "__main__":
    test_search_result_schema_instantiation()
    test_semantic_search_unfiltered()
    test_no_raw_qdrant_objects_exposed()
    test_geographic_filter_tile_1()
    test_geographic_filter_tile_4()
    test_geographic_filter_complete_source_area()
    test_geographic_filter_outside_area()
    test_qdrant_payload_filter_construction()
    print("All Phase 9 tests passed!")


