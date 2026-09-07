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

def get_quality_mask_s2(tif_path, scl_band_index=4, erode_pixels=2):
    """
    Read a 5-band Sentinel-2 TIF (R, G, B, NIR, SCL) and return a boolean
    good-pixel mask plus the raw SCL array.

    Parameters
    ----------
    tif_path       : str  — Path to the 5-band default.tif from download.py.
    scl_band_index : int  — Band index of the SCL layer (default 4 = 5th band).
    erode_pixels   : int  — Pixels to erode around bad regions to remove cloud
                            halos. Set to 0 to disable.

    Returns
    -------
    good_mask  : np.ndarray[bool], shape (H, W)
        True  -> pixel is valid and usable for change detection.
        False -> pixel is cloud/shadow/snow/no-data — exclude from analysis.
    scl_array  : np.ndarray[uint16], shape (H, W)
        Raw SCL class values (needed for stats and debug visualisation).
    """
    img = tifffile.imread(tif_path)  # (H, W, bands) from tifffile

    # Handle both (H, W, C) and (C, H, W) layouts
    if img.ndim == 3 and img.shape[0] < img.shape[-1]:
        scl_array = img[scl_band_index].astype(np.uint16)
    else:
        scl_array = img[:, :, scl_band_index].astype(np.uint16)

    # Build bad-pixel boolean mask
    bad_mask = np.zeros(scl_array.shape, dtype=bool)
    for cls in BAD_SCL_CLASSES:
        bad_mask |= (scl_array == cls)

    # Erode the good mask to remove cloud halos bleeding into valid pixels
    good_mask = ~bad_mask
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

def get_quality_mask(sensor_type, **kwargs):
    """
    Single entry point for all sensor types. The Temporal AI module calls this
    without needing to know about SCL, QA_PIXEL, or SAR speckle filters.

    Usage
    -----
    sentinel2:
        mask = get_quality_mask("sentinel2", tif_path="path/to/default.tif")

    edge_s2cloudless (offline edge processing):
        mask = get_quality_mask("edge_s2cloudless", npy_path="path/to/..._quality_mask.npy")

    landsat (stub):
        mask = get_quality_mask("landsat", qa_pixel_path="path/to/QA_PIXEL.TIF")

    sentinel1 (stub):
        mask = get_quality_mask("sentinel1", sar_path="path/to/amplitude.tif")

    Returns
    -------
    good_mask : np.ndarray[bool], shape (H, W)
        True = usable pixel, False = exclude from change detection.
    """
    if sensor_type == "sentinel2":
        mask, _ = get_quality_mask_s2(
            tif_path=kwargs["tif_path"],
            scl_band_index=kwargs.get("scl_band_index", 4),
            erode_pixels=kwargs.get("erode_pixels", 2),
        )
        return mask

    elif sensor_type == "edge_s2cloudless":
        # Simply loads the pre-computed boolean mask from local_ingest.py
        import numpy as np
        return np.load(kwargs["npy_path"])

    elif sensor_type == "landsat":
        # TODO: implement QA_PIXEL bitmask logic for LC09 data already in d:/trinetraAI/
        raise NotImplementedError(
            "Landsat QA_PIXEL masking is a stub. "
            "Implement get_landsat_quality_mask() using the QA_PIXEL.TIF files."
        )

    elif sensor_type == "sentinel1":
        # SAR: no cloud issue — stub for speckle/outlier filter
        raise NotImplementedError(
            "Sentinel-1 SAR masking is a stub. "
            "Apply median_filter + percentile outlier clip."
        )

    else:
        raise ValueError(
            f"Unknown sensor_type '{sensor_type}'. "
            "Valid options: 'sentinel2', 'edge_s2cloudless', 'landsat', 'sentinel1'."
        )
