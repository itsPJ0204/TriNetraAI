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

def compare_tiles(
    tile_t1_path: str, 
    tile_t2_path: str, 
    force_classical: bool = False,
    output_dir: str = "outputs",
    min_area: int = 100
) -> dict:
    """
    Compares two co-registered image tiles from Time 1 and Time 2:
    Detects change locations AND identifies the semantic nature of each change.
    """
    os.makedirs(output_dir, exist_ok=True)

    t1_arr = read_satellite_image(tile_t1_path)
    t2_arr = read_satellite_image(tile_t2_path)

    if t1_arr.shape[:2] != t2_arr.shape[:2]:
        raise ValueError(f"Tile shape mismatch! T1: {t1_arr.shape}, T2: {t2_arr.shape}")

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

    # 3. Post-process & Classify Semantic Change ('What the change is')
    analysis = process_detection(raw_mask, t1_arr, t2_arr, min_area=min_area)
    
    base_name = os.path.splitext(os.path.basename(tile_t2_path))[0]
    mask_file = os.path.join(output_dir, f"{base_name}_mask.png")
    overlay_file = os.path.join(output_dir, f"{base_name}_overlay.png")

    cv2.imwrite(mask_file, analysis["clean_mask"])
    cv2.imwrite(overlay_file, cv2.cvtColor(analysis["overlay"], cv2.COLOR_RGB2BGR))

    return {
        "status": "success",
        "mode_used": execution_mode,
        "has_change": analysis["has_change"],
        "change_ratio": analysis["change_ratio"],
        "target_count": analysis["target_count"],
        "detected_targets": analysis["detected_targets"],
        "mask_path": mask_file,
        "overlay_path": overlay_file,
        "raw_mask_array": analysis["clean_mask"],
        "overlay_array": analysis["overlay"]
    }
