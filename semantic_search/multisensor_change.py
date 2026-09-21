"""
semantic_search/multisensor_change.py — Sentinel-1 & Sentinel-2 Sensor-Aware Temporal Change Fusion
===================================================================================================
Combines independently computed Sentinel-1 (C-band SAR backscatter) and Sentinel-2 (Optical reflection)
temporal change evidence at the geographic/tile level.

Key Design Principles:
1. Complete Isolation: S1 and S2 pipelines operate independently on their native physics.
2. Spatial Grounding: Matching is performed strictly via EPSG:4326 geographic bounding box overlap.
   Tile indices from different sensors are never assumed to represent the same location.
3. Candidate Representation: Common geographic candidate schema containing calibrated S1 decibel metrics,
   S2 optical change metrics, QA suppression metadata, and provenance.
4. Scientific Neutrality: SAR backscatter changes are labeled as "Calibrated SAR Backscatter Change"
   without inferring unsubstantiated optical causes. Fusion scores represent candidate ranking heuristics,
   not uncalibrated probabilities.
5. Evidence Categories:
   - BOTH_S1_S2_CHANGE: Both radar and optical sensors detect significant change in the overlapping area.
   - S1_ONLY_CHANGE: Radar detects significant backscatter change, optical detects no change / QA occluded / absent.
   - S2_ONLY_CHANGE: Optical detects significant spectral change, radar detects nominal backscatter / absent.
   - LOW_EVIDENCE: Neither sensor detects significant change in the geographic area.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import re
from typing import Any

import numpy as np
import rasterio

from semantic_search.sentinel1_change import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_S1_RAW_DIR,
    DEFAULT_S1_TILES_DIR,
    Sentinel1PhysicalChangeMetric,
    run_sentinel1_physical_change_analysis,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_S2_TILES_DIR = PROJECT_ROOT / "data" / "tiles" / "sentinel2"
DEFAULT_FUSION_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "multisensor_change"


# ===========================================================================
# DATA STRUCTURES
# ===========================================================================


@dataclass
class S1Evidence:
    """Sentinel-1 SAR temporal change evidence."""
    tile_id: str
    tile_index: int
    tile_name: str
    before_date: str
    after_date: str
    mean_delta_vv_db: float
    mean_abs_delta_vv_db: float
    mean_delta_vh_db: float
    mean_abs_delta_vh_db: float
    mean_combined_abs_db: float
    pct_abs_delta_vv_gt_3db: float
    pct_combined_gt_3db: float
    pct_combined_gt_5db: float
    physical_tier: str  # "NOMINAL", "MODERATE", "ELEVATED", "CRITICAL"
    geographic_bounds: dict[str, float]
    crs: str
    semantic_label: str = "Calibrated SAR Backscatter Change"
    provenance: str = "Sentinel-1 Level-1 GRD IW Calibrated Log-Ratio (dB)"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class S2Evidence:
    """Sentinel-2 Optical temporal change evidence."""
    tile_id: str
    tile_index: int
    tile_name: str
    before_date: str
    after_date: str
    change_ratio: float
    target_count: int
    has_change: bool
    detected_targets: list[dict[str, Any]]
    qa_applied: bool
    valid_pixel_pct: float
    optical_mode: str  # "neural_bit", "classical_absdiff", "qa_early_exit"
    geographic_bounds: dict[str, float]
    crs: str
    semantic_label: str = "Optical Spectral Change"
    provenance: str = "Sentinel-2 L2A BOA Multispectral Reflection"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MultisensorFusionCandidate:
    """Common geographic candidate representation fusing S1 and S2 evidence."""
    candidate_id: str
    geographic_bounds: dict[str, float]  # {"left", "bottom", "right", "top"}
    crs: str
    sensor_coverage: str  # "sentinel1", "sentinel2", "multisensor"
    fusion_category: str  # "BOTH_S1_S2_CHANGE", "S1_ONLY_CHANGE", "S2_ONLY_CHANGE", "LOW_EVIDENCE"
    s1_before_date: str | None
    s1_after_date: str | None
    s2_before_date: str | None
    s2_after_date: str | None
    s1_evidence: dict[str, Any] | None
    s2_evidence: dict[str, Any] | None
    spatial_overlap_iou: float | None
    fusion_score: float  # Candidate ranking heuristic [0.0, 1.0]
    fusion_summary: str
    data_quality_provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ===========================================================================
# GEOGRAPHIC BOUNDS & OVERLAP UTILITIES
# ===========================================================================


def compute_bbox_intersection(
    b1: dict[str, float], b2: dict[str, float]
) -> tuple[dict[str, float] | None, float, float]:
    """Compute geographic intersection bounding box, intersection area (deg^2), and IoU.

    Coordinates must be in EPSG:4326 (degrees).
    """
    l1, b_1, r1, t1 = float(b1["left"]), float(b1["bottom"]), float(b1["right"]), float(b1["top"])
    l2, b_2, r2, t2 = float(b2["left"]), float(b2["bottom"]), float(b2["right"]), float(b2["top"])

    inter_l = max(l1, l2)
    inter_b = max(b_1, b_2)
    inter_r = min(r1, r2)
    inter_t = min(t1, t2)

    if inter_r <= inter_l or inter_t <= inter_b:
        return None, 0.0, 0.0

    inter_area = (inter_r - inter_l) * (inter_t - inter_b)
    area1 = max(0.0, (r1 - l1) * (t1 - b_1))
    area2 = max(0.0, (r2 - l2) * (t2 - b_2))
    union_area = area1 + area2 - inter_area
    iou = inter_area / union_area if union_area > 0 else 0.0

    inter_bbox = {
        "left": round(inter_l, 6),
        "bottom": round(inter_b, 6),
        "right": round(inter_r, 6),
        "top": round(inter_t, 6),
    }
    return inter_bbox, inter_area, iou


def find_s2_grid_tiles(
    date_str: str,
    tiles_root: Path | str = DEFAULT_S2_TILES_DIR,
) -> dict[int, Path]:
    """Find and index all Sentinel-2 grid tiles for a given date, excluding full composites."""
    root = Path(tiles_root) / date_str
    if not root.is_dir():
        raise FileNotFoundError(f"Sentinel-2 tiles directory not found for date {date_str}: {root}")

    grid_tiles: dict[int, Path] = {}
    for p in sorted(root.glob("*.tif*")):
        if "full" in p.name.lower() or "composite" in p.name.lower():
            continue
        m = re.search(r"tile_(\d+)", p.stem, re.IGNORECASE)
        if m:
            grid_tiles[int(m.group(1))] = p

    return grid_tiles


# ===========================================================================
# SENTINEL-2 TEMPORAL CHANGE ANALYSIS RUNNER
# ===========================================================================


def run_sentinel2_temporal_change_analysis(
    before_date: str = "2026-01-18",
    after_date: str = "2026-06-27",
    tiles_root: Path | str = DEFAULT_S2_TILES_DIR,
    force_classical: bool = True,
    apply_qa_suppression: bool = True,
    min_area: int = 100,
    max_targets: int = 2,
) -> dict[str, Any]:
    """Execute Sentinel-2 optical temporal change detection across matching grid tiles."""
    from detective_api import compare_tiles

    tiles_before = find_s2_grid_tiles(before_date, tiles_root=tiles_root)
    tiles_after = find_s2_grid_tiles(after_date, tiles_root=tiles_root)

    common_indices = sorted(set(tiles_before.keys()) & set(tiles_after.keys()))
    if not common_indices:
        raise ValueError(f"No matching Sentinel-2 tiles found between {before_date} and {after_date}")

    s2_evidences: list[S2Evidence] = []

    for tile_idx in common_indices:
        p_before = tiles_before[tile_idx]
        p_after = tiles_after[tile_idx]

        with rasterio.open(p_before) as src:
            bounds_dict = {
                "left": float(src.bounds.left),
                "bottom": float(src.bounds.bottom),
                "right": float(src.bounds.right),
                "top": float(src.bounds.top),
            }
            crs_str = str(src.crs) if src.crs else "EPSG:4326"

        try:
            report = compare_tiles(
                tile_t1_path=str(p_before),
                tile_t2_path=str(p_after),
                force_classical=force_classical,
                apply_qa_suppression=apply_qa_suppression,
                min_area=min_area,
                max_targets=max_targets,
                output_dir=str(PROJECT_ROOT / "outputs" / "sentinel2_change"),
            )
            qa_info = report.get("qa_suppression", {})
            qa_applied = bool(qa_info.get("qa_applied", False))
            valid_pixel_pct = float(qa_info.get("valid_pixel_pct", 100.0))
            change_ratio = float(report.get("change_ratio", 0.0))
            has_change = bool(report.get("has_change", False))
            target_count = int(report.get("target_count", 0))
            detected_targets = report.get("detected_targets", [])
            mode_used = str(report.get("mode_used", "classical_absdiff"))
        except Exception as err:
            logger.warning("Error processing S2 tile %d (%s ↔ %s): %s", tile_idx, before_date, after_date, err)
            qa_applied = False
            valid_pixel_pct = 100.0
            change_ratio = 0.0
            has_change = False
            target_count = 0
            detected_targets = []
            mode_used = "error_fallback"

        evidence = S2Evidence(
            tile_id=f"sentinel2_{before_date}_{after_date}_tile_{tile_idx}",
            tile_index=tile_idx,
            tile_name=p_before.name,
            before_date=before_date,
            after_date=after_date,
            change_ratio=round(change_ratio, 4),
            target_count=target_count,
            has_change=has_change,
            detected_targets=detected_targets,
            qa_applied=qa_applied,
            valid_pixel_pct=valid_pixel_pct,
            optical_mode=mode_used,
            geographic_bounds=bounds_dict,
            crs=crs_str,
            semantic_label="Optical Spectral Change",
            provenance="Sentinel-2 L2A BOA Multispectral Reflection",
        )
        s2_evidences.append(evidence)

    return {
        "status": "success",
        "sensor": "sentinel2",
        "before_date": before_date,
        "after_date": after_date,
        "tiles_matched": len(s2_evidences),
        "evidences": s2_evidences,
    }


# ===========================================================================
# MULTISENSOR FUSION ENGINE (PHASE 2)
# ===========================================================================


def _is_s1_change_meaningful(evidence: S1Evidence) -> bool:
    """Determine if Sentinel-1 SAR evidence indicates meaningful backscatter change."""
    return (
        evidence.physical_tier in ("MODERATE", "ELEVATED", "CRITICAL")
        or evidence.mean_combined_abs_db >= 10.0
        or evidence.pct_combined_gt_5db >= 70.0
    )


def _is_s2_change_meaningful(evidence: S2Evidence) -> bool:
    """Determine if Sentinel-2 Optical evidence indicates meaningful spectral change."""
    if evidence.optical_mode == "qa_early_exit" or evidence.valid_pixel_pct < 15.0:
        return False  # Heavy cloud occlusion suppresses confidence
    return evidence.has_change and evidence.change_ratio >= 0.03


def _compute_fusion_ranking_score(
    s1_ev: S1Evidence | None,
    s2_ev: S2Evidence | None,
    category: str,
) -> float:
    """Compute an uncalibrated candidate ranking score in [0.0, 1.0].

    Note: This is a candidate ranking heuristic, NOT a calibrated statistical probability.
    """
    s1_score = 0.0
    if s1_ev is not None:
        # Normalized dB power ratio: 0 dB -> 0.0, 25 dB -> 1.0
        s1_score = float(np.clip(s1_ev.mean_combined_abs_db / 25.0, 0.0, 1.0))

    s2_score = 0.0
    if s2_ev is not None:
        # Optical change ratio: 0% -> 0.0, 20% -> 1.0
        s2_score = float(np.clip(s2_ev.change_ratio * 5.0, 0.0, 1.0))
        if s2_ev.optical_mode == "qa_early_exit":
            s2_score *= 0.1

    if category == "BOTH_S1_S2_CHANGE":
        # Multi-sensor harmonic mean emphasizes dual-sensor agreement
        score = 2.0 * (s1_score * s2_score) / (s1_score + s2_score + 1e-6)
        return round(float(np.clip(score, 0.1, 1.0)), 4)
    elif category == "S1_ONLY_CHANGE":
        return round(float(np.clip(s1_score * 0.85, 0.05, 0.9)), 4)
    elif category == "S2_ONLY_CHANGE":
        return round(float(np.clip(s2_score * 0.85, 0.05, 0.9)), 4)
    else:  # LOW_EVIDENCE
        base = max(s1_score, s2_score) * 0.2
        return round(float(np.clip(base, 0.0, 0.25)), 4)


def _generate_fusion_summary(
    category: str,
    s1_ev: S1Evidence | None,
    s2_ev: S2Evidence | None,
) -> str:
    """Generate an evidence-based human-readable summary without ungrounded semantic assumptions."""
    if category == "BOTH_S1_S2_CHANGE":
        s1_text = f"SAR ΔVV={s1_ev.mean_delta_vv_db:+.2f}dB, ΔVH={s1_ev.mean_delta_vh_db:+.2f}dB (Tier: {s1_ev.physical_tier})" if s1_ev else ""
        s2_text = f"Optical change={s2_ev.change_ratio*100:.1f}%, targets={s2_ev.target_count}" if s2_ev else ""
        return f"Coincident Multi-Sensor Anomaly: {s1_text} | {s2_text}"
    elif category == "S1_ONLY_CHANGE":
        s1_text = f"SAR ΔVV={s1_ev.mean_delta_vv_db:+.2f}dB, ΔVH={s1_ev.mean_delta_vh_db:+.2f}dB (Tier: {s1_ev.physical_tier})" if s1_ev else ""
        s2_status = "Optical unchanged" if s2_ev and s2_ev.valid_pixel_pct >= 15.0 else ("Optical cloud-occluded" if s2_ev else "Optical unavailable")
        return f"Radar-Dominant Anomaly: {s1_text} ({s2_status})"
    elif category == "S2_ONLY_CHANGE":
        s2_text = f"Optical spectral shift in {s2_ev.change_ratio*100:.1f}% area, {s2_ev.target_count} targets flagged" if s2_ev else ""
        s1_status = f"Radar backscatter nominal ({s1_ev.mean_combined_abs_db:.2f}dB)" if s1_ev else "Radar unavailable"
        return f"Optical-Dominant Anomaly: {s2_text} ({s1_status})"
    else:
        return "Low Evidence: Radar and optical signatures remain within nominal baseline variance."


def run_multisensor_temporal_fusion(
    sensor: str = "both",
    s1_before_date: str = "2026-03-13",
    s1_after_date: str = "2026-06-17",
    s2_before_date: str = "2026-01-18",
    s2_after_date: str = "2026-06-27",
    s1_mode: str = "physical",
    force_s2_classical: bool = True,
    max_s2_targets: int = 2,
    overlap_iou_threshold: float = 0.01,
    s1_raw_root: Path | str = DEFAULT_S1_RAW_DIR,
    s2_tiles_root: Path | str = DEFAULT_S2_TILES_DIR,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Perform sensor-aware temporal change fusion across Sentinel-1 and Sentinel-2."""
    normalized_sensor = (sensor or "both").lower().strip()
    if normalized_sensor in ("all", "multisensor"):
        normalized_sensor = "both"

    if normalized_sensor not in ("sentinel1", "sentinel2", "both"):
        raise ValueError(f"Invalid sensor '{sensor}'. Expected 'sentinel1', 'sentinel2', or 'both'.")

    out_dir = Path(output_dir) if output_dir is not None else DEFAULT_FUSION_OUTPUT_DIR / f"{normalized_sensor}_fusion"
    out_dir.mkdir(parents=True, exist_ok=True)

    s1_evidences: list[S1Evidence] = []
    s2_evidences: list[S2Evidence] = []

    # 1. Execute Sentinel-1 Temporal Analysis if requested
    if normalized_sensor in ("sentinel1", "both"):
        s1_report = run_sentinel1_physical_change_analysis(
            before_date=s1_before_date,
            after_date=s1_after_date,
            raw_root=s1_raw_root,
            output_dir=out_dir / "sentinel1",
            save_individual_tiles=False,
            save_mosaic=False,
        )
        for t_dict in s1_report.get("all_tile_metrics", []):
            ev = S1Evidence(
                tile_id=t_dict["tile_id"],
                tile_index=t_dict["tile_index"],
                tile_name=t_dict["tile_name"],
                before_date=s1_before_date,
                after_date=s1_after_date,
                mean_delta_vv_db=t_dict["mean_delta_vv_db"],
                mean_abs_delta_vv_db=t_dict["mean_abs_delta_vv_db"],
                mean_delta_vh_db=t_dict["mean_delta_vh_db"],
                mean_abs_delta_vh_db=t_dict["mean_abs_delta_vh_db"],
                mean_combined_abs_db=t_dict["mean_combined_abs_db"],
                pct_abs_delta_vv_gt_3db=t_dict["pct_abs_delta_vv_gt_3db"],
                pct_combined_gt_3db=t_dict["pct_combined_gt_3db"],
                pct_combined_gt_5db=t_dict["pct_combined_gt_5db"],
                physical_tier=t_dict["physical_change_tier"],
                geographic_bounds=t_dict["geographic_bounds"],
                crs=t_dict["crs"],
                semantic_label="Calibrated SAR Backscatter Change",
                provenance=t_dict.get("provenance", "Sentinel-1 Level-1 GRD IW Calibrated Log-Ratio (dB)"),
            )
            s1_evidences.append(ev)

    # 2. Execute Sentinel-2 Temporal Analysis if requested
    if normalized_sensor in ("sentinel2", "both"):
        s2_report = run_sentinel2_temporal_change_analysis(
            before_date=s2_before_date,
            after_date=s2_after_date,
            tiles_root=s2_tiles_root,
            force_classical=force_s2_classical,
            max_targets=max_s2_targets,
        )
        s2_evidences = s2_report.get("evidences", [])

    # 3. Fuse Evidence at Geographic Bounding Box Level
    candidates: list[MultisensorFusionCandidate] = []
    matched_s1_indices: set[int] = set()
    matched_s2_indices: set[int] = set()

    candidate_counter = 1

    if normalized_sensor == "both":
        # Cross-sensor geographic matching via spatial bounding box intersection
        for s1_ev in s1_evidences:
            for s2_ev in s2_evidences:
                inter_bbox, inter_area, iou = compute_bbox_intersection(
                    s1_ev.geographic_bounds, s2_ev.geographic_bounds
                )
                if inter_bbox is not None and (iou >= overlap_iou_threshold or inter_area > 0):
                    matched_s1_indices.add(s1_ev.tile_index)
                    matched_s2_indices.add(s2_ev.tile_index)

                    s1_sig = _is_s1_change_meaningful(s1_ev)
                    s2_sig = _is_s2_change_meaningful(s2_ev)

                    if s1_sig and s2_sig:
                        cat = "BOTH_S1_S2_CHANGE"
                    elif s1_sig and not s2_sig:
                        cat = "S1_ONLY_CHANGE"
                    elif not s1_sig and s2_sig:
                        cat = "S2_ONLY_CHANGE"
                    else:
                        cat = "LOW_EVIDENCE"

                    score = _compute_fusion_ranking_score(s1_ev, s2_ev, cat)
                    summary = _generate_fusion_summary(cat, s1_ev, s2_ev)

                    cand = MultisensorFusionCandidate(
                        candidate_id=f"candidate_{candidate_counter}",
                        geographic_bounds=inter_bbox,
                        crs="EPSG:4326",
                        sensor_coverage="multisensor",
                        fusion_category=cat,
                        s1_before_date=s1_before_date,
                        s1_after_date=s1_after_date,
                        s2_before_date=s2_before_date,
                        s2_after_date=s2_after_date,
                        s1_evidence=s1_ev.to_dict(),
                        s2_evidence=s2_ev.to_dict(),
                        spatial_overlap_iou=round(iou, 4),
                        fusion_score=score,
                        fusion_summary=summary,
                        data_quality_provenance={
                            "s1_provenance": s1_ev.provenance,
                            "s2_provenance": s2_ev.provenance,
                            "s2_qa_applied": s2_ev.qa_applied,
                            "s2_valid_pixel_pct": s2_ev.valid_pixel_pct,
                            "fusion_method": "Geospatial Bounding Box Intersection Fusion",
                        },
                    )
                    candidates.append(cand)
                    candidate_counter += 1

    # 4. Handle Unmatched / Single-Sensor Candidates
    # Unmatched S1 tiles
    for s1_ev in s1_evidences:
        if s1_ev.tile_index not in matched_s1_indices:
            s1_sig = _is_s1_change_meaningful(s1_ev)
            cat = "S1_ONLY_CHANGE" if s1_sig else "LOW_EVIDENCE"
            score = _compute_fusion_ranking_score(s1_ev, None, cat)
            summary = _generate_fusion_summary(cat, s1_ev, None)

            cand = MultisensorFusionCandidate(
                candidate_id=f"candidate_{candidate_counter}",
                geographic_bounds=s1_ev.geographic_bounds,
                crs=s1_ev.crs,
                sensor_coverage="sentinel1",
                fusion_category=cat,
                s1_before_date=s1_before_date,
                s1_after_date=s1_after_date,
                s2_before_date=None,
                s2_after_date=None,
                s1_evidence=s1_ev.to_dict(),
                s2_evidence=None,
                spatial_overlap_iou=0.0,
                fusion_score=score,
                fusion_summary=summary,
                data_quality_provenance={
                    "s1_provenance": s1_ev.provenance,
                    "s2_provenance": "None (No optical overlap or S1-only mode)",
                    "fusion_method": "Sentinel-1 Physical Decibel Engine",
                },
            )
            candidates.append(cand)
            candidate_counter += 1

    # Unmatched S2 tiles
    for s2_ev in s2_evidences:
        if s2_ev.tile_index not in matched_s2_indices:
            s2_sig = _is_s2_change_meaningful(s2_ev)
            cat = "S2_ONLY_CHANGE" if s2_sig else "LOW_EVIDENCE"
            score = _compute_fusion_ranking_score(None, s2_ev, cat)
            summary = _generate_fusion_summary(cat, None, s2_ev)

            cand = MultisensorFusionCandidate(
                candidate_id=f"candidate_{candidate_counter}",
                geographic_bounds=s2_ev.geographic_bounds,
                crs=s2_ev.crs,
                sensor_coverage="sentinel2",
                fusion_category=cat,
                s1_before_date=None,
                s1_after_date=None,
                s2_before_date=s2_before_date,
                s2_after_date=s2_after_date,
                s1_evidence=None,
                s2_evidence=s2_ev.to_dict(),
                spatial_overlap_iou=0.0,
                fusion_score=score,
                fusion_summary=summary,
                data_quality_provenance={
                    "s1_provenance": "None (No SAR overlap or S2-only mode)",
                    "s2_provenance": s2_ev.provenance,
                    "s2_qa_applied": s2_ev.qa_applied,
                    "s2_valid_pixel_pct": s2_ev.valid_pixel_pct,
                    "fusion_method": "Sentinel-2 Optical Bitemporal Detective",
                },
            )
            candidates.append(cand)
            candidate_counter += 1

    # Sort candidates by candidate ranking score descending
    candidates.sort(key=lambda c: c.fusion_score, reverse=True)

    # Category breakdown
    category_counts = {
        "BOTH_S1_S2_CHANGE": sum(1 for c in candidates if c.fusion_category == "BOTH_S1_S2_CHANGE"),
        "S1_ONLY_CHANGE": sum(1 for c in candidates if c.fusion_category == "S1_ONLY_CHANGE"),
        "S2_ONLY_CHANGE": sum(1 for c in candidates if c.fusion_category == "S2_ONLY_CHANGE"),
        "LOW_EVIDENCE": sum(1 for c in candidates if c.fusion_category == "LOW_EVIDENCE"),
    }

    fusion_report = {
        "status": "success",
        "pipeline": "Sentinel-1 + Sentinel-2 Sensor-Aware Temporal Change Fusion (Phase 2)",
        "sensor_requested": sensor,
        "sensor_executed": normalized_sensor,
        "s1_temporal_pair": {
            "before_date": s1_before_date if normalized_sensor in ("sentinel1", "both") else None,
            "after_date": s1_after_date if normalized_sensor in ("sentinel1", "both") else None,
            "tiles_processed": len(s1_evidences),
        },
        "s2_temporal_pair": {
            "before_date": s2_before_date if normalized_sensor in ("sentinel2", "both") else None,
            "after_date": s2_after_date if normalized_sensor in ("sentinel2", "both") else None,
            "tiles_processed": len(s2_evidences),
        },
        "fusion_statistics": {
            "total_candidates": len(candidates),
            "multisensor_matched_areas": len([c for c in candidates if c.sensor_coverage == "multisensor"]),
            "s1_only_candidates": len([c for c in candidates if c.sensor_coverage == "sentinel1"]),
            "s2_only_candidates": len([c for c in candidates if c.sensor_coverage == "sentinel2"]),
            "category_distribution": category_counts,
        },
        "top_ranked_candidates": [c.to_dict() for c in candidates[:10]],
        "all_candidates": [c.to_dict() for c in candidates],
        "output_directory": str(out_dir.resolve()),
        "provenance_note": (
            "Sensor evidence fusion candidate ranking system. SAR backscatter changes are labeled neutrally "
            "as calibrated radar power differences (dB) and optical changes as spectral shifts. No unsupported "
            "probabilities or unverified ground-truth classifications are claimed."
        ),
    }

    report_json_path = out_dir / "multisensor_fusion_report.json"
    report_json_path.write_text(json.dumps(fusion_report, indent=2), encoding="utf-8")

    return fusion_report
