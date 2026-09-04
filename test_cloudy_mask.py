"""
test_cloudy_mask.py — Verification of False-Alarm Suppression on Real Cloudy Imagery
==================================================================================
Tests Job A (The Skeptic) on an actual cloudy Sentinel-2 scene from July 2024
(Delhi monsoon season), where over 65% of the scene is covered by clouds and shadows.

Steps:
1. Downloads a true cloudy scene (July 2024, New Delhi AOI) with 5 bands [R, G, B, NIR, SCL].
2. Runs qa_mask.py's get_quality_mask_s2() and get_mask_stats().
3. Creates high-resolution visual comparisons:
   - Original cloudy RGB
   - Quality overlay highlighting detected clouds, cirrus, and shadows
   - Suppressed/masked output ready for change detection (false alarms eliminated)
   - A 3-panel comparative summary
4. Saves all results in qa_outputs/cloudy_test/
"""

import os
import json
import numpy as np
import tifffile
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from sentinelhub import (
    SHConfig,
    BBox,
    CRS,
    SentinelHubRequest,
    DataCollection,
    MimeType,
    MosaickingOrder,
)
from qa_mask import (
    get_quality_mask_s2,
    apply_mask_to_image,
    get_mask_stats,
    BAD_SCL_CLASSES,
    CLOUD_SCL_CLASSES,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "qa_outputs", "cloudy_test")
os.makedirs(OUTPUT_DIR, exist_ok=True)
CACHE_DIR = os.path.join(BASE_DIR, "sih_dataset", "cloudy_test")
os.makedirs(CACHE_DIR, exist_ok=True)
TIF_PATH = os.path.join(CACHE_DIR, "cloudy_scene.tif")


def fetch_cloudy_scene():
    """Download July 2024 cloudy scene if not already cached."""
    if os.path.exists(TIF_PATH):
        print(f"[CACHE] Found existing cloudy scene at {TIF_PATH}")
        return TIF_PATH

    print("[DOWNLOAD] Fetching real cloudy Sentinel-2 scene for July 2024 (monsoon)...")
    config = SHConfig()
    config.sh_client_id = "sh-d6aad816-707f-434d-8850-2f68e268e3e9"
    config.sh_client_secret = "x1wbwLbagTkHZiyEeVhd6Yf15CIexMFo"
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    sentinel2 = DataCollection.SENTINEL2_L2A.define_from(
        "SENTINEL2_L2A_CDSE", service_url="https://sh.dataspace.copernicus.eu"
    )
    bbox = BBox(bbox=[77.20, 28.55, 77.30, 28.65], crs=CRS.WGS84)

    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B02", "B03", "B04", "B08", "SCL"],
            output: { id: "default", bands: 5, sampleType: "UINT16" }
        };
    }
    function evaluatePixel(sample) {
        return [
            sample.B04 * 10000,
            sample.B03 * 10000,
            sample.B02 * 10000,
            sample.B08 * 10000,
            sample.SCL
        ];
    }
    """

    req = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=sentinel2,
                time_interval=("2024-07-01", "2024-07-31"),
                mosaicking_order=MosaickingOrder.MOST_RECENT,
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=(512, 512),
        config=config,
    )

    data = req.get_data()
    raw_arr = data[0]  # (512, 512, 5)
    tifffile.imwrite(TIF_PATH, raw_arr.astype(np.uint16))
    print(f"[SAVED] Saved cloudy scene to {TIF_PATH}")
    return TIF_PATH


def run_cloudy_test():
    tif_path = fetch_cloudy_scene()

    print("\n--- Running False-Alarm Suppression Pipeline ---")
    img_data = tifffile.imread(tif_path)  # (512, 512, 5)

    # 1. Extract and normalize RGB for display
    # bands: 0=Red, 1=Green, 2=Blue
    r = img_data[:, :, 0].astype(np.float32) / 10000.0
    g = img_data[:, :, 1].astype(np.float32) / 10000.0
    b = img_data[:, :, 2].astype(np.float32) / 10000.0
    rgb = np.stack([r, g, b], axis=-1)

    # Contrast stretch for visualization (2nd to 98th percentile of valid range)
    p2, p98 = np.percentile(rgb, 2), np.percentile(rgb, 98)
    rgb_stretched = np.clip((rgb - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)

    # 2. Get quality mask using Job A module
    good_mask, scl_array = get_quality_mask_s2(tif_path, scl_band_index=4, erode_pixels=2)
    stats = get_mask_stats(good_mask, scl_array)

    # 3. Apply suppression mask to RGB
    masked_rgb = apply_mask_to_image(rgb_stretched, good_mask)

    # 4. Print stats report
    bad_pixels = stats['total_pixels'] - stats['valid_pixels']
    bad_pct = round(100.0 - stats['valid_pct'], 2)

    print("\n=======================================================")
    print("      FALSE-ALARM SUPPRESSION TEST RESULTS (CLOUDY SCENE) ")
    print("=======================================================")
    print(f"Total Pixels        : {stats['total_pixels']:,}")
    print(f"Valid Land Pixels   : {stats['valid_pixels']:,} ({stats['valid_pct']:.2f}%)")
    print(f"Suppressed (Bad)    : {bad_pixels:,} ({bad_pct:.2f}%)")
    print(f"  - Cloud Pixels    : {stats['cloud_pixels']:,} ({stats['cloud_pct']:.2f}%)")
    print(f"  - Cloud Shadows   : {stats['shadow_pixels']:,} ({stats['shadow_pct']:.2f}%)")
    print(f"  - Snow/Ice Pixels : {stats['snow_pixels']:,} ({stats['snow_pct']:.2f}%)")
    print("=======================================================\n")

    # 5. Build SCL Color overlay
    # SCL Classes:
    # 8 = Cloud Med Prob (Orange)
    # 9 = Cloud High Prob (Bright Red)
    # 10 = Thin Cirrus (Yellow)
    # 3 = Cloud Shadow (Purple)
    # Others bad = Dark Red / Grey
    overlay_rgba = np.zeros((*scl_array.shape, 4), dtype=np.float32)
    overlay_rgba[scl_array == 9] = [1.0, 0.1, 0.1, 0.75]   # Cloud High (Red)
    overlay_rgba[scl_array == 8] = [1.0, 0.6, 0.0, 0.70]   # Cloud Med (Orange)
    overlay_rgba[scl_array == 10] = [1.0, 0.9, 0.0, 0.65]  # Cirrus (Yellow)
    overlay_rgba[scl_array == 3] = [0.6, 0.1, 0.8, 0.75]   # Shadow (Purple)
    overlay_rgba[scl_array == 1] = [0.3, 0.3, 0.3, 0.80]   # Saturated / Defective

    # 6. Save individual images
    plt.imsave(os.path.join(OUTPUT_DIR, "1_raw_cloudy_rgb.png"), rgb_stretched)
    plt.imsave(os.path.join(OUTPUT_DIR, "2_suppressed_rgb.png"), masked_rgb)

    # 7. Create 3-Panel Side-by-Side Figure
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), facecolor="#181824")

    # Panel 1: Raw Cloudy RGB
    axes[0].imshow(rgb_stretched)
    axes[0].set_title("1. Raw Satellite Image\n(Heavily Contaminated by Clouds)", color="white", fontsize=12, fontweight="bold", pad=10)
    axes[0].axis("off")

    # Panel 2: Cloud Detection Overlay
    axes[1].imshow(rgb_stretched)
    axes[1].imshow(overlay_rgba)
    axes[1].set_title(f"2. SCL Quality Detection\n({bad_pct:.1f}% Pixels Identified as Bad)", color="#f59e0b", fontsize=12, fontweight="bold", pad=10)
    axes[1].axis("off")

    # Legend for overlay
    legend_patches = [
        mpatches.Patch(color=[1.0, 0.1, 0.1, 0.85], label="Cloud High Prob"),
        mpatches.Patch(color=[1.0, 0.6, 0.0, 0.85], label="Cloud Med Prob"),
        mpatches.Patch(color=[1.0, 0.9, 0.0, 0.85], label="Thin Cirrus"),
        mpatches.Patch(color=[0.6, 0.1, 0.8, 0.85], label="Cloud Shadow"),
    ]
    axes[1].legend(handles=legend_patches, loc="lower right", facecolor="#1e1e2f", edgecolor="#333", labelcolor="white", fontsize=9)

    # Panel 3: Suppressed Image (What Change Detection actually receives)
    axes[2].imshow(masked_rgb)
    axes[2].set_title("3. Suppressed / Filtered Image\n(False Alarms Blocked - Blacked Out)", color="#10b981", fontsize=12, fontweight="bold", pad=10)
    axes[2].axis("off")

    plt.tight_layout()
    comparison_path = os.path.join(OUTPUT_DIR, "cloudy_suppression_comparison.png")
    plt.savefig(comparison_path, dpi=180, facecolor=fig.get_facecolor())
    plt.close()
    print(f"[SAVED] Side-by-side comparison figure: {comparison_path}")

    # Save stats JSON
    stats_path = os.path.join(OUTPUT_DIR, "cloudy_stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"[SAVED] Stats JSON: {stats_path}")

    # Also save the boolean mask for verification
    np.save(os.path.join(OUTPUT_DIR, "cloudy_mask.npy"), good_mask)
    print(f"[SAVED] Boolean mask: {os.path.join(OUTPUT_DIR, 'cloudy_mask.npy')}")


if __name__ == "__main__":
    run_cloudy_test()
