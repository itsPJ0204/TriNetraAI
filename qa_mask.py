"""
qa_mask.py — QA & False-Alarm Suppression (Job A)
===================================================
Sentinel-2 L2A cloud/quality masking using the SCL (Scene Classification Layer) band.

Band layout in the 5-band default.tif produced by download.py:
    Index 0 -> B04 (Red),   scaled x10000
    Index 1 -> B03 (Green), scaled x10000
    Index 2 -> B02 (Blue),  scaled x10000
    Index 3 -> B08 (NIR),   scaled x10000
    Index 4 -> SCL          (raw integer class code, NOT scaled)

SCL class reference (ESA Sentinel-2 L2A specification):
    0  = No Data / Fill
    1  = Saturated / Defective
    2  = Dark Area
    3  = Cloud Shadow
    4  = Vegetation
    5  = Bare Soil
    6  = Water
    7  = Unclassified
    8  = Cloud Medium Probability  <- BAD
    9  = Cloud High Probability    <- BAD
    10 = Thin Cirrus               <- BAD
    11 = Snow / Ice                <- BAD

Public interface
----------------
    get_quality_mask_s2(tif_path, scl_band_index=4, erode_pixels=2) -> (good_mask, scl_array)
    apply_mask_to_image(img_rgb, mask) -> np.ndarray
    get_mask_stats(mask, scl_array) -> dict
    visualise_mask(tif_path, mask, scl_array, save_dir, year_label) -> dict
    get_quality_mask(sensor_type, **kwargs) -> np.ndarray   <- unified interface
"""

import os

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy.ndimage import binary_erosion


# ---------------------------------------------------------------------------
# SCL class sets
# ---------------------------------------------------------------------------

# Pixel classes that indicate unusable data (cloud, shadow, snow, no-data)
BAD_SCL_CLASSES = frozenset({
    0,   # No Data / Fill
    1,   # Saturated / Defective
    3,   # Cloud Shadow
    8,   # Cloud (medium probability)
    9,   # Cloud (high probability)
    10,  # Thin Cirrus
    11,  # Snow / Ice
})

# Subset of BAD classes specifically caused by clouds (for stats breakdown)
CLOUD_SCL_CLASSES = frozenset({8, 9, 10})

# Snow class (separate stat)
SNOW_SCL_CLASSES = frozenset({11})


# ---------------------------------------------------------------------------
# Core: Sentinel-2 SCL masking
# ---------------------------------------------------------------------------

def get_quality_mask_s2(tif_path, scl_band_index=None, erode_pixels=None):
    """
    Read a Sentinel-2 or optical GeoTIFF and return a boolean good-pixel mask
    plus the raw SCL/quality array.
    Uses rasterio for exact spatial alignment and dynamically falls back to optical
    cloud thresholding if SCL band is absent (<5 bands).
    """
    import rasterio

    # Read using rasterio for exact CRS and coordinate alignment
    try:
        with rasterio.open(tif_path) as src:
            num_bands = src.count
            h, w = src.height, src.width

            if num_bands >= 5:
                # SCL is typically band 5 (1-based index) in 5-band products, or band 13 in 13-band products
                target_band = num_bands if (scl_band_index is None and num_bands == 5) else (scl_band_index + 1 if scl_band_index is not None else 5)
                if target_band > num_bands:
                    target_band = num_bands
                scl_array = src.read(target_band).astype(np.uint16)
            elif num_bands >= 3:
                # 3-band or 4-band optical imagery without dedicated SCL band
                # Compute optical brightness/cloud mask
                rgb = src.read([1, 2, 3]).astype(np.float32)
                # Normalize
                p2, p98 = np.percentile(rgb[rgb > 0] if np.any(rgb > 0) else rgb, (2, 98))
                norm_rgb = np.clip((rgb - p2) / (p98 - p2 + 1e-5), 0, 1)
                brightness = np.mean(norm_rgb, axis=0)
                # Cloud detection heuristic: high brightness (>0.85) with low color variance
                cloud_candidate = (brightness > 0.82) & (np.std(norm_rgb, axis=0) < 0.12)
                scl_array = np.where(cloud_candidate, 9, 4).astype(np.uint16)  # 9 = Cloud, 4 = Vegetation/Valid
            else:
                scl_array = np.full((h, w), 4, dtype=np.uint16)
    except Exception:
        # Fallback to tifffile
        img = tifffile.imread(tif_path)
        if img.ndim == 3:
            num_bands = img.shape[-1] if img.shape[0] >= img.shape[-1] else img.shape[0]
            if num_bands >= 5:
                idx = 4 if scl_band_index is None else scl_band_index
                scl_array = img[:, :, idx].astype(np.uint16) if img.shape[-1] == num_bands else img[idx].astype(np.uint16)
            else:
                scl_array = np.full(img.shape[:2], 4, dtype=np.uint16)
        else:
            scl_array = np.full(img.shape, 4, dtype=np.uint16)

    # Build bad-pixel boolean mask
    bad_mask = np.zeros(scl_array.shape, dtype=bool)
    for cls in BAD_SCL_CLASSES:
        bad_mask |= (scl_array == cls)

    # Adaptive halo erosion based on tile dimensions
    good_mask = ~bad_mask
    if erode_pixels is None:
        erode_pixels = max(2, min(scl_array.shape[0], scl_array.shape[1]) // 128)
    
    if erode_pixels > 0:
        good_mask = binary_erosion(good_mask, iterations=erode_pixels)

    return good_mask.astype(bool), scl_array


# ---------------------------------------------------------------------------
# Helpers: apply mask, compute stats, visualise
# ---------------------------------------------------------------------------

def apply_mask_to_image(img_rgb, mask):
    """
    Apply a boolean good-pixel mask to an RGB image array.
    Pixels where mask=False (bad) are set to zero (black).

    Parameters
    ----------
    img_rgb : np.ndarray, shape (H, W, 3)  float [0..1] or uint16
    mask    : np.ndarray[bool], shape (H, W)

    Returns
    -------
    masked_img : np.ndarray, same dtype and shape as img_rgb
    """
    masked = img_rgb.copy()
    masked[~mask] = 0
    return masked


def get_mask_stats(mask, scl_array):
    """
    Compute pixel-level quality statistics from the mask and raw SCL values.

    Returns
    -------
    dict with keys:
        total_pixels, valid_pixels, valid_pct,
        cloud_pixels, cloud_pct,
        snow_pixels, snow_pct,
        shadow_pixels, shadow_pct,
        nodata_pixels, nodata_pct
    """
    total = int(mask.size)
    valid = int(mask.sum())

    cloud_mask  = np.isin(scl_array, list(CLOUD_SCL_CLASSES))
    snow_mask   = np.isin(scl_array, list(SNOW_SCL_CLASSES))
    shadow_mask = (scl_array == 3)
    nodata_mask = (scl_array == 0)

    def pct(n):
        return round(float(n) / total * 100, 2)

    return {
        "total_pixels":  total,
        "valid_pixels":  valid,
        "valid_pct":     pct(valid),
        "cloud_pixels":  int(cloud_mask.sum()),
        "cloud_pct":     pct(cloud_mask.sum()),
        "snow_pixels":   int(snow_mask.sum()),
        "snow_pct":      pct(snow_mask.sum()),
        "shadow_pixels": int(shadow_mask.sum()),
        "shadow_pct":    pct(shadow_mask.sum()),
        "nodata_pixels": int(nodata_mask.sum()),
        "nodata_pct":    pct(nodata_mask.sum()),
    }


def _normalise_rgb(img):
    """Convert uint16 (H,W,C) TIF array to float [0,1] RGB via percentile stretch."""
    rgb = img[:, :, :3].astype(np.float32)
    nonzero = rgb[rgb > 0]
    if nonzero.size > 0:
        p2, p98 = np.percentile(nonzero, (2, 98))
        if p98 > p2:
            rgb = np.clip((rgb - p2) / (p98 - p2), 0, 1)
        else:
            rgb = np.clip(rgb / 10000.0, 0, 1)
    else:
        rgb = np.zeros_like(rgb)
    return rgb


def visualise_mask(tif_path, mask, scl_array, save_dir, year_label=""):
    """
    Save two output images for a single year's data:
      1. cloud_mask_<year_label>.png  — side-by-side RGB + colour-coded overlay
      2. masked_rgb_<year_label>.png  — true-colour with bad pixels blacked out

    Returns dict of {"overlay_path": ..., "masked_path": ...}
    """
    os.makedirs(save_dir, exist_ok=True)
    img = tifffile.imread(tif_path)
    rgb = _normalise_rgb(img)

    # --- Build colour-coded overlay ---
    overlay = rgb.copy()
    cloud_mask  = np.isin(scl_array, list(CLOUD_SCL_CLASSES))
    snow_mask   = np.isin(scl_array, list(SNOW_SCL_CLASSES))
    shadow_mask = (scl_array == 3)
    bad_other   = (~mask) & ~cloud_mask & ~snow_mask & ~shadow_mask

    overlay[cloud_mask]  = [1.0, 0.20, 0.20]  # red    -> cloud
    overlay[snow_mask]   = [0.4, 0.70, 1.00]  # blue   -> snow/ice
    overlay[shadow_mask] = [0.6, 0.30, 0.80]  # purple -> shadow
    overlay[bad_other]   = [1.0, 0.60, 0.00]  # orange -> no-data / other bad

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    axes[0].imshow(rgb)
    axes[0].set_title(f"True Colour — {year_label}", fontsize=12, fontweight="bold")
    axes[0].axis("off")

    axes[1].imshow(overlay)
    axes[1].set_title(f"QA Mask Overlay — {year_label}", fontsize=12, fontweight="bold")
    axes[1].axis("off")

    legend_patches = [
        mpatches.Patch(color=(0.25, 0.75, 0.25), label="Valid pixel"),
        mpatches.Patch(color=(1.0, 0.20, 0.20),  label="Cloud (SCL 8/9/10)"),
        mpatches.Patch(color=(0.40, 0.70, 1.00), label="Snow / Ice (SCL 11)"),
        mpatches.Patch(color=(0.60, 0.30, 0.80), label="Cloud Shadow (SCL 3)"),
        mpatches.Patch(color=(1.0, 0.60, 0.00),  label="No Data / Other Bad"),
    ]
    axes[1].legend(handles=legend_patches, loc="lower left", fontsize=8,
                   framealpha=0.85, fancybox=True)

    overlay_path = os.path.join(save_dir, f"cloud_mask_{year_label}.png")
    plt.tight_layout()
    plt.savefig(overlay_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Masked true-colour ---
    masked_rgb = apply_mask_to_image(rgb, mask)
    fig2, ax2 = plt.subplots(figsize=(7, 7))
    ax2.imshow(masked_rgb)
    ax2.set_title(
        f"Valid Pixels Only — {year_label}\n(bad pixels blacked out)",
        fontsize=11, fontweight="bold"
    )
    ax2.axis("off")
    masked_path = os.path.join(save_dir, f"masked_rgb_{year_label}.png")
    plt.tight_layout()
    plt.savefig(masked_path, dpi=150, bbox_inches="tight")
    plt.close(fig2)

    print(f"  Saved overlay : {overlay_path}")
    print(f"  Saved masked  : {masked_path}")
    return {"overlay_path": overlay_path, "masked_path": masked_path}


# ---------------------------------------------------------------------------
# Unified sensor-agnostic interface (used by Temporal AI teammate)
# ---------------------------------------------------------------------------

def get_quality_mask(sensor_type="auto", **kwargs):
    """
    Unified sensor-agnostic entry point.
    Supports auto-detection, Sentinel-2, edge_s2cloudless (.npy), and Landsat.
    """
    tif_path = kwargs.get("tif_path", "")
    npy_path = kwargs.get("npy_path", "")

    if sensor_type == "auto":
        if npy_path and str(npy_path).endswith(".npy"):
            sensor_type = "edge_s2cloudless"
        elif tif_path:
            sensor_type = "sentinel2"
        else:
            sensor_type = "sentinel2"

    if sensor_type == "sentinel2":
        mask, _ = get_quality_mask_s2(
            tif_path=kwargs["tif_path"],
            scl_band_index=kwargs.get("scl_band_index", None),
            erode_pixels=kwargs.get("erode_pixels", None),
        )
        return mask

    elif sensor_type == "edge_s2cloudless":
        return np.load(kwargs["npy_path"]).astype(bool)

    elif sensor_type == "landsat":
        raise NotImplementedError("Landsat QA_PIXEL masking is a stub.")

    elif sensor_type == "sentinel1":
        raise NotImplementedError("Sentinel-1 SAR masking is a stub.")

    else:
        raise ValueError(f"Unknown sensor_type '{sensor_type}'.")
