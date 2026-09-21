"""Tests for end-to-end Sentinel-2 date ingestion and incremental indexing."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from qdrant_client import QdrantClient
from semantic_search.indexer import (
    compute_file_fingerprint,
    extract_tile_metadata_and_identity,
    load_indexing_manifest,
)
from semantic_search.sentinel2 import (
    generate_sentinel2_rgb_tiles,
    ingest_new_sentinel2,
    ingest_sentinel2_date,
)


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path: Path, monkeypatch) -> None:
    """Ensure all tests run against isolated temporary manifest and in-memory Qdrant instance."""
    emb_dir = tmp_path / "embeddings"
    emb_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("semantic_search.indexer.EMBEDDINGS_DIR", emb_dir)
    monkeypatch.setattr("semantic_search.indexer.MANIFEST_PATH", emb_dir / "indexing_manifest.json")
    monkeypatch.setattr("semantic_search.indexer.EMBEDDINGS_CACHE_NPZ_PATH", emb_dir / "tile_embeddings_cache.npz")
    monkeypatch.setattr("semantic_search.indexer.EMBEDDINGS_NPY_PATH", emb_dir / "image_embeddings.npy")
    monkeypatch.setattr("semantic_search.indexer.IMAGE_PATHS_JSON_PATH", emb_dir / "image_paths.json")

    # Fully isolate Qdrant using an in-memory client so production Docker Qdrant is never touched
    test_qdrant = QdrantClient(":memory:")
    monkeypatch.setattr("semantic_search.indexer.get_qdrant_client", lambda *args, **kwargs: test_qdrant)
    monkeypatch.setattr("semantic_search.vector_store.get_qdrant_client", lambda *args, **kwargs: test_qdrant)


@pytest.fixture
def mock_sentinel2_raw_date(tmp_path: Path) -> Path:
    """Create a temporary synthetic Sentinel-2 raw date directory with 4 bands."""
    date_str = "2026-09-10"
    raw_dir = tmp_path / "raw" / "sentinel2" / date_str
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 300x300 pixels (yields 4 tiles with 256x256 grid: (256,256), (44,256), (256,44), (44,44))
    width, height = 300, 300
    transform = from_origin(77.0, 28.0, 10.0, 10.0)
    crs = "EPSG:32643"

    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": 1,
        "width": width,
        "height": height,
        "crs": crs,
        "transform": transform,
    }

    # Deterministic raster data for B02, B03, B04, B08
    np.random.seed(42)
    bands_data = {
        "B02": np.random.randint(1000, 8000, size=(height, width), dtype=np.uint16),
        "B03": np.random.randint(1200, 9000, size=(height, width), dtype=np.uint16),
        "B04": np.random.randint(1500, 10000, size=(height, width), dtype=np.uint16),
        "B08": np.random.randint(2000, 15000, size=(height, width), dtype=np.uint16),
    }

    for band_name, data in bands_data.items():
        band_file = raw_dir / f"{date_str}-00_00_{date_str}-23_59_Sentinel-2_L2A_{band_name}_(Raw).tiff"
        with rasterio.open(band_file, "w", **profile) as dst:
            dst.write(data, 1)

    return raw_dir


def test_first_run_ingest_sentinel2_date(mock_sentinel2_raw_date: Path, tmp_path: Path) -> None:
    """Verify first run embeds and indexes all generated tiles into Qdrant."""
    tiles_out = tmp_path / "tiles" / "sentinel2" / "2026-09-10"
    emb_dir = tmp_path / "embeddings"

    report = ingest_sentinel2_date(
        raw_date_dir=mock_sentinel2_raw_date,
        output_date_dir=tiles_out,
        tile_size=256,
        verbose=False,
    )

    assert report["date"] == "2026-09-10"
    assert report["tiles_discovered"] == 4
    assert report["tiles_new"] == 4
    assert report["tiles_unchanged"] == 0
    assert report["tiles_changed"] == 0
    assert report["embeddings_generated"] == 4
    assert report["qdrant_points_added"] == 4
    assert report["failed"] == 0
    assert len(report["tiles"]) == 4

    # Verify manifest was populated
    manifest = json.loads((emb_dir / "indexing_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["tiles"]) == 4


def test_second_run_idempotent_skip(mock_sentinel2_raw_date: Path, tmp_path: Path) -> None:
    """Verify repeated run on same date skips existing tiles without re-embedding."""
    tiles_out = tmp_path / "tiles" / "sentinel2" / "2026-09-10"

    # Run 1
    report1 = ingest_sentinel2_date(
        raw_date_dir=mock_sentinel2_raw_date,
        output_date_dir=tiles_out,
        tile_size=256,
        verbose=False,
    )
    assert report1["tiles_new"] == 4
    assert report1["embeddings_generated"] == 4

    # Run 2: Exact same data
    report2 = ingest_sentinel2_date(
        raw_date_dir=mock_sentinel2_raw_date,
        output_date_dir=tiles_out,
        tile_size=256,
        verbose=False,
    )

    assert report2["tiles_discovered"] == 4
    assert report2["tiles_new"] == 0
    assert report2["tiles_unchanged"] == 4
    assert report2["tiles_changed"] == 0
    assert report2["embeddings_generated"] == 0
    assert report2["qdrant_points_added"] == 0
    assert report2["failed"] == 0


def test_incremental_multi_date_isolation(tmp_path: Path) -> None:
    """Verify adding a second date only indexes the second date's tiles."""
    emb_dir = tmp_path / "embeddings"

    transform = from_origin(77.0, 28.0, 10.0, 10.0)
    crs = "EPSG:32643"
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": 1,
        "width": 256,
        "height": 256,
        "crs": crs,
        "transform": transform,
    }

    # Date 1: 2026-09-10
    d1_dir = tmp_path / "raw" / "sentinel2" / "2026-09-10"
    d1_dir.mkdir(parents=True, exist_ok=True)
    for b in ("B02", "B03", "B04", "B08"):
        with rasterio.open(d1_dir / f"2026-09-10_Sentinel-2_{b}.tif", "w", **profile) as dst:
            dst.write(np.full((256, 256), 2000, dtype=np.uint16), 1)

    t1_out = tmp_path / "tiles" / "sentinel2" / "2026-09-10"
    rep1 = ingest_sentinel2_date(d1_dir, output_date_dir=t1_out, tile_size=256, verbose=False)
    assert rep1["tiles_new"] == 1
    assert rep1["embeddings_generated"] == 1

    # Date 2: 2026-09-11
    d2_dir = tmp_path / "raw" / "sentinel2" / "2026-09-11"
    d2_dir.mkdir(parents=True, exist_ok=True)
    for b in ("B02", "B03", "B04", "B08"):
        with rasterio.open(d2_dir / f"2026-09-11_Sentinel-2_{b}.tif", "w", **profile) as dst:
            dst.write(np.full((256, 256), 3000, dtype=np.uint16), 1)

    t2_out = tmp_path / "tiles" / "sentinel2" / "2026-09-11"
    rep2 = ingest_sentinel2_date(d2_dir, output_date_dir=t2_out, tile_size=256, verbose=False)
    assert rep2["date"] == "2026-09-11"
    assert rep2["tiles_new"] == 1
    assert rep2["tiles_unchanged"] == 0
    assert rep2["embeddings_generated"] == 1

    # Manifest should now contain 2 tiles across both dates
    manifest = json.loads((emb_dir / "indexing_manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["tiles"]) == 2


def test_ingest_new_sentinel2_multi_date_lifecycle(tmp_path: Path) -> None:
    """Verify high-level ingest_new_sentinel2 automatic multi-date discovery and idempotency."""
    raw_root = tmp_path / "raw" / "sentinel2"
    tiles_root = tmp_path / "tiles" / "sentinel2"

    transform = from_origin(77.0, 28.0, 10.0, 10.0)
    crs = "EPSG:32643"
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": 1,
        "width": 256,
        "height": 256,
        "crs": crs,
        "transform": transform,
    }

    # Setup 2 dates initially: 2026-09-10 and 2026-09-11
    for d in ("2026-09-10", "2026-09-11"):
        d_path = raw_root / d
        d_path.mkdir(parents=True, exist_ok=True)
        for b in ("B02", "B03", "B04", "B08"):
            with rasterio.open(d_path / f"{d}_Sentinel-2_{b}.tif", "w", **profile) as dst:
                dst.write(np.full((256, 256), 2000, dtype=np.uint16), 1)

    # 1. First run of ingest_new_sentinel2(): processes both dates
    res1 = ingest_new_sentinel2(
        raw_root=raw_root,
        output_root=tiles_root,
        tile_size=256,
        verbose=False,
    )

    assert res1["dates_discovered"] == 2
    assert res1["dates_processed"] == 2
    assert res1["dates_skipped"] == 0
    assert res1["tiles_new"] == 2
    assert res1["tiles_unchanged"] == 0
    assert res1["tiles_changed"] == 0
    assert res1["embeddings_generated"] == 2
    assert res1["qdrant_points_added"] == 2
    assert res1["qdrant_points_updated"] == 0
    assert res1["failed"] == 0

    # 2. Second run of ingest_new_sentinel2(): exactly 0 new embeddings and 0 Qdrant writes
    res2 = ingest_new_sentinel2(
        raw_root=raw_root,
        output_root=tiles_root,
        tile_size=256,
        verbose=False,
    )

    assert res2["dates_discovered"] == 2
    assert res2["dates_processed"] == 0
    assert res2["dates_skipped"] == 2
    assert res2["tiles_new"] == 0
    assert res2["tiles_unchanged"] == 2
    assert res2["tiles_changed"] == 0
    assert res2["embeddings_generated"] == 0
    assert res2["qdrant_points_added"] == 0
    assert res2["qdrant_points_updated"] == 0
    assert res2["failed"] == 0

    # 3. Add 3rd date folder 2026-09-12
    d3_path = raw_root / "2026-09-12"
    d3_path.mkdir(parents=True, exist_ok=True)
    for b in ("B02", "B03", "B04", "B08"):
        with rasterio.open(d3_path / f"2026-09-12_Sentinel-2_{b}.tif", "w", **profile) as dst:
            dst.write(np.full((256, 256), 4000, dtype=np.uint16), 1)

    res3 = ingest_new_sentinel2(
        raw_root=raw_root,
        output_root=tiles_root,
        tile_size=256,
        verbose=False,
    )

    assert res3["dates_discovered"] == 3
    assert res3["dates_processed"] == 1
    assert res3["dates_skipped"] == 2
    assert res3["tiles_new"] == 1
    assert res3["tiles_unchanged"] == 2
    assert res3["tiles_changed"] == 0
    assert res3["embeddings_generated"] == 1
    assert res3["qdrant_points_added"] == 1
    assert res3["qdrant_points_updated"] == 0
    assert res3["failed"] == 0

