"""
local_ingest.py — Pure offline edge inference pipeline
======================================================
This script runs entirely offline on the edge device.
It scans the local `edge_data/raw_input` folder for new 13-band TIFF files
and generates accurate cloud masks using the `s2cloudless` ML model.
It then applies the masks to the RGB bands and saves the cleaned images.
"""

import os
import tifffile
import numpy as np
import matplotlib.pyplot as plt
from s2cloudless import S2PixelCloudDetector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "edge_data", "raw_input")
OUT_DIR = os.path.join(BASE_DIR, "edge_data", "processed_output")
os.makedirs(OUT_DIR, exist_ok=True)


def process_local_imagery():
    print("==================================================")
    print("   EDGE NODE: STARTING OFFLINE LOCAL INGESTION")
    print("==================================================")

    # 1. Initialize the offline s2cloudless model
    print("[INIT] Loading s2cloudless machine learning model into memory...")
    cloud_detector = S2PixelCloudDetector(
        threshold=0.4,       # probability threshold
        average_over=4,      # average probability over 4x4 patches
        dilation_size=2,     # dilate by 2 pixels to catch cloud halos
        all_bands=False      # We will manually pass the 10 exact bands required
    )

    # 2. Scan for raw imagery on local drive
    valid_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".tif")]
    if not valid_files:
        print("[IDLE] No new images found in raw_input/")
        return

    for filename in valid_files:
        tif_path = os.path.join(RAW_DIR, filename)
        print(f"\n[PROCESSING] Ingesting {filename}...")

        # 3. Read image and scale to [0.0, 1.0] reflectance
        img_raw = tifffile.imread(tif_path)  # Shape: (512, 512, 13)
        
        # Apply Sentinel-2 L1C processing baseline 04.00 offset (-1000)
        img_float = img_raw.astype(np.float32) - 1000.0
        img_float[img_float < 0] = 0.0
        img_reflectance = img_float / 10000.0
        
        # s2cloudless requires bands: 1, 2, 4, 5, 8, 8A, 9, 10, 11, 12
        # Corresponding 13-band indices: 0, 1, 3, 4, 7, 8, 9, 10, 11, 12
        band_indices = [0, 1, 3, 4, 7, 8, 9, 10, 11, 12]
        img_10_band = img_reflectance[:, :, band_indices]

        # Prepare for model. Model expects shape (N, H, W, 10)
        img_batch = np.expand_dims(img_10_band, axis=0)

        # 4. Run offline inference
        print("  -> Running ML cloud detection (CPU)...")
        # get_cloud_masks returns binary mask: 1=cloud, 0=clear
        cloud_masks = cloud_detector.get_cloud_masks(img_batch) 
        
        binary_mask = cloud_masks[0]  # Shape: (512, 512)
        good_mask = (binary_mask == 0) # True where clear sky

        # Compute stats
        total_pixels = good_mask.size
        valid_pixels = good_mask.sum()
        cloud_pixels = total_pixels - valid_pixels
        cloud_pct = (cloud_pixels / total_pixels) * 100
        print(f"  -> Detected {cloud_pixels:,} cloud pixels ({cloud_pct:.1f}%)")

        # 5. Extract RGB for visualization (Indices: Red=3, Green=2, Blue=1)
        r = img_reflectance[:, :, 3]
        g = img_reflectance[:, :, 2]
        b = img_reflectance[:, :, 1]
        rgb = np.stack([r, g, b], axis=-1)

        # Contrast stretch
        p2, p98 = np.percentile(rgb[rgb > 0], (2, 98))
        rgb_stretched = np.clip((rgb - p2) / (p98 - p2 + 1e-6), 0.0, 1.0)

        # Apply suppression
        masked_rgb = rgb_stretched.copy()
        masked_rgb[~good_mask] = 0.0

        # 6. Save outputs
        base_name = os.path.splitext(filename)[0]
        
        # Save raw rgb
        raw_rgb_path = os.path.join(OUT_DIR, f"{base_name}_raw_rgb.png")
        plt.imsave(raw_rgb_path, rgb_stretched)
        
        # Save masked rgb
        suppressed_path = os.path.join(OUT_DIR, f"{base_name}_suppressed_rgb.png")
        plt.imsave(suppressed_path, masked_rgb)

        # Save numpy boolean mask for downstream change detection
        npy_path = os.path.join(OUT_DIR, f"{base_name}_quality_mask.npy")
        np.save(npy_path, good_mask)

        print(f"  -> Saved cleaned RGB: {suppressed_path}")
        print(f"  -> Saved boolean mask: {npy_path}")

    print("\n[SUCCESS] Edge processing batch complete.")


if __name__ == "__main__":
    process_local_imagery()
