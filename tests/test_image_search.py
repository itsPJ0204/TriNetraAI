"""Comprehensive unit and integration tests for image-to-image and multimodal search."""

from pathlib import Path
import numpy as np
from PIL import Image
import pytest

from semantic_search.schemas import SearchResult
from semantic_search.search import (
    fuse_embeddings,
    image_input_to_embedding,
    search,
    search_by_image,
)


@pytest.fixture
def sample_pil_image() -> Image.Image:
    """Generate a simple RGB PIL image."""
    arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    return Image.fromarray(arr, mode="RGB")


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    """Save a sample PNG image to disk and return path."""
    img_path = tmp_path / "test_sample.png"
    arr = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    Image.fromarray(arr, mode="RGB").save(img_path)
    return img_path


@pytest.fixture
def sentinel2_tile_path() -> Path:
    """Path to an existing valid Sentinel-2 RGB GeoTIFF tile."""
    candidates = list(Path("data/tiles/sentinel2").rglob("*tile_1.tif"))
    assert len(candidates) > 0, "No sentinel2_tile_1.tif found under data/tiles/sentinel2"
    return candidates[0]


# ==============================================================================
# 1. Embedding & Fusion Unit Tests
# ==============================================================================


def test_image_input_to_embedding_pil(sample_pil_image: Image.Image) -> None:
    """image_input_to_embedding produces a normalized 512-dim vector from a PIL Image."""
    vec = image_input_to_embedding(sample_pil_image)
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (512,)
    assert vec.dtype == np.float32
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-4)


def test_image_input_to_embedding_file_path(sample_image_path: Path) -> None:
    """image_input_to_embedding works with str and Path arguments."""
    vec_path = image_input_to_embedding(sample_image_path)
    vec_str = image_input_to_embedding(str(sample_image_path))
    assert vec_path.shape == (512,)
    assert np.allclose(vec_path, vec_str, atol=1e-5)


def test_image_input_to_embedding_geotiff(sentinel2_tile_path: Path) -> None:
    """image_input_to_embedding works with Sentinel-2 GeoTIFF tiles."""
    vec = image_input_to_embedding(sentinel2_tile_path)
    assert vec.shape == (512,)
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-4)


def test_image_input_to_embedding_invalid_type() -> None:
    """Non-image inputs raise TypeError, None raises ValueError."""
    with pytest.raises(TypeError):
        image_input_to_embedding(12345)

    with pytest.raises(ValueError):
        image_input_to_embedding(None)


def test_image_input_to_embedding_missing_file(tmp_path: Path) -> None:
    """Non-existent file path raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        image_input_to_embedding(tmp_path / "does_not_exist.png")


def test_fuse_embeddings_strategies() -> None:
    """Test all fusion strategies produce normalized 512-dim vectors."""
    v1 = np.random.randn(512).astype(np.float32)
    v1 /= np.linalg.norm(v1)
    v2 = np.random.randn(512).astype(np.float32)
    v2 /= np.linalg.norm(v2)

    # weighted_sum default
    fused_default = fuse_embeddings(v1, v2)
    assert fused_default.shape == (512,)
    assert np.isclose(np.linalg.norm(fused_default), 1.0, atol=1e-4)

    # weighted_sum with alpha
    fused_alpha_0 = fuse_embeddings(v1, v2, alpha=0.0)
    assert np.allclose(fused_alpha_0, v2, atol=1e-4)

    fused_alpha_1 = fuse_embeddings(v1, v2, alpha=1.0)
    assert np.allclose(fused_alpha_1, v1, atol=1e-4)

    # average
    fused_avg = fuse_embeddings(v1, v2, fusion_strategy="average")
    assert np.allclose(fused_avg, fused_default, atol=1e-4)

    # image_only
    fused_img = fuse_embeddings(v1, v2, fusion_strategy="image_only")
    assert np.allclose(fused_img, v1, atol=1e-5)

    # text_only
    fused_txt = fuse_embeddings(v1, v2, fusion_strategy="text_only")
    assert np.allclose(fused_txt, v2, atol=1e-5)

    # custom weights
    fused_custom = fuse_embeddings(v1, v2, image_weight=0.7, text_weight=0.3)
    assert np.isclose(np.linalg.norm(fused_custom), 1.0, atol=1e-4)


def test_fuse_embeddings_invalid_parameters() -> None:
    """Invalid fusion parameters raise ValueError."""
    v = np.ones(512, dtype=np.float32) / np.sqrt(512)

    with pytest.raises(ValueError):
        fuse_embeddings(v, v, alpha=-0.1)

    with pytest.raises(ValueError):
        fuse_embeddings(v, v, alpha=1.5)

    with pytest.raises(ValueError):
        fuse_embeddings(v, v, fusion_strategy="unknown_strategy")

    with pytest.raises(ValueError):
        fuse_embeddings(v, v, image_weight=-1.0, text_weight=1.0)


# ==============================================================================
# 2. Image-Only Search Tests
# ==============================================================================


def test_search_by_image_only_pil(sample_pil_image: Image.Image) -> None:
    """Pure image-to-image search returns top_k SearchResults."""
    results = search_by_image(sample_pil_image, top_k=5)
    assert isinstance(results, list)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, SearchResult)
        assert isinstance(r.score, float)
        assert -1.0 <= r.score <= 1.0
        assert r.tile_name.endswith(".tif")
        assert r.crs == "EPSG:4326"
        assert r.bounds is not None


def test_search_by_image_only_path(sentinel2_tile_path: Path) -> None:
    """Image-to-image search with a real tile should return that tile as rank 1 with high similarity."""
    results = search_by_image(sentinel2_tile_path, top_k=3)
    assert len(results) == 3
    # The query image is tile 1, so sentinel2_tile_1.tif must be the top match
    assert results[0].tile_name == "sentinel2_tile_1.tif"
    assert results[0].score > 0.90  # Extremely high similarity to itself


# ==============================================================================
# 3. Multimodal Search (Image + Text) Tests
# ==============================================================================


def test_search_by_image_multimodal(sentinel2_tile_path: Path) -> None:
    """Multimodal search (image + query) succeeds and returns valid results."""
    results = search_by_image(
        image=sentinel2_tile_path,
        query="dense green forest vegetation",
        top_k=5,
        alpha=0.6,
        fusion_strategy="weighted_sum",
    )
    assert isinstance(results, list)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, SearchResult)
        assert -1.0 <= r.score <= 1.0


def test_search_by_image_multimodal_shifts_scores(sample_pil_image: Image.Image) -> None:
    """Adding a text query to an image query alters the ranking/scores compared to pure image."""
    img_only = search_by_image(sample_pil_image, top_k=5)
    multimodal = search_by_image(sample_pil_image, query="airport runway", top_k=5, alpha=0.3)

    img_scores = [r.score for r in img_only]
    mm_scores = [r.score for r in multimodal]
    assert img_scores != mm_scores


# ==============================================================================
# 4. Geographic BBox Filtering Tests
# ==============================================================================


def test_search_by_image_bbox_filtering(sample_pil_image: Image.Image) -> None:
    """search_by_image respects geographic bbox filtering."""
    bbox_tile_1 = {
        "left": 77.158,
        "bottom": 28.645,
        "right": 77.178,
        "top": 28.662,
    }
    results = search_by_image(sample_pil_image, bbox=bbox_tile_1, top_k=10)
    assert len(results) >= 1
    for r in results:
        assert r.tile_name == "sentinel2_tile_1.tif"


def test_search_by_image_bbox_outside(sample_pil_image: Image.Image) -> None:
    """search_by_image returns empty list when bbox is outside data coverage."""
    bbox_outside = {
        "left": 10.0,
        "bottom": 10.0,
        "right": 11.0,
        "top": 11.0,
    }
    results = search_by_image(sample_pil_image, bbox=bbox_outside, top_k=5)
    assert results == []


# ==============================================================================
# 5. Input Validation & Error Handling Tests
# ==============================================================================


def test_search_by_image_invalid_inputs(sample_pil_image: Image.Image) -> None:
    """Validate that invalid parameters raise descriptive exceptions."""
    # Invalid image
    with pytest.raises(ValueError):
        search_by_image(None)

    with pytest.raises(TypeError):
        search_by_image(12345)

    with pytest.raises(FileNotFoundError):
        search_by_image("non_existent_image_file.tif")

    # Invalid query
    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, query="")

    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, query="   ")

    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, query=123)

    # Invalid top_k
    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, top_k=0)

    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, top_k=-5)

    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, top_k="five")

    # Invalid bbox
    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, bbox={"left": 10})

    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, bbox={"left": 10, "right": 5, "bottom": 1, "top": 2})

    # Invalid alpha
    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, query="river", alpha=1.5)

    # Invalid fusion strategy
    with pytest.raises(ValueError):
        search_by_image(sample_pil_image, query="river", fusion_strategy="bad_strategy")


# ==============================================================================
# 6. Backward Compatibility with search()
# ==============================================================================


def test_search_text_backward_compatibility() -> None:
    """Existing search() function remains 100% operational with all calling conventions."""
    # Standard call
    results = search("river", top_k=3)
    assert isinstance(results, list)
    assert len(results) == 3
    for r in results:
        assert isinstance(r, SearchResult)
        assert isinstance(r.score, float)
        assert r.tile_name.endswith(".tif")

    # Legacy positional top_k: search("river", 2)
    results_pos = search("river", 2)
    assert len(results_pos) == 2

    # geographic_bbox alias
    bbox_tile_1 = {
        "left": 77.158,
        "bottom": 28.645,
        "right": 77.178,
        "top": 28.662,
    }
    results_alias = search("river", geographic_bbox=bbox_tile_1, top_k=2)
    assert len(results_alias) >= 1
    assert all(r.tile_name == "sentinel2_tile_1.tif" for r in results_alias)


# ==============================================================================
# 7. Unconventional Image Inputs & Fusion Extremes
# ==============================================================================


def test_image_input_grayscale_and_rgba(tmp_path: Path) -> None:
    """Verify grayscale (L) and RGBA images are converted to RGB properly."""
    # Grayscale PIL
    gray_arr = np.random.randint(0, 256, (64, 64), dtype=np.uint8)
    gray_img = Image.fromarray(gray_arr, mode="L")
    vec_gray = image_input_to_embedding(gray_img)
    assert vec_gray.shape == (512,)
    assert np.isclose(np.linalg.norm(vec_gray), 1.0, atol=1e-4)

    # RGBA PIL
    rgba_arr = np.random.randint(0, 256, (64, 64, 4), dtype=np.uint8)
    rgba_img = Image.fromarray(rgba_arr, mode="RGBA")
    vec_rgba = image_input_to_embedding(rgba_img)
    assert vec_rgba.shape == (512,)
    assert np.isclose(np.linalg.norm(vec_rgba), 1.0, atol=1e-4)

    # Grayscale file
    gray_file = tmp_path / "gray.png"
    gray_img.save(gray_file)
    vec_file = image_input_to_embedding(gray_file)
    assert np.allclose(vec_gray, vec_file, atol=1e-5)


def test_image_input_single_band_geotiff(tmp_path: Path) -> None:
    """Verify 1-band uint16 GeoTIFF is safely handled by rasterio fallback."""
    import rasterio

    tiff_path = tmp_path / "single_band.tif"
    data = np.random.randint(0, 4000, (64, 64), dtype=np.uint16)
    with rasterio.open(
        tiff_path,
        "w",
        driver="GTiff",
        height=64,
        width=64,
        count=1,
        dtype=rasterio.uint16,
    ) as dst:
        dst.write(data, 1)

    vec = image_input_to_embedding(tiff_path)
    assert vec.shape == (512,)
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-4)


def test_search_by_image_alpha_extremes(sample_pil_image: Image.Image) -> None:
    """alpha=1 gives pure image search results, alpha=0 gives pure text search results."""
    query = "dense urban city"
    res_img = search_by_image(sample_pil_image, top_k=3)
    res_alpha_1 = search_by_image(sample_pil_image, query=query, top_k=3, alpha=1.0)
    res_strategy_img = search_by_image(
        sample_pil_image, query=query, top_k=3, fusion_strategy="image_only"
    )

    # alpha=1.0 and image_only must return identical scores/ordering as pure image search
    assert [r.tile_name for r in res_alpha_1] == [r.tile_name for r in res_img]
    assert np.allclose([r.score for r in res_alpha_1], [r.score for r in res_img], atol=1e-4)
    assert [r.tile_name for r in res_strategy_img] == [r.tile_name for r in res_img]

    # alpha=0.0 and text_only must return identical scores/ordering as pure text search
    res_txt = search(query, top_k=3)
    res_alpha_0 = search_by_image(sample_pil_image, query=query, top_k=3, alpha=0.0)
    res_strategy_txt = search_by_image(
        sample_pil_image, query=query, top_k=3, fusion_strategy="text_only"
    )

    assert [r.tile_name for r in res_alpha_0] == [r.tile_name for r in res_txt]
    assert np.allclose([r.score for r in res_alpha_0], [r.score for r in res_txt], atol=1e-4)
    assert [r.tile_name for r in res_strategy_txt] == [r.tile_name for r in res_txt]

