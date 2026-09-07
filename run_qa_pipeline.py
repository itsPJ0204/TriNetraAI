"""
run_qa_pipeline.py — Job A Runner: Cloud Mask Pipeline
=======================================================
Processes all three yearly Sentinel-2 composites and outputs:

    qa_outputs/
    |-- cloud_mask_2024.png     <- RGB + colour-coded QA overlay
    |-- masked_rgb_2024.png     <- true-colour with bad pixels blacked out
    |-- cloud_mask_2024.npy     <- raw boolean mask array (H, W) for downstream use
    |-- cloud_stats_2024.json   <- pixel quality statistics
    |-- cloud_mask_2025.png  ...
    |-- ... (same for 2025 and 2026)

Usage:
    python run_qa_pipeline.py

Requirements:
    - sih_dataset/year_{1,2,3}/default.tif must be 5-band TIFs (run download.py first)
    - pip install tifffile scipy matplotlib numpy
"""

import json
import os
import numpy as np

from qa_mask import get_quality_mask_s2, get_mask_stats, visualise_mask

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "sih_dataset")
OUTPUT_DIR  = os.path.join(BASE_DIR, "qa_outputs")

YEARS = [
    (1, "2024"),
    (2, "2025"),
    (3, "2026"),
]

SCL_BAND_INDEX = 4   # band index 4 = SCL in our 5-band default.tif
ERODE_PIXELS   = 2   # erosion iterations to remove cloud halos

# ---------------------------------------------------------------------------
# Sanity check thresholds (will warn but not abort)
# ---------------------------------------------------------------------------
WARN_IF_VALID_BELOW = 20.0   # < 20% valid pixels = nearly fully covered scene
NOTE_IF_VALID_ABOVE = 99.0   # > 99% = cloud-free composite (good, worth noting)


def run_pipeline():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_stats = {}

    print("=" * 60)
    print("  Sentinel-2 QA & Cloud Mask Pipeline (Job A)")
    print("=" * 60)

    for year_idx, year_label in YEARS:
        tif_path = os.path.join(DATASET_DIR, f"year_{year_idx}", "default.tif")

        if not os.path.exists(tif_path):
            print(f"\n[SKIP] {tif_path} not found — run download.py first.")
            continue

        print(f"\n--- Year {year_label} ---")
        print(f"  Input : {tif_path}")

        # 1. Generate mask
        good_mask, scl_array = get_quality_mask_s2(
            tif_path=tif_path,
            scl_band_index=SCL_BAND_INDEX,
            erode_pixels=ERODE_PIXELS,
        )

        # 2. Compute statistics
        stats = get_mask_stats(good_mask, scl_array)
        stats["year"] = year_label
        stats["tif_path"] = tif_path
        all_stats[year_label] = stats

        print(f"  Valid pixels : {stats['valid_pct']}%  "
              f"| Cloud: {stats['cloud_pct']}%  "
              f"| Snow: {stats['snow_pct']}%  "
              f"| Shadow: {stats['shadow_pct']}%")

        # Sanity checks
        if stats["valid_pct"] < WARN_IF_VALID_BELOW:
            print(f"  [WARNING] Only {stats['valid_pct']}% valid pixels — scene is nearly fully covered!")
        elif stats["valid_pct"] > NOTE_IF_VALID_ABOVE:
            print(f"  [NOTE] {stats['valid_pct']}% valid — composite is essentially cloud-free.")

        # 3. Save raw mask array (for Temporal AI teammate to consume)
        mask_npy_path = os.path.join(OUTPUT_DIR, f"cloud_mask_{year_label}.npy")
        np.save(mask_npy_path, good_mask)
        print(f"  Saved mask   : {mask_npy_path}  (shape={good_mask.shape}, dtype=bool)")

        # 4. Save statistics JSON
        stats_path = os.path.join(OUTPUT_DIR, f"cloud_stats_{year_label}.json")
        with open(stats_path, "w") as f:
            json.dump(stats, f, indent=2)
        print(f"  Saved stats  : {stats_path}")

        # 5. Generate and save visualisations
        visualise_mask(
            tif_path=tif_path,
            mask=good_mask,
            scl_array=scl_array,
            save_dir=OUTPUT_DIR,
            year_label=year_label,
        )

    # 6. Summary across all years
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  {'Year':<6}  {'Valid%':>7}  {'Cloud%':>7}  {'Snow%':>7}  {'Shadow%':>8}")
    print(f"  {'-'*6}  {'-'*7}  {'-'*7}  {'-'*7}  {'-'*8}")
    for year_label, s in all_stats.items():
        print(f"  {year_label:<6}  {s['valid_pct']:>7.2f}  {s['cloud_pct']:>7.2f}  "
              f"{s['snow_pct']:>7.2f}  {s['shadow_pct']:>8.2f}")

    # Save combined summary
    summary_path = os.path.join(OUTPUT_DIR, "qa_summary.json")
    with open(summary_path, "w") as f:
        json.dump(all_stats, f, indent=2)
    print(f"\n  Combined summary saved: {summary_path}")
    print(f"\n  All outputs in: {OUTPUT_DIR}")
    print("\nPipeline complete!")


if __name__ == "__main__":
    run_pipeline()
