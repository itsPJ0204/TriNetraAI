"""Phase 16: Search robustness, query normalization, input validation, and edge-case tests."""

from typing import Any
import pytest

from semantic_search import SearchResult, normalize_query, search
from semantic_search.vector_store import COLLECTION_NAME, get_qdrant_client


def test_normalize_query_unit() -> None:
    """Verify deterministic query normalization logic for various whitespace and formatting."""
    assert normalize_query("river") == "river"
    assert normalize_query("   river   ") == "river"
    assert normalize_query("buildings    near    a    river") == "buildings near a river"
    assert normalize_query("\t\n  find   urban\t areas   \n") == "find urban areas"
    assert normalize_query("UPPERCASE   QUERY") == "UPPERCASE QUERY"

    # Invalid query inputs must raise ValueError
    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query("")

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query("   ")

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query("\t\n  \r")

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query(None)

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query(12345)

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query(True)

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query(["river"])

    with pytest.raises(ValueError, match="Search query must be a non-empty string."):
        normalize_query({"query": "river"})


def test_case_insensitivity_and_casing_consistency() -> None:
    """Verify uppercase and mixed-case queries produce identical retrieval results and scores."""
    res_lower = search("river", top_k=4)
    res_upper = search("RIVER", top_k=4)
    res_mixed = search("RiVeR", top_k=4)

    assert len(res_lower) == 4
    assert len(res_upper) == 4
    assert len(res_mixed) == 4

    # Top tiles match
    assert res_lower[0].tile_name == res_upper[0].tile_name == res_mixed[0].tile_name

    # Scores match within floating point precision
    for i in range(4):
        assert res_lower[i].tile_name == res_upper[i].tile_name == res_mixed[i].tile_name
        assert pytest.approx(res_lower[i].score, rel=1e-5) == res_upper[i].score
        assert pytest.approx(res_lower[i].score, rel=1e-5) == res_mixed[i].score


def test_whitespace_variations_consistency() -> None:
    """Verify queries with surrounding and repeated whitespace produce identical results."""
    res_clean = search("buildings near a river", top_k=4)
    res_padded = search("   buildings near a river   ", top_k=4)
    res_multi_space = search("buildings    near    a    river", top_k=4)
    res_tabs_newlines = search("\tbuildings  \n  near\t  a   river\n", top_k=4)

    tiles_clean = [r.tile_name for r in res_clean]
    tiles_padded = [r.tile_name for r in res_padded]
    tiles_multi = [r.tile_name for r in res_multi_space]
    tiles_tabs = [r.tile_name for r in res_tabs_newlines]

    assert tiles_clean == tiles_padded == tiles_multi == tiles_tabs

    scores_clean = [r.score for r in res_clean]
    scores_padded = [r.score for r in res_padded]
    scores_multi = [r.score for r in res_multi_space]
    scores_tabs = [r.score for r in res_tabs_newlines]

    assert pytest.approx(scores_clean, rel=1e-5) == scores_padded
    assert pytest.approx(scores_clean, rel=1e-5) == scores_multi
    assert pytest.approx(scores_clean, rel=1e-5) == scores_tabs


def test_short_and_long_natural_language_queries() -> None:
    """Verify short and longer natural-language queries return valid SearchResult rankings."""
    # Short query
    res_short = search("urban area", top_k=3)
    assert len(res_short) == 3
    assert all(isinstance(r, SearchResult) for r in res_short)

    # Long natural language query
    res_long = search("find urban areas with roads and green spaces", top_k=4)
    assert len(res_long) == 4
    assert all(isinstance(r, SearchResult) for r in res_long)
    # Cosine scores are monotonically non-increasing
    scores = [r.score for r in res_long]
    assert scores == sorted(scores, reverse=True)


def test_synonym_and_complex_queries() -> None:
    """Verify synonym-style and multi-concept query expressions execute cleanly."""
    synonym_queries = [
        "water body",
        "vegetated area",
        "constructed buildings",
    ]
    for q in synonym_queries:
        res = search(q, top_k=2)
        assert len(res) == 2
        assert all(isinstance(r, SearchResult) for r in res)
        assert all(isinstance(r.score, float) for r in res)

    complex_queries = [
        "find buildings near a river",
        "roads passing through green areas",
    ]
    for q in complex_queries:
        res = search(q, top_k=4)
        assert len(res) == 4
        assert all(isinstance(r, SearchResult) for r in res)


def test_irrelevant_and_ambiguous_queries() -> None:
    """Verify out-of-domain and ambiguous queries execute cleanly without crashing."""
    # Irrelevant query
    res_irrel = search("cars on a highway", top_k=2)
    assert len(res_irrel) == 2
    assert all(isinstance(r, SearchResult) for r in res_irrel)

    # Ambiguous single-word query
    res_ambig = search("things", top_k=2)
    assert len(res_ambig) == 2
    assert all(isinstance(r, SearchResult) for r in res_ambig)


def test_input_validation_errors() -> None:
    """Verify invalid query inputs raise expected ValueError."""
    invalid_inputs = [
        "",
        "   ",
        "\t\t",
        "\n\n",
        None,
        123,
        False,
        True,
        ["river"],
        {"query": "river"},
    ]
    for bad_input in invalid_inputs:
        with pytest.raises(ValueError, match="Search query must be a non-empty string."):
            search(bad_input)  # type: ignore


def test_top_k_edge_cases() -> None:
    """Verify top_k bounds and limits."""
    # top_k = 1
    res_1 = search("river", top_k=1)
    assert len(res_1) == 1

    # top_k larger than total indexed tiles (90 tiles in index)
    res_large = search("river", top_k=100)
    assert len(res_large) == 90
    assert [r.tile_name for r in res_large] == [r.tile_name for r in search("river", top_k=90)]

    # Invalid top_k values
    invalid_top_ks = [0, -1, -100, True, False, 2.5, "4", [2]]
    for bad_k in invalid_top_ks:
        with pytest.raises(ValueError, match="top_k must be a positive integer."):
            search("river", top_k=bad_k)  # type: ignore


def test_bbox_and_normalized_query_combination() -> None:
    """Verify combining normalized messy queries with geographic bounding-box filtering."""
    bbox_tile_1 = {
        "left": 77.158,
        "bottom": 28.645,
        "right": 77.178,
        "top": 28.662,
    }
    # Messy query + bbox
    res = search("   RIVER    FLOWING   ", bbox=bbox_tile_1, top_k=5)
    assert len(res) >= 1
    assert all(r.tile_name == "sentinel2_tile_1.tif" for r in res)
    assert all(r.crs == "EPSG:4326" for r in res)


def test_qdrant_collection_immutability() -> None:
    """Verify vector store collection remains strictly untouched after robustness testing."""
    client = get_qdrant_client()
    count = client.count(COLLECTION_NAME, exact=True).count
    info = client.get_collection(COLLECTION_NAME)

    assert count == 90
    assert info.config.params.vectors.size == 512
