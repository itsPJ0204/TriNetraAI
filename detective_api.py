"""
detective_api.py — Temporal Change Detective Public API (Role 3)
================================================================
Inputs:
    - tile_t1_path: Path to Time 1 (Before) satellite tile
    - tile_t2_path: Path to Time 2 (After) satellite tile
Outputs:
    - Structured JSON report detailing:
        * WHERE change occurred (mask, bbox coordinates, surface area %)
        * WHAT the change is (Semantic AI transition & classification)
        * Filepaths to generated change mask and analyst overlay
"""

import os
import cv2
import numpy as np
from src.preprocessor import read_satellite_image
from src.classical_cd import run_classical_cd
from src.postprocessor import process_detection

NEURAL_ENGINE = None

def get_engine():
    global NEURAL_ENGINE
    if NEURAL_ENGINE is None:
        from src.neural_cd import BITInferenceEngine
        NEURAL_ENGINE = BITInferenceEngine(checkpoint_path="checkpoints/bit_levircd.pth")
    return NEURAL_ENGINE

def _extract_qa_mask(tile_path: str, external_mask=None) -> np.ndarray:
    """
    Extracts or computes Person 4's QA quality mask during ingestion.
    Returns boolean mask (True = valid ground, False = cloud/shadow/noise).
    """
    if external_mask is not None:
        if isinstance(external_mask, str) and os.path.exists(external_mask):
            if external_mask.endswith(".npy"):
                return np.load(external_mask).astype(bool)
            else:
                loaded = cv2.imread(external_mask, cv2.IMREAD_GRAYSCALE)
                return (loaded > 128)
        elif isinstance(external_mask, np.ndarray):
            return external_mask.astype(bool)

    # Attempt SCL / Optical extraction via Person 4's unified interface
    if tile_path.lower().endswith(('.tif', '.tiff')) and os.path.exists(tile_path):
        try:
            from qa_mask import get_quality_mask
            mask = get_quality_mask(sensor_type="auto", tif_path=tile_path)
            return mask
        except Exception:
            pass

    return None

def compare_tiles(
    tile_t1_path: str, 
    tile_t2_path: str, 
    force_classical: bool = False,
    output_dir: str = "outputs",
    min_area: int = 100,
    qa_mask_t1 = None,
    qa_mask_t2 = None,
    apply_qa_suppression: bool = True,
    cloud_occlusion_threshold: float = 15.0,
    max_targets: int = 5,
) -> dict:
    """
    Compares two co-registered image tiles from Time 1 and Time 2:
    - During ingestion, Person 4's QA model is triggered on-demand to suppress clouds/shadows.
    - Early-exit guard skips heavy inference if tile is heavily occluded by clouds (<15% valid ground).
    - Runs Dual-Engine BIT Transformer / Classical CV change detection.
    - Classifies WHAT the change is (Semantic AI transition matrix).
    """
    os.makedirs(output_dir, exist_ok=True)

    # Ingestion step
    t1_arr = read_satellite_image(tile_t1_path)
    t2_arr = read_satellite_image(tile_t2_path)

    if t1_arr.shape[:2] != t2_arr.shape[:2]:
        raise ValueError(f"Tile shape mismatch! T1: {t1_arr.shape}, T2: {t2_arr.shape}")

    # Person 4 QA False-Alarm Suppression triggered during bitemporal ingestion
    qa_info = {"qa_applied": False, "valid_pixel_pct": 100.0, "suppressed_pixels": 0}
    joint_qa_mask = None
    if apply_qa_suppression:
        mask1 = _extract_qa_mask(tile_t1_path, qa_mask_t1)
        mask2 = _extract_qa_mask(tile_t2_path, qa_mask_t2)

        if mask1 is not None and mask2 is not None:
            if mask1.shape != t1_arr.shape[:2]:
                mask1 = cv2.resize(mask1.astype(np.uint8), (t1_arr.shape[1], t1_arr.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
            if mask2.shape != t2_arr.shape[:2]:
                mask2 = cv2.resize(mask2.astype(np.uint8), (t2_arr.shape[1], t2_arr.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)
            joint_qa_mask = mask1 & mask2
            valid_pct = round(float(joint_qa_mask.sum()) / joint_qa_mask.size * 100.0, 2)
            qa_info = {
                "qa_applied": True,
                "valid_pixel_pct": valid_pct,
                "suppressed_pixels": int((~joint_qa_mask).sum())
            }

            # Early Exit Gate for high cloud occlusion (>85% cloud / <15% ground)
            if valid_pct < cloud_occlusion_threshold:
                base_name = os.path.splitext(os.path.basename(tile_t2_path))[0]
                empty_mask = np.zeros(t1_arr.shape[:2], dtype=np.uint8)
                mask_file = os.path.join(output_dir, f"{base_name}_mask.png")
                overlay_file = os.path.join(output_dir, f"{base_name}_overlay.png")
                cv2.imwrite(mask_file, empty_mask)
                cv2.imwrite(overlay_file, cv2.cvtColor(t2_arr, cv2.COLOR_RGB2BGR))
                return {
                    "status": "skipped_excessive_cloud_cover",
                    "mode_used": "qa_early_exit",
                    "qa_suppression": qa_info,
                    "has_change": False,
                    "change_ratio": 0.0,
                    "target_count": 0,
                    "detected_targets": [],
                    "message": f"Temporal inspection skipped: only {valid_pct}% valid ground visible due to heavy cloud occlusion.",
                    "mask_path": mask_file,
                    "overlay_path": overlay_file,
                    "raw_mask_array": empty_mask,
                    "overlay_array": t2_arr
                }

    execution_mode = "classical"
    raw_mask = None

    # 1. Neural BIT Detection
    if not force_classical:
        try:
            engine = get_engine()
            raw_mask = engine.predict(t1_arr, t2_arr)
            execution_mode = "neural_bit"
        except Exception as e:
            print(f"[Temporal Detective] Neural inference unavailable ({e}). Running classical CV engine.")

    # 2. Classical Fallback
    if raw_mask is None:
        raw_mask = run_classical_cd(t1_arr, t2_arr)
        execution_mode = "classical_absdiff"

    # Apply QA False Alarm Suppression to raw change detections
    if joint_qa_mask is not None:
        raw_mask[~joint_qa_mask] = 0

    # 3. Post-process & Classify Semantic Change ('What the change is')
    analysis = process_detection(raw_mask, t1_arr, t2_arr, min_area=min_area, max_targets=max_targets)
    
    base_name = os.path.splitext(os.path.basename(tile_t2_path))[0]
    mask_file = os.path.join(output_dir, f"{base_name}_mask.png")
    overlay_file = os.path.join(output_dir, f"{base_name}_overlay.png")

    cv2.imwrite(mask_file, analysis["clean_mask"])
    cv2.imwrite(overlay_file, cv2.cvtColor(analysis["overlay"], cv2.COLOR_RGB2BGR))

    return {
        "status": "success",
        "mode_used": execution_mode,
        "qa_suppression": qa_info,
        "has_change": analysis["has_change"],
        "change_ratio": analysis["change_ratio"],
        "target_count": analysis["target_count"],
        "detected_targets": analysis["detected_targets"],
        "mask_path": mask_file,
        "overlay_path": overlay_file,
        "raw_mask_array": analysis["clean_mask"],
        "overlay_array": analysis["overlay"]
    }
