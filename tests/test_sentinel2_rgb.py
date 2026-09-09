"""Tests for Sentinel-2 L2A RGB composite generation, normalization, and geospatial tiling."""

from pathlib import Path
import numpy as np
from PIL import Image
import pytest
import rasterio
import torch

from semantic_search.model import load_remoteclip
from semantic_search.sentinel2 import (
    DEFAULT_RAW_DIR,
    create_sentinel2_rgb_composite,
    extract_acquisition_date,
    find_sentinel2_bands,
    normalize_uint16_to_uint8,
    split_grid_windows,
    split_tile_windows,
    tile_sentinel2_rgb,
)


@pytest.fixture
def raw_sentinel2_dir() -> Path:
    assert DEFAULT_RAW_DIR.is_dir(), f"Sentinel-2 raw dir not found: {DEFAULT_RAW_DIR}"
    return DEFAULT_RAW_DIR


def test_extract_acquisition_date() -> None:
    """Verify dynamic extraction of ISO date from Sentinel-2 filenames."""
    filename = "2026-06-27-00_00_2026-06-27-23_59_Sentinel-2_L2A_B04_(Raw).tiff"
    date = extract_acquisition_date(filename)
    assert date == "2026-06-27"

    with pytest.raises(ValueError, match="Could not extract acquisition date"):
        extract_acquisition_date("sentinel_image_no_date.tif")


def test_find_sentinel2_bands(raw_sentinel2_dir: Path) -> None:
    """Verify discovery of all 4 Sentinel-2 raw band TIFFs."""
    bands = find_sentinel2_bands(raw_sentinel2_dir)
    assert set(bands.keys()) == {"B02", "B03", "B04", "B08"}
    for b, path in bands.items():
        assert path.is_file()
        assert b in path.name


def test_normalize_uint16_to_uint8() -> None:
    """Verify deterministic percentile stretch from uint16 to uint8."""
    # Synthetic 16-bit band with realistic distribution
    raw = np.array([[100, 500, 2000], [5000, 10000, 65535]], dtype=np.uint16)
    u8 = normalize_uint16_to_uint8(raw, p_low=0.0, p_high=100.0)

    assert u8.dtype == np.uint8
    assert u8.shape == raw.shape
    assert u8.min() == 0
    assert u8.max() == 255


def test_split_tile_windows_geometry() -> None:
    """Verify 256x256 window calculation covers 1284x1157 exactly with 30 windows."""
    windows = split_tile_windows(width=1284, height=1157, tile_size=256)
    assert len(windows) == 30

    total_area = sum(int(w.width * w.height) for w in windows)
    assert total_area == 1284 * 1157

    # Check right edge windows (cols=5, rows 0..3) -> width 4, height 256
    # Check bottom edge windows (row=4, cols 0..4) -> width 256, height 133
    # Check bottom-right corner window (row=4, col=5) -> width 4, height 133
    dim_counts: dict[tuple[int, int], int] = {}
    for w in windows:
        dim = (int(w.width), int(w.height))
        dim_counts[dim] = dim_counts.get(dim, 0) + 1

    assert dim_counts[(256, 256)] == 20
    assert dim_counts[(4, 256)] == 4
    assert dim_counts[(256, 133)] == 5
    assert dim_counts[(4, 133)] == 1


def test_rgb_band_ordering_and_exclusion_of_b08(raw_sentinel2_dir: Path) -> None:
    """Verify that R=B04, G=B03, B=B02 and B08 (NIR) is not used in RGB."""
    rgb_array, profile, date = create_sentinel2_rgb_composite(raw_dir=raw_sentinel2_dir)

    assert rgb_array.shape[0] == 3  # Exactly 3 bands: R, G, B
    assert rgb_array.dtype == np.uint8
    assert profile["count"] == 3
    assert profile["dtype"] == "uint8"
    assert date == "2026-06-27"

    # Verify each channel corresponds to normalized B04, B03, B02
    bands = find_sentinel2_bands(raw_sentinel2_dir)
    with rasterio.open(bands["B04"]) as s_r, rasterio.open(bands["B03"]) as s_g, rasterio.open(bands["B02"]) as s_b:
        r_expected = normalize_uint16_to_uint8(s_r.read(1))
        g_expected = normalize_uint16_to_uint8(s_g.read(1))
        b_expected = normalize_uint16_to_uint8(s_b.read(1))

    assert np.array_equal(rgb_array[0], r_expected)
    assert np.array_equal(rgb_array[1], g_expected)
    assert np.array_equal(rgb_array[2], b_expected)

    # Verify B08 was not modified on disk
    with rasterio.open(bands["B08"]) as s_nir:
        assert s_nir.count == 1
        assert s_nir.dtypes[0] == "uint16"


def test_sentinel2_256x256_tiling_and_metadata(tmp_path: Path, raw_sentinel2_dir: Path) -> None:
    """Verify 256x256 tiling creates 30 tiles, preserves 100% coverage, CRS, transform, bounds, and date."""
    tiles = tile_sentinel2_rgb(
        raw_dir=raw_sentinel2_dir, output_dir=tmp_path, tile_size=256, overwrite=True
    )
    assert len(tiles) == 30

    with rasterio.open(find_sentinel2_bands(raw_sentinel2_dir)["B04"]) as src:
        total_tile_pixels = 0
        src_w, src_h = src.width, src.height
        src_crs = src.crs

        edge_tiles = []
        for tile_path in tiles:
            assert tile_path.is_file()
            with rasterio.open(tile_path) as tile:
                assert tile.count == 3
                assert tile.crs == src_crs
                assert tile.dtypes == ("uint8", "uint8", "uint8")
                assert tile.tags().get("date") == "2026-06-27"
                assert tile.tags().get("r_band") == "B04"
                assert tile.tags().get("g_band") == "B03"
                assert tile.tags().get("b_band") == "B02"
                assert tile.tags().get("provenance") == "Sentinel-2 L2A"

                # Check non-empty
                data = tile.read()
                assert np.count_nonzero(data) > 0.9 * data.size
                assert data.mean() > 10.0

                if tile.width != 256 or tile.height != 256:
                    edge_tiles.append((tile.width, tile.height))

                total_tile_pixels += tile.width * tile.height

        assert total_tile_pixels == src_w * src_h == 1284 * 1157
        assert len(edge_tiles) == 10  # 4 right, 5 bottom, 1 bottom-right


def test_sentinel2_tile_remoteclip_compatibility(tmp_path: Path, raw_sentinel2_dir: Path) -> None:
    """Verify that generated RGB GeoTIFF tiles can be processed by RemoteCLIP directly."""
    tiles = tile_sentinel2_rgb(
        raw_dir=raw_sentinel2_dir, output_dir=tmp_path, tile_size=256, overwrite=True
    )
    sample_tile = tiles[0]

    with Image.open(sample_tile) as img:
        rgb_img = img.convert("RGB")
        assert rgb_img.size == (256, 256)

    model, _, preprocess = load_remoteclip(device="cpu")
    tensor = preprocess(rgb_img).unsqueeze(0)
    with torch.inference_mode():
        feat = model.encode_image(tensor)
        norm_feat = torch.nn.functional.normalize(feat, p=2, dim=-1)

    emb = norm_feat.squeeze(0).cpu().numpy()
    assert emb.shape == (512,)
    assert np.all(np.isfinite(emb))
    assert abs(float(np.linalg.norm(emb)) - 1.0) < 1e-4
