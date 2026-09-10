"""Unit and integration tests for scripts/search_by_image.py CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scripts.search_by_image import main
from semantic_search.schemas import SearchResult


@pytest.fixture
def sentinel2_tile_path() -> Path:
    """Path to an existing valid Sentinel-2 RGB GeoTIFF tile."""
    candidates = list(Path("data/tiles/sentinel2").rglob("*tile_1.tif"))
    assert len(candidates) > 0, "No sentinel2_tile_1.tif found under data/tiles/sentinel2"
    return candidates[0]


@pytest.fixture
def mock_search_results(sentinel2_tile_path: Path) -> list[SearchResult]:
    """Sample SearchResult list for testing CLI output rendering."""
    return [
        SearchResult(
            tile_name=sentinel2_tile_path.name,
            score=0.923456,
            crs="EPSG:4326",
            bounds={"left": 77.20, "bottom": 28.58, "right": 77.25, "top": 28.64},
            width=256,
            height=256,
            image_path=str(sentinel2_tile_path),
            date="2026-06-27",
        )
    ]


# ==============================================================================
# 1. Validation & Error Handling Tests
# ==============================================================================


def test_cli_missing_image_arg() -> None:
    """Invoking CLI without positional image argument exits with error code."""
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code != 0


def test_cli_nonexistent_image(capsys: pytest.CaptureFixture[str]) -> None:
    """Non-existent image file returns 1 and reports clear error."""
    code = main(["nonexistent/path/to/image.png"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR: Image file not found" in captured.out


def test_cli_directory_instead_of_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Providing a directory path instead of a file returns 1."""
    code = main([str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR: Image path is not a file" in captured.out


def test_cli_invalid_top_k(sentinel2_tile_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Zero or negative top_k returns 1 with clear error message."""
    code = main([str(sentinel2_tile_path), "--top-k", "0"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR: --top-k must be a positive integer" in captured.out

    code_neg = main([str(sentinel2_tile_path), "--top-k", "-2"])
    captured_neg = capsys.readouterr()
    assert code_neg == 1
    assert "ERROR: --top-k must be a positive integer" in captured_neg.out


def test_cli_invalid_alpha(sentinel2_tile_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Alpha outside [0.0, 1.0] returns 1 with clear error message."""
    code = main([str(sentinel2_tile_path), "--alpha", "1.5"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR: --alpha must be between 0.0 and 1.0" in captured.out

    code_neg = main([str(sentinel2_tile_path), "--alpha", "-0.1"])
    captured_neg = capsys.readouterr()
    assert code_neg == 1
    assert "ERROR: --alpha must be between 0.0 and 1.0" in captured_neg.out


def test_cli_invalid_bbox_coordinates(sentinel2_tile_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Inverted bbox coordinates return 1 with clear error message."""
    # left >= right
    code = main([str(sentinel2_tile_path), "--bbox", "77.5", "28.0", "77.0", "29.0"])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR: Invalid bounding box: 'left'" in captured.out

    # bottom >= top
    code2 = main([str(sentinel2_tile_path), "--bbox", "77.0", "29.5", "77.5", "29.0"])
    captured2 = capsys.readouterr()
    assert code2 == 1
    assert "ERROR: Invalid bounding box: 'bottom'" in captured2.out


def test_cli_empty_query_flag(sentinel2_tile_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Passing an empty or whitespace string for --query returns 1."""
    code = main([str(sentinel2_tile_path), "--query", "   "])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR: --query cannot be empty or whitespace only" in captured.out


def test_cli_invalid_fusion_strategy(sentinel2_tile_path: Path) -> None:
    """Invalid fusion strategy is rejected by argparse."""
    with pytest.raises(SystemExit) as exc_info:
        main([str(sentinel2_tile_path), "--fusion-strategy", "invalid_strategy"])
    assert exc_info.value.code != 0


# ==============================================================================
# 2. Output Formatting & Core API Invocation Tests
# ==============================================================================


def test_cli_successful_search_formatting(
    sentinel2_tile_path: Path,
    mock_search_results: list[SearchResult],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI formats rank, tile_name, score, path, bounds, crs, dimensions, date."""
    with patch("scripts.search_by_image.search_by_image", return_value=mock_search_results) as mock_search:
        code = main([str(sentinel2_tile_path), "--top-k", "3"])
        captured = capsys.readouterr()

        assert code == 0
        mock_search.assert_called_once_with(
            image=sentinel2_tile_path,
            query=None,
            top_k=3,
            bbox=None,
            alpha=0.5,
            fusion_strategy="weighted_sum",
            image_weight=None,
            text_weight=None,
        )

        assert "Search Results:" in captured.out
        assert f"1. {sentinel2_tile_path.name} — score: 0.923456" in captured.out
        assert f"Path:       {sentinel2_tile_path}" in captured.out
        assert "CRS:        EPSG:4326" in captured.out
        assert "Bounds:     {'left': 77.2, 'bottom': 28.58, 'right': 77.25, 'top': 28.64}" in captured.out
        assert "Dimensions: 256x256" in captured.out
        assert "Date:       2026-06-27" in captured.out


def test_cli_multimodal_arguments_passed(
    sentinel2_tile_path: Path,
    mock_search_results: list[SearchResult],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """All multimodal options are properly converted and passed to search_by_image."""
    with patch("scripts.search_by_image.search_by_image", return_value=mock_search_results) as mock_search:
        code = main(
            [
                str(sentinel2_tile_path),
                "--query",
                "dense vegetation",
                "--top-k",
                "2",
                "--bbox",
                "77.1",
                "28.5",
                "77.3",
                "28.7",
                "--alpha",
                "0.7",
                "--fusion-strategy",
                "weighted_sum",
                "--image-weight",
                "0.7",
                "--text-weight",
                "0.3",
            ]
        )
        assert code == 0
        mock_search.assert_called_once_with(
            image=sentinel2_tile_path,
            query="dense vegetation",
            top_k=2,
            bbox={"left": 77.1, "bottom": 28.5, "right": 77.3, "top": 28.7},
            alpha=0.7,
            fusion_strategy="weighted_sum",
            image_weight=0.7,
            text_weight=0.3,
        )


def test_cli_empty_search_results(
    sentinel2_tile_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When no tiles match, CLI outputs informative message and returns 0."""
    with patch("scripts.search_by_image.search_by_image", return_value=[]):
        code = main([str(sentinel2_tile_path)])
        captured = capsys.readouterr()
        assert code == 0
        assert "No matching satellite tiles found." in captured.out


def test_cli_handles_backend_exception(
    sentinel2_tile_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Runtime / Connection errors from backend are caught and reported cleanly."""
    with patch("scripts.search_by_image.search_by_image", side_effect=ConnectionError("Failed to connect to Qdrant")):
        code = main([str(sentinel2_tile_path)])
        captured = capsys.readouterr()
        assert code == 1
        assert "ERROR: Failed to connect to Qdrant" in captured.out


# ==============================================================================
# 3. Live Integration Test
# ==============================================================================


def test_cli_live_integration(
    sentinel2_tile_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Live end-to-end CLI execution with real Sentinel-2 tile against Qdrant."""
    code = main([str(sentinel2_tile_path), "--top-k", "2"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Search Results:" in captured.out
    assert "1. " in captured.out
    assert "score: " in captured.out
    assert "Date:       " in captured.out
