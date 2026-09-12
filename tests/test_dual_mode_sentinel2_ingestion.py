import os
import shutil
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds
from qdrant_client import QdrantClient

from semantic_search.sentinel2 import (
    detect_sentinel2_raw_inputs,
    find_sentinel2_bands,
    find_sentinel2_rgb_image,
    generate_sentinel2_rgb_tiles,
    ingest_sentinel2_date,
    discover_sentinel2_date_dirs,
)
from semantic_search import indexer, vector_store


@pytest.fixture(autouse=True)
def isolate_qdrant_and_manifest(tmp_path, monkeypatch):
    """Isolate Qdrant and indexing manifest to prevent test leakage into Docker Qdrant."""
    test_manifest_path = tmp_path / "test_manifest.json"
    memory_client = QdrantClient(":memory:")

    monkeypatch.setattr(indexer, "MANIFEST_PATH", test_manifest_path)
    monkeypatch.setattr(vector_store, "get_qdrant_client", lambda *args, **kwargs: memory_client)
    monkeypatch.setattr(indexer, "get_qdrant_client", lambda *args, **kwargs: memory_client)
    monkeypatch.setattr("semantic_search.sentinel2.index_satellite_tiles", lambda **kw: {
        "discovered": 4,
        "new": 4 if kw.get("force", False) or not test_manifest_path.exists() else 0,
        "already_indexed": 0 if kw.get("force", False) or not test_manifest_path.exists() else 4,
        "changed": 0,
        "embeddings_generated": 4 if kw.get("force", False) or not test_manifest_path.exists() else 0,
        "failed": 0
    })

    yield memory_client


def _create_synthetic_band(path: Path, width=300, height=300, dtype="uint16", value=1000):
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_bounds(77.0, 28.0, 77.1, 28.1, width, height)
    data = (np.ones((1, height, width)) * value).astype(dtype)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype=dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)


def _create_synthetic_rgb(path: Path, width=300, height=300, dtype="uint8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_bounds(77.0, 28.0, 77.1, 28.1, width, height)
    data = np.stack([
        (np.ones((height, width)) * 120).astype(dtype),
        (np.ones((height, width)) * 180).astype(dtype),
        (np.ones((height, width)) * 60).astype(dtype),
    ], axis=0)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype=dtype,
        crs="EPSG:4326",
        transform=transform,
        photometric="RGB",
    ) as dst:
        dst.write(data)


def test_mode_separate_bands(tmp_path):
    date_dir = tmp_path / "raw" / "2026-05-10"
    date_dir.mkdir(parents=True)

    _create_synthetic_band(date_dir / "2026-05-10_B02.tiff")
    _create_synthetic_band(date_dir / "2026-05-10_B03.tiff")
    _create_synthetic_band(date_dir / "2026-05-10_B04.tiff")
    _create_synthetic_band(date_dir / "2026-05-10_B08.tiff")

    detection = detect_sentinel2_raw_inputs(date_dir)
    assert detection["mode"] == "separate_bands"
    assert "B02" in detection["bands"]
    assert "B08" in detection["bands"]

    out_dir = tmp_path / "tiles" / "2026-05-10"
    report = generate_sentinel2_rgb_tiles(date_dir, output_date_dir=out_dir, tile_size=256)
    assert report["mode"] == "separate_bands"
    assert report["num_tiles"] == 4  # 300x300 cut into 256x256 windows
    assert report["crs"] == "EPSG:4326"


def test_mode_true_colour_image(tmp_path):
    date_dir = tmp_path / "raw" / "2026-09-15"
    date_dir.mkdir(parents=True)

    rgb_file = date_dir / "2026-09-15_TCI.tiff"
    _create_synthetic_rgb(rgb_file)

    detection = detect_sentinel2_raw_inputs(date_dir)
    assert detection["mode"] == "true_colour"
    assert detection["rgb_path"] == rgb_file

    out_dir = tmp_path / "tiles" / "2026-09-15"
    report = generate_sentinel2_rgb_tiles(date_dir, output_date_dir=out_dir, tile_size=256)
    assert report["mode"] == "true_colour"
    assert report["num_tiles"] == 4
    assert report["crs"] == "EPSG:4326"
    assert (out_dir / "sentinel2_rgb_full.tif").is_file()
    assert (out_dir / "sentinel2_tile_1.tif").is_file()


def test_dual_format_priority(tmp_path):
    date_dir = tmp_path / "raw" / "2026-11-20"
    date_dir.mkdir(parents=True)

    # Put both separate bands and an RGB composite
    _create_synthetic_band(date_dir / "2026-11-20_B02.tiff")
    _create_synthetic_band(date_dir / "2026-11-20_B03.tiff")
    _create_synthetic_band(date_dir / "2026-11-20_B04.tiff")
    _create_synthetic_band(date_dir / "2026-11-20_B08.tiff")
    _create_synthetic_rgb(date_dir / "2026-11-20_TCI.tiff")

    detection = detect_sentinel2_raw_inputs(date_dir)
    assert detection["mode"] == "separate_bands", "Should prioritize separate bands because B08 is available"


def test_date_discovery_mixed(tmp_path):
    raw_root = tmp_path / "raw"
    date1 = raw_root / "2025-01-01"
    date2 = raw_root / "2025-02-02"
    invalid_dir = raw_root / "2025-03-03"  # empty

    date1.mkdir(parents=True)
    date2.mkdir(parents=True)
    invalid_dir.mkdir(parents=True)

    # date1: separate bands
    _create_synthetic_band(date1 / "B02.tif")
    _create_synthetic_band(date1 / "B03.tif")
    _create_synthetic_band(date1 / "B04.tif")
    _create_synthetic_band(date1 / "B08.tif")

    # date2: true colour image
    _create_synthetic_rgb(date2 / "true_colour.tif")

    discovered = discover_sentinel2_date_dirs(raw_root)
    assert len(discovered) == 2
    names = [d.name for d in discovered]
    assert "2025-01-01" in names
    assert "2025-02-02" in names
    assert "2025-03-03" not in names
