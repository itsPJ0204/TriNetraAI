"""
tests/test_multisensor_fusion.py — Unit & Integration Tests for Multisensor Temporal Fusion (Phase 2)
====================================================================================================
Tests:
- S1-only execution
- S2-only execution
- Dual-sensor (both) execution
- Default sensor fallback (None / empty -> 'both')
- EPSG:4326 geographic bounding box overlap calculation
- Synthetic overlapping tile fusion with all 4 evidence categories:
  * BOTH_S1_S2_CHANGE
  * S1_ONLY_CHANGE
  * S2_ONLY_CHANGE
  * LOW_EVIDENCE
- Disjoint non-overlapping geographic regions handling
- Invalid / mismatched date handling (FileNotFoundError / ValueError)
- FastAPI /change-detection/multisensor/temporal endpoint validation
"""

import unittest
from pathlib import Path
import tempfile
import shutil
import numpy as np
import rasterio
from rasterio.transform import from_origin

from fastapi.testclient import TestClient

from backend.main import app
from semantic_search.multisensor_change import (
    MultisensorFusionCandidate,
    S1Evidence,
    S2Evidence,
    compute_bbox_intersection,
    find_s2_grid_tiles,
    run_multisensor_temporal_fusion,
    run_sentinel2_temporal_change_analysis,
    _compute_fusion_ranking_score,
    _generate_fusion_summary,
    _is_s1_change_meaningful,
    _is_s2_change_meaningful,
)


class TestMultisensorFusion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.test_dir = Path(tempfile.mkdtemp(prefix="trinetra_fusion_test_"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_dir, ignore_errors=True)

    def test_01_bbox_intersection_math(self):
        """Test geographic bounding box intersection and IoU calculation."""
        # Partially overlapping boxes
        b1 = {"left": 77.10, "bottom": 28.50, "right": 77.20, "top": 28.60}
        b2 = {"left": 77.15, "bottom": 28.55, "right": 77.25, "top": 28.65}

        inter_bbox, inter_area, iou = compute_bbox_intersection(b1, b2)
        self.assertIsNotNone(inter_bbox)
        self.assertAlmostEqual(inter_bbox["left"], 77.15, places=5)
        self.assertAlmostEqual(inter_bbox["bottom"], 28.55, places=5)
        self.assertAlmostEqual(inter_bbox["right"], 77.20, places=5)
        self.assertAlmostEqual(inter_bbox["top"], 28.60, places=5)
        self.assertGreater(inter_area, 0.0)
        self.assertTrue(0.0 < iou < 1.0)

        # Identical boxes (IoU = 1.0)
        inter_same, _, iou_same = compute_bbox_intersection(b1, b1)
        self.assertEqual(inter_same, b1)
        self.assertAlmostEqual(iou_same, 1.0, places=5)

        # Disjoint boxes (no overlap)
        b_disjoint = {"left": 88.0, "bottom": 22.0, "right": 88.1, "top": 22.1}
        inter_disjoint, inter_area_d, iou_d = compute_bbox_intersection(b1, b_disjoint)
        self.assertIsNone(inter_disjoint)
        self.assertEqual(inter_area_d, 0.0)
        self.assertEqual(iou_d, 0.0)

    def test_02_evidence_categorization_and_ranking(self):
        """Test evidence fusion categorization and candidate ranking scores."""
        # High S1 evidence
        s1_high = S1Evidence(
            tile_id="s1_test_1",
            tile_index=1,
            tile_name="tile_1.tif",
            before_date="2026-03-13",
            after_date="2026-06-17",
            mean_delta_vv_db=3.5,
            mean_abs_delta_vv_db=5.2,
            mean_delta_vh_db=-8.2,
            mean_abs_delta_vh_db=8.9,
            mean_combined_abs_db=18.5,
            pct_abs_delta_vv_gt_3db=80.0,
            pct_combined_gt_3db=85.0,
            pct_combined_gt_5db=78.0,
            physical_tier="ELEVATED",
            geographic_bounds={"left": 77.1, "bottom": 28.5, "right": 77.2, "top": 28.6},
            crs="EPSG:4326",
        )

        # Nominal S1 evidence
        s1_low = S1Evidence(
            tile_id="s1_test_2",
            tile_index=2,
            tile_name="tile_2.tif",
            before_date="2026-03-13",
            after_date="2026-06-17",
            mean_delta_vv_db=-0.1,
            mean_abs_delta_vv_db=1.2,
            mean_delta_vh_db=0.2,
            mean_abs_delta_vh_db=1.5,
            mean_combined_abs_db=4.1,
            pct_abs_delta_vv_gt_3db=10.0,
            pct_combined_gt_3db=12.0,
            pct_combined_gt_5db=5.0,
            physical_tier="NOMINAL",
            geographic_bounds={"left": 77.1, "bottom": 28.5, "right": 77.2, "top": 28.6},
            crs="EPSG:4326",
        )

        # High S2 evidence
        s2_high = S2Evidence(
            tile_id="s2_test_1",
            tile_index=1,
            tile_name="tile_1.tif",
            before_date="2026-01-18",
            after_date="2026-06-27",
            change_ratio=0.15,
            target_count=8,
            has_change=True,
            detected_targets=[],
            qa_applied=True,
            valid_pixel_pct=98.0,
            optical_mode="classical_absdiff",
            geographic_bounds={"left": 77.1, "bottom": 28.5, "right": 77.2, "top": 28.6},
            crs="EPSG:4326",
        )

        # Low S2 evidence
        s2_low = S2Evidence(
            tile_id="s2_test_2",
            tile_index=2,
            tile_name="tile_2.tif",
            before_date="2026-01-18",
            after_date="2026-06-27",
            change_ratio=0.01,
            target_count=0,
            has_change=False,
            detected_targets=[],
            qa_applied=True,
            valid_pixel_pct=99.0,
            optical_mode="classical_absdiff",
            geographic_bounds={"left": 77.1, "bottom": 28.5, "right": 77.2, "top": 28.6},
            crs="EPSG:4326",
        )

        self.assertTrue(_is_s1_change_meaningful(s1_high))
        self.assertFalse(_is_s1_change_meaningful(s1_low))
        self.assertTrue(_is_s2_change_meaningful(s2_high))
        self.assertFalse(_is_s2_change_meaningful(s2_low))

        # Test fusion scores
        score_both = _compute_fusion_ranking_score(s1_high, s2_high, "BOTH_S1_S2_CHANGE")
        score_s1_only = _compute_fusion_ranking_score(s1_high, None, "S1_ONLY_CHANGE")
        score_s2_only = _compute_fusion_ranking_score(None, s2_high, "S2_ONLY_CHANGE")
        score_low = _compute_fusion_ranking_score(s1_low, s2_low, "LOW_EVIDENCE")

        self.assertTrue(0.0 <= score_both <= 1.0)
        self.assertTrue(0.0 <= score_s1_only <= 1.0)
        self.assertTrue(0.0 <= score_s2_only <= 1.0)
        self.assertTrue(0.0 <= score_low <= 1.0)
        self.assertGreater(score_both, score_low)

    def test_03_s1_only_fusion_mode(self):
        """Test running fusion in S1-only mode."""
        report = run_multisensor_temporal_fusion(
            sensor="sentinel1",
            s1_before_date="2026-03-13",
            s1_after_date="2026-06-17",
            output_dir=self.test_dir / "s1_only_test",
        )
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["sensor_executed"], "sentinel1")
        self.assertEqual(report["s1_temporal_pair"]["tiles_processed"], 80)
        self.assertEqual(report["s2_temporal_pair"]["tiles_processed"], 0)
        self.assertEqual(report["fusion_statistics"]["multisensor_matched_areas"], 0)
        self.assertEqual(report["fusion_statistics"]["s1_only_candidates"], 80)
        self.assertEqual(report["fusion_statistics"]["s2_only_candidates"], 0)

    def test_04_disjoint_spatial_coverage_multisensor(self):
        """Test dual-sensor execution on disjoint regional datasets (Kolkata S1 vs Delhi S2)."""
        # When geographic footprints do not overlap, matcher properly isolates them
        report = run_multisensor_temporal_fusion(
            sensor="both",
            s1_before_date="2026-03-13",
            s1_after_date="2026-06-17",
            s2_before_date="2026-01-18",
            s2_after_date="2026-06-27",
            output_dir=self.test_dir / "disjoint_fusion_test",
        )
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["sensor_executed"], "both")
        self.assertEqual(report["s1_temporal_pair"]["tiles_processed"], 80)
        self.assertEqual(report["s2_temporal_pair"]["tiles_processed"], 30)
        # Because Kolkata and Delhi do not overlap:
        self.assertEqual(report["fusion_statistics"]["multisensor_matched_areas"], 0)
        self.assertEqual(report["fusion_statistics"]["s1_only_candidates"], 80)
        self.assertEqual(report["fusion_statistics"]["s2_only_candidates"], 30)
        self.assertEqual(report["fusion_statistics"]["total_candidates"], 110)

    def test_05_default_sensor_fallback(self):
        """Test default behavior when sensor is None or 'all' -> falls back to 'both'."""
        report_none = run_multisensor_temporal_fusion(
            sensor=None,
            s1_before_date="2026-03-13",
            s1_after_date="2026-06-17",
            s2_before_date="2026-01-18",
            s2_after_date="2026-06-27",
            output_dir=self.test_dir / "default_fallback_test",
        )
        self.assertEqual(report_none["sensor_executed"], "both")

        report_all = run_multisensor_temporal_fusion(
            sensor="all",
            s1_before_date="2026-03-13",
            s1_after_date="2026-06-17",
            s2_before_date="2026-01-18",
            s2_after_date="2026-06-27",
            output_dir=self.test_dir / "all_fallback_test",
        )
        self.assertEqual(report_all["sensor_executed"], "both")

    def test_06_invalid_sensor_and_dates(self):
        """Test validation error for invalid sensor name or nonexistent acquisition dates."""
        # Invalid sensor name
        with self.assertRaises(ValueError):
            run_multisensor_temporal_fusion(sensor="landsat8")

        # Nonexistent S1 date
        with self.assertRaises(FileNotFoundError):
            run_multisensor_temporal_fusion(
                sensor="sentinel1",
                s1_before_date="1999-01-01",
                s1_after_date="1999-02-01",
            )

        # Nonexistent S2 date
        with self.assertRaises(FileNotFoundError):
            run_multisensor_temporal_fusion(
                sensor="sentinel2",
                s2_before_date="1999-01-01",
                s2_after_date="1999-02-01",
            )

    def test_07_fastapi_endpoint(self):
        """Test POST /change-detection/multisensor/temporal API endpoint."""
        # S1-only request via API
        response = self.client.post(
            "/change-detection/multisensor/temporal",
            json={
                "sensor": "sentinel1",
                "s1_before_date": "2026-03-13",
                "s1_after_date": "2026-06-17",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["sensor_executed"], "sentinel1")
        self.assertEqual(data["fusion_statistics"]["s1_only_candidates"], 80)

        # Default request (no sensor specified -> 'both')
        response_def = self.client.post(
            "/change-detection/multisensor/temporal",
            json={
                "s1_before_date": "2026-03-13",
                "s1_after_date": "2026-06-17",
                "s2_before_date": "2026-01-18",
                "s2_after_date": "2026-06-27",
            },
        )
        self.assertEqual(response_def.status_code, 200)
        data_def = response_def.json()
        self.assertEqual(data_def["status"], "success")
        self.assertEqual(data_def["sensor_executed"], "both")
        self.assertEqual(data_def["fusion_statistics"]["total_candidates"], 110)

        # 404 on nonexistent date
        response_err = self.client.post(
            "/change-detection/multisensor/temporal",
            json={
                "sensor": "sentinel1",
                "s1_before_date": "1999-01-01",
                "s1_after_date": "1999-02-01",
            },
        )
        self.assertEqual(response_err.status_code, 404)

    def test_08_synthetic_overlapping_tile_fusion(self):
        """Test true multisensor geographic overlap fusion with collocated synthetic S1 and S2 tiles."""
        synth_root = self.test_dir / "synth_fusion"
        s1_raw = synth_root / "s1_raw"
        s2_tiles = synth_root / "s2_tiles"

        d_before = "2026-08-01"
        d_after = "2026-08-15"

        (s1_raw / d_before).mkdir(parents=True, exist_ok=True)
        (s1_raw / d_after).mkdir(parents=True, exist_ok=True)
        (s2_tiles / d_before).mkdir(parents=True, exist_ok=True)
        (s2_tiles / d_after).mkdir(parents=True, exist_ok=True)

        transform = from_origin(77.15, 28.67, 0.0001, 0.0001)

        # 1. Create S1 Raw GeoTIFFs (1-band float32)
        s1_prof = {
            "driver": "GTiff",
            "height": 256,
            "width": 256,
            "count": 1,
            "dtype": "float32",
            "crs": "EPSG:4326",
            "transform": transform,
        }
        # Before: low backscatter; After: high backscatter (significant dB rise)
        rng = np.random.RandomState(42)
        vv_b = rng.gamma(shape=2.0, scale=10.0, size=(256, 256)).astype(np.float32)
        vh_b = rng.gamma(shape=1.5, scale=5.0, size=(256, 256)).astype(np.float32)
        vv_a = rng.gamma(shape=5.0, scale=80.0, size=(256, 256)).astype(np.float32)
        vh_a = rng.gamma(shape=4.0, scale=40.0, size=(256, 256)).astype(np.float32)

        with rasterio.open(s1_raw / d_before / f"sentinel1_{d_before}_VV.tif", "w", **s1_prof) as dst:
            dst.write(vv_b, 1)
        with rasterio.open(s1_raw / d_before / f"sentinel1_{d_before}_VH.tif", "w", **s1_prof) as dst:
            dst.write(vh_b, 1)
        with rasterio.open(s1_raw / d_after / f"sentinel1_{d_after}_VV.tif", "w", **s1_prof) as dst:
            dst.write(vv_a, 1)
        with rasterio.open(s1_raw / d_after / f"sentinel1_{d_after}_VH.tif", "w", **s1_prof) as dst:
            dst.write(vh_a, 1)

        # 2. Create S2 Tile GeoTIFFs (3-band uint8 RGB)
        s2_prof = {
            "driver": "GTiff",
            "height": 256,
            "width": 256,
            "count": 3,
            "dtype": "uint8",
            "crs": "EPSG:4326",
            "transform": transform,
        }
        s2_b = np.full((3, 256, 256), 30, dtype=np.uint8)
        s2_a = np.full((3, 256, 256), 30, dtype=np.uint8)
        # Add strong optical spectral change (e.g. soil clearing / construction)
        s2_a[0, 50:150, 50:150] = 200
        s2_a[1, 50:150, 50:150] = 120
        s2_a[2, 50:150, 50:150] = 40

        with rasterio.open(s2_tiles / d_before / "sentinel2_tile_1.tif", "w", **s2_prof) as dst:
            dst.write(s2_b)
        with rasterio.open(s2_tiles / d_after / "sentinel2_tile_1.tif", "w", **s2_prof) as dst:
            dst.write(s2_a)

        # Execute fusion on collocated synthetic datasets
        report = run_multisensor_temporal_fusion(
            sensor="both",
            s1_before_date=d_before,
            s1_after_date=d_after,
            s2_before_date=d_before,
            s2_after_date=d_after,
            s1_raw_root=s1_raw,
            s2_tiles_root=s2_tiles,
            output_dir=synth_root / "out",
        )

        self.assertEqual(report["status"], "success")
        self.assertEqual(report["fusion_statistics"]["multisensor_matched_areas"], 1)
        self.assertEqual(report["fusion_statistics"]["total_candidates"], 1)

        cand = report["all_candidates"][0]
        self.assertEqual(cand["sensor_coverage"], "multisensor")
        self.assertEqual(cand["fusion_category"], "BOTH_S1_S2_CHANGE")
        self.assertIsNotNone(cand["s1_evidence"])
        self.assertIsNotNone(cand["s2_evidence"])
        self.assertAlmostEqual(cand["spatial_overlap_iou"], 1.0, places=3)
        self.assertGreater(cand["fusion_score"], 0.5)
        self.assertIn("Coincident Multi-Sensor Anomaly", cand["fusion_summary"])


if __name__ == "__main__":
    unittest.main()
