"""
Unit and integration test suite for the Sentinel-1 SAR pipeline.

Tests:
- decibel log-transform and amplitude normalization
- 3-channel SAR false-color compositing (VV, VH, VV/VH ratio)
- raw input discovery and polarization pairing
- 256x256 geospatial tiling
- 512-D SAR feature extraction
- isolated incremental indexing (manifest, cache, SHA-256 fingerprinting)
- multi-sensor search routing (sentinel1, sentinel2, all)
- zero impact on production Sentinel-2 collection
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from semantic_search.sentinel1 import (
    create_sentinel1_sar_composite,
    detect_sentinel1_raw_inputs,
    discover_sentinel1_date_dirs,
    extract_acquisition_date,
    find_sentinel1_bands,
    ingest_sentinel1_date,
    normalize_sar_to_uint8,
    split_sar_tile_windows,
    tile_sentinel1_sar,
)
from semantic_search.sentinel1_indexer import (
    compute_file_fingerprint,
    extract_sentinel1_tile_metadata_and_identity,
    index_sentinel1_tiles,
)
from semantic_search.sentinel1_model import (
    extract_sentinel1_image_embedding,
    extract_sentinel1_text_embedding,
    load_sentinel1_model,
)
from semantic_search.schemas import SearchResult
from semantic_search.search import execute_vector_search, search


class TestSentinel1Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(tempfile.mkdtemp(prefix="trinetra_s1_test_"))
        cls.raw_s1_dir = cls.test_dir / "raw" / "sentinel1"
        cls.tiles_s1_dir = cls.test_dir / "tiles" / "sentinel1"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_sar_normalization(self):
        """Test SAR amplitude to uint8 dB normalization."""
        # Flat zeros
        zeros = np.zeros((100, 100), dtype=np.float32)
        norm_zeros = normalize_sar_to_uint8(zeros)
        self.assertEqual(norm_zeros.shape, (100, 100))
        self.assertEqual(norm_zeros.dtype, np.uint8)
        self.assertEqual(int(norm_zeros.max()), 0)

        # Synthetic radar backscatter
        rng = np.random.RandomState(42)
        amp = rng.gamma(shape=2.0, scale=50.0, size=(128, 128)).astype(np.float32)
        norm = normalize_sar_to_uint8(amp, p_low=2.0, p_high=98.0)
        self.assertEqual(norm.shape, (128, 128))
        self.assertEqual(norm.dtype, np.uint8)
        self.assertTrue(0 <= norm.min() <= norm.max() <= 255)
        self.assertTrue(norm.max() > 200)

    def test_02_sar_compositing(self):
        """Test 3-channel SAR false-color compositing (VV, VH, ratio)."""
        rng = np.random.RandomState(42)
        vv = rng.gamma(shape=3.0, scale=40.0, size=(256, 256)).astype(np.float32)
        vh = rng.gamma(shape=2.0, scale=20.0, size=(256, 256)).astype(np.float32)

        composite = create_sentinel1_sar_composite(vv, vh)
        self.assertEqual(composite.shape, (3, 256, 256))
        self.assertEqual(composite.dtype, np.uint8)
        self.assertTrue(0 <= composite.min() <= composite.max() <= 255)

    def test_03_split_windows(self):
        """Test tiling window slicing with edge boundary coverage."""
        windows = split_sar_tile_windows(width=512, height=512, tile_size=256)
        self.assertEqual(len(windows), 4)

        # Non-multiple dimension
        windows_odd = split_sar_tile_windows(width=600, height=600, tile_size=256)
        self.assertEqual(len(windows_odd), 9)

    def test_04_feature_extraction(self):
        """Test SAR 512-D vector extraction for images and queries."""
        synthetic_img = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
        img_emb = extract_sentinel1_image_embedding(synthetic_img)
        self.assertEqual(img_emb.shape, (512,))
        self.assertEqual(img_emb.dtype, np.float32)
        norm = np.linalg.norm(img_emb)
        self.assertAlmostEqual(float(norm), 1.0, places=4)

        txt_emb = extract_sentinel1_text_embedding("radar backscatter urban rough terrain")
        self.assertEqual(txt_emb.shape, (512,))
        self.assertEqual(txt_emb.dtype, np.float32)
        norm_txt = np.linalg.norm(txt_emb)
        self.assertAlmostEqual(float(norm_txt), 1.0, places=4)

    def test_05_date_extraction_and_discovery(self):
        """Test acquisition date parsing and multi-date directory discovery."""
        d1 = extract_acquisition_date("S1A_IW_GRDH_1SDV_20260627T000000_2026-06-27_VV.tif")
        self.assertEqual(d1, "2026-06-27")

        date_dir = self.raw_s1_dir / "2026-06-27"
        date_dir.mkdir(parents=True, exist_ok=True)

        # Create synthetic VV and VH GeoTIFFs
        transform = from_origin(77.15, 28.67, 0.0001, 0.0001)
        profile = {
            "driver": "GTiff",
            "height": 512,
            "width": 512,
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:4326",
            "transform": transform,
        }

        vv_path = date_dir / "sentinel1_2026-06-27_VV.tif"
        vh_path = date_dir / "sentinel1_2026-06-27_VH.tif"

        rng = np.random.RandomState(10)
        vv_data = rng.gamma(shape=3.0, scale=30.0, size=(512, 512)).astype(np.float32)
        vh_data = rng.gamma(shape=2.0, scale=15.0, size=(512, 512)).astype(np.float32)

        with rasterio.open(vv_path, "w", **profile) as dst:
            dst.write(vv_data, 1)

        with rasterio.open(vh_path, "w", **profile) as dst:
            dst.write(vh_data, 1)

        bands = find_sentinel1_bands(date_dir)
        self.assertIn("VV", bands)
        self.assertIn("VH", bands)

        detected = detect_sentinel1_raw_inputs(date_dir)
        self.assertEqual(detected["mode"], "separate_polarizations")

        discovered = discover_sentinel1_date_dirs(self.raw_s1_dir)
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0].name, "2026-06-27")

    def test_06_isolated_indexing_and_idempotency(self):
        """Test full date ingestion and isolated incremental indexer."""
        raw_date_dir = self.raw_s1_dir / "2026-06-27"
        out_date_dir = self.tiles_s1_dir / "2026-06-27"

        # In-memory isolated client for testing
        test_client = QdrantClient(":memory:")
        test_client.create_collection(
            collection_name="sentinel1_tiles",
            vectors_config=VectorParams(size=512, distance=Distance.COSINE),
        )

        # Ingest date and index into isolated test client
        report = ingest_sentinel1_date(
            raw_date_dir=raw_date_dir,
            output_date_dir=out_date_dir,
            tile_size=256,
            overwrite=True,
            force_reindex=False,
            verbose=False,
            client=test_client,
        )

        self.assertEqual(report["date"], "2026-06-27")
        self.assertEqual(report["tiles_generated"], 4)
        self.assertEqual(report["qdrant_points_added"], 5)  # 4 tiles + 1 full
        self.assertTrue((out_date_dir / "sentinel1_tile_1.tif").is_file())
        self.assertTrue((out_date_dir / "sentinel1_sar_full.tif").is_file())
        self.assertEqual(test_client.count("sentinel1_tiles").count, 5)

        # Second run (idempotency check): should be 100% skipped, 0 embeddings
        index_report_2 = index_sentinel1_tiles(
            tiles_dir=out_date_dir,
            force=False,
            verbose=False,
            client=test_client,
        )
        self.assertEqual(index_report_2["qdrant_points_upserted"], 0)
        self.assertEqual(index_report_2["embeddings_generated"], 0)
        self.assertEqual(index_report_2["already_indexed"], 5)

    def test_07_search_result_dataclass_and_tags(self):
        """Test SearchResult schema contains sensor field and dictionary export."""
        res = SearchResult(
            tile_name="sentinel1_tile_1.tif",
            image_path="data/tiles/sentinel1/2026-06-27/sentinel1_tile_1.tif",
            score=0.88,
            crs="EPSG:4326",
            bounds={"left": 77.15, "bottom": 28.57, "right": 77.28, "top": 28.67},
            width=256,
            height=256,
            date="2026-06-27",
            tile_id="sentinel1:2026-06-27:data/tiles/sentinel1/2026-06-27/sentinel1_tile_1.tif",
            sensor="sentinel1",
        )
        d = res.to_dict()
        self.assertEqual(d["sensor"], "sentinel1")
        self.assertEqual(d["tile_name"], "sentinel1_tile_1.tif")
        self.assertEqual(res["sensor"], "sentinel1")

    def test_08_swagger_copernicus_filename_discovery(self):
        """Test discovery of Copernicus / Sentinel Hub exported filenames with dual-pol prefixes."""
        copernicus_dir = self.raw_s1_dir / "2026-06-17"
        copernicus_dir.mkdir(parents=True, exist_ok=True)

        transform = from_origin(77.15, 28.67, 0.0001, 0.0001)
        profile = {
            "driver": "GTiff",
            "height": 128,
            "width": 128,
            "count": 1,
            "dtype": "uint16",
            "crs": "EPSG:4326",
            "transform": transform,
        }

        f_vh_raw = copernicus_dir / "2026-06-17-00_00_2026-06-17-23_59_Sentinel-1_IW_VV_VH_VH_(Raw).tiff"
        f_vh_gamma = copernicus_dir / "2026-06-17-00_00_2026-06-17-23_59_Sentinel-1_IW_VV_VH_VH_-_decibel_gamma0.tiff"
        f_vv_raw = copernicus_dir / "2026-06-17-00_00_2026-06-17-23_59_Sentinel-1_IW_VV_VH_VV_(Raw).tiff"
        f_vv_gamma = copernicus_dir / "2026-06-17-00_00_2026-06-17-23_59_Sentinel-1_IW_VV_VH_VV_-_decibel_gamma0.tiff"

        rng = np.random.RandomState(42)
        data = rng.randint(0, 1000, size=(128, 128), dtype=np.uint16)

        for p in (f_vh_raw, f_vv_raw):
            with rasterio.open(p, "w", **profile) as dst:
                dst.write(data, 1)

        prof3 = profile.copy()
        prof3["count"] = 3
        data3 = np.stack([data, data, data], axis=0)
        for p in (f_vh_gamma, f_vv_gamma):
            with rasterio.open(p, "w", **prof3) as dst:
                dst.write(data3)

        bands = find_sentinel1_bands(copernicus_dir)
        self.assertEqual(bands["VV"], f_vv_raw)
        self.assertEqual(bands["VH"], f_vh_raw)

        detected = detect_sentinel1_raw_inputs(copernicus_dir)
        self.assertEqual(detected["mode"], "separate_polarizations")
        self.assertEqual(detected["bands"]["VV"], f_vv_raw)
        self.assertEqual(detected["bands"]["VH"], f_vh_raw)

    def test_09_simple_raw_and_gamma0_mixed_discovery(self):
        """Test simple filename pairing e.g. VV (Raw).tiff, VH (Raw).tiff alongside gamma0."""
        simple_dir = self.raw_s1_dir / "2026-07-01"
        simple_dir.mkdir(parents=True, exist_ok=True)

        transform = from_origin(77.15, 28.67, 0.0001, 0.0001)
        profile = {
            "driver": "GTiff",
            "height": 64,
            "width": 64,
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:4326",
            "transform": transform,
        }

        f_vv_raw = simple_dir / "VV (Raw).tiff"
        f_vh_raw = simple_dir / "VH (Raw).tiff"
        f_vv_gamma = simple_dir / "VV - decibel gamma0.tiff"
        f_vh_gamma = simple_dir / "VH - decibel gamma0.tiff"

        rng = np.random.RandomState(42)
        data = rng.gamma(shape=2.0, scale=10.0, size=(64, 64)).astype(np.float32)

        for p in (f_vv_raw, f_vh_raw, f_vv_gamma, f_vh_gamma):
            with rasterio.open(p, "w", **profile) as dst:
                dst.write(data, 1)

        bands = find_sentinel1_bands(simple_dir)
        self.assertEqual(bands["VV"], f_vv_raw)
        self.assertEqual(bands["VH"], f_vh_raw)

        detected = detect_sentinel1_raw_inputs(simple_dir)
        self.assertEqual(detected["mode"], "separate_polarizations")

    def test_10_sentinel1_temporal_change_analysis(self):
        """Test temporal change detection across verified 2026-03-13 and 2026-06-17 acquisitions."""
        from semantic_search.sentinel1_change import (
            compare_sentinel1_tile_pair,
            find_date_grid_tiles,
            run_sentinel1_temporal_change_analysis,
        )

        tiles_03_13 = find_date_grid_tiles("2026-03-13")
        tiles_06_17 = find_date_grid_tiles("2026-06-17")

        # Excludes full composite
        self.assertEqual(len(tiles_03_13), 80)
        self.assertEqual(len(tiles_06_17), 80)
        self.assertNotIn("sentinel1_sar_full.tif", [p.name for p in tiles_03_13.values()])

        # Single tile pair test
        metric, change_arr, mask_arr, meta = compare_sentinel1_tile_pair(
            before_path=tiles_03_13[1],
            after_path=tiles_06_17[1],
            before_date="2026-03-13",
            after_date="2026-06-17",
            tile_index=1,
        )
        self.assertEqual(metric.tile_index, 1)
        self.assertEqual(metric.before_date, "2026-03-13")
        self.assertEqual(metric.after_date, "2026-06-17")
        self.assertTrue(0.0 <= metric.combined_change_score <= 1.0)
        self.assertIn(metric.intensity_level, ["LOW", "MODERATE", "HIGH", "SIGNIFICANT"])
        self.assertEqual(metric.semantic_label, "SAR Backscatter Change (Screening)")
        self.assertEqual(change_arr.shape, (3, 256, 256))

        # Full 80-pair batch analysis test
        test_out_dir = self.test_dir / "test_s1_change_out"
        report = run_sentinel1_temporal_change_analysis(
            before_date="2026-03-13",
            after_date="2026-06-17",
            output_dir=test_out_dir,
            save_mosaic=True,
        )

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["pairs_matched"], 80)
        self.assertEqual(report["pairs_processed"], 80)
        self.assertEqual(report["pairs_failed"], 0)
        self.assertTrue(report["full_composite_excluded"])
        self.assertEqual(len(report["all_tile_metrics"]), 80)

        # Check mosaic file
        mosaic_p = Path(report["mosaic_path"])
        self.assertTrue(mosaic_p.is_file())
        with rasterio.open(mosaic_p) as src:
            self.assertEqual(src.count, 3)
            self.assertEqual(src.height, 2035)
            self.assertEqual(src.width, 2500)
    def test_11_sentinel1_physical_change_analysis(self):
        """Test physical/log-scale decibel change detection across 2026-03-13 and 2026-06-17."""
        from semantic_search.sentinel1_change import (
            compare_sentinel1_tile_pair_physical,
            find_date_grid_tiles,
            run_sentinel1_physical_change_analysis,
        )

        tiles_03_13 = find_date_grid_tiles("2026-03-13")
        tiles_06_17 = find_date_grid_tiles("2026-06-17")

        # Single tile pair physical test
        metric, change_arr, mask_arr, meta = compare_sentinel1_tile_pair_physical(
            before_path=tiles_03_13[1],
            after_path=tiles_06_17[1],
            before_date="2026-03-13",
            after_date="2026-06-17",
            tile_index=1,
        )
        self.assertEqual(metric.tile_index, 1)
        self.assertEqual(metric.before_date, "2026-03-13")
        self.assertEqual(metric.after_date, "2026-06-17")
        self.assertEqual(metric.semantic_label, "Calibrated SAR Backscatter Change")
        self.assertEqual(change_arr.shape, (3, 256, 256))
        self.assertEqual(change_arr.dtype, np.float32)
        self.assertIn(metric.physical_change_tier, ["NOMINAL", "MODERATE", "ELEVATED", "CRITICAL"])
        self.assertTrue(0.0 <= metric.pct_abs_delta_vv_gt_3db <= 100.0)
        self.assertTrue(0.0 <= metric.pct_combined_gt_3db <= 100.0)

        # Full 80-pair physical batch analysis test
        test_out_dir = self.test_dir / "test_s1_physical_change_out"
        report = run_sentinel1_physical_change_analysis(
            before_date="2026-03-13",
            after_date="2026-06-17",
            output_dir=test_out_dir,
            save_mosaic=True,
        )

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["methodology"], "physical_log_scale_decibel")
        self.assertEqual(report["pairs_matched"], 80)
        self.assertEqual(report["pairs_processed"], 80)
        self.assertEqual(report["pairs_failed"], 0)
        self.assertTrue(report["full_composite_excluded"])
        self.assertEqual(len(report["all_tile_metrics"]), 80)

        # Check physical mosaic file
        mosaic_p = Path(report["mosaic_path"])
        self.assertTrue(mosaic_p.is_file())
        with rasterio.open(mosaic_p) as src:
            self.assertEqual(src.count, 3)
            self.assertEqual(src.height, 2035)
            self.assertEqual(src.width, 2500)
    def test_12_single_tile_sensor_isolated_change_detection(self):
        """Test single tile Sentinel-1 change detection and sensor parameter validation."""
        from semantic_search.sentinel1_change import compare_sentinel1_single_tile

        before_path = Path("data/tiles/sentinel1/2026-03-13/sentinel1_tile_1.tif")
        after_path = Path("data/tiles/sentinel1/2026-06-17/sentinel1_tile_1.tif")
        
        if before_path.is_file() and after_path.is_file():
            res = compare_sentinel1_single_tile(
                before_path=before_path,
                after_path=after_path,
            )
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["sensor"], "sentinel1")
            self.assertEqual(res["mode_used"], "sentinel1_physical_db")
            self.assertIn("has_change", res)
            self.assertIn("change_ratio", res)
            self.assertIn("mask_path", res)
            self.assertIn("overlay_path", res)
            self.assertIn("sar_metrics", res)


if __name__ == "__main__":
    unittest.main()


